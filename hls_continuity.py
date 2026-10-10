"""Ordered CHZZK HLS delivery. Network failures must never become skipped media.

The plugin supplies API-advertised manifests; this module never constructs CDN
hosts. A writer owns the output cursor, independently of the worker's queue.
"""

import hashlib
import json
import queue
import re
import struct
import sys
import threading
import time
from collections import OrderedDict
from concurrent.futures import CancelledError, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlparse

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from streamlink.exceptions import StreamError
from streamlink.stream.hls import HLSStreamReader, HLSStreamWorker, parse_m3u8
from streamlink.stream.hls.hls import HLSStreamWriter
from recording_continuity import EVENT_PREFIX


HEDGE_DELAY = 2.0
RECOVERY_TIMEOUT = 90.0
API_REFRESH_INTERVAL = 30.0
RECOVERY_REFRESH_INTERVAL = 5.0
TIME_TOLERANCE = 0.02


class Unavailable(StreamError):
    """A required segment could not be delivered."""

    def __init__(self, message, status=None, category="unavailable"):
        super().__init__(message)
        self.status = status
        self.category = category


class BroadcastEnded(Unavailable):
    pass


class BroadcastChanged(Unavailable):
    pass


def timestamp(value):
    return value.isoformat() if value is not None else None


def parse_timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("A timezone is required")
    return result


def quality_from_url(url):
    for part in urlparse(url).path.split("/"):
        if re.fullmatch(r"\d+p(?:\d+)?", part):
            return part
    return None


def validate_media(data, is_map=False):
    """Reject empty/truncated TS or ISO-BMFF before exposing any bytes."""
    if not data:
        raise Unavailable("Empty media response", category="invalid_media")
    if data[0] == 0x47 and not is_map:
        if len(data) % 188 or any(data[i] != 0x47 for i in range(0, len(data), 188)):
            raise Unavailable("Incomplete transport stream", category="invalid_media")
        return
    offset, boxes = 0, set()
    while offset < len(data):
        if len(data) - offset < 8:
            raise Unavailable("Incomplete MP4 box header", category="invalid_media")
        size, kind = struct.unpack_from(">I4s", data, offset)
        header = 8
        if size == 1:
            if len(data) - offset < 16:
                raise Unavailable("Incomplete MP4 extended size", category="invalid_media")
            size = struct.unpack_from(">Q", data, offset + 8)[0]
            header = 16
        elif size == 0:
            size = len(data) - offset
        if size < header or offset + size > len(data):
            raise Unavailable("Incomplete MP4 box", category="invalid_media")
        boxes.add(kind)
        offset += size
    required = {b"moov"} if is_map else {b"moof", b"mdat"}
    if not required <= boxes:
        raise Unavailable("Unexpected media container", category="invalid_media")


@dataclass
class Manifest:
    url: str = field(repr=False)
    history: bool = False
    playlist: object = field(default=None, repr=False)
    loaded_at: float = 0.0


@dataclass
class LocatedSegment:
    segment: object = field(repr=False)
    manifest: Manifest = field(repr=False)
    live_id: int
    rendition: str

    def __getattr__(self, name):
        return getattr(self.segment, name)

    def __repr__(self):
        return f"<CHZZK segment {self.num} at {timestamp(self.date)}>"

    @property
    def end(self):
        return self.date + timedelta(seconds=self.duration) if self.date else None


@dataclass
class Download:
    located: LocatedSegment
    initialization: bytes
    media: bytes


