"""Ordered CHZZK HLS delivery. Network failures must never become skipped media.

The plugin supplies advertised manifests and known Akamai hostname probes.
A writer validates alternatives and owns the cursor independently of the queue.
"""

import copy
import hashlib
import json
import math
import queue
import re
import struct
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from concurrent.futures import CancelledError, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlparse, urlunparse

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from streamlink.exceptions import StreamError
from streamlink.stream.hls import HLSStreamReader, HLSStreamWorker, parse_m3u8
from streamlink.stream.hls.hls import HLSStreamWriter
from streamlink.stream.hls.m3u8 import M3U8Parser, parse_tag
from recording_continuity import EVENT_PREFIX
from recording_buffer import BUFFER_BYTES, BUFFER_SECONDS, BufferFull, MediaBuffer


HEDGE_DELAY = 2.0
HISTORY_BUDGET = 2.0
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


def failure_category(error):
    """Classify exception types without retaining exception messages/URLs."""
    names = set()
    pending = [error]
    seen = set()
    while pending and len(seen) < 16:
        cause = pending.pop()
        if not isinstance(cause, BaseException) or id(cause) in seen:
            continue
        seen.add(id(cause))
        names.add(type(cause).__name__.lower())
        pending.extend(getattr(cause, key, None) for key in (
            "err", "reason", "__cause__", "__context__"))
        pending.extend(cause.args)
    if any("timeout" in name for name in names):
        return "timeout"
    if any("ssl" in name or "certificate" in name for name in names):
        return "tls"
    if names & {"gaierror", "nameresolutionerror"}:
        return "dns"
    if names & {"protocolerror", "incompleteread", "chunkedencodingerror", "contentdecodingerror"}:
        return "truncated"
    if any("connection" in name for name in names):
        return "connect"
    return "parse" if "valueerror" in names else "network"


def quality_from_url(url):
    for part in urlparse(url).path.split("/"):
        if re.fullmatch(r"\d+p(?:\d+)?", part):
            return part
    return None


def cdn_from_url(url):
    host = (urlparse(url).hostname or "").lower()
    if host == "akamaized.net" or host.endswith(".akamaized.net"):
        return "akamai"
    if any(host == domain or host.endswith("." + domain)
           for domain in ("pstatic.net", "navercdn.com")):
        return "korean"
    return "unknown"


@dataclass(frozen=True)
class SourcePath:
    url: str = field(repr=False)
    history: bool = False
    mode: str = "hls"
    cdn: str = "unknown"
    probe: bool = False

    @property
    def priority(self):
        return ({"korean": 0, "unknown": 1, "akamai": 2}[self.cdn],
                self.history, self.mode != "llhls")


def source_path(value):
    if isinstance(value, SourcePath):
        return value
    url, history = value
    return SourcePath(url, history, "hls", cdn_from_url(url))


@dataclass(frozen=True)
class Part:
    uri: str = field(repr=False)
    duration: float
    byterange: object = None
    gap: bool = False
    mapping: object = field(default=None, repr=False)
    key: object = field(default=None, repr=False)


