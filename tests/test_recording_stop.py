"""Cooperative shutdown against real fMP4 output and recorder failure evidence."""

import asyncio
import contextlib
import io
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import chzzk_record as recorder
from config_store import normalize_config
from continuity_report import ContinuityReport, summarize
from i18n import SUPPORTED_LANGUAGES, translate
from recording_buffer import BufferFull, MediaBuffer
from recording_continuity import EVENT_PREFIX, parse_event
from test_hls_continuity import CDN, INITIALIZATION, MEDIA, START


class StopControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_file_is_private_fresh_idempotent_and_cleaned(self):
        sandbox = recorder.RecordingProcessSandbox('fixture', 'test')
        old = sandbox.stop_file

        async def cooperative_wait():
            while not old.is_file():
                await asyncio.sleep(0.001)
            process.returncode = 0
            return 0

        process = Mock(returncode=None, wait=cooperative_wait)
        sandbox.stream_process = process
        with patch.object(recorder, 'terminate_process', AsyncMock()) as terminate:
            await sandbox.stop_streamlink()
            await sandbox.stop_streamlink()
            terminate.assert_not_awaited()
        if os.name != 'nt':
            self.assertEqual(os.stat(old).st_mode & 0o777, 0o600)
        replacement = recorder.RecordingProcessSandbox('fixture', 'test')
        try:
            self.assertNotEqual(old, replacement.stop_file)
            self.assertFalse(replacement.stop_file.exists())
            self.assertEqual(replacement.stop_arguments()[0], '--chzzk-stop-file')
        finally:
            await sandbox.cleanup()
            await replacement.cleanup()
        self.assertFalse(old.parent.exists())
        self.assertFalse(replacement.stop_file.parent.exists())

    async def test_request_write_failure_and_timeout_fail_report_once(self):
        for failure in ('write', 'timeout', 'directory'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                report_path = Path(directory) / 'report.jsonl'
                report = ContinuityReport(report_path)
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(recorder, 'continuity_report', report))
                    stack.enter_context(patch.object(recorder, 'logger', Mock()))
                    stack.enter_context(patch.object(recorder, 'STREAMLINK_COOPERATIVE_STOP_SECONDS', 0.02))
                    if failure == 'directory':
                        stack.enter_context(patch.object(recorder.tempfile, 'TemporaryDirectory',
                                                         side_effect=OSError('secret')))
                    sandbox = recorder.RecordingProcessSandbox('fixture', 'test')
                    if failure == 'write':
                        stack.enter_context(patch.object(Path, 'touch', side_effect=OSError('secret')))
                    process = Mock(returncode=None)

                    async def wait():
                        while process.returncode is None:
                            await asyncio.sleep(0.001)
                        return process.returncode

                    async def terminate(*args, **kwargs):
                        self.assertLessEqual(kwargs['timeout'], 20)
                        process.returncode = -15

                    process.wait = wait
                    sandbox.stream_process = process
                    fallback = stack.enter_context(patch.object(recorder, 'terminate_process',
                                                                 AsyncMock(side_effect=terminate)))
                    await sandbox.stop_streamlink()
                    await sandbox.stop_streamlink()
                    sandbox.record_output_error('forced_stop')
                    await sandbox.cleanup()
                    self.assertEqual(fallback.await_count, 1)
                report.finish(True)
                rows = [json.loads(line) for line in report_path.read_text().splitlines()]
                errors = [row for row in rows if row['kind'] == 'output_error']
                self.assertEqual(len(errors), 1)
                self.assertEqual(errors[0]['category'], 'forced_stop')
                self.assertNotIn('secret', report_path.read_text())
                self.assertFalse(summarize(report_path.read_text().splitlines())['passed'])

    async def test_ffmpeg_corruption_is_reported_without_raw_lines_or_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.jsonl'
            report = ContinuityReport(path)
            sandbox = recorder.RecordingProcessSandbox('fixture', 'test')
            stream = asyncio.StreamReader()
            stream.feed_data(b'Packet corrupt secret-url\nPacket corrupt secret-cookie\npartial file\npartial file\n')
            stream.feed_eof()
            with patch.object(recorder, 'continuity_report', report), patch.object(recorder, 'logger', Mock()):
                await recorder.read_stream(stream, 'test', 'stderr', sandbox.record_output_error)
            await sandbox.cleanup()
            report.finish(True)
            text = path.read_text()
            self.assertNotIn('secret', text)
            rows = [json.loads(line) for line in text.splitlines()]
            self.assertEqual([r['category'] for r in rows if r['kind'] == 'output_error'],
                             ['corrupt_packet', 'partial_input'])
            self.assertEqual(summarize(text.splitlines())['error_count'], 3)  # No checkpoint plus two output errors.

    async def test_shutdown_warnings_are_translated(self):
        for language in SUPPORTED_LANGUAGES:
            for key in ('stream_stop_request_failed', 'stream_stop_timeout', 'stop_cleanup_failed',
                        'output_error', 'output_error_corrupt_packet', 'output_error_partial_input',
                        'output_error_forced_stop'):
                key = 'record.' + key
                self.assertNotEqual(translate(language, key, channel_name='fixture', category='test'), key)


