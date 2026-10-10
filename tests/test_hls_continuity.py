"""Fault injection against real Streamlink 8.6.2 readers and local HTTP CDNs."""

import contextlib
import asyncio
import io
import json
import os
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from unittest.mock import AsyncMock

from streamlink import Streamlink

import hls_continuity as continuity
from config_store import normalize_config
from i18n import SUPPORTED_LANGUAGES, translate
from plugin.chzzk import ChzzkHLSStream, source_paths
from recording_continuity import EVENT_PREFIX, REASONS, RecordingContinuity, parse_event
from recording_options import effective_previous_hour


START = datetime(2026, 10, 10, tzinfo=timezone.utc)


def box(kind, payload=b""):
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


INITIALIZATION = box(b"ftyp", b"isom") + box(b"moov", b"same codec")
MEDIA = [box(b"moof", bytes([i])) + box(b"mdat", bytes([i]) * 10) for i in range(4)]


class CDN:
    def __init__(self):
        self.assets = {}
        self.responses = {}
        self.delays = {}
        self.trickle = {}
        self.statuses = {}
        self.truncate = set()
        self.hits = Counter()
        self.queries = []
        self.active = 0
        self.peak = 0
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                media = not path.endswith("m3u8")
                with owner.lock:
                    owner.hits[path] += 1
                    owner.queries.append(self.path)
                    if media:
                        owner.active += 1
                        owner.peak = max(owner.peak, owner.active)
                try:
                    time.sleep(owner.delays.get(path, 0))
                    status = owner.statuses.get(path, 200 if path in owner.assets else 404)
                    body = owner.assets.get(path, b"") if status == 200 else b""
                    with owner.lock:
                        responses = owner.responses.get(path)
                        if status == 200 and responses:
                            body = responses.pop(0) if len(responses) > 1 else responses[0]
                    self.send_response(status)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    if path in owner.truncate:
                        body = body[:len(body) // 2]
                    if path in owner.trickle:
                        for byte in body:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            time.sleep(owner.trickle[path])
                    else:
                        self.wfile.write(body)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    with owner.lock:
                        if media:
                            owner.active -= 1

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.http.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)

    def url(self, prefix):
        return f"http://127.0.0.1:{self.http.server_port}/{prefix}/1080p/list.m3u8"

    def playlist(self, prefix, indices=(0, 1, 2, 3), dated=True, end=True,
                 initialization=INITIALIZATION, media=MEDIA, duration=4,
                 discontinuity=None, changed_map=None):
        directory = f"/{prefix}/1080p/"
        lines = ["#EXTM3U", "#EXT-X-VERSION:7", "#EXT-X-TARGETDURATION:5",
                 '#EXT-X-MAP:URI="init.mp4"', "#EXT-X-MEDIA-SEQUENCE:0"]
        for index in indices:
            if index == discontinuity:
                lines.append("#EXT-X-DISCONTINUITY")
                lines.append('#EXT-X-MAP:URI="init.mp4"')
            if index == changed_map:
                lines.append('#EXT-X-MAP:URI="changed.mp4"')
            if dated:
                lines.append("#EXT-X-PROGRAM-DATE-TIME:" +
                             (START + timedelta(seconds=index * duration)).isoformat())
            lines.extend([f"#EXTINF:{duration},", f"{index}.m4v"])
            self.assets[directory + f"{index}.m4v"] = media[index]
        if end:
            lines.append("#EXT-X-ENDLIST")
        self.assets[directory + "list.m3u8"] = "\n".join(lines).encode()
        self.assets[directory + "init.mp4"] = initialization
        self.assets[directory + "changed.mp4"] = initialization + box(b"free", b"changed")

    def ll_playlist(self, prefix, counts=(2, 3, 1, 4), end=True):
        groups = []
        for index, count in enumerate(counts):
            parts = [box(b"moof", bytes([index, part])) + box(b"mdat", bytes([index, part]) * 10)
                     for part in range(count)]
            groups.append(b"".join(parts))
            for part, data in enumerate(parts):
                self.assets[f"/{prefix}/1080p/{index}_{part}.m4v"] = data
        self.playlist(prefix, indices=tuple(range(len(counts))), media=groups, end=end)
        path = f"/{prefix}/1080p/list.m3u8"
        lines = self.assets[path].decode().splitlines()
        lines[2:2] = ['#EXT-X-SERVER-CONTROL:CAN-BLOCK-RELOAD=YES',
                      '#EXT-X-PART-INF:PART-TARGET=2']
        output = []
        index = 0
        for line in lines:
            if line.startswith("#EXTINF:"):
                for part in range(counts[index]):
                    output.append(f'#EXT-X-PART:DURATION={4 / counts[index]},URI="{index}_{part}.m4v"')
                index += 1
            output.append(line)
        self.assets[path] = "\n".join(output).encode()
        return groups


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(continuity, "HEDGE_DELAY", 0.05))
        self.stack.enter_context(patch.object(continuity, "RECOVERY_TIMEOUT", 0.6))
        self.stderr = io.StringIO()
        self.stack.enter_context(contextlib.redirect_stderr(self.stderr))
        self.cdn = self.stack.enter_context(CDN())
        self.session = Streamlink()
        self.session.set_option("stream-segment-threads", 2)
        self.session.set_option("stream-segment-timeout", 0.3)
        self.session.set_option("hls-live-edge", 1)
        self.addCleanup(self.session.http.close)

    def stream(self, paths=None, lookback=0, resume=None, flag=None):
        paths = paths or [(self.cdn.url("primary"), False)]
        stream = ChzzkHLSStream(self.session, self.cdn.url("primary"), "test",
                               live_id=1, source_paths=paths, start_lookback=lookback,
                               resume=resume, time_machine_active=flag)
        stream.continuity.provider = lambda: (1, paths, flag)
        return stream

    def read(self, stream):
        reader = stream.open()
        result = bytearray()
        try:
            while chunk := reader.read(65536):
                result.extend(chunk)
        finally:
            reader.close()
        return bytes(result)

    def events(self):
        return [parse_event(line) for line in self.stderr.getvalue().splitlines()
                if line.startswith(EVENT_PREFIX)]

    def test_normal_order_exactly_once(self):
        self.cdn.playlist("primary")
        result = self.read(self.stream())
        self.assertEqual(result, INITIALIZATION + b"".join(MEDIA))
        self.assertFalse(any(e["kind"] == "gap" for e in self.events()))

    def test_slow_primary_hedges_and_does_not_duplicate(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("backup")
        self.cdn.delays['/primary/1080p/1.m4v'] = 0.2
        result = self.read(self.stream([(self.cdn.url("primary"), False),
                                       (self.cdn.url("backup"), True)]))
        self.assertEqual(result, INITIALIZATION + b"".join(MEDIA))
        self.assertGreater(self.cdn.hits['/backup/1080p/1.m4v'], 0)
        self.assertLessEqual(self.cdn.peak, 4)

    def test_failed_primary_requests_backup_immediately(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("backup")
        self.cdn.statuses['/primary/1080p/1.m4v'] = 503
        self.assertEqual(self.read(self.stream([(self.cdn.url("primary"), False),
                                               (self.cdn.url("backup"), True)])),
                         INITIALIZATION + b"".join(MEDIA))

    def test_sliding_playlist_does_not_end_retry_of_known_media_url(self):
        self.cdn.playlist("primary")
        stream = self.stream()
        source = stream.continuity
        manifest, playlist = source.candidates()[0]
        target = source.locate(playlist.segments[0], manifest)
        self.cdn.playlist("primary", indices=(2, 3))
        source.playlist(manifest, force=True)
        path = '/primary/1080p/0.m4v'
        self.cdn.statuses[path] = 404
        timer = threading.Timer(0.1, lambda: self.cdn.statuses.pop(path, None))
        timer.start()
        self.addCleanup(timer.join)
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        with patch.object(continuity, "RECOVERY_TIMEOUT", 1.5):
            self.assertEqual(reader.writer.fetch(target).media, MEDIA[0])
        self.assertGreaterEqual(self.cdn.hits[path], 2)

    def test_expired_manifest_window_is_rechecked_before_gap(self):
        self.cdn.playlist("primary", indices=(0, 2, 3))
        self.cdn.playlist("history", indices=(2, 3))
        stream = self.stream([(self.cdn.url("primary"), False),
                              (self.cdn.url("history"), True)])
        source = stream.continuity
        candidates = source.candidates()
        manifest, playlist = next((m, p) for m, p in candidates if not m.history)
        previous = source.locate(playlist.segments[0], manifest)
        target = source.locate(playlist.segments[1], manifest)
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        reader.writer.deliver(previous, reader.writer.download(previous, previous))
        self.cdn.playlist("primary", indices=(2, 3))
        source.playlist(manifest, force=True)
        timer = threading.Timer(0.1, lambda: self.cdn.playlist("history"))
        timer.start()
        self.addCleanup(timer.join)
        with patch.object(continuity, "RECOVERY_TIMEOUT", 2.5):
            reader.writer.write(target, reader.writer.download(target, target))
        self.assertEqual(reader.buffer.read(65536, block=False),
                         INITIALIZATION + b"".join(MEDIA[:3]))
        self.assertFalse(any(e["kind"] == "gap" for e in self.events()))

    def test_http_failures_include_safe_deduplicated_diagnostics(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("backup")
        self.cdn.statuses['/primary/1080p/1.m4v'] = 503
        self.assertEqual(self.read(self.stream([(self.cdn.url("primary"), False),
                                               (self.cdn.url("backup"), True)])),
                         INITIALIZATION + b"".join(MEDIA))
        diagnostic = [e for e in self.events() if e["kind"] == "diagnostic"
                      and e["status"] == 503]
        self.assertEqual(len(diagnostic), 1)
        self.assertEqual(diagnostic[0]["stage"], "media")
        self.assertEqual(diagnostic[0]["role"], "primary")
        self.assertEqual(diagnostic[0]["sequence"], 1)
        self.assertEqual(diagnostic[0]["category"], "http")
        self.assertNotIn("http://", json.dumps(diagnostic))

    def test_recovery_deadline_still_bounds_missing_media(self):
        self.cdn.playlist("primary")
        stream = self.stream()
        manifest, playlist = stream.continuity.candidates()[0]
        target = stream.continuity.locate(playlist.segments[0], manifest)
        self.cdn.playlist("primary", indices=(2, 3))
        stream.continuity.playlist(manifest, force=True)
        self.cdn.statuses['/primary/1080p/0.m4v'] = 404
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        before = time.monotonic()
        with self.assertRaises(continuity.Unavailable):
            reader.writer.fetch(target)
        elapsed = time.monotonic() - before
        self.assertGreaterEqual(elapsed, 0.5)
        self.assertLess(elapsed, 1.2)

    def test_slow_manifest_lookup_does_not_hold_completed_primary(self):
        self.cdn.playlist("primary")
        stream = self.stream()
        source = stream.continuity
        manifest, playlist = source.candidates()[0]
        target = source.locate(playlist.segments[0], manifest)
        self.cdn.delays['/primary/1080p/0.m4v'] = 0.12
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)

        def slow_lookup(*_):
            time.sleep(0.4)
            return iter(())

        with patch.object(source, "alternatives", slow_lookup):
            before = time.monotonic()
            result = reader.writer.fetch(target)
            elapsed = time.monotonic() - before
        self.assertEqual(result.media, MEDIA[0])
        self.assertLess(elapsed, 0.3)

    def test_failed_fallback_lookup_does_not_abort_primary(self):
        self.cdn.playlist("primary")
        stream = self.stream()
        manifest, playlist = stream.continuity.candidates()[0]
        target = stream.continuity.locate(playlist.segments[0], manifest)
        self.cdn.delays['/primary/1080p/0.m4v'] = 0.12
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        with patch.object(stream.continuity, "alternatives",
                          side_effect=continuity.Unavailable("API unavailable")):
            self.assertEqual(reader.writer.fetch(target).media, MEDIA[0])

    def test_truncated_response_is_replaced_before_output(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("backup")
        self.cdn.truncate.add('/primary/1080p/1.m4v')
        self.assertEqual(self.read(self.stream([(self.cdn.url("primary"), False),
                                               (self.cdn.url("backup"), True)])),
                         INITIALIZATION + b"".join(MEDIA))

    def test_trickling_body_obeys_download_deadline(self):
        self.cdn.playlist("primary")
        path = '/primary/1080p/0.m4v'
        self.cdn.trickle[path] = 0.03
        reader = continuity.ChzzkContinuityReader(self.stream())
        self.addCleanup(reader.writer.close)
        before = time.monotonic()
        with self.assertRaises(continuity.Unavailable):
            reader.writer.http_bytes(self.cdn.url("primary").replace('list.m3u8', '0.m4v'))
        self.assertLess(time.monotonic() - before, 0.5)

    def test_playlist_jump_repairs_from_history(self):
        self.cdn.playlist("primary", indices=(0, 2, 3))
        self.cdn.playlist("history")
        result = self.read(self.stream([(self.cdn.url("primary"), False),
                                       (self.cdn.url("history"), True)]))
        self.assertEqual(result, INITIALIZATION + b"".join(MEDIA))
        self.assertIn("recovery_completed", [e["kind"] for e in self.events()])

    def test_unrecoverable_gap_stops_before_future_media(self):
        self.cdn.playlist("primary", indices=(0, 2, 3))
        result = self.read(self.stream())
        self.assertEqual(result, INITIALIZATION + MEDIA[0])
        self.assertIn("gap", [e["kind"] for e in self.events()])
        self.assertEqual(self.events()[-1]["resume_from"],
                         (START + timedelta(seconds=8)).isoformat())
        self.assertTrue(self.events()[-1]["after_gap"])

    def test_partial_repair_preserves_prefix_without_duplicate_on_retry(self):
        self.cdn.playlist("primary", indices=(0, 3))
        self.cdn.playlist("history", indices=(0, 1, 3))
        result = self.read(self.stream([(self.cdn.url("primary"), False),
                                       (self.cdn.url("history"), True)]))
        self.assertEqual(result, INITIALIZATION + MEDIA[0] + MEDIA[1])
        gap = next(e for e in self.events() if e["kind"] == "gap")
        self.assertEqual(gap["from"], (START + timedelta(seconds=8)).isoformat())

    def test_broadcast_end_drains_already_queued_media(self):
        self.cdn.playlist("primary")
        stream = self.stream()
        stream.continuity.provider = lambda: None
        self.assertEqual(self.read(stream), INITIALIZATION + b"".join(MEDIA))

    def test_backup_with_different_initialization_is_rejected(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("backup", initialization=INITIALIZATION + box(b"free", b"other"))
        self.cdn.statuses['/primary/1080p/1.m4v'] = 503
        result = self.read(self.stream([(self.cdn.url("primary"), False),
                                       (self.cdn.url("backup"), True)]))
        self.assertEqual(result, INITIALIZATION + MEDIA[0])
        self.assertIn("gap", [e["kind"] for e in self.events()])
        gap = next(e for e in self.events() if e["kind"] == "gap")
        self.assertEqual(gap["to"], (START + timedelta(seconds=8)).isoformat())

    def test_no_dates_disallow_cross_manifest_recovery(self):
        self.cdn.playlist("primary", dated=False)
        self.cdn.playlist("backup", dated=False)
        self.cdn.statuses['/primary/1080p/1.m4v'] = 503
        self.assertEqual(self.read(self.stream([(self.cdn.url("primary"), False),
                                               (self.cdn.url("backup"), True)])),
                         INITIALIZATION + MEDIA[0])

    def test_map_change_emits_resume_boundary(self):
        self.cdn.playlist("primary", changed_map=2)
        result = self.read(self.stream())
        self.assertEqual(result, INITIALIZATION + MEDIA[0] + MEDIA[1])
        boundary = self.events()[-1]
        self.assertEqual(boundary["reason"], "initialization_changed")
        self.assertEqual(boundary["resume_from"], (START + timedelta(seconds=8)).isoformat())

    def test_discontinuity_is_a_file_boundary(self):
        self.cdn.playlist("primary", discontinuity=2)
        self.assertEqual(self.read(self.stream()), INITIALIZATION + MEDIA[0] + MEDIA[1])
        self.assertEqual(self.events()[-1]["reason"], "discontinuity")

    def test_token_error_refreshes_api_and_segment_url(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("renewed")
        self.cdn.statuses['/primary/1080p/1.m4v'] = 403
        stream = self.stream()
        calls = []

        def provider():
            calls.append(True)
            return 1, [(self.cdn.url("renewed"), False)]

        stream.continuity.provider = provider
        self.assertEqual(self.read(stream), INITIALIZATION + b"".join(MEDIA))
        self.assertTrue(calls)

    def test_playlist_token_error_refreshes_without_waiting_30_seconds(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("renewed")
        self.cdn.statuses['/primary/1080p/list.m3u8'] = 403
        stream = self.stream()
        stream.continuity.provider = lambda: (1, [(self.cdn.url("renewed"), False)])
        self.assertEqual(self.read(stream), INITIALIZATION + b"".join(MEDIA))

    def test_token_error_refreshes_even_when_backup_succeeds(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("backup")
        self.cdn.statuses['/primary/1080p/1.m4v'] = 403
        paths = [(self.cdn.url("primary"), False), (self.cdn.url("backup"), True)]
        stream = self.stream(paths)
        refreshed = threading.Event()

        def provider():
            refreshed.set()
            return 1, paths

        stream.continuity.provider = provider
        self.assertEqual(self.read(stream), INITIALIZATION + b"".join(MEDIA))
        self.assertTrue(refreshed.is_set())

    def test_transient_api_refresh_failure_does_not_skip_media(self):
        self.cdn.playlist("primary")
        path = '/primary/1080p/1.m4v'
        self.cdn.statuses[path] = 403
        stream = self.stream()

        def provider():
            self.cdn.statuses[path] = 200
            raise continuity.Unavailable("API unavailable")

        stream.continuity.provider = provider
        with patch.object(continuity, "RECOVERY_TIMEOUT", 1.5):
            self.assertEqual(self.read(stream), INITIALIZATION + b"".join(MEDIA))

    def test_broadcast_end_interrupts_recovery_before_deadline(self):
        self.cdn.playlist("primary")
        self.cdn.statuses['/primary/1080p/1.m4v'] = 403
        stream = self.stream()
        stream.continuity.provider = lambda: None
        before = time.monotonic()
        self.assertEqual(self.read(stream), INITIALIZATION + MEDIA[0])
        self.assertLess(time.monotonic() - before, 0.5)
        self.assertTrue(stream.continuity.ended)

    def test_short_history_even_when_time_machine_flag_is_false(self):
        self.cdn.playlist("primary", indices=(3,))
        self.cdn.playlist("history")
        result = self.read(self.stream([(self.cdn.url("primary"), False),
                                       (self.cdn.url("history"), True)], lookback=3600, flag=False))
        self.assertEqual(result, INITIALIZATION + b"".join(MEDIA))
        self.assertEqual(next(e for e in self.events() if e["kind"] == "start")["available_seconds"], 16)
        self.assertIs(next(e for e in self.events() if e["kind"] == "start")["time_machine_active"], False)

    def test_no_history_still_records_current_broadcast(self):
        self.cdn.playlist("primary")
        self.assertEqual(self.read(self.stream(lookback=3600)), INITIALIZATION + MEDIA[3])
        self.assertEqual(next(e for e in self.events() if e["kind"] == "start")["available_seconds"], 4)

    def test_inaccessible_old_media_starts_at_surviving_tail(self):
        self.cdn.playlist("primary", indices=(3,))
        self.cdn.playlist("history")
        self.cdn.statuses['/history/1080p/0.m4v'] = 404
        self.cdn.statuses['/history/1080p/1.m4v'] = 410
        result = self.read(self.stream([(self.cdn.url("primary"), False),
                                       (self.cdn.url("history"), True)], lookback=3600))
        self.assertEqual(result, INITIALIZATION + MEDIA[2] + MEDIA[3])
        start = next(event for event in self.events() if event["kind"] == "start")
        self.assertEqual(start["available_seconds"], 8)

    def test_resume_only_records_requested_tail(self):
        self.cdn.playlist("primary")
        resume = dict(live_id=1, rendition="1080p",
                      **{"from": (START + timedelta(seconds=8)).isoformat()})
        self.assertEqual(self.read(self.stream(resume=resume)),
                         INITIALIZATION + MEDIA[2] + MEDIA[3])

    def test_gap_resume_uses_earliest_tail_and_reports_expired_position(self):
        self.cdn.playlist("primary", indices=(3,))
        self.cdn.playlist("history", indices=(2, 3))
        resume = dict(live_id=1, rendition="1080p", after_gap=True,
                      **{"from": (START + timedelta(seconds=4)).isoformat()})
        self.assertEqual(self.read(self.stream([(self.cdn.url("primary"), False),
                                               (self.cdn.url("history"), True)], resume=resume)),
                         INITIALIZATION + MEDIA[2] + MEDIA[3])
        gap = next(e for e in self.events() if e["kind"] == "gap")
        self.assertEqual(gap["reason"], "resume_unavailable")
        self.assertEqual(gap["from"], (START + timedelta(seconds=4)).isoformat())
        self.assertEqual(gap["to"], (START + timedelta(seconds=8)).isoformat())

    def test_strict_boundary_resume_does_not_silently_skip_expired_position(self):
        self.cdn.playlist("primary", indices=(2, 3))
        resume = dict(live_id=1, rendition="1080p",
                      **{"from": (START + timedelta(seconds=4)).isoformat()})
        self.assertEqual(self.read(self.stream(resume=resume)), b"")
        self.assertIn("gap", [e["kind"] for e in self.events()])

    def test_broadcast_identity_mismatch_rejects_candidate(self):
        self.cdn.playlist("primary")
        stream = self.stream()
        m, p = stream.continuity.candidates()[0]
        left = stream.continuity.locate(p.segments[0], m)
        right = stream.continuity.locate(p.segments[0], m)
        right.live_id = 2
        self.assertFalse(stream.continuity.matches(left, right))
        right.live_id = 1
        right.rendition = "720p"
        self.assertFalse(stream.continuity.matches(left, right))

    def test_cancel_during_recovery_wakes_reader(self):
        self.cdn.playlist("primary")
        self.cdn.delays['/primary/1080p/1.m4v'] = 0.3
        reader = self.stream().open()
        self.assertTrue(reader.read(len(INITIALIZATION) + len(MEDIA[0])))
        before = time.monotonic()
        reader.close()
        self.assertLess(time.monotonic() - before, 1)
        self.assertFalse(reader.read(65536))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_real_fmp4_recovery_preserves_1000_frames_and_audio(self):
        supplied = os.environ.get("CHZZK_TEST_MEDIA")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(supplied) if supplied else Path(directory) / "intact.mp4"
            if not supplied:
                subprocess.run([
                    "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=60",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "16.666667",
                    "-c:v", "libx264", "-preset", "ultrafast", "-g", "250", "-keyint_min", "250",
                    "-sc_threshold", "0", "-c:a", "aac", "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                    str(path),
                ], check=True, timeout=30)
            data = path.read_bytes()
            offset, start, fragments, initialization = 0, None, [], b""
            # The earlier real CHZZK reproduction has four styp-delimited
            # segments, each containing several moof/mdat partial fragments.
            has_styp = b"styp" in data[:1300]
            while offset < len(data):
                size, kind = struct.unpack_from(">I4s", data, offset)
                marker = kind == (b"styp" if has_styp else b"moof")
                if marker:
                    if start is None:
                        initialization = data[:offset]
                    else:
                        fragments.append(data[start:offset])
                    start = offset
                offset += size
            fragments.append(data[start:])
            self.assertEqual(len(fragments), 4)
            duration = 250 / 60
            self.cdn.playlist("primary", indices=(0, 2, 3), initialization=initialization,
                              media=fragments, duration=duration)
            self.cdn.playlist("history", initialization=initialization,
                              media=fragments, duration=duration)
            output = self.read(self.stream([(self.cdn.url("primary"), False),
                                           (self.cdn.url("history"), True)]))
            self.assertEqual(output, data)
            recorded = Path(directory) / "recovered.ts"
            subprocess.run(["ffmpeg", "-v", "error", "-fflags", "+genpts+discardcorrupt", "-i", "pipe:0",
                            "-c", "copy", "-bsf:v", "h264_mp4toannexb", "-mpegts_copyts", "0",
                            "-avoid_negative_ts", "make_zero", "-f", "mpegts", str(recorded)],
                           input=output, check=True, timeout=30)
            probe = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_packets",
                "-show_entries", "stream=codec_type,nb_read_frames:packet=codec_type,pts_time,duration_time",
                "-of", "json", str(recorded),
            ], timeout=30))
            video = next(s for s in probe["streams"] if s["codec_type"] == "video")
            self.assertEqual(int(video["nb_read_frames"]), 1000)
            audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
            self.assertGreater(int(audio["nb_read_frames"]), 700)
            for kind, limit in (("video", 0.04), ("audio", 0.06)):
                packets = sorted(float(p["pts_time"]) for p in probe["packets"]
                                 if p["codec_type"] == kind and "pts_time" in p)
                self.assertLess(max(b - a for a, b in zip(packets, packets[1:])), limit)


class LLHLSTests(unittest.TestCase):
    setUp = DeliveryTests.setUp
    stream = DeliveryTests.stream
    read = DeliveryTests.read
    events = DeliveryTests.events
    def ll_stream(self, extra=()):
        return self.stream([continuity.SourcePath(self.cdn.url("primary"), False, "llhls", "korean"), *extra])

    def test_variable_partial_groups_are_output_once_without_full_requests(self):
        groups = self.cdn.ll_playlist("primary")
        self.assertEqual(self.read(self.ll_stream()), INITIALIZATION + b"".join(groups))
        self.assertFalse(any(self.cdn.hits[f'/primary/1080p/{i}.m4v'] for i in range(4)))
        self.assertTrue(any(e["kind"] == "source" and e.get("mode") == "llhls" for e in self.events()))

    def test_missing_and_truncated_part_discard_group_before_full_fallback(self):
        for truncated in (False, True):
            with self.subTest(truncated=truncated):
                groups = self.cdn.ll_playlist("primary")
                path = '/primary/1080p/1_1.m4v'
                self.cdn.statuses.clear()
                self.cdn.truncate.clear()
                if truncated:
                    self.cdn.truncate.add(path)
                else:
                    self.cdn.statuses[path] = 404
                self.assertEqual(self.read(self.ll_stream()), INITIALIZATION + b"".join(groups))
                self.assertGreater(self.cdn.hits['/primary/1080p/1.m4v'], 0)

    def test_duplicate_uri_or_body_never_outputs_duplicate_parts(self):
        for duplicate_uri in (False, True):
            with self.subTest(duplicate_uri=duplicate_uri):
                groups = self.cdn.ll_playlist("primary")
                if duplicate_uri:
                    path = '/primary/1080p/list.m3u8'
                    self.cdn.assets[path] = self.cdn.assets[path].replace(b'1_1.m4v', b'1_0.m4v')
                else:
                    self.cdn.assets['/primary/1080p/1_1.m4v'] = self.cdn.assets['/primary/1080p/1_0.m4v']
                self.assertEqual(self.read(self.ll_stream()), INITIALIZATION + b"".join(groups))

    def test_plain_hls_without_parts_stays_compatible(self):
        self.cdn.playlist("primary")
        self.assertEqual(self.read(self.ll_stream()), INITIALIZATION + b"".join(MEDIA))
        self.assertTrue(any(e["kind"] == "source" and e.get("mode") == "hls" for e in self.events()))

    def test_encrypted_llhls_uses_existing_whole_segment_decryption(self):
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        groups = self.cdn.ll_playlist("primary")
        key = b"0123456789abcdef"
        iv = (9).to_bytes(16, "big")
        path = '/primary/1080p/list.m3u8'
        self.cdn.assets[path] = self.cdn.assets[path].replace(
            b'#EXT-X-MEDIA-SEQUENCE:0',
            b'#EXT-X-KEY:METHOD=AES-128,URI="key",IV=0x00000000000000000000000000000009\n#EXT-X-MEDIA-SEQUENCE:0')
        self.cdn.assets['/primary/1080p/key'] = key
        for i, group in enumerate(groups):
            self.cdn.assets[f'/primary/1080p/{i}.m4v'] = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(group, 16))
        self.assertEqual(self.read(self.ll_stream()), INITIALIZATION + b"".join(groups))
        self.assertFalse(any(self.cdn.hits[f'/primary/1080p/{i}_0.m4v'] for i in range(4)))

    def test_history_alternatives_are_limited_to_actual_last_hour(self):
        self.cdn.playlist("primary", duration=1200)
        self.cdn.playlist("history", duration=1200)
        source = self.stream([(self.cdn.url("primary"), False),
                              (self.cdn.url("history"), True)]).continuity
        source.discover()
        oldest = source.locate(source.primary.playlist.segments[0], source.primary)
        within_hour = source.locate(source.primary.playlist.segments[1], source.primary)
        self.assertFalse(list(source.alternatives(oldest)))
        self.assertTrue(list(source.alternatives(within_hour)))

    def test_discontinuity_sequence_mismatch_rejects_backup(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("history")
        for prefix, sequence in (("primary", 1), ("history", 2)):
            path = f'/{prefix}/1080p/list.m3u8'
            self.cdn.assets[path] += f'\n#EXT-X-DISCONTINUITY-SEQUENCE:{sequence}'.encode()
        source = self.stream([(self.cdn.url("primary"), False),
                              (self.cdn.url("history"), True)]).continuity
        source.discover()
        target = source.locate(source.primary.playlist.segments[0], source.primary)
        self.assertFalse(list(source.alternatives(target)))

    def test_korean_history_precedes_akamai_media(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("history")
        self.cdn.playlist("akamai")
        self.cdn.statuses['/primary/1080p/1.m4v'] = 503
        paths = [continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                 continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai"),
                 continuity.SourcePath(self.cdn.url("history"), True, cdn="korean")]
        stream = self.stream(paths)
        self.assertEqual(self.read(stream), INITIALIZATION + b"".join(MEDIA))
        self.assertGreater(self.cdn.hits['/history/1080p/1.m4v'], 0)
        self.assertEqual(self.cdn.hits['/akamai/1080p/1.m4v'], 0)
        self.assertEqual(stream.continuity.primary.cdn, "korean")

    def test_failed_korean_history_uses_akamai_same_interval(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("history")
        self.cdn.playlist("akamai")
        for prefix in ("primary", "history"):
            self.cdn.statuses[f'/{prefix}/1080p/1.m4v'] = 404
        paths = [continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                 continuity.SourcePath(self.cdn.url("history"), True, cdn="korean"),
                 continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai")]
        self.assertEqual(self.read(self.stream(paths)), INITIALIZATION + b"".join(MEDIA))
        self.assertGreater(self.cdn.hits['/akamai/1080p/1.m4v'], 0)

    def test_slow_history_lookup_does_not_lose_akamai_window(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("history")
        self.cdn.playlist("akamai")
        self.cdn.statuses['/primary/1080p/1.m4v'] = 404
        self.cdn.delays['/history/1080p/list.m3u8'] = 0.4
        paths = [continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                 continuity.SourcePath(self.cdn.url("history"), True, cdn="korean"),
                 continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai")]
        with patch.object(continuity, "HISTORY_BUDGET", 0.05):
            before = time.monotonic()
            self.assertEqual(self.read(self.stream(paths)), INITIALIZATION + b"".join(MEDIA))
            self.assertLess(time.monotonic() - before, 0.35)
        self.assertGreater(self.cdn.hits['/akamai/1080p/1.m4v'], 0)

    def test_akamai_only_source_keeps_recording(self):
        groups = self.cdn.ll_playlist("primary")
        paths = [continuity.SourcePath(self.cdn.url("primary"), False, "llhls", "akamai")]
        self.assertEqual(self.read(self.stream(paths)), INITIALIZATION + b"".join(groups))

    def test_standby_failure_and_delay_never_delay_primary_start(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("akamai")
        self.cdn.delays['/akamai/1080p/list.m3u8'] = 0.4
        self.cdn.statuses['/akamai/1080p/init.mp4'] = 503
        paths = [continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                 continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai")]
        before = time.monotonic()
        self.assertEqual(self.read(self.stream(paths)), INITIALIZATION + b"".join(MEDIA))
        self.assertLess(time.monotonic() - before, 0.3)

    def test_standby_checks_initialization_and_preserves_primary(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("akamai")
        paths = [continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                 continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai")]
        stream = self.stream(paths)
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        reader.writer.prepare_standby()
        reader.writer.standby_future.result(timeout=1)
        self.assertGreater(self.cdn.hits['/akamai/1080p/init.mp4'], 0)
        self.assertEqual(stream.continuity.primary.cdn, "korean")
        self.assertTrue(any(e["kind"] == "source" and e.get("state") == "ready" for e in self.events()))

    def test_failed_standby_initialization_emits_safe_status(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("akamai", initialization=b"invalid")
        stream = self.stream([continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                              continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai")])
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        reader.writer.prepare_standby()
        reader.writer.standby_future.result(timeout=1)
        self.assertTrue(any(e["kind"] == "source" and e.get("state") == "unavailable" for e in self.events()))
        self.assertNotIn("http://", self.stderr.getvalue())

    def test_substituted_akamai_probe_validates_same_interval_init_and_media(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("akamai")
        paths = [continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                 continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai", probe=True)]
        stream = self.stream(paths)
        stream.continuity.discover()
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        reader.writer.prepare_standby()
        reader.writer.standby_future.result(timeout=1)
        self.assertGreater(self.cdn.hits['/akamai/1080p/3.m4v'], 0)
        self.assertTrue(any(e["kind"] == "source" and e.get("state") == "ready" for e in self.events()))
        self.assertEqual(stream.continuity.primary.cdn, "korean")
        self.assertLessEqual(self.cdn.peak, 4)

    def test_substituted_probe_with_different_init_is_not_ready(self):
        self.cdn.playlist("primary")
        self.cdn.playlist("akamai", initialization=INITIALIZATION + box(b"free", b"changed"))
        paths = [continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                 continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai", probe=True)]
        stream = self.stream(paths)
        stream.continuity.discover()
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        reader.writer.prepare_standby()
        reader.writer.standby_future.result(timeout=1)
        self.assertFalse(any(e["kind"] == "source" and e.get("state") == "ready" for e in self.events()))
        self.assertTrue(any(e["kind"] == "source" and e.get("state") == "unavailable" for e in self.events()))

    def test_interval_gap_uses_akamai_after_slow_korean_history_budget(self):
        self.cdn.playlist("primary", indices=(0, 2, 3))
        self.cdn.playlist("history")
        self.cdn.playlist("akamai")
        self.cdn.delays['/history/1080p/list.m3u8'] = 0.4
        paths = [continuity.SourcePath(self.cdn.url("primary"), cdn="korean"),
                 continuity.SourcePath(self.cdn.url("history"), True, cdn="korean"),
                 continuity.SourcePath(self.cdn.url("akamai"), cdn="akamai")]
        with patch.object(continuity, "HISTORY_BUDGET", 0.05):
            self.assertEqual(self.read(self.stream(paths)), INITIALIZATION + b"".join(MEDIA))
        self.assertGreater(self.cdn.hits['/akamai/1080p/1.m4v'], 0)

    def test_published_parts_prefetch_and_blocking_reload_keep_completed_cursor(self):
        self.cdn.ll_playlist("primary", counts=(2, 2), end=False)
        complete = self.cdn.assets['/primary/1080p/list.m3u8']
        # Start with segment 0 complete and only part 0 of segment 1 published.
        lines = complete.decode().splitlines()
        marker = lines.index('#EXT-X-PROGRAM-DATE-TIME:' + (START + timedelta(seconds=4)).isoformat())
        first = "\n".join(lines[:marker + 2]).encode()
        first += b'\n#EXT-X-PRELOAD-HINT:TYPE=PART,URI="unpublished.m4v"'
        path = '/primary/1080p/list.m3u8'
        self.cdn.responses[path] = [first, first, complete + b'\n#EXT-X-ENDLIST']
        self.cdn.delays[path] = 0.1
        groups = [self.cdn.assets[f'/primary/1080p/{i}.m4v'] for i in range(2)]
        self.assertEqual(self.read(self.ll_stream()), INITIALIZATION + b"".join(groups))
        self.assertTrue(any('_HLS_msn=1&_HLS_part=1' in query for query in self.cdn.queries))
        self.assertEqual(self.cdn.hits['/primary/1080p/1_0.m4v'], 1)
        self.assertEqual(self.cdn.hits['/primary/1080p/unpublished.m4v'], 0)
        self.assertFalse(any(e["kind"] in {"gap", "recovery_started"} for e in self.events()))

    def test_pending_prefetch_is_shared_with_one_segment_thread(self):
        from types import SimpleNamespace
        groups = self.cdn.ll_playlist("primary", counts=(2, 2))
        self.session.set_option("stream-segment-threads", 1)
        stream = self.ll_stream()
        source = stream.continuity
        source.discover()
        target = source.locate(source.primary.playlist.segments[1], source.primary)
        self.cdn.delays['/primary/1080p/1_0.m4v'] = 0.15
        reader = continuity.ChzzkContinuityReader(stream)
        self.addCleanup(reader.writer.close)
        partial = SimpleNamespace(media_sequence=1, segments=[], trailing_parts=target.parts)
        reader.writer.prefetch_parts(source.primary, partial)
        self.assertEqual(reader.writer.fetch(target).media, groups[1])
        self.assertEqual(self.cdn.hits['/primary/1080p/1_0.m4v'], 1)
        self.assertLessEqual(self.cdn.peak, 2)

    def test_incomplete_part_durations_or_gap_flag_use_whole_segment(self):
        for marker in (b'DURATION=0.1,URI="1_0.m4v"', b'DURATION=1.3333333333333333,GAP=YES,URI="1_0.m4v"'):
            groups = self.cdn.ll_playlist("primary")
            path = '/primary/1080p/list.m3u8'
            self.cdn.assets[path] = self.cdn.assets[path].replace(b'DURATION=1.3333333333333333,URI="1_0.m4v"', marker)
            self.assertEqual(self.read(self.ll_stream()), INITIALIZATION + b"".join(groups))
            self.assertGreater(self.cdn.hits['/primary/1080p/1.m4v'], 0)

    def test_real_llhls_variable_groups_preserve_video_and_audio_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "parts.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=60",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "16.666667",
                "-c:v", "libx264", "-preset", "ultrafast", "-g", "60", "-sc_threshold", "0",
                "-c:a", "aac", "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                str(path),
            ], check=True, timeout=30)
            data = path.read_bytes()
            offsets = []
            offset = 0
            while offset < len(data):
                size, kind = struct.unpack_from(">I4s", data, offset)
                if kind == b"moof":
                    offsets.append(offset)
                offset += size
            self.assertEqual(len(offsets), 17)
            initialization = data[:offsets[0]]
            fragments = [data[a:b] for a, b in zip(offsets, offsets[1:] + [len(data)])]
            counts = (4, 5, 3, 5)
            lines = ['#EXTM3U', '#EXT-X-TARGETDURATION:5', '#EXT-X-MEDIA-SEQUENCE:0',
                     '#EXT-X-MAP:URI="init.mp4"', '#EXT-X-PART-INF:PART-TARGET=1']
            consumed = 0
            elapsed = 0.0
            for number, count in enumerate(counts):
                lines.append('#EXT-X-PROGRAM-DATE-TIME:' + (START + timedelta(seconds=elapsed)).isoformat())
                duration = 0.0
                for part in range(count):
                    seconds = 2 / 3 if consumed == 16 else 1.0
                    uri = f'{number}_{part}.m4v'
                    self.cdn.assets['/primary/1080p/' + uri] = fragments[consumed]
                    lines.append(f'#EXT-X-PART:DURATION={seconds},URI="{uri}"')
                    consumed += 1
                    duration += seconds
                lines.extend([f'#EXTINF:{duration},', f'{number}.m4v'])
                self.cdn.assets[f'/primary/1080p/{number}.m4v'] = b"".join(fragments[consumed - count:consumed])
                elapsed += duration
            lines.append('#EXT-X-ENDLIST')
            self.cdn.assets['/primary/1080p/list.m3u8'] = "\n".join(lines).encode()
            self.cdn.assets['/primary/1080p/init.mp4'] = initialization
            # A broken part in group 1 must discard that group and fetch the
            # full segment exactly once, while all other groups use parts.
            self.cdn.truncate.add('/primary/1080p/1_2.m4v')
            output = self.read(self.ll_stream())
            self.assertEqual(output, data)
            received = Path(directory) / "received.mp4"
            received.write_bytes(output)
            recorded = Path(directory) / "recorded.ts"
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(received), '-c', 'copy',
                            '-bsf:v', 'h264_mp4toannexb', '-f', 'mpegts', str(recorded)],
                           check=True, timeout=30)
            probe = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_packets',
                '-show_entries', 'stream=codec_type,nb_read_frames:packet=codec_type,pts_time',
                '-of', 'json', str(recorded),
            ], timeout=30))
            self.assertEqual(int(next(s for s in probe['streams'] if s['codec_type'] == 'video')['nb_read_frames']), 1000)
            self.assertGreater(int(next(s for s in probe['streams'] if s['codec_type'] == 'audio')['nb_read_frames']), 700)
            for kind, limit in (("video", 0.04), ("audio", 0.06)):
                pts = sorted(float(p['pts_time']) for p in probe['packets']
                             if p['codec_type'] == kind and 'pts_time' in p)
                self.assertLess(max(b - a for a, b in zip(pts, pts[1:])), limit)
            self.assertEqual(self.cdn.hits['/primary/1080p/1.m4v'], 1)


class SettingsAndProtocolTests(unittest.TestCase):
    def test_previous_hour_inheritance_and_strict_booleans(self):
        config = normalize_config({"record_previous_hour": "false"})
        self.assertFalse(config["record_previous_hour"])
        self.assertFalse(effective_previous_hour({}, False))
        self.assertTrue(effective_previous_hour({}, True))
        self.assertFalse(effective_previous_hour({"record_previous_hour": False}, True))
        self.assertTrue(effective_previous_hour({"record_previous_hour": True}, False))

    def test_history_option_is_not_repeated_on_retry(self):
        state = RecordingContinuity()
        state.begin(1)
        self.assertEqual(state.arguments(True)[1], "3600")
        state.accept(dict(kind="start", live_id=1, rendition="1080p", requested_seconds=3600,
                          available_seconds=600))
        state.begin(1)
        self.assertEqual(state.arguments(True)[1], "0")
        state.begin(2)
        self.assertEqual(state.arguments(True)[1], "3600")

    def test_boundary_carries_only_broadcast_rendition_and_position(self):
        state = RecordingContinuity()
        state.begin(1)
        state.accept(dict(kind="boundary", live_id=1, rendition="1080p", reason="discontinuity",
                          resume_from=START.isoformat()))
        self.assertTrue(state.boundary)
        args = state.arguments(True)
        self.assertEqual(set(json.loads(args[-1])), {"live_id", "rendition", "from"})

    def test_invalid_protocol_events_do_not_change_state(self):
        self.assertIsNone(parse_event(EVENT_PREFIX + '{"version":1}'))
        self.assertIsNone(parse_event(EVENT_PREFIX + "[]"))
        self.assertIsNone(parse_event(EVENT_PREFIX + "x" * 5000))

    def test_gap_boundary_preserves_resume_without_repeating_history(self):
        state = RecordingContinuity()
        state.begin(1)
        state.accept(dict(kind="boundary", live_id=1, rendition="1080p",
                          reason="segment_unavailable", resume_from=START.isoformat(), after_gap=True))
        arguments = state.arguments(True)
        self.assertEqual(arguments[1], "0")
        self.assertEqual(json.loads(arguments[-1])["from"], START.isoformat())
        self.assertTrue(json.loads(arguments[-1])["after_gap"])

    def test_diagnostics_never_forward_exception_text_or_signed_urls(self):
        state = RecordingContinuity()
        state.begin(1)
        event = dict(version=1, kind="diagnostic", live_id=1, rendition="1080p",
                     stage="media", role="primary", category="http", status=403,
                     sequence=42, at=START.isoformat(),
                     exception="https://cdn.example/media?token=secret", cookie="secret")
        parsed = parse_event(EVENT_PREFIX + json.dumps(event))
        _, fields, warning = state.accept(parsed)
        self.assertFalse(warning)
        self.assertNotIn("secret", fields["details"])
        self.assertNotIn("http", fields["details"].replace('"http"', ''))
        for name, bad in (("status", True), ("sequence", -1), ("role", "secret"),
                          ("category", "https://cdn.example"), ("after_gap", "false"),
                          ("stage", []), ("role", {}), ("category", []), ("kind", [])):
            malformed = dict(event, **{name: bad})
            self.assertIsNone(parse_event(EVENT_PREFIX + json.dumps(malformed)))

    def test_diagnostic_cache_is_bounded_and_does_not_store_exception_text(self):
        from types import SimpleNamespace
        source = continuity.ContinuitySource(
            SimpleNamespace(session=None, _url="https://cdn.example/1080p/list.m3u8", name="test"),
            None, 1, [])
        with patch.object(source, "emit") as emit:
            error = continuity.Unavailable("signed secret URL", 404, "http")
            for sequence in range(140):
                located = SimpleNamespace(num=sequence, date=START)
                source.report_failure("media", "primary", error, located)
                source.report_failure("media", "primary", error, located)
        self.assertEqual(emit.call_count, 140)
        self.assertEqual(len(source.diagnostics), 128)
        self.assertNotIn("secret", str(source.diagnostics))

    def test_user_text_is_translated_in_every_locale(self):
        for locale in SUPPORTED_LANGUAGES:
            for key in ("gui.previous_hour", "gui.previous_hour_help", "record.history_short",
                        "record.recovery_started", "record.continuity_gap", "record.continuity_diagnostic",
                        "record.source_selected", "record.source_ready", "record.source_absent",
                        "record.source_unavailable", "record.cdn_korean", "record.cdn_akamai",
                        "record.cdn_unknown", "record.mode_llhls", "record.mode_hls",
                        *("record.continuity_reason_" + reason for reason in REASONS)):
                self.assertNotEqual(translate(locale, key, channel_name="test", seconds=1,
                                              at="now", start="a", end="b", reason="test", details="test",
                                              cdn="test", mode="test"), key)
            self.assertIn("\n6.", translate(locale, "gui.cli_recording_menu"))

    def test_rejects_truncated_containers(self):
        with self.assertRaises(continuity.Unavailable):
            continuity.validate_media(MEDIA[0][:-1])
        with self.assertRaises(continuity.Unavailable):
            continuity.validate_media(INITIALIZATION[:-1], is_map=True)

    def test_api_cdn_extraction_requires_advertised_http_url(self):
        import base64
        encoded = base64.b64encode(b"https://cdn.example/master.m3u8").decode()
        paths = source_paths([dict(mediaId="HLS", protocol="HLS", path="https://cdn.example/live",
                                   encodingTrack=[dict(p2pPath="https://p2p.example/?cdn_url=" + encoded)])])
        self.assertEqual([(p.url, p.history) for p in paths],
                         [("https://cdn.example/live", False),
                          ("https://cdn.example/master.m3u8", True)])

    def test_korean_llhls_stays_primary_with_additional_akamai_probe(self):
        paths = source_paths([
            dict(mediaId="HLS", protocol="HLS", path="https://livecloud.akamaized.net/master.m3u8"),
            dict(mediaId="HLS", protocol="HLS", path="https://nvelop-livecloud.pstatic.net/master.m3u8"),
            dict(mediaId="LLHLS", protocol="HLS", path="https://nvelop-livecloud.pstatic.net/ll/master.m3u8"),
        ])
        self.assertEqual([(p.cdn, p.mode) for p in paths],
                         [("korean", "llhls"), ("korean", "hls"), ("akamai", "llhls"),
                          ("akamai", "hls")])
        self.assertIn('/ll/master.m3u8', paths[0].url)
        self.assertFalse(paths[-1].probe)

    def test_akamai_probe_keeps_signed_path_query_and_only_known_origins(self):
        url = 'https://nvelop-livecloud.pstatic.net/signed/path/master.m3u8?hdnts=a%2Fb%20c&vp=1'
        paths = source_paths([dict(mediaId="LLHLS", protocol="HLS", path=url)])
        self.assertEqual(paths[0].url, url)
        self.assertEqual(paths[1].url, url.replace('nvelop-livecloud.pstatic.net', 'livecloud.akamaized.net', 1))
        self.assertTrue(paths[1].probe)
        for host in ('nvelop-livecloud.pstatic.net.evil.example', 'unrecognized.pstatic.net'):
            other = source_paths([dict(mediaId="HLS", protocol="HLS", path=f'https://{host}/master.m3u8')])
            self.assertEqual(len(other), 1)

    def test_source_events_reject_invalid_values_and_remove_secrets(self):
        event = dict(version=1, kind="source", live_id=1, rendition="1080p",
                     cdn="akamai", mode="llhls", state="ready", url="https://secret.example/token")
        parsed = parse_event(EVENT_PREFIX + json.dumps(event))
        self.assertNotIn("url", parsed)
        for key in ("cdn", "mode", "state"):
            bad = dict(event, **{key: ["invalid"]})
            self.assertIsNone(parse_event(EVENT_PREFIX + json.dumps(bad)))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class RecorderIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_boundary_finalizes_file_and_resumes_without_replaying_history(self):
        await self.check_finalized_files("discontinuity")

    async def test_unrecoverable_gap_finalizes_file_and_resumes_earliest_tail(self):
        await self.check_finalized_files("gap")

    async def test_failed_fragment_resumes_after_only_the_missing_fragment(self):
        await self.check_finalized_files("failed_segment")

    async def check_finalized_files(self, mode):
        import chzzk_record as recorder
        from unittest.mock import Mock

        with tempfile.TemporaryDirectory() as directory, CDN() as cdn:
            fixture = Path(directory) / "fixture.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=60",
                "-f", "lavfi", "-i", "sine=sample_rate=48000", "-t", "16.666667",
                "-c:v", "libx264", "-preset", "ultrafast", "-g", "250", "-sc_threshold", "0",
                "-c:a", "aac", "-movflags", "frag_keyframe+empty_moov+default_base_moof", str(fixture),
            ], check=True, timeout=30)
            data = fixture.read_bytes()
            offset, starts = 0, []
            while offset < len(data):
                size, kind = struct.unpack_from(">I4s", data, offset)
                if kind == b"moof":
                    starts.append(offset)
                offset += size
            fragments = [data[a:b] for a, b in zip(starts, starts[1:] + [len(data)])]
            initialization = data[:starts[0]]
            for prefix in ("primary", "continued"):
                indices = ((0, 1, 2, 3) if mode == "discontinuity" or
                           (mode == "failed_segment" and prefix == "primary") else
                           (0, 2, 3) if prefix == "primary" else (2, 3))
                cdn.playlist(prefix, indices=indices, initialization=initialization, media=fragments,
                             duration=250 / 60, discontinuity=2 if mode == "discontinuity" else None)
            if mode == "failed_segment":
                cdn.statuses['/primary/1080p/1.m4v'] = 503
            if mode != "discontinuity":
                path = '/continued/1080p/list.m3u8'
                complete = cdn.assets[path]
                live = complete.replace(b'\n#EXT-X-ENDLIST', b'')
                cdn.responses[path] = [live] * 4 + [complete]
            stop = asyncio.Event()
            commands = []

            async def live_info(*_):
                if len(commands) >= 2:
                    stop.set()
                    return "CLOSE", {}
                return "OPEN", {"liveId": 1, "liveTitle": "test recording"}

            async def start_streamlink(sandbox, command):
                commands.append(command)
                resume = (json.loads(command[command.index("--chzzk-resume") + 1])
                          if "--chzzk-resume" in command else None)
                lookback = int(command[command.index("--chzzk-start-lookback") + 1])
                prefix = "primary" if len(commands) == 1 else "continued"
                settings = dict(url=cdn.url(prefix), resume=resume, lookback=lookback)
                code = """
import json,sys
import hls_continuity
from streamlink import Streamlink
from plugin.chzzk import ChzzkHLSStream
hls_continuity.RECOVERY_TIMEOUT=0.6;hls_continuity.HEDGE_DELAY=0.05
settings=json.loads(sys.argv[1]);session=Streamlink()
session.set_option('hls-live-edge',1)
stream=ChzzkHLSStream(session,settings['url'],'test',live_id=1,
    source_paths=[(settings['url'],False),(settings['url'],True)],
    start_lookback=settings['lookback'],resume=settings['resume'])
stream.continuity.provider=lambda:(1,[(settings['url'],False),(settings['url'],True)])
reader=stream.open()
try:
    while chunk:=reader.read(65536):
        sys.stdout.buffer.write(chunk);sys.stdout.buffer.flush()
finally:
    reader.close()
"""
                sandbox.stream_process = await recorder.create_isolated_subprocess_exec(
                    os.sys.executable, "-c", code, json.dumps(settings),
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                return sandbox.stream_process

            config = normalize_config({})
            diagnostic_logger = Mock()
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(recorder, "shutdown_event", stop))
                stack.enter_context(patch.object(recorder, "logger", diagnostic_logger))
                stack.enter_context(patch.object(recorder, "channel_progress", {}))
                stack.enter_context(patch.object(recorder, "channel_progress_lock", asyncio.Lock()))
                stack.enter_context(patch.object(recorder, "get_session_cookies", AsyncMock(return_value={})))
                stack.enter_context(patch.object(recorder, "load_config_async", AsyncMock(return_value={})))
                stack.enter_context(patch.object(recorder, "get_live_info", live_info))
                stack.enter_context(patch.object(recorder, "prepare_recording_quality", AsyncMock(
                    return_value={"stream": "best", "filters": []})))
                stack.enter_context(patch.object(recorder.RecordingProcessSandbox, "start_streamlink", start_streamlink))
                await asyncio.wait_for(recorder.record_stream(
                    {"id": "test", "name": "fixture", "output_dir": directory, "active": "on"},
                    {}, None, 0, 1, Path(shutil.which("ffmpeg")), 2,
                    config["hevc_settings"], config["av1_settings"], "ts", 0,
                    config["h264_settings"], config["quality_settings"], True,
                ), timeout=25)
            outputs = list(Path(directory).glob("*.ts"))
            self.assertEqual(len(outputs), 2, (list(Path(directory).iterdir()),
                                               diagnostic_logger.mock_calls))
            self.assertFalse(list(Path(directory).glob("*.part")))
            frame_counts = []
            for output in outputs:
                data = json.loads(subprocess.check_output([
                    "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                    "-show_entries", "stream=nb_read_frames", "-of", "json", str(output),
                ], timeout=10))
                frame_counts.append(int(data["streams"][0]["nb_read_frames"]))
            self.assertEqual(sorted(frame_counts), [500, 500] if mode == "discontinuity" else [250, 500])
            self.assertEqual([c[c.index("--chzzk-start-lookback") + 1] for c in commands], ["3600", "0"])
            self.assertIn("--chzzk-resume", commands[1])
            if mode != "discontinuity":
                self.assertTrue(json.loads(commands[1][commands[1].index("--chzzk-resume") + 1])["after_gap"])
                self.assertTrue(any("복구하지 못했습니다" in str(call)
                                    for call in diagnostic_logger.warning.call_args_list))
            self.assertNotIn("--hls-live-restart", commands[0])


class RecorderPreferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_waiting_channel_uses_updated_preference_at_next_start(self):
        import chzzk_record as recorder

        channel = {"id": "test", "record_previous_hour": None}
        config = {"channels": [channel], "record_previous_hour": False}
        with patch.object(recorder, "load_config_async", AsyncMock(return_value=config)):
            self.assertFalse(await recorder.previous_hour_for_start(channel, False))
            config["record_previous_hour"] = True
            self.assertTrue(await recorder.previous_hour_for_start(channel, False))
            config["channels"] = [dict(channel, record_previous_hour=False)]
            self.assertFalse(await recorder.previous_hour_for_start(channel, True))


if __name__ == "__main__":
    unittest.main()