class ChzzkM3U8Parser(M3U8Parser):
    """Keep Streamlink's complete-segment cursor and add advertised LL parts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parts = []
        self.m3u8.part_groups = {}
        self.m3u8.trailing_parts = ()
        self.m3u8.can_block_reload = False
        self.m3u8.part_target = None

    @parse_tag("EXT-X-PART")
    def parse_part(self, value):
        attr = self.parse_attributes(value)
        duration = float(attr.get("DURATION", 0))
        uri = attr.get("URI")
        if not uri or not math.isfinite(duration) or duration <= 0:
            raise ValueError("Invalid partial segment")
        self.parts.append(Part(self.uri(uri), duration,
                               self.parse_byterange(attr.get("BYTERANGE", "")),
                               attr.get("GAP") == "YES", self._map, self._key))

    @parse_tag("EXT-X-PART-INF")
    def parse_part_inf(self, value):
        target = float(self.parse_attributes(value).get("PART-TARGET", 0))
        if math.isfinite(target) and target > 0:
            self.m3u8.part_target = target

    @parse_tag("EXT-X-SERVER-CONTROL")
    def parse_server_control(self, value):
        self.m3u8.can_block_reload = self.parse_attributes(value).get("CAN-BLOCK-RELOAD") == "YES"

    @parse_tag("EXT-X-DISCONTINUITY-SEQUENCE")
    def parse_discontinuity_sequence(self, value):
        self.m3u8.discontinuity_sequence = int(value)

    def get_segment(self, uri, **data):
        segment = super().get_segment(uri, **data)
        # PDT is often given only once in an LL playlist.
        if segment.date is None and self.m3u8.segments:
            previous = self.m3u8.segments[-1]
            if previous.date is not None and not segment.discontinuity:
                segment.date = previous.date + timedelta(seconds=previous.duration)
        self.m3u8.part_groups[len(self.m3u8.segments)] = tuple(self.parts)
        self.parts = []
        return segment

    def parse(self, data):
        playlist = super().parse(data)
        first = playlist.media_sequence or 0
        playlist.part_groups = {first + i: parts for i, parts in playlist.part_groups.items()}
        playlist.trailing_parts = tuple(self.parts)
        return playlist


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
    mode: str = "hls"
    cdn: str = "unknown"
    probe: bool = False
    lookup: tuple = field(default=(0, 'unavailable', None), repr=False)
    lock: object = field(default_factory=threading.RLock, repr=False)


@dataclass
class LocatedSegment:
    segment: object = field(repr=False)
    manifest: Manifest = field(repr=False)
    live_id: int
    rendition: str
    parts: tuple = field(default=(), repr=False)
    discontinuity_id: int | None = None

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
    mode: str = "hls"


@dataclass
class BufferedDownload:
    located: LocatedSegment
    buffer: MediaBuffer
    row: dict
    mode: str

    @property
    def initialization(self):
        return self.buffer.load(self.row)[0]

    @property
    def media(self):
        return self.buffer.load(self.row)[1]

    def materialize(self):
        initialization, media = self.buffer.load(self.row)
        if initialization:
            validate_media(initialization, True)
        validate_media(media)
        if not initialization and media[0] != 0x47:
            raise Unavailable('Missing buffered initialization', category='initialization')
        return Download(self.located, initialization, media, self.mode)


class ContinuitySource:
    """Small manifest pool refreshed from the API, with serialized discovery."""

    def __init__(self, stream, provider, live_id, paths, lookback=0, resume=None,
                 time_machine_active=None, mode="hls", cdn=None):
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
        self.discovery_lock = threading.RLock()
        self.event_lock = threading.Lock()
        self.diagnostic_lock = threading.Lock()
        self.diagnostics = OrderedDict()
        self.last_refresh = time.monotonic()
        self.last_discovery = 0.0
        self.paths = [source_path(p) for p in paths]
        self.manifests = OrderedDict()
        initial = next((p for p in self.paths if p.url == stream._url), None)
        self.primary = self.add(stream._url, False,
                                initial.mode if initial else mode,
                                cdn or (initial.cdn if initial else cdn_from_url(stream._url)))
        self.ended = False
        self.changed = False
        self.recovering = False
        self.last_progress = time.monotonic()
        self.recovery_deadline = None
        self.recovery_wall = None
        self.waiting_for_resume = bool(resume and resume["live_id"] == self.live_id
                                      and resume["rendition"] == self.rendition)
        if self.waiting_for_resume and resume.get("recovery_deadline"):
            self.recovery_wall = parse_timestamp(resume["recovery_deadline"])
            remaining = max(0, min(RECOVERY_TIMEOUT,
                (self.recovery_wall - datetime.now(timezone.utc)).total_seconds()))
            self.recovery_deadline = time.monotonic() + remaining
        self.terminal = None
        self.catalog = OrderedDict()
        self.writer = None
        self.snapshot_times = {}
        self.recovery_target = None

    def recovery_limit(self, limit=None):
        with self.lock:
            if self.recovery_deadline is None:
                self.recovery_deadline = (limit if limit is not None else
                                          time.monotonic() + RECOVERY_TIMEOUT)
                self.recovery_wall = datetime.now(timezone.utc) + timedelta(
                    seconds=max(0, self.recovery_deadline - time.monotonic()))
            return self.recovery_deadline

    def progressed(self):
        with self.lock:
            self.last_progress = time.monotonic()
            self.recovery_deadline = None
            self.recovery_wall = None

    def emit(self, kind, **fields):
        if kind == 'recovery_started':
            self.recovery_target = fields.get('at')
            if self.writer is not None:
                self.writer.start_capture(fields.get('at'))
            self.recovery_snapshot('started', fields.get('at'), force=True)
        elif kind == 'recovery_completed':
            self.recovery_snapshot('completed', fields.get('at'), force=True)
        elif kind == 'boundary':
            self.recovery_snapshot('boundary', fields.get('resume_from'), force=True)
        event = dict(version=1, kind=kind, live_id=self.live_id,
                     rendition=self.rendition, **fields)
        with self.event_lock:
            sys.stderr.write(EVENT_PREFIX + json.dumps(event) + "\n")
            sys.stderr.flush()

    def recovery_snapshot(self, result, target=None, force=False, manifest=None):
        target = target or (timestamp(self.writer.previous.end)
                            if self.writer and self.writer.previous else self.recovery_target)
        manifest = manifest or self.primary
        key = (manifest.cdn, manifest.history, manifest.mode)
        now = time.monotonic()
        with self.lock:
            if not force and now - self.snapshot_times.get(key, 0) < 5:
                return
            self.snapshot_times[key] = now
            playlist = manifest.playlist
            dated = [s for s in playlist.segments if s.date] if playlist else []
            elapsed, lookup, lookup_at = manifest.lookup
        buffer = self.writer.media_buffer if self.writer else None
        self.emit('recovery_snapshot', observed_at=timestamp(datetime.now(timezone.utc)),
                  cdn=manifest.cdn, mode=manifest.mode,
                  role='history' if manifest.history else 'current', result=result,
                  lookup_result=lookup, lookup_at=lookup_at, elapsed_ms=round(elapsed * 1000, 3),
                  window_from=timestamp(dated[0].date) if dated else None,
                  window_to=timestamp(dated[-1].date + timedelta(seconds=dated[-1].duration)) if dated else None,
                  target=target, recovery_deadline=timestamp(self.recovery_wall),
                  buffered_count=len(buffer.entries()) if buffer else 0,
                  buffered_bytes=buffer.used if buffer else 0)

    def report_failure(self, stage, role, error, located=None):
        """Bounded, URL-free diagnostics; never serialize request exceptions."""
        if self.stop.is_set() or isinstance(error, (BroadcastEnded, BroadcastChanged)):
            return
        status = getattr(error, "status", None)
        category = getattr(error, "category", failure_category(error))
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

    def add(self, url, history, mode="hls", cdn=None, probe=False):
        parsed = urlparse(url)
        key = (parsed.netloc, parsed.path, history, mode)
        with self.lock:
            manifest = self.manifests.get(key)
            if manifest is None or manifest.url != url:
                manifest = Manifest(url, history, mode=mode, cdn=cdn or cdn_from_url(url), probe=probe)
                self.manifests[key] = manifest
            self.manifests.move_to_end(key)
            # Bound each CDN/role/mode separately. Keep the selected primary.
            same_role = [k for k, m in self.manifests.items()
                         if (m.cdn, m.history, m.mode) == (manifest.cdn, history, mode)
                         and m is not getattr(self, "primary", None)]
            for old in same_role[:-4]:
                self.manifests.pop(old)
        return manifest

    def request_params(self):
        params = dict(self.stream.args)
        for name in ("url", "exception", "stream", "timeout", "retries"):
            params.pop(name, None)
        return params

    def playlist(self, manifest, force=False, blocking=False):
        with manifest.lock:
            if (not force and manifest.playlist is not None
                    and time.monotonic() - manifest.loaded_at < 2):
                return manifest.playlist
            if self.stop.is_set():
                raise Unavailable("Stopped")
            started = time.monotonic()
            try:
                url = manifest.url
                previous = manifest.playlist
                block = (blocking and previous is not None and manifest.mode == "llhls"
                         and previous.can_block_reload and not previous.is_endlist)
                if block:
                    query = [pair for pair in urlparse(url).query.split("&")
                             if pair and pair.split("=", 1)[0] not in {"_HLS_msn", "_HLS_part"}]
                    query.extend([f"_HLS_msn={(previous.media_sequence or 0) + len(previous.segments)}",
                                  f"_HLS_part={len(previous.trailing_parts)}"])
                    url = urlunparse(urlparse(url)._replace(query="&".join(query)))
                params = self.request_params()
                # Blocking reload can normally wait up to three target durations.
                # Give it that budget, capped below the no-progress deadline.
                read_timeout = min(30, max(5, 3 * (previous.targetduration or 2))) if block else 5
                with self.session.http.get(
                    url, timeout=(5, read_timeout), retries=0,
                    exception=StreamError, **params,
                ) as response:
                    response.encoding = "utf-8"
                    playlist = parse_m3u8(response.text, base_uri=manifest.url, parser=self.stream.__parser__)
                if playlist.is_master:
                    matches = [p for p in playlist.playlists if p.stream_info
                               and quality_from_url(p.uri) == self.rendition]
                    if not matches:
                        raise Unavailable("Rendition unavailable")
                    child = self.add(matches[0].uri, manifest.history, manifest.mode, manifest.cdn, manifest.probe)
                    return self.playlist(child, force)
                if playlist.iframes_only or not playlist.segments:
                    raise Unavailable("No complete segments")
                manifest.playlist = playlist
                manifest.loaded_at = time.monotonic()
                manifest.lookup = (
                    time.monotonic() - started, 'available', timestamp(datetime.now(timezone.utc)))
                self.remember(manifest, playlist)
                if self.recovering:
                    self.recovery_snapshot('waiting', manifest=manifest)
                return playlist
            except (StreamError, ValueError) as error:
                # Do not include signed URLs embedded in requests exceptions.
                response = getattr(getattr(error, "err", error), "response", None)
                status = getattr(response, "status_code", None)
                failure = error if isinstance(error, Unavailable) else Unavailable(
                    "Manifest request failed", status, "http" if status else failure_category(error))
                manifest.lookup = (
                    time.monotonic() - started, failure.category, timestamp(datetime.now(timezone.utc)))
                if self.recovering:
                    self.recovery_snapshot('waiting', manifest=manifest)
                self.report_failure("manifest", "history" if manifest.history else "current", failure)
                if status in (401, 403):
                    # Refresh metadata only. Resolving manifests recursively
                    # on a persistent 403 would recurse without a deadline.
                    self.refresh(force=True)
                    self.last_discovery = 0.0
                if isinstance(error, Unavailable):
                    raise
                raise failure from None

    def refresh(self, force=False):
        if not force and time.monotonic() - self.last_refresh < API_REFRESH_INTERVAL:
            return
        with self.discovery_lock:
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
                self.paths = [source_path(p) for p in paths]

    def resolve(self, path):
        manifest = self.add(path.url, path.history, path.mode, path.cdn, path.probe)
        playlist = self.playlist(manifest)
        # playlist() follows a master, storing the parsed variant in the pool.
        if playlist.uri != manifest.url:
            manifest = self.add(playlist.uri, path.history, path.mode, path.cdn, path.probe)
        return manifest, playlist

    def discover(self, force=False):
        self.refresh(force)
        if not force and time.monotonic() - self.last_discovery < API_REFRESH_INTERVAL:
            return
        self.last_discovery = time.monotonic()
        pending = sorted(self.paths, key=lambda p: p.priority)
        tried = set()
        while pending and len(tried) < 32:
            path = pending.pop(0)
            if path.history:
                continue
            if path.url in tried:
                continue
            tried.add(path.url)
            try:
                candidate, _ = self.resolve(path)
                self.primary = candidate
                self.stream._url = candidate.url
                return
            except Unavailable as error:
                if error.status in (401, 403):
                    pending = sorted([p for p in self.paths if p.url not in tried],
                                     key=lambda p: p.priority)
                continue

    def candidates(self, refresh=False, group=None):
        self.refresh(force=refresh and
                     time.monotonic() - self.last_refresh >= RECOVERY_REFRESH_INTERVAL)
        result = []
        seen = set()
        for path in sorted(self.paths, key=lambda p: p.priority):
            if group == "korean" and path.cdn == "akamai":
                continue
            if group == "akamai" and path.cdn != "akamai":
                continue
            try:
                manifest, _ = self.resolve(path)
                if id(manifest) in seen:
                    continue
                seen.add(id(manifest))
                result.append((manifest, self.playlist(manifest, force=refresh)))
            except Unavailable:
                continue
        result.extend(self.retained_candidates(group))
        return result

    def remember(self, manifest, playlist):
        located = [self.locate(s, manifest, playlist) for s in playlist.segments]
        with self.lock:
            for item in located:
                key = (manifest.url, item.num, timestamp(item.date), item.discontinuity_id)
                self.catalog[key] = item
                self.catalog.move_to_end(key)
            dates = [s.end for s in self.catalog.values() if s.end]
            cutoff = max(dates) - timedelta(seconds=BUFFER_SECONDS) if dates else None
            for key, item in list(self.catalog.items()):
                if item.end and cutoff and item.end < cutoff:
                    self.catalog.pop(key)
            while len(self.catalog) > 2048:
                self.catalog.popitem(last=False)
        if self.writer and self.writer.capture_thread is not None:
            self.writer.capture_playlist(manifest, playlist)

    def retained_candidates(self, group=None):
        with self.lock:
            items = list(self.catalog.values())
        if self.writer:
            items = self.writer.buffered_segments() + items
        grouped = OrderedDict()
        for item in items:
            if group == 'korean' and item.manifest.cdn == 'akamai':
                continue
            if group == 'akamai' and item.manifest.cdn != 'akamai':
                continue
            grouped.setdefault(id(item.manifest), (item.manifest, []))[1].append(item)
        return [(m, SimpleNamespace(segments=sorted(segments, key=lambda s: (s.date or datetime.min.replace(tzinfo=timezone.utc), s.num))))
                for m, segments in grouped.values()]

    def locate(self, segment, manifest, playlist=None):
        if isinstance(segment, LocatedSegment):
            return segment
        playlist = playlist or manifest.playlist
        parts = getattr(playlist, "part_groups", {}).get(segment.num, ())
        sequence = getattr(playlist, "discontinuity_sequence", None)
        if sequence is not None:
            sequence += sum(s.discontinuity for s in playlist.segments if s.num <= segment.num)
        return LocatedSegment(copy.deepcopy(segment), manifest, self.live_id, self.rendition,
                              copy.deepcopy(parts), sequence)

    @staticmethod
    def matches(left, right):
        if left.live_id != right.live_id or left.rendition != right.rendition:
            return False
        if left.date is None or right.date is None:
            return left.manifest.url == right.manifest.url and left.num == right.num
        return (abs((left.date - right.date).total_seconds()) <= TIME_TOLERANCE
                and abs(left.duration - right.duration) <= TIME_TOLERANCE
                and left.discontinuity == right.discontinuity
                and (left.discontinuity_id is None or right.discontinuity_id is None
                     or left.discontinuity_id == right.discontinuity_id))

    @staticmethod
    def in_history_window(manifest, playlist, segment):
        if not manifest.history:
            return True
        latest = playlist.segments[-1]
        return (segment.date is not None and latest.date is not None
                and (latest.date + timedelta(seconds=latest.duration) - segment.date).total_seconds()
                <= 3600 + TIME_TOLERANCE)

    def alternatives(self, target, refresh=False, group=None):
        candidates = self.candidates(refresh, group)
        for manifest, playlist in candidates:
            for segment in playlist.segments:
                located = self.locate(segment, manifest, playlist)
                if ((segment.uri != target.uri or manifest.mode != target.manifest.mode)
                        and self.in_history_window(manifest, playlist, segment)
                        and self.matches(target, located)):
                    yield located

    def between(self, previous, following, refresh=False, candidates=None):
        """Yield the surviving prefix before a hole, preserving valid media."""
        if self.ended:
            raise BroadcastEnded("Broadcast ended")
        if self.changed:
            raise BroadcastChanged("Broadcast changed")
        candidates = self.candidates(refresh) if candidates is None else candidates
        if previous.end is None or following.date is None:
            segments = [self.locate(s, m, p) for m, p in candidates
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
            found = next((self.locate(s, m, p) for m, p in candidates for s in p.segments
                          if s.date is not None
                          and abs((s.date - position).total_seconds()) <= TIME_TOLERANCE
                          and s.duration > 0
                          and self.in_history_window(m, p, s)), None)
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
        self.writer.prepare_standby()
        while not self.closed and not source.stop.is_set():
            try:
                if source.ended:
                    raise BroadcastEnded("Broadcast ended")
                if source.changed:
                    raise BroadcastChanged("Broadcast changed")
                if last is None:
                    source.discover()
                if time.monotonic() - source.last_refresh >= API_REFRESH_INTERVAL:
                    source.discover()
                if last is not None:
                    for saved in self.writer.buffered_segments():
                        if last.end and saved.date >= last.end - timedelta(seconds=TIME_TOLERANCE):
                            yield saved
                            last = saved
                manifest = source.primary
                playlist = source.playlist(manifest, force=self.writer.capture_thread is None,
                                           blocking=last is not None and self.writer.capture_thread is None)
                self.writer.prefetch_parts(manifest, playlist)
                segments = [source.locate(s, manifest, playlist) for s in playlist.segments]
                if last is None:
                    resume = source.resume
                    if resume and resume["live_id"] == source.live_id and resume["rendition"] == source.rendition:
                        source.waiting_for_resume = True
                        segments = self.writer.resume_segments()
                        if not segments:
                            if source.terminal:
                                return
                            if not self.wait(1):
                                return
                            continue
                        source.waiting_for_resume = False
                        manifest = source.primary
                        playlist = manifest.playlist
                    elif source.lookback and segments[-1].end:
                        cutoff = segments[-1].end - timedelta(seconds=source.lookback)
                        candidates = source.candidates()
                        has_history = any(m.history and any(s.date for s in p.segments)
                                          for m, p in candidates)
                        if has_history:
                            available = [source.locate(s, m, p) for m, p in candidates
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
                if playlist.is_endlist and not manifest.history:
                    return
                if not queued and time.monotonic() - source.last_progress >= 5:
                    limit = source.recovery_limit(source.last_progress + RECOVERY_TIMEOUT)
                    if time.monotonic() >= limit:
                        source.terminal = ("gap", "playlist_stalled")
                        return
                    self.refresh_stalled_playlist(last)
                interval = (0.05 if manifest.mode == "llhls" and playlist.can_block_reload
                            else min(2, playlist.part_target or playlist.targetduration or 2))
                if not self.wait(interval):
                    return
            except BroadcastEnded:
                source.terminal = ("boundary", "broadcast_ended")
                return
            except BroadcastChanged:
                source.terminal = ("boundary", "broadcast_changed")
                return
            except (StreamError, ValueError):
                limit = source.recovery_limit(source.last_progress + RECOVERY_TIMEOUT)
                if (not source.waiting_for_resume and time.monotonic() >= limit):
                    source.terminal = ("gap", "playlist_unavailable")
                    return
                source.recovering = True
                self.refresh_stalled_playlist(last)
                if not self.wait(1):
                    return

    def refresh_stalled_playlist(self, last):
        """Try dated current/history alternatives even with no queued next media."""
        source = self.stream.continuity
        if time.monotonic() - source.last_discovery < RECOVERY_REFRESH_INTERVAL:
            return
        source.last_discovery = time.monotonic()
        try:
            candidates = self.writer.resume_candidates()
            if last is None:
                network = next((m for m, _ in candidates if not getattr(m, 'buffered', False)), None)
                if network is not None:
                    source.primary = network
                return
            for manifest, playlist in candidates:
                if getattr(manifest, 'buffered', False):
                    continue
                following = [source.locate(s, manifest, playlist) for s in playlist.segments
                             if ((last.end and s.date and s.date >= last.end - timedelta(seconds=TIME_TOLERANCE))
                                 or (last.end is None and manifest.url == last.manifest.url and s.num > last.num))
                             and source.in_history_window(manifest, playlist, s)]
                if following:
                    source.primary = manifest
                    return
        except (StreamError, ValueError):
            pass


class ChzzkContinuityWriter(HLSStreamWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = self.stream.continuity
        self.source.writer = self
        self.requests = ThreadPoolExecutor(max_workers=2 * self.threads - 1,
                                          thread_name_prefix="chzzk-request")
        self.request_slots = threading.BoundedSemaphore(2 * self.threads - 1)
        self.capture_requests = ThreadPoolExecutor(max_workers=1, thread_name_prefix='chzzk-capture')
        self.capture_thread = None
        self.capture_lock = threading.Lock()
        self.capture_pending = set()
        self.capture_from = None
        self.local = threading.local()
        self.lookups = ThreadPoolExecutor(max_workers=3, thread_name_prefix="chzzk-manifest")
        self.lookup_slots = threading.BoundedSemaphore(self.threads + 1)
        self.refresh_lock = threading.Lock()
        self.refresh_future = None
        self.cache_lock = threading.Lock()
        self.maps = OrderedDict()
        self.keys = OrderedDict()
        self.previous = None
        self.output_target = None
        self.initialization = None
        self.failed = False
        self.start_download = None
        self.parts = OrderedDict()
        self.standby_future = None
        self.selected_source = None
        self.delivery_lock = threading.RLock()
        self.buffer_warning = False
        self.buffer_writable = True
        self.owned_buffer = None
        self.media_buffer = None
        try:
            directory = getattr(self.stream, 'buffer_dir', None)
            if directory == '-':
                self.buffer_writable = False
                return
            if directory is None:
                self.owned_buffer = tempfile.TemporaryDirectory(prefix='chzzk-buffer-')
                directory = self.owned_buffer.name
            self.media_buffer = MediaBuffer(directory, self.source.live_id, self.source.rendition)
            if self.source.resume:
                self.media_buffer.discard_before(parse_timestamp(self.source.resume['from']))
        except (OSError, ValueError):
            self.buffer_failed(disable=True)

    def buffer_failed(self, disable=False):
        if disable:
            self.buffer_writable = False
        if not self.buffer_warning:
            self.source.emit('buffer_status', state='unavailable')
            self.buffer_warning = True

    def buffered_segments(self):
        if self.media_buffer is None:
            return []
        result = []
        for row in self.media_buffer.entries():
            manifest = Manifest('', mode=row['mode'], cdn=row['cdn'])
            manifest.buffered = True
            segment = SimpleNamespace(num=row['number'], date=parse_timestamp(row['at']),
                                      duration=row['duration'], discontinuity=row['discontinuity'],
                                      uri='', map=None, key=None, byterange=None)
            located = LocatedSegment(segment, manifest, row['live_id'], row['rendition'],
                                     discontinuity_id=row['discontinuity_id'])
            located.buffer_row = row
            result.append(located)
        return result

    def buffered_download(self, target):
        if self.media_buffer is None or target.date is None:
            return None
        for located in self.buffered_segments():
            row = located.buffer_row
            if self.source.matches(target, located):
                result = BufferedDownload(located, self.media_buffer, row, row['mode'])
                try:
                    result.materialize()
                    return result
                except (OSError, ValueError, Unavailable):
                    self.discard_buffered(row)
        return None

    def discard_buffered(self, row):
        try:
            self.media_buffer.remove(row['key'])
        except OSError:
            self.buffer_failed(disable=True)
        self.buffer_failed()

    def preserve(self, result):
        if (self.closed or self.source.stop.is_set() or isinstance(result, BufferedDownload)
                or self.media_buffer is None or not self.buffer_writable or result.located.date is None):
            return result
        item = result.located
        metadata = dict(at=timestamp(item.date), duration=item.duration, number=item.num,
                        discontinuity=bool(item.discontinuity), discontinuity_id=item.discontinuity_id,
                        cdn=item.manifest.cdn, mode=result.mode)
        try:
            row = self.media_buffer.store(metadata, result.initialization, result.media)
            return BufferedDownload(item, self.media_buffer, row, result.mode)
        except BufferFull:
            if self.source.recovering:
                self.source.recovery_snapshot('buffer_full', timestamp(item.date))
        except (OSError, ValueError):
            self.buffer_failed(disable=True)
        return result

    def start_capture(self, at=None):
        if self.media_buffer is None or not self.buffer_writable or self.closed:
            return
        with self.capture_lock:
            if self.capture_thread is not None:
                return
            self.capture_from = self.previous.end if self.previous else parse_timestamp(at) if at else None
            self.media_buffer.note_pending(self.capture_from)
            self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True, name='chzzk-poll')
            self.capture_thread.start()

    def capture_loop(self):
        while not self.source.stop.is_set() and self.buffer_writable:
            try:
                manifest = self.source.primary
                self.source.playlist(manifest, force=True)
                if self.source.recovering:
                    self.source.recovery_snapshot('waiting')
            except (StreamError, ValueError, OSError):
                if self.source.recovering:
                    self.source.recovery_snapshot('waiting')
            self.source.stop.wait(0.5)

    def capture_playlist(self, manifest, playlist):
        if (self.source.stop.is_set() or not self.buffer_writable
                or (manifest.probe and not getattr(manifest, 'validated', False))):
            return
        for raw in playlist.segments:
            item = self.source.locate(raw, manifest, playlist)
            if (item.date is None or (self.capture_from and item.date < self.capture_from - timedelta(seconds=TIME_TOLERANCE))
                    or not self.media_buffer.can_store(item.date, item.duration)):
                continue
            key = (timestamp(item.date), item.duration, item.discontinuity_id)
            with self.capture_lock:
                if key in self.capture_pending or len(self.capture_pending) >= 128:
                    continue
                if any(self.source.matches(item, cached) for cached in self.buffered_segments()):
                    continue
                self.capture_pending.add(key)
            try:
                self.capture_requests.submit(self.capture_one, key, item)
            except RuntimeError:
                with self.capture_lock:
                    self.capture_pending.discard(key)

    def capture_one(self, key, item):
        self.local.capture = True
        try:
            if (not self.source.stop.is_set() and self.buffer_writable
                    and self.media_buffer.can_store(item.date, item.duration)):
                # One short attempt, never a 90-second recovery in the capture lane.
                self.preserve(self.download(item, item))
        except (StreamError, ValueError, OSError):
            pass
        finally:
            self.local.capture = False
            with self.capture_lock:
                self.capture_pending.discard(key)

    def resume_candidates(self):
        """Bound slow Korean discovery while allowing Akamai within two seconds."""
        futures = {}
        started = time.monotonic()
        limit = started + HISTORY_BUDGET + 5
        result = []

        def submit(group):
            if not self.lookup_slots.acquire(blocking=False):
                return False
            try:
                future = self.lookups.submit(self.source.candidates, True, group)
            except RuntimeError:
                self.lookup_slots.release()
                return False
            future.add_done_callback(lambda _: self.lookup_slots.release())
            futures[group] = future
            return True

        submit("korean")
        akamai_started = not any(p.cdn == "akamai" for p in self.source.paths)
        try:
            while not self.source.stop.is_set() and time.monotonic() < limit:
                for group, future in list(futures.items()):
                    if future.done():
                        del futures[group]
                        try:
                            result.extend(future.result())
                        except (StreamError, ValueError, CancelledError):
                            pass
                if not akamai_started and (not futures or time.monotonic() - started >= HISTORY_BUDGET):
                    akamai_started = submit("akamai")
                if not futures and akamai_started:
                    break
                self.source.stop.wait(0.05)
            return result
        finally:
            for future in futures.values():
                future.cancel()

    def resume_segments(self):
        source = self.source
        resume = source.resume
        cutoff = parse_timestamp(resume["from"])
        cached = self.buffered_segments()
        candidates = ([(s.manifest, SimpleNamespace(segments=[s])) for s in cached]
                      if any(s.date == cutoff for s in cached) else self.resume_candidates())
        if self.source.primary.playlist is not None:
            candidates.append((self.source.primary, self.source.primary.playlist))
        available = [source.locate(s, m, p) for m, p in candidates for s in p.segments
                     if s.date and s.date >= cutoff - timedelta(seconds=TIME_TOLERANCE)
                     and source.in_history_window(m, p, s)]
        unique = {}
        for item in available:
            unique.setdefault((item.date, item.duration, item.discontinuity_id, item.uri,
                               item.manifest.cdn, item.manifest.mode), item)
        available = list(unique.values())
        available.sort(key=lambda s: (s.date, s.manifest.cdn == "akamai", s.manifest.mode != "llhls"))
        exact = [s for s in available if abs((s.date - cutoff).total_seconds()) <= TIME_TOLERANCE]
        pending = "recovery_deadline" in resume
        expired = pending and time.monotonic() >= source.recovery_limit()
        if not exact and not resume.get("after_gap", False):
            source.terminal = ("gap", "resume_unavailable")
            return []
        if pending and not expired and not exact:
            return []
        # After the shared deadline, probe each candidate once; never start a
        # fresh 90-second retry for a position already known to be unavailable.
        attempts = available if expired or not pending else exact
        for target in attempts:
            try:
                result = self.buffered_download(target)
                if result is None:
                    if getattr(target.manifest, 'buffered', False):
                        continue
                    probe_limit = time.monotonic() + self.timeout
                    future = self.submit_request(target, target, probe_limit)
                    result = self.preserve(future.result(timeout=max(0, probe_limit - time.monotonic())))
            except (StreamError, ValueError, CancelledError, TimeoutError):
                continue
            self.start_download = result
            if not getattr(target.manifest, 'buffered', False):
                source.primary = target.manifest
            return [target] + [s for s in available if s.date > target.date]
        return []

    def prepare_standby(self):
        if self.standby_future is not None:
            return
        self.source.emit("source", cdn=self.source.primary.cdn,
                         mode=self.source.primary.mode, state="selected")
        self.selected_source = (self.source.primary.cdn, self.source.primary.mode)

        def prepare():
            if not any(p.cdn == "akamai" for p in self.source.paths):
                self.source.emit("source", cdn="akamai", mode="hls", state="absent")
                return
            try:
                candidates = self.source.candidates(group="akamai")
                for manifest, playlist in candidates:
                    if not playlist.segments:
                        continue
                    try:
                        while not self.source.stop.is_set():
                            if self.request_slots.acquire(timeout=0.1):
                                break
                        else:
                            return
                        try:
                            if manifest.probe:
                                # The hostname substitution is only a probe.
                                # Verify a common dated interval and init/media
                                # before announcing it as a usable standby.
                                limit = time.monotonic() + HISTORY_BUDGET
                                while (self.source.primary.playlist is None
                                       and not self.source.stop.is_set()
                                       and time.monotonic() < limit):
                                    self.source.stop.wait(0.05)
                                primary = self.source.primary
                                ordinary = primary.playlist
                                pair = next(((self.source.locate(b, manifest, playlist), self.source.locate(a, primary, ordinary))
                                             for b in reversed(playlist.segments)
                                             for a in ordinary.segments
                                             if self.source.matches(self.source.locate(a, primary, ordinary),
                                                                    self.source.locate(b, manifest, playlist))), None) if ordinary else None
                                if pair is None:
                                    raise Unavailable("Probe interval unavailable")
                                self.download(*pair)
                                manifest.validated = True
                            else:
                                self.load_map(self.source.locate(playlist.segments[-1], manifest, playlist))
                        finally:
                            self.request_slots.release()
                    except Unavailable:
                        continue
                    if self.source.stop.is_set():
                        return
                    self.source.emit("source", cdn="akamai", mode=manifest.mode, state="ready",
                                     independent_cdn=manifest.cdn != self.source.primary.cdn)
                    return
            except (StreamError, ValueError):
                pass
            if not self.source.stop.is_set():
                self.source.emit("source", cdn="akamai", mode="hls", state="unavailable")

        self.standby_future = self.lookups.submit(prepare)

    @staticmethod
    def part_key(number, part):
        return (number, part.uri, part.byterange,
                part.mapping.uri if part.mapping else None)

    def part_bytes(self, part):
        data = self.http_bytes(part.uri, part.byterange)
        validate_media(data)
        if data[0] == 0x47:
            raise Unavailable("Partial TS unsupported", category="invalid_media")
        return data

    def prefetch_parts(self, manifest, playlist):
        if manifest.mode != "llhls" or manifest.history or self.source.stop.is_set():
            return
        number = (playlist.media_sequence or 0) + len(playlist.segments)
        # Only fetch published parts of the unfinished group. PRELOAD-HINT
        # is deliberately not treated as confirmed available media.
        for part in playlist.trailing_parts:
            if (part.gap or part.mapping is None
                    or (part.key and part.key.method != "NONE")
                    or (part.byterange and part.byterange.offset is None)):
                continue
            key = self.part_key(number, part)
            with self.cache_lock:
                if key in self.parts or not self.request_slots.acquire(blocking=False):
                    continue
                try:
                    future = self.requests.submit(self.part_bytes, part)
                except RuntimeError:
                    self.request_slots.release()
                    return
                future.add_done_callback(lambda _: self.request_slots.release())
                self.parts[key] = future
                while len(self.parts) > 64:
                    _, old = self.parts.popitem(last=False)
                    old.cancel()

    def download_parts(self, located):
        parts = located.parts
        if (not parts or located.map is None
                or (located.key and located.key.method != "NONE")
                or any(p.gap or p.mapping != located.map or p.key != located.key for p in parts)
                or abs(sum(p.duration for p in parts) - located.duration) > TIME_TOLERANCE
                or len({(p.uri, p.byterange) for p in parts}) != len(parts)):
            raise Unavailable("Incomplete or unsupported partial group")
        chunks = []
        for part in parts:
            with self.cache_lock:
                future = self.parts.get(self.part_key(located.num, part))
            # Every submitted request reserves a slot, and the pool has that
            # many workers. A pending preload therefore always has a worker;
            # sharing it cannot starve the pool with queued dependencies.
            data = future.result(timeout=self.timeout) if future else self.part_bytes(part)
            chunks.append(data)
        if len({hashlib.sha256(data).digest() for data in chunks}) != len(chunks):
            raise Unavailable("Duplicate partial media", category="invalid_media")
        data = b"".join(chunks)
        validate_media(data)
        return data

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
        return [self.source.locate(s, manifest, ordinary) for s in ordinary.segments[-max(1, int(self.reader.worker.live_edge)):]]

    def put(self, segment):
        if not self.closed and not self.failed:
            if segment is None:
                self.queue(None, None)
            else:
                if self.output_target is None:
                    self.output_target = segment
                if self.media_buffer is not None:
                    self.media_buffer.note_pending(segment.date)
                self.queue(segment, self.executor.submit(self.fetch, segment))

    def _queue_get(self):
        item = super()._queue_get()
        if item is not None:
            self.output_target = item[0]
        return item

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
        self.capture_requests.shutdown(wait=False, cancel_futures=True)
        if self.owned_buffer is not None:
            # Active requests check stop before storing; wait for their bounded
            # attempts before removing a locally owned directory.
            self.capture_requests.shutdown(wait=True, cancel_futures=True)
            if self.capture_thread and self.capture_thread is not threading.current_thread():
                self.capture_thread.join(timeout=6)
            self.owned_buffer.cleanup()

    def http_bytes(self, uri, byterange=None):
        if self.source.stop.is_set():
            raise Unavailable("Stopped")
        params = self.source.request_params()
        headers = dict(params.pop("headers", {}))
        if byterange:
            if byterange.offset is None:
                raise Unavailable("Implicit byte range unsupported")
            headers["Range"] = f"bytes={byterange.offset}-{byterange.offset + byterange.range - 1}"
        budget = min(2, self.timeout) if getattr(self.local, 'capture', False) else self.timeout
        deadline = time.monotonic() + budget
        try:
            with self.session.http.get(
                uri, headers=headers, stream=True, timeout=(min(5, budget), min(2, budget)),
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
                    if len(data) + len(chunk) > BUFFER_BYTES:
                        raise Unavailable('Oversized media response', category='invalid_media')
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
            raise Unavailable("Media request failed", category=failure_category(error)) from None

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
            if located.manifest is not target.manifest or located.uri != target.uri:
                expected = self.load_map(target)
                if hashlib.sha256(initialization).digest() != hashlib.sha256(expected).digest():
                    raise Unavailable("Different initialization", category="initialization")
            stage = "media"
            media = None
            used_parts = False
            if located.manifest.mode == "llhls" and located.parts and not getattr(self.local, 'capture', False):
                try:
                    media = self.download_parts(located)
                    used_parts = True
                except (Unavailable, ValueError, CancelledError, TimeoutError) as error:
                    self.source.report_failure("media", "primary", error, located)
                    # Whole-segment fallback discards every partial byte.
            if media is None:
                media = self.decrypt(self.http_bytes(located.uri, located.byterange), located.key, located.num)
            validate_media(media)
            if not initialization and media[0] != 0x47:
                raise Unavailable("Missing fragment initialization", category="initialization")
            mode = "llhls" if used_parts else "hls"
            return Download(located, initialization, media, mode)
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

    def repair_chain(self, previous, following, refresh, deadline):
        """Find missing positions without letting slow history age out Akamai."""
        try:
            chain = iter(self.source.between(previous, following,
                                            candidates=self.source.retained_candidates()))
            first = next(chain, None)
        except Unavailable:
            first = None
        if first is not None:
            yield first
            yield from chain
            return
        futures = {}
        started = time.monotonic()

        def submit(group):
            if not self.lookup_slots.acquire(blocking=False):
                return False
            try:
                future = self.lookups.submit(self.source.candidates, refresh, group)
            except RuntimeError:
                self.lookup_slots.release()
                raise Unavailable("Stopped") from None
            future.add_done_callback(lambda _: self.lookup_slots.release())
            futures[group] = future
            return True

        submit("korean")
        akamai_started = False
        has_akamai = any(p.cdn == "akamai" for p in self.source.paths)
        try:
            while not self.source.stop.is_set() and time.monotonic() < deadline:
                for group, future in list(futures.items()):
                    if not future.done():
                        continue
                    del futures[group]
                    try:
                        candidates = future.result()
                        chain = iter(self.source.between(previous, following, candidates=candidates))
                        first = next(chain, None)
                    except (BroadcastEnded, BroadcastChanged):
                        raise
                    except (StreamError, ValueError, CancelledError):
                        continue
                    if first is not None:
                        yield first
                        yield from chain
                        return
                if has_akamai and not akamai_started and (
                        not futures or time.monotonic() - started >= HISTORY_BUDGET):
                    akamai_started = submit("akamai")
                if not futures:
                    raise Unavailable("Required interval unavailable")
                self.source.stop.wait(0.05)
            raise Unavailable("Required interval unavailable")
        finally:
            for future in futures.values():
                future.cancel()

    def fetch(self, target):
        def following():
            return (self.media_buffer is not None and self.buffer_writable and target.date is not None
                    and self.output_target is not None and target is not self.output_target
                    and threading.current_thread() is not self)

        while not self.source.stop.is_set():
            cached = self.buffered_download(target)
            if cached is not None:
                return cached
            if following() and not self.media_buffer.can_store(target.date, target.duration):
                self.source.stop.wait(0.1)
                continue
            used = self.media_buffer.used if self.media_buffer else 0
            result = self.preserve(self._fetch(target))
            if isinstance(result, BufferedDownload) or not following():
                return result
            # A full store must not turn queued completed tasks into large
            # in-memory downloads. Keep the output head eligible for direct
            # delivery, and retry later tails only after capacity is freed.
            del result
            while following() and self.media_buffer.used == used and not self.source.stop.is_set():
                self.source.stop.wait(0.1)
        raise Unavailable('Stopped')

    def _fetch(self, target):
        if self.start_download and self.source.matches(target, self.start_download.located):
            return self.start_download
        required = target
        deadline = time.monotonic() + RECOVERY_TIMEOUT
        while not self.source.stop.is_set() and time.monotonic() < deadline:
            primary = self.submit_request(target, required, deadline)
            futures = [primary]
            lookups = {}
            pending = []
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
                deadline = min(deadline, self.source.recovery_limit(deadline))
                # Manifest/API discovery can be slow too. Poll it alongside the
                # primary response so a completed download is never held up by
                # resolving a fallback that is no longer needed.
                def lookup_group(group):
                    if not self.lookup_slots.acquire(blocking=False):
                        return False
                    try:
                        future = self.lookups.submit(
                            lambda: list(self.source.alternatives(required, refresh_candidates, group)))
                    except RuntimeError:
                        self.lookup_slots.release()
                        raise Unavailable("Stopped") from None
                    future.add_done_callback(lambda _: self.lookup_slots.release())
                    lookups[group] = future
                    return True

                lookup_group("korean")
                history_started = time.monotonic()
                akamai_started = False
                has_akamai = any(p.cdn == "akamai" for p in self.source.paths)
                while (futures or lookups or pending or (has_akamai and not akamai_started)) and not self.source.stop.is_set() and time.monotonic() < deadline:
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
                    for group, lookup in list(lookups.items()):
                        if not lookup.done():
                            continue
                        try:
                            pending.extend(lookup.result())
                        except (BroadcastEnded, BroadcastChanged):
                            raise
                        except (StreamError, ValueError, CancelledError):
                            pass
                        del lookups[group]
                    # Let domestic current/history attempts finish first. A
                    # slow history lookup gets two seconds before Akamai is
                    # considered too, under the same recovery deadline.
                    exhausted = "korean" not in lookups and not pending and not futures
                    if has_akamai and not akamai_started and (
                            exhausted or time.monotonic() - history_started >= HISTORY_BUDGET):
                        akamai_started = lookup_group("akamai")
                    while pending and len(futures) < 2:
                        alternative = pending.pop(0)
                        futures.append(self.submit_request(alternative, required, deadline))
                    if futures or lookups or (has_akamai and not akamai_started):
                        self.source.stop.wait(0.05)
                if refresh_needed:
                    self.refresh_future.result(timeout=max(0, deadline - time.monotonic()))
                # Retry the known media URL until the recovery deadline. A
                # fragment absent from fresh playlists can still be fetchable.
                self.source.stop.wait(max(0, min(1, deadline - time.monotonic())))
            except (BroadcastEnded, BroadcastChanged):
                raise
            except (StreamError, ValueError, TimeoutError, CancelledError):
                # A transient API/manifest failure is not proof of a gap.
                self.source.stop.wait(max(0, min(1, deadline - time.monotonic())))
            finally:
                for lookup in lookups.values():
                    lookup.cancel()
                for future in futures:
                    future.cancel()
        self.source.report_failure("media", "primary",
                                   Unavailable("Recovery deadline", category="timeout"), required)
        raise Unavailable("Required segment unavailable")

    def boundary(self, following, reason, resume_from=None, after_gap=False):
        with self.delivery_lock:
            if self.failed or self.source.stop.is_set():
                return
            self.failed = True
            fields = dict(reason=reason,
                          resume_from=timestamp(following.date if following else resume_from),
                          after_gap=after_gap)
            if after_gap:
                self.source.recovery_limit()
                fields["recovery_deadline"] = timestamp(self.source.recovery_wall)
            self.source.emit("boundary", **fields)
            self.close()

    def fail(self, previous, following, reason, missing_next=False):
        with self.delivery_lock:
            return self._fail(self.previous or previous, following, reason, missing_next)

    def _fail(self, previous, following, reason, missing_next=False):
        if self.failed or self.source.stop.is_set():
            return
        start = previous.end if previous else following.date if following else None
        if start is None and self.source.resume:
            start = parse_timestamp(self.source.resume["from"])
        # No gap is confirmed until the next validated media is actually
        # delivered. Preserve the last output end, including unknown-next stalls.
        resume_from = start
        if reason == "broadcast_ended":
            resume_from = None
        allow_gap = (resume_from is not None and (reason != "resume_unavailable"
                     or bool(self.source.resume and self.source.resume.get("after_gap", False))))
        self.boundary(None, reason, resume_from=resume_from, after_gap=allow_gap)

    def deliver(self, target, result):
        with self.delivery_lock:
            if self.failed or self.source.stop.is_set():
                return False
            return self._deliver(target, result)

    def _deliver(self, target, result):
        if isinstance(result, BufferedDownload):
            try:
                result = result.materialize()
            except (OSError, ValueError, Unavailable):
                self.discard_buffered(result.row)
                result = self._fetch(target)
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
        if self.previous is None and self.source.resume and target.date:
            cutoff = parse_timestamp(self.source.resume["from"])
            if (target.date - cutoff).total_seconds() > TIME_TOLERANCE:
                self.source.emit("gap", reason="resume_unavailable",
                                 **{"from": timestamp(cutoff), "to": timestamp(target.date)})
        self.source.emit("checkpoint", **{"from": timestamp(target.date), "to": timestamp(target.end)})
        self.previous = target
        if self.media_buffer and target.end:
            try:
                self.media_buffer.discard_before(target.end)
            except OSError:
                self.buffer_failed()
        selected = (result.located.manifest.cdn, result.mode)
        if selected != self.selected_source:
            self.source.emit("source", cdn=selected[0], mode=selected[1], state="selected")
            self.selected_source = selected
        with self.cache_lock:
            for key in list(self.parts):
                if key[0] <= target.num:
                    self.parts.pop(key).cancel()
        self.start_download = None
        self.source.progressed()
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
                deadline = self.source.recovery_limit()
                refresh = False
                while not self.source.stop.is_set():
                    try:
                        chain = self.repair_chain(self.previous, target, refresh, deadline)
                        for segment in chain:
                            if not self.deliver(segment, self.fetch(segment)):
                                return
                            deadline = self.source.recovery_limit()
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
                limit = source.recovery_deadline or source.last_progress + RECOVERY_TIMEOUT
                if not source.waiting_for_resume and time.monotonic() >= limit + 5:
                    self.writer.fail(self.writer.previous, None, "output_stalled")