class BufferReasonTests(unittest.TestCase):
    def test_stale_and_actual_limit_reasons_are_distinct(self):
        metadata = dict(at=START.isoformat(), duration=4, number=0, discontinuity=False,
                        discontinuity_id=0, cdn='korean', mode='hls')
        for reason in ('already_output', 'time_limit', 'byte_limit', 'count_limit'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                buffer = MediaBuffer(directory, 1, '1080p')
                if reason == 'already_output':
                    buffer.discard_before(START + timedelta(seconds=4))
                elif reason == 'time_limit':
                    buffer.max_seconds = 3
                elif reason == 'byte_limit':
                    buffer.max_bytes = 1  # Must include payload and metadata reservation.
                else:
                    buffer.rows = {str(i): dict(metadata) for i in range(2048)}
                with self.assertRaises(BufferFull) as failure:
                    buffer.store(metadata, INITIALIZATION, MEDIA[0])
                self.assertEqual(failure.exception.reason, reason)
                self.assertEqual(buffer.used, 0)

    def test_snapshot_optional_reason_is_bounded_and_legacy_is_accepted(self):
        event = dict(version=1, kind='recovery_snapshot', live_id=1, rendition='1080p',
                     observed_at=START.isoformat(), cdn='korean', mode='hls', role='current',
                     result='buffer_full', lookup_result='available', elapsed_ms=1,
                     buffered_count=0, buffered_bytes=0)
        self.assertIsNotNone(parse_event(EVENT_PREFIX + json.dumps(event)))
        for reason in ('already_output', 'time_limit', 'byte_limit', 'count_limit'):
            clean = parse_event(EVENT_PREFIX + json.dumps(dict(
                event, buffer_reason=reason,
                result='buffer_skipped' if reason == 'already_output' else 'buffer_full',
                url='secret', exception='secret')))
            self.assertEqual(clean['buffer_reason'], reason)
            self.assertNotIn('secret', json.dumps(clean))
        for reason in ('secret', [], True, None):
            self.assertIsNone(parse_event(EVENT_PREFIX + json.dumps(dict(event, buffer_reason=reason))))

    def test_output_errors_fail_even_with_contiguous_checkpoints(self):
        checkpoint = dict(version=1, kind='checkpoint', channel_id='test', live_id=1, rendition='1080p',
                          **{'from': START.isoformat(), 'to': (START + timedelta(seconds=4)).isoformat()})
        base = [dict(version=1, kind='report_started'), checkpoint]
        footer = dict(version=1, kind='report_finished', complete=True)
        for category in ('corrupt_packet', 'partial_input', 'forced_stop', 'invalid', []):
            error = dict(version=1, kind='output_error', channel_id='test',
                         observed_at=START.isoformat(), category=category)
            result = summarize(json.dumps(row) for row in [*base, error, footer])
            self.assertFalse(result['passed'])
            self.assertEqual(result['error_count'], 1)
            self.assertEqual(result['gap_count'], 0)
            self.assertEqual(result['duplicate_count'], 0)
        malformed = dict(version=1, kind='output_error', channel_id='test',
                         observed_at='invalid', category='corrupt_packet')
        self.assertFalse(summarize(json.dumps(r) for r in [*base, malformed, footer])['passed'])
        # This is recorder evidence, never an accepted child protocol message.
        self.assertIsNone(parse_event(EVENT_PREFIX + json.dumps(dict(checkpoint, kind='output_error'))))


CHILD = r'''
import json,sys,time
from pathlib import Path
from streamlink import Streamlink
from plugin.chzzk import ChzzkHLSStream
settings=json.loads(sys.argv[1])
session=Streamlink()
session.set_option('hls-live-edge',4)
session.set_option('ringbuffer-size',4096)
session.set_option('stream-segment-timeout',0.2)
session.set_option('stream-segment-attempts',1)
url=settings['url'];marker=Path(settings['marker']);stop=Path(settings['stop_file'])
stream=ChzzkHLSStream(session,url,'test',live_id=1,
    source_paths=[(url,False),(url,True)],start_lookback=3600,
    buffer_dir=settings['buffer_dir'],stop_file=str(stop))
stream.continuity.provider=lambda:(1,[(url,False),(url,True)])
if settings['mode']=='recovery':
    emit=stream.continuity.emit
    def observe(kind,**fields):
        emit(kind,**fields)
        writer=stream.continuity.writer
        if kind=='recovery_started' and writer and writer.previous:
            marker.touch()
    stream.continuity.emit=observe
reader=stream.__reader__(stream)
if settings['mode']!='recovery':
    write=reader.buffer.write
    paused=False
    def partial(data):
        global paused
        if not paused and data[:8].endswith(b'moof'):
            paused=True
            write(data[:4096])
            marker.touch()
            deadline=time.monotonic()+10
            while not stop.is_file():
                if time.monotonic()>deadline: raise RuntimeError('Stop not received')
                time.sleep(.005)
            return write(data[4096:])
        return write(data)
    reader.buffer.write=partial
reader.open()
try:
    while chunk:=reader.read(4096):
        sys.stdout.buffer.write(chunk);sys.stdout.buffer.flush()
finally:
    reader.close()
'''


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class RealStopTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_during_fragment_completes_video_audio_and_checkpoint(self):
        await self.record('delivery')

    async def test_stop_with_backpressure_drains_complete_fragment(self):
        await self.record('backpressure')

    async def test_stop_during_recovery_preserves_last_complete_fragment(self):
        await self.record('recovery')

    async def test_task_cancellation_uses_same_complete_fragment_shutdown(self):
        await self.record('cancel')

    async def record(self, mode):
        with tempfile.TemporaryDirectory() as directory, CDN() as cdn:
            root = Path(directory)
            fixture = root / 'source.mp4'
            subprocess.run([
                'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=160x90:rate=60',
                '-f', 'lavfi', '-i', 'sine=sample_rate=48000', '-t', '16.666667',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-g', '250', '-sc_threshold', '0',
                '-c:a', 'aac', '-movflags', 'frag_keyframe+empty_moov+default_base_moof', str(fixture)
            ], check=True, timeout=30)
            data = fixture.read_bytes()
            starts, offset = [], 0
            while offset < len(data):
                size, kind = struct.unpack_from('>I4s', data, offset)
                if kind == b'moof':
                    starts.append(offset)
                offset += size
            initialization = data[:starts[0]]
            fragments = [data[a:b] for a, b in zip(starts, starts[1:] + [len(data)])]
            cdn.playlist('primary', initialization=initialization, media=fragments,
                         duration=250 / 60, end=False)
            if mode == 'recovery':
                cdn.statuses['/primary/1080p/1.m4v'] = 503
            marker = root / 'delivery-started'
            stop = asyncio.Event()
            report_path = root / 'report.jsonl'
            report = ContinuityReport(report_path)
            commands, received = [], bytearray()
            pipe_started = asyncio.Event()
            original_pipe = recorder.pipe_stream_to_stdin

            async def start(sandbox, command):
                commands.append(command)
                settings = dict(url=cdn.url('primary'), marker=str(marker), mode=mode,
                                buffer_dir=command[command.index('--chzzk-buffer-dir') + 1],
                                stop_file=command[command.index('--chzzk-stop-file') + 1])
                sandbox.stream_process = await recorder.create_isolated_subprocess_exec(
                    os.sys.executable, '-c', CHILD, json.dumps(settings),
                    stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)
                return sandbox.stream_process

            async def pipe(reader, writer, name):
                if mode == 'backpressure':
                    # Keep the producer blocked while its stop request is handled.
                    await stop.wait()
                    await asyncio.sleep(0.2)
                pipe_started.set()

                class Tee:
                    async def read(self, size):
                        chunk = await reader.read(size)
                        received.extend(chunk)
                        return chunk

                return await original_pipe(Tee(), writer, name)

            logger = Mock()
            config = normalize_config({})
            with contextlib.ExitStack() as stack:
                for name, value in (('shutdown_event', stop), ('logger', logger),
                                    ('continuity_report', report), ('channel_progress', {}),
                                    ('channel_progress_lock', asyncio.Lock())):
                    stack.enter_context(patch.object(recorder, name, value))
                stack.enter_context(patch.object(recorder, 'get_session_cookies', AsyncMock(return_value={})))
                stack.enter_context(patch.object(recorder, 'load_config_async', AsyncMock(return_value={})))
                stack.enter_context(patch.object(recorder, 'get_live_info', AsyncMock(
                    return_value=('OPEN', {'liveId': 1, 'liveTitle': 'stop fixture'}))))
                stack.enter_context(patch.object(recorder, 'prepare_recording_quality', AsyncMock(
                    return_value={'stream': 'best', 'filters': []})))
                stack.enter_context(patch.object(recorder.RecordingProcessSandbox, 'start_streamlink', start))
                stack.enter_context(patch.object(recorder, 'pipe_stream_to_stdin', pipe))
                task = asyncio.create_task(recorder.record_stream(
                    dict(id='test', name='fixture', output_dir=directory, active='on'), {}, None,
                    0, 1, Path(shutil.which('ffmpeg')), 2, config['hevc_settings'],
                    config['av1_settings'], 'mkv', 0, config['h264_settings'],
                    config['quality_settings'], True))
                try:
                    async with asyncio.timeout(10):
                        while not marker.exists():
                            if task.done():
                                task.result()
                                self.fail(str(logger.mock_calls))
                            await asyncio.sleep(0.01)
                    if mode == 'backpressure':
                        self.assertFalse(pipe_started.is_set())
                    if mode == 'cancel':
                        task.cancel()
                    else:
                        stop.set()
                    await asyncio.wait_for(task, timeout=25)
                finally:
                    if not task.done():
                        stop.set()
                        await task
                    report.finish(True)
            expected = initialization + fragments[0]
            self.assertEqual(bytes(received), expected)
            self.assertEqual(len(commands), 1)
            summary = summarize(report_path.read_text().splitlines())
            self.assertTrue(summary['passed'], (summary, logger.mock_calls))
            self.assertEqual(summary['checkpoint_count'], 1)
            self.assertEqual(summary['error_count'], 0)
            self.assertFalse(Path(commands[0][commands[0].index('--chzzk-stop-file') + 1]).parent.exists())
            self.assertFalse(list(root.glob('.chzzk-buffer-*')))
            outputs = list(root.glob('*.mkv'))
            self.assertEqual(len(outputs), 1)
            prefix = root / 'prefix.mp4'
            prefix.write_bytes(expected)
            def probe(path):
                return json.loads(subprocess.check_output([
                    'ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_packets',
                    '-show_entries', 'stream=codec_type,nb_read_frames:packet=codec_type,pts_time',
                    '-of', 'json', str(path)], timeout=20))
            baseline, recorded = probe(prefix), probe(outputs[0])
            for kind in ('video', 'audio'):
                before = next(s for s in baseline['streams'] if s['codec_type'] == kind)
                after = next(s for s in recorded['streams'] if s['codec_type'] == kind)
                self.assertEqual(int(after['nb_read_frames']), int(before['nb_read_frames']))
                pts = sorted(float(p['pts_time']) for p in recorded['packets']
                             if p['codec_type'] == kind and 'pts_time' in p)
                source_pts = sorted(float(p['pts_time']) for p in baseline['packets']
                                    if p['codec_type'] == kind and 'pts_time' in p)
                self.assertEqual(len(pts), len(source_pts))
                self.assertEqual(len(pts), len(set(pts)))
                # AAC priming gives the fixture an initial video interval longer
                # than 1/60s. Compare every timestamp with that actual input,
                # allowing only Matroska's millisecond rounding and start offset.
                for actual, original in zip(pts, source_pts):
                    self.assertLessEqual(abs((actual-pts[0])-(original-source_pts[0])), 0.002)
                self.assertLessEqual(max(b-a for a,b in zip(pts,pts[1:])),
                                     max(b-a for a,b in zip(source_pts,source_pts[1:])) + 0.002)
            self.assertEqual(int(next(s for s in recorded['streams']
                                      if s['codec_type']=='video')['nb_read_frames']), 250)
            decoded = subprocess.run([
                'ffmpeg', '-v', 'warning', '-xerror', '-i', str(outputs[0]), '-map', '0',
                '-fps_mode:v', 'passthrough', '-enc_time_base:v', '1:1000', '-f', 'null', '-'
            ], capture_output=True, timeout=20)
            self.assertEqual(decoded.returncode, 0, decoded.stderr.decode())
            self.assertEqual(decoded.stderr, b'')


if __name__ == '__main__':
    unittest.main()