class ContinuitySource:
    """Small manifest pool refreshed from the API, with serialized discovery."""

    def __init__(self, stream, provider, live_id, paths, lookback=0, resume=None,
                 time_machine_active=None):
        self.stream = stream
        self.session = stream.session
        self.provider = provider
        self.live_id = live_id
        self.rendition = quality_from_url(stream._url) or stream.name or "unknown"
        self.lookback = lookback
        self.resume = resume
        # A UI feature flag is a hint, not proof that advertised CDN media is
        # accessible. Actual dated manifests and successful downloads decide.
        self.time_machine_active = time_machine_active
        self.stop = threading.Event()
        self.lock = threading.RLock()
        self.event_lock = threading.Lock()
        self.diagnostic_lock = threading.Lock()
        self.diagnostics = OrderedDict()
        self.last_refresh = time.monotonic()
        self.last_discovery = 0.0
        self.paths = paths
        self.manifests = OrderedDict()
        self.primary = self.add(stream._url, False)
        self.ended = False
        self.changed = False
        self.recovering = False
        self.last_progress = time.monotonic()
        self.terminal = None

    def emit(self, kind, **fields):
        event = dict(version=1, kind=kind, live_id=self.live_id,
                     rendition=self.rendition, **fields)
        with self.event_lock:
            sys.stderr.write(EVENT_PREFIX + json.dumps(event) + "\n")
            sys.stderr.flush()

    def report_failure(self, stage, role, error, located=None):
        """Bounded, URL-free diagnostics; never serialize request exceptions."""
        if self.stop.is_set() or isinstance(error, (BroadcastEnded, BroadcastChanged)):
            return
        status = getattr(error, "status", None)
        category = getattr(error, "category", "network")
        sequence = located.num if located is not None else None
        at = timestamp(located.date) if located is not None else None
        key = (stage, role, category, status, sequence, at)
        with self.diagnostic_lock:
            if key in self.diagnostics:
                return
            self.diagnostics[key] = None
            while len(self.diagnostics) > 128:
                self.diagnostics.popitem(last=False)
        self.emit("diagnostic", stage=stage, role=role, category=category,
                  status=status, sequence=sequence, at=at)

    def add(self, url, history):
        parsed = urlparse(url)
        key = (parsed.netloc, parsed.path, history)
        manifest = self.manifests.get(key)
        if manifest is None or manifest.url != url:
            manifest = Manifest(url, history)
            self.manifests[key] = manifest
        self.manifests.move_to_end(key)
        # Retain two advertised CDN origins per role, with at most two paths
        # per origin. A second path must not evict the other CDN's fallback.
        same_role = [k for k in self.manifests if k[2] == history]
        hosts = list(dict.fromkeys(k[0] for k in reversed(same_role)))[:2]
        same_host = [k for k in same_role if k[0] == parsed.netloc]
        for old in [k for k in same_role if k[0] not in hosts] + same_host[:-2]:
            self.manifests.pop(old)
        return manifest

    def request_params(self):
        params = dict(self.stream.args)
        for name in ("url", "exception", "stream", "timeout", "retries"):
            params.pop(name, None)
        return params

    def playlist(self, manifest, force=False):
        with self.lock:
            if (not force and manifest.playlist is not None
                    and time.monotonic() - manifest.loaded_at < 2):
                return manifest.playlist
            if self.stop.is_set():
                raise Unavailable("Stopped")
            try:
                with self.session.http.get(
                    manifest.url, timeout=(5, 5), retries=0,
                    exception=StreamError, **self.request_params(),
                ) as response:
                    response.encoding = "utf-8"
                    playlist = parse_m3u8(response, parser=self.stream.__parser__)
                if playlist.is_master:
                    matches = [p for p in playlist.playlists if p.stream_info
                               and quality_from_url(p.uri) == self.rendition]
                    if not matches:
                        raise Unavailable("Rendition unavailable")
                    child = self.add(matches[0].uri, manifest.history)
                    return self.playlist(child, force)
                if playlist.iframes_only or not playlist.segments:
                    raise Unavailable("No complete segments")
                manifest.playlist = playlist
                manifest.loaded_at = time.monotonic()
                return playlist
            except (StreamError, ValueError) as error:
                # Do not include signed URLs embedded in requests exceptions.
                response = getattr(getattr(error, "err", error), "response", None)
                status = getattr(response, "status_code", None)
                failure = error if isinstance(error, Unavailable) else Unavailable(
                    "Manifest request failed", status, "http" if status else "network")
                self.report_failure("manifest", "history" if manifest.history else "current", failure)
                if status in (401, 403):
                    self.discover(force=True)
                if isinstance(error, Unavailable):
                    raise
                raise failure from None

    def discover(self, force=False):
        with self.lock:
            if self.stop.is_set():
                return
            if force or time.monotonic() - self.last_refresh >= API_REFRESH_INTERVAL:
                self.last_refresh = time.monotonic()
                try:
                    snapshot = self.provider()
                except (StreamError, ValueError) as error:
                    self.report_failure("api", "current", error)
                    raise
                if snapshot is None:
                    self.ended = True
                    raise BroadcastEnded("Broadcast ended")
                live_id, paths, *flags = snapshot
                self.time_machine_active = flags[0] if flags else None
                if live_id != self.live_id:
                    self.changed = True
                    raise BroadcastChanged("Broadcast changed")
                self.paths = paths
            if not force and time.monotonic() - self.last_discovery < API_REFRESH_INTERVAL:
                return
            self.last_discovery = time.monotonic()
            for path, history in self.paths:
                try:
                    with self.session.http.get(
                        path, timeout=(5, 5), retries=0, exception=StreamError,
                        **self.request_params(),
                    ) as response:
                        response.encoding = "utf-8"
                        playlist = parse_m3u8(response, parser=self.stream.__parser__)
                    if playlist.is_master:
                        matches = [p for p in playlist.playlists if p.stream_info
                                   and quality_from_url(p.uri) == self.rendition]
                        if not matches:
                            continue
                        url = matches[0].uri
                    elif quality_from_url(path) == self.rendition:
                        url = path
                    else:
                        continue
                    candidate = self.add(url, history)
                    if not history:
                        self.primary = candidate
                        self.stream._url = candidate.url
                except (StreamError, ValueError) as error:
                    response = getattr(getattr(error, "err", error), "response", None)
                    status = getattr(response, "status_code", None)
                    self.report_failure("manifest", "history" if history else "current",
                                        Unavailable("Discovery failed", status,
                                                    "http" if status else "network"))
                    continue

    def candidates(self, refresh=False):
        with self.lock:
            if (refresh or time.monotonic() - self.last_refresh >= API_REFRESH_INTERVAL
                    or len(self.manifests) == 1):
                # Non-authentication failures may refresh discovery sooner,
                # without flooding the API on every failed media retry.
                self.discover(force=refresh and
                              time.monotonic() - self.last_refresh >= RECOVERY_REFRESH_INTERVAL)
            result = []
            for manifest in list(self.manifests.values()):
                try:
                    playlist = self.playlist(manifest, force=refresh)
                    result.append((manifest, playlist))
                except Unavailable:
                    continue
            return result

    def locate(self, segment, manifest):
        return LocatedSegment(segment, manifest, self.live_id, self.rendition)

    @staticmethod
    def matches(left, right):
        if left.live_id != right.live_id or left.rendition != right.rendition:
            return False
        if left.date is None or right.date is None:
            return left.manifest.url == right.manifest.url and left.num == right.num
        return (abs((left.date - right.date).total_seconds()) <= TIME_TOLERANCE
                and abs(left.duration - right.duration) <= TIME_TOLERANCE
                and left.discontinuity == right.discontinuity)

    def alternatives(self, target, refresh=False):
        candidates = self.candidates(refresh)
        candidates.sort(key=lambda item: urlparse(item[0].url).netloc ==
                        urlparse(target.manifest.url).netloc)
        for manifest, playlist in candidates:
            for segment in playlist.segments:
                located = self.locate(segment, manifest)
                if segment.uri != target.uri and self.matches(target, located):
                    yield located

    def between(self, previous, following, refresh=False):
        """Yield the surviving prefix before a hole, preserving valid media."""
        if self.ended:
            raise BroadcastEnded("Broadcast ended")
        if self.changed:
            raise BroadcastChanged("Broadcast changed")
        candidates = self.candidates(refresh)
        if previous.end is None or following.date is None:
            segments = [self.locate(s, m) for m, p in candidates
                        if m.url == previous.manifest.url == following.manifest.url
                        for s in p.segments
                        if previous.num < s.num < following.num]
            segments.sort(key=lambda s: s.num)
            expected = previous.num + 1
            for segment in segments:
                if segment.num < expected:
                    continue
                if segment.num != expected:
                    raise Unavailable("Sequence no longer available")
                yield segment
                expected += 1
            if expected != following.num:
                raise Unavailable("Sequence no longer available")
            return
        position = previous.end
        while (following.date - position).total_seconds() > TIME_TOLERANCE:
            found = next((self.locate(s, m) for m, p in candidates for s in p.segments
                          if s.date is not None
                          and abs((s.date - position).total_seconds()) <= TIME_TOLERANCE
                          and s.duration > 0), None)
            if found is None or found.end > following.date + timedelta(seconds=TIME_TOLERANCE):
                # A sliding/temporarily unavailable manifest is not proof that
                # every advertised CDN has permanently lost this interval.
                raise Unavailable("Required interval no longer available")
            yield found
            position = found.end


class ChzzkContinuityWorker(HLSStreamWorker):
    def check_sequence_gap(self, segment):
        # The writer checks delivered media, rather than the queue's sequence.
        pass

    def iter_segments(self):
        source = self.stream.continuity
        last = None
        while not self.closed and not source.stop.is_set():
            try:
                if last is None:
                    source.discover()
                if time.monotonic() - source.last_refresh >= API_REFRESH_INTERVAL:
                    source.discover()
                manifest = source.primary
                playlist = source.playlist(manifest, force=True)
                segments = [source.locate(s, manifest) for s in playlist.segments]
                if last is None:
                    resume = source.resume
                    if resume and resume["live_id"] == source.live_id and resume["rendition"] == source.rendition:
                        cutoff = parse_timestamp(resume["from"])
                        available = [source.locate(s, m) for m, p in source.candidates()
                                     for s in p.segments if s.date and
                                     s.date >= cutoff - timedelta(seconds=TIME_TOLERANCE)]
                        segments = sorted(available, key=lambda s: s.date)
                        if not segments:
                            source.terminal = ("gap", "resume_unavailable")
                            return
                        if abs((segments[0].date - cutoff).total_seconds()) > TIME_TOLERANCE:
                            if not resume.get("after_gap", False):
                                source.terminal = ("gap", "resume_unavailable")
                                return
                            source.emit("gap", reason="resume_unavailable",
                                        **{"from": timestamp(cutoff), "to": timestamp(segments[0].date)})
                    elif source.lookback and segments[-1].end:
                        cutoff = segments[-1].end - timedelta(seconds=source.lookback)
                        candidates = source.candidates()
                        has_history = any(m.history and any(s.date for s in p.segments)
                                          for m, p in candidates)
                        if has_history:
                            available = [source.locate(s, m) for m, p in candidates
                                         for s in p.segments if s.date and s.date >= cutoff]
                            if available:
                                segments = sorted(available, key=lambda s: s.date)
                            # A manifest alone is not proof that its oldest media
                            # remains accessible to this API caller.
                            segments = self.writer.accessible_start(segments, playlist, manifest)
                        else:
                            segments = segments[-max(1, int(self.live_edge)):]
                    elif self.hls_live_restart or playlist.is_endlist:
                        pass
                    else:
                        segments = segments[-max(1, int(self.live_edge)):]
                    if not segments:
                        raise Unavailable("No start position")
                    available_seconds = ((segments[-1].end - segments[0].date).total_seconds()
                                         if segments[-1].end and segments[0].date else 0)
                    source.emit("start", at=timestamp(segments[0].date),
                                requested_seconds=source.lookback,
                                available_seconds=round(available_seconds, 3),
                                time_machine_active=source.time_machine_active)
                queued = False
                for segment in segments:
                    if last:
                        if last.end and segment.date:
                            if (segment.date - last.end).total_seconds() < -TIME_TOLERANCE:
                                continue
                        elif (segment.manifest.url == last.manifest.url
                              and segment.num <= last.num):
                            continue
                    queued |= yield segment
                    last = segment
                if playlist.is_endlist:
                    return
                if not queued and time.monotonic() - source.last_progress >= RECOVERY_TIMEOUT:
                    # Check API before interpreting a stopped playlist as a gap.
                    source.discover(force=True)
                    source.terminal = ("gap", "playlist_stalled")
                    return
                if not self.wait(min(2, playlist.targetduration or 2)):
                    return
            except BroadcastEnded:
                return
            except BroadcastChanged:
                source.terminal = ("boundary", "broadcast_changed")
                return
            except (StreamError, ValueError):
                if time.monotonic() - source.last_progress >= RECOVERY_TIMEOUT:
                    source.terminal = ("gap", "playlist_unavailable")
                    return
                source.recovering = True
                if not self.wait(1):
                    return


class ChzzkContinuityWriter(HLSStreamWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = self.stream.continuity
        self.requests = ThreadPoolExecutor(max_workers=2 * self.threads,
                                          thread_name_prefix="chzzk-request")
        self.request_slots = threading.BoundedSemaphore(2 * self.threads)
        self.lookups = ThreadPoolExecutor(max_workers=2, thread_name_prefix="chzzk-manifest")
        self.lookup_slots = threading.BoundedSemaphore(self.threads + 1)
        self.refresh_lock = threading.Lock()
        self.refresh_future = None
        self.cache_lock = threading.Lock()
        self.maps = OrderedDict()
        self.keys = OrderedDict()
        self.previous = None
        self.initialization = None
        self.failed = False
        self.start_download = None

    def accessible_start(self, segments, ordinary, manifest):
        # For gone old media (404/410), find the surviving tail within 30s.
        unique = {}
        for item in segments:
            unique.setdefault(item.date, item)
        ordered = list(unique.values())
        deadline = time.monotonic() + min(30, RECOVERY_TIMEOUT)
        low, high, found = 0, len(ordered) - 1, None
        index = 0
        while low <= high and time.monotonic() < deadline and not self.source.stop.is_set():
            target = ordered[index]
            try:
                result = self.download(target, target)
                found = (index, result)
                if index == 0:
                    break
                high = index - 1
            except Unavailable as error:
                if error.status not in (404, 410):
                    break
                low = index + 1
            index = (low + high) // 2
        if found:
            index, result = found
            self.start_download = result
            return ordered[index:]
        # Optional history must not prevent a live recording.
        return [self.source.locate(s, manifest) for s in ordinary.segments[-max(1, int(self.reader.worker.live_edge)):]]

    def put(self, segment):
        if not self.closed and not self.failed:
            if segment is None:
                self.queue(None, None)
            else:
                self.queue(segment, self.executor.submit(self.fetch, segment))

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.source.stop.set()
        self._wait.set()
        self.reader.worker.close()
        # RingBuffer.close wakes readers but leaves its remaining bytes readable.
        self.reader.buffer.close()
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.requests.shutdown(wait=False, cancel_futures=True)
        self.lookups.shutdown(wait=False, cancel_futures=True)

    def http_bytes(self, uri, byterange=None):
        if self.source.stop.is_set():
            raise Unavailable("Stopped")
        params = self.source.request_params()
        headers = dict(params.pop("headers", {}))
        if byterange:
            if byterange.offset is None:
                raise Unavailable("Implicit byte range unsupported")
            headers["Range"] = f"bytes={byterange.offset}-{byterange.offset + byterange.range - 1}"
        deadline = time.monotonic() + self.timeout
        try:
            with self.session.http.get(
                uri, headers=headers, stream=True, timeout=(min(5, self.timeout), min(2, self.timeout)),
                retries=0, exception=StreamError, **params,
            ) as response:
                if byterange and response.status_code != 206:
                    raise Unavailable("Byte range not honored", category="truncated")
                data = bytearray()
                # read1 returns currently received bytes instead of waiting to
                # fill a chunk. Even a trickling body cannot postpone deadline
                # and stop checks until an entire 64 KiB has arrived.
                while chunk := response.raw.read1(65536, decode_content=True):
                    if self.source.stop.is_set() or time.monotonic() > deadline:
                        raise Unavailable("Media request interrupted", category="timeout")
                    data.extend(chunk)
                length = response.headers.get("Content-Length")
                if length and not response.headers.get("Content-Encoding") and len(data) != int(length):
                    raise Unavailable("Incomplete HTTP response", category="truncated")
                if byterange and len(data) != byterange.range:
                    raise Unavailable("Incomplete byte range", category="truncated")
                return bytes(data)
        except Exception as error:
            status = getattr(getattr(error, "err", error), "response", None)
            if status is not None and status.status_code in (401, 403):
                raise Unavailable("token", status.status_code, "http") from None
            if status is not None:
                raise Unavailable("http", status.status_code, "http") from None
            if isinstance(error, Unavailable):
                raise
            if isinstance(error, (BroadcastEnded, BroadcastChanged)):
                raise
            cause = getattr(error, "err", error)
            name = type(cause).__name__
            category = ("timeout" if "timeout" in name.lower() else
                        "truncated" if name in {"ProtocolError", "IncompleteRead",
                                                "ChunkedEncodingError", "ContentDecodingError"}
                        else "network")
            raise Unavailable("Media request failed", category=category) from None

    def decrypt(self, data, key, number):
        if key is None or key.method == "NONE":
            return data
        if key.method != "AES-128" or not key.uri or self.passthrough_encrypted:
            raise Unavailable("Unsupported encryption")
        with self.cache_lock:
            key_data = self.keys.get(key.uri)
        if key_data is None:
            key_data = self.http_bytes(key.uri)
            with self.cache_lock:
                self.keys[key.uri] = key_data
                while len(self.keys) > 8:
                    self.keys.popitem(last=False)
        iv = key.iv or self.num_to_iv(number)
        return unpad(AES.new(key_data, AES.MODE_CBC, b"\0" * (16 - len(iv)) + iv).decrypt(data), 16)

    def load_map(self, located):
        mapping = located.map
        if mapping is None:
            return b""
        cache_key = (mapping.uri, mapping.byterange)
        with self.cache_lock:
            cached = self.maps.get(cache_key)
        if cached is not None:
            return cached
        data = self.decrypt(self.http_bytes(mapping.uri, mapping.byterange), mapping.key, located.num)
        validate_media(data, is_map=True)
        with self.cache_lock:
            self.maps[cache_key] = data
            while len(self.maps) > 16:
                self.maps.popitem(last=False)
        return data

    def download(self, located, target):
        stage = "initialization"
        try:
            initialization = self.load_map(located)
            if located.uri != target.uri:
                expected = self.load_map(target)
                if hashlib.sha256(initialization).digest() != hashlib.sha256(expected).digest():
                    raise Unavailable("Different initialization", category="initialization")
            stage = "media"
            media = self.decrypt(self.http_bytes(located.uri, located.byterange), located.key, located.num)
            validate_media(media)
            if not initialization and media[0] != 0x47:
                raise Unavailable("Missing fragment initialization", category="initialization")
            return Download(located, initialization, media)
        except (Unavailable, ValueError) as error:
            if isinstance(error, ValueError):
                error = Unavailable("Invalid encrypted media", category="invalid_media")
            self.source.report_failure(stage, "primary" if located.uri == target.uri else "alternate",
                                       error, located)
            raise error from None

    def submit_request(self, located, target, deadline):
        while not self.source.stop.is_set() and time.monotonic() < deadline:
            if self.request_slots.acquire(timeout=0.1):
                try:
                    future = self.requests.submit(self.download, located, target)
                except RuntimeError:
                    self.request_slots.release()
                    raise Unavailable("Stopped") from None
                future.add_done_callback(lambda _: self.request_slots.release())
                return future
        raise Unavailable("Stopped or request deadline reached")

    def refresh_token(self):
        # A token error triggers discovery immediately, even when a backup can
        # finish first. Concurrent segment failures share one refresh task.
        with self.refresh_lock:
            if self.refresh_future is None or self.refresh_future.done():
                try:
                    self.refresh_future = self.lookups.submit(self.source.discover, True)
                except RuntimeError:
                    raise Unavailable("Stopped") from None
            return self.refresh_future

    def fetch(self, target):
        if self.start_download and self.source.matches(target, self.start_download.located):
            return self.start_download
        required = target
        deadline = time.monotonic() + RECOVERY_TIMEOUT
        while not self.source.stop.is_set() and time.monotonic() < deadline:
            primary = self.submit_request(target, required, deadline)
            futures = [primary]
            lookup = None
            refresh_needed = False
            refresh_candidates = False
            try:
                try:
                    return primary.result(timeout=HEDGE_DELAY)
                except Unavailable as error:
                    futures.remove(primary)
                    refresh_candidates = True
                    if error.status in (401, 403):
                        self.refresh_token()
                        refresh_needed = True
                except ValueError:
                    futures.remove(primary)
                    refresh_candidates = True
                except TimeoutError:
                    pass
                # Manifest/API discovery can be slow too. Poll it alongside the
                # primary response so a completed download is never held up by
                # resolving a fallback that is no longer needed.
                if self.lookup_slots.acquire(blocking=False):
                    try:
                        lookup = self.lookups.submit(
                            lambda refresh=refresh_candidates: next(self.source.alternatives(required, refresh), None))
                    except RuntimeError:
                        self.lookup_slots.release()
                        raise Unavailable("Stopped") from None
                    lookup.add_done_callback(lambda _: self.lookup_slots.release())
                while (futures or lookup) and not self.source.stop.is_set() and time.monotonic() < deadline:
                    for future in list(futures):
                        if not future.done():
                            continue
                        futures.remove(future)
                        try:
                            return future.result()
                        except (Unavailable, ValueError, CancelledError) as error:
                            if getattr(error, "status", None) in (401, 403):
                                self.refresh_token()
                                refresh_needed = True
                    if self.source.ended:
                        raise BroadcastEnded("Broadcast ended")
                    if self.source.changed:
                        raise BroadcastChanged("Broadcast changed")
                    if lookup and lookup.done():
                        try:
                            alternative = lookup.result()
                        except (BroadcastEnded, BroadcastChanged):
                            raise
                        except (StreamError, ValueError, CancelledError):
                            alternative = None
                        lookup = None
                        if alternative:
                            futures.append(self.submit_request(alternative, required, deadline))
                    if futures or lookup:
                        self.source.stop.wait(0.05)
                if refresh_needed:
                    self.refresh_future.result(timeout=max(0, deadline - time.monotonic()))
                # Replace expired segment URLs by an API-advertised equivalent.
                alternative = next(self.source.alternatives(required), None)
                if alternative:
                    target = alternative
                    continue
                # Retry the known media URL until the recovery deadline. A
                # fragment absent from fresh playlists can still be fetchable.
                self.source.stop.wait(max(0, min(1, deadline - time.monotonic())))
            except (BroadcastEnded, BroadcastChanged):
                raise
            except (StreamError, ValueError, TimeoutError, CancelledError):
                # A transient API/manifest failure is not proof of a gap.
                self.source.stop.wait(max(0, min(1, deadline - time.monotonic())))
            finally:
                if lookup:
                    lookup.cancel()
                for future in futures:
                    future.cancel()
        self.source.report_failure("media", "primary",
                                   Unavailable("Recovery deadline", category="timeout"), required)
        raise Unavailable("Required segment unavailable")

    def boundary(self, following, reason, resume_from=None, after_gap=False):
        if self.failed or self.source.stop.is_set():
            return
        self.failed = True
        self.source.emit("boundary", reason=reason,
                         resume_from=timestamp(following.date if following else resume_from),
                         after_gap=after_gap)
        self.close()

    def fail(self, previous, following, reason, missing_next=False):
        if self.failed or self.source.stop.is_set():
            return
        start = previous.end if previous else following.date if following else None
        if start is None and self.source.resume:
            start = parse_timestamp(self.source.resume["from"])
        self.source.emit("gap", reason=reason,
                         **{"from": timestamp(start),
                            "to": timestamp(following.end if missing_next else following.date)
                            if following else None})
        # Keep the earliest position after the known hole instead of jumping
        # to a moving live edge during process/file finalization.
        resume_from = (following.end if missing_next else following.date) if following else None
        if reason == "broadcast_ended":
            resume_from = None
        self.boundary(None, reason, resume_from=resume_from, after_gap=resume_from is not None)

    def deliver(self, target, result):
        if self.previous and (target.discontinuity or result.initialization != self.initialization):
            self.boundary(target, "discontinuity" if target.discontinuity else "initialization_changed")
            return False
        if self.previous is None:
            if result.initialization:
                self.reader.buffer.write(result.initialization)
            self.initialization = result.initialization
        self.reader.buffer.write(result.media)
        if self.source.stop.is_set():
            return False
        self.previous = target
        self.start_download = None
        self.source.last_progress = time.monotonic()
        if self.source.recovering:
            self.source.emit("recovery_completed", at=timestamp(target.end))
            self.source.recovering = False
        return True

    def write(self, target, result, *data):
        previous = self.previous
        if previous:
            if previous.end and target.date:
                delta = (target.date - previous.end).total_seconds()
                if delta < -TIME_TOLERANCE:
                    # A clock reset is a boundary, never an unnoticed rewind.
                    self.boundary(target, "discontinuity")
                    return
                missing = delta > TIME_TOLERANCE
            else:
                if previous.manifest.url != target.manifest.url:
                    self.fail(previous, target, "position_unknown")
                    return
                missing = target.num != previous.num + 1
            if missing:
                self.source.emit("recovery_started", at=timestamp(previous.end))
                self.source.recovering = True
                deadline = time.monotonic() + RECOVERY_TIMEOUT
                refresh = False
                while not self.source.stop.is_set():
                    try:
                        chain = self.source.between(self.previous, target, refresh)
                        for segment in chain:
                            if not self.deliver(segment, self.fetch(segment)):
                                return
                            deadline = time.monotonic() + RECOVERY_TIMEOUT
                        break
                    except BroadcastEnded:
                        self.fail(self.previous, target, "broadcast_ended")
                        return
                    except BroadcastChanged:
                        self.boundary(None, "broadcast_changed")
                        return
                    except Unavailable:
                        if time.monotonic() >= deadline:
                            self.fail(self.previous, target, "interval_unavailable")
                            return
                        refresh = True
                        self.source.stop.wait(1)
        if not self.source.stop.is_set():
            self.deliver(target, result)

    def run(self):
        try:
            while not self.closed:
                try:
                    item = self._queue_get()
                except queue.Empty:
                    continue
                if item is None:
                    if self.source.terminal:
                        kind, reason = self.source.terminal
                        if kind == "gap":
                            self.fail(self.previous, None, reason)
                        else:
                            self.boundary(None, reason)
                    break
                segment, future, _ = item
                waited_at = time.monotonic()
                announced = False
                while not self.closed:
                    try:
                        result = future.result(timeout=0.2)
                        if result is None:
                            raise Unavailable("No segment response")
                        self.write(segment, result)
                        break
                    except TimeoutError:
                        if not announced and time.monotonic() - waited_at >= HEDGE_DELAY:
                            self.source.emit("recovery_started", at=timestamp(segment.date))
                            self.source.recovering = True
                            announced = True
                        continue
                    except BroadcastEnded:
                        self.fail(self.previous, segment, "broadcast_ended", missing_next=True)
                        return
                    except BroadcastChanged:
                        self.boundary(None, "broadcast_changed")
                        return
                    except Exception:
                        self.fail(self.previous, segment, "segment_unavailable", missing_next=True)
                        return
        finally:
            self.close()


class ChzzkContinuityReader(HLSStreamReader):
    __worker__ = ChzzkContinuityWorker
    __writer__ = ChzzkContinuityWriter

    def read(self, size):
        source = self.stream.continuity
        # Short waits permit recovery/cancellation checks without a stock read
        # timeout terminating Streamlink in the middle of an explicit repair.
        while True:
            try:
                return self.buffer.read(size, block=self.writer.is_alive(), timeout=1)
            except OSError:
                if source.stop.is_set():
                    return self.buffer.read(size, block=False)
                if time.monotonic() - source.last_progress >= RECOVERY_TIMEOUT + 5:
                    self.writer.fail(self.writer.previous, None, "output_stalled")
