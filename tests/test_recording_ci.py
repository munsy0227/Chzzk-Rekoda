"""Recording CI lifecycle checks without contacting CHZZK or waiting minutes."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, translate
from scripts import run_recording_test as runner


FIXTURE = r'''
import argparse, json, os, subprocess, sys, time
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--gui-events', action='store_true')
parser.add_argument('--config', type=Path)
parser.add_argument('--continuity-report', type=Path)
args = parser.parse_args()
mode = os.environ['CI_FIXTURE_MODE']
directory = args.continuity_report.parent
if mode == 'startup-failure':
    raise SystemExit(7)
args.config.parent.joinpath('log.log').write_text(
    'Recording started for fixture\n' + ('ffmpeg failed for fixture\n' if mode == 'ffmpeg-error' else ''),
    encoding='utf-8')
if mode != 'no-output':
    directory.joinpath('녹화 segment.ts').write_bytes(b'' if mode == 'empty' else b'media')
with args.continuity_report.open('w', encoding='utf-8') as report:
    report.write(json.dumps(dict(version=1, kind='report_started')) + '\n')
    for first, last in [(0, 4), (8 if mode == 'gap' else 4, 12 if mode == 'gap' else 8)]:
        report.write(json.dumps(dict(version=1, kind='checkpoint', channel_id='test',
            live_id=1, rendition='1080p', **{
                'from': f'2026-10-11T00:00:{first:02d}+00:00',
                'to': f'2026-10-11T00:00:{last:02d}+00:00'})) + '\n')
    report.flush()
    if mode in {'corrupt_packet', 'partial_input', 'forced_stop'}:
        report.write(json.dumps(dict(version=1, kind='output_error', channel_id='test',
            observed_at='2026-10-11T00:00:09+00:00', category=mode)) + '\n')
        report.flush()
    if mode == 'force':
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'],
                                 start_new_session=os.name != 'nt')
        directory.joinpath('child.pid').write_text(str(child.pid))
        time.sleep(120)
    elif mode != 'early':
        # Fill the stdout pipe before waiting for stop: the helper must drain it.
        sys.stdout.write('x' * (1024 * 1024))
        sys.stdout.flush()
        command = json.loads(sys.stdin.readline())
        directory.joinpath('stop.json').write_text(json.dumps(command))
    directory.joinpath('recording-finished').touch()
    if mode != 'incomplete':
        report.write(json.dumps(dict(version=1, kind='report_finished', complete=True)) + '\n')
raise SystemExit(0)
'''


class RecordingCITests(unittest.TestCase):
    def test_channel_default_blank_custom_and_invalid_inputs(self):
        for value in ('', '  ', runner.DEFAULT_CHANNEL):
            self.assertEqual(runner.channel_id(value), runner.DEFAULT_CHANNEL)
        self.assertEqual(runner.channel_id('  ' + 'AB' * 16 + '  '), 'ab' * 16)
        for value in ('abc', 'g' * 32, 'a' * 31, 'a' * 33, 'https://example.com', '$(echo test)'):
            with self.assertRaises(runner.TestFailure):
                runner.channel_id(value)
        for kind, minimum, maximum in (('long', 270, 330), ('codec', 5, 20)):
            for duration in (str(minimum), str(maximum)):
                with patch.dict(os.environ, {'CHANNEL_ID': '', 'DURATION_MINUTES': duration}):
                    self.assertEqual(runner.test_inputs(kind), (runner.DEFAULT_CHANNEL, int(duration)))
            for duration in ('', '0', '-1', 'abc', str(minimum - 1), str(maximum + 1)):
                with patch.dict(os.environ, {'DURATION_MINUTES': duration}):
                    with self.assertRaises(runner.TestFailure):
                        runner.test_inputs(kind)

    def test_normal_stop_and_failure_paths_preserve_evidence(self):
        scenarios = {'normal': 0, 'gap': 1, 'incomplete': 1, 'early': 1,
                     'no-output': 1, 'empty': 1, 'ffmpeg-error': 1, 'startup-failure': 7,
                     'corrupt_packet': 1, 'partial_input': 1, 'forced_stop': 1}
        for mode, expected in scenarios.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='한글 CI ') as temporary:
                project = Path(temporary)
                (project / 'chzzk_record.py').write_text(FIXTURE, encoding='utf-8')
                output = project / 'output with spaces'
                config = runner.write_config(runner.DEFAULT_CHANNEL, output)
                with patch.object(runner, 'PROJECT_DIR', project), \
                        patch.dict(os.environ, {'CI_FIXTURE_MODE': mode}), \
                        contextlib.redirect_stdout(io.StringIO()):
                    status = runner.monitor_recording(
                        0.35, 0.18 if mode == 'no-output' else 180, output, config,
                        poll_interval=0.02, stop_timeout=2, early_exit_tolerance=0.01)
                self.assertEqual(status, expected)
                summary = json.loads((output / 'continuity-summary.json').read_text(encoding='utf-8'))
                if mode == 'startup-failure':
                    self.assertFalse(summary['passed'])
                    continue
                self.assertTrue((output / 'recording-finished').exists())
                evidence = (output / 'continuity.jsonl').read_text(encoding='utf-8')
                if mode == 'incomplete':
                    self.assertNotIn('report_finished', evidence)
                else:
                    self.assertIn('report_finished', evidence)
                if mode not in {'early'}:
                    self.assertEqual(json.loads((output / 'stop.json').read_text())['command'], 'stop')
                self.assertEqual(summary['gap_count'], int(mode == 'gap'))
                if mode in {'normal', 'gap'}:
                    self.assertEqual(summary['error_count'], 0)
                if mode == 'incomplete':
                    self.assertFalse(summary['passed'])
                if mode == 'no-output':
                    self.assertTrue((output / '.recording-stalled').exists())

    @unittest.skipUnless(os.name == 'posix' and shutil.which('ps'), 'POSIX process tree required')
    def test_forced_stop_kills_children_in_separate_sessions(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / 'chzzk_record.py').write_text(FIXTURE, encoding='utf-8')
            output = project / 'output'
            config = runner.write_config(runner.DEFAULT_CHANNEL, output)
            with patch.object(runner, 'PROJECT_DIR', project), \
                    patch.dict(os.environ, {'CI_FIXTURE_MODE': 'force'}), \
                    contextlib.redirect_stdout(io.StringIO()):
                status = runner.monitor_recording(0.35, 180, output, config,
                                                  poll_interval=0.02, stop_timeout=0.1)
            self.assertEqual(status, 1)
            child = int((output / 'child.pid').read_text())
            result = subprocess.run(['ps', '-p', str(child), '-o', 'stat='], capture_output=True, text=True)
            self.assertTrue(not result.stdout.strip() or result.stdout.strip().startswith('Z'), result.stdout)
            self.assertFalse(json.loads((output / 'continuity-summary.json').read_text())['passed'])

    def test_windows_force_cleanup_targets_the_process_tree(self):
        with patch.object(runner.os, 'name', 'nt'), patch.object(runner.subprocess, 'run') as run:
            runner.force_stop_tree(SimpleNamespace(pid=321))
        self.assertEqual(run.call_args.args[0], ['taskkill', '/PID', '321', '/T', '/F'])

    def test_janitor_keeps_reports_nonmedia_and_fresh_recordings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = 2000
            for name in ('old.ts', 'old.mkv', 'old.webm', 'fresh.ts', 'continuity.jsonl',
                         'continuity-summary.json', 'original-title.txt'):
                path = root / name
                path.write_bytes(b'data')
                os.utime(path, (now - (10 if name == 'fresh.ts' else 901),) * 2)
            runner.prune_recordings(root, now)
            self.assertEqual({path.name for path in root.iterdir()},
                             {'fresh.ts', 'continuity.jsonl', 'continuity-summary.json', 'original-title.txt'})

    def test_config_paths_and_codec_metadata(self):
        with tempfile.TemporaryDirectory(prefix='한글 CI ') as temporary:
            root = Path(temporary)
            config = json.loads(runner.write_config('a' * 32, root, 'av1').read_text(encoding='utf-8'))
            self.assertEqual(config['channels'][0]['output_dir'], str(root))
            self.assertEqual(config['av1_settings']['encoder'], 'libsvtav1')
            (root / 'fixture.mkv').write_bytes(b'media')
            for streams, passed in (([{'codec_name': 'av1'}, {'codec_name': 'av1'}], True),
                                    ([{'codec_name': 'h264'}], False), ([], False)):
                with patch.object(runner.subprocess, 'run', return_value=SimpleNamespace(
                        stdout=json.dumps({'streams': streams}))), contextlib.redirect_stdout(io.StringIO()):
                    if passed:
                        runner.verify_codec(root, 'av1')
                    else:
                        with self.assertRaises(runner.TestFailure):
                            runner.verify_codec(root, 'av1')

    def test_failed_codec_keeps_its_log_and_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def fail_recording(_duration, _stall, directory, config):
                config.parent.joinpath('log.log').write_text('failure evidence')
                directory.joinpath('continuity-summary.json').write_text('{"passed":false}')
                return 7

            with patch.object(runner, 'save_environment'), \
                    patch.object(runner, 'probe_encoders', side_effect=lambda path: path.mkdir()), \
                    patch.object(runner, 'verify_live'), \
                    patch.object(runner, 'monitor_recording', side_effect=fail_recording), \
                    patch.dict(os.environ, {'CHANNEL_ID': '', 'DURATION_MINUTES': '5'}):
                self.assertEqual(runner.run_suite('codec', root), 7)
            self.assertEqual((root / 'chzzk-codec-logs/h264.log').read_text(), 'failure evidence')
            self.assertFalse(json.loads((root / 'chzzk-codec-h264/continuity-summary.json').read_text())['passed'])

    def test_environment_records_versions_even_when_ffmpeg_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {'ImageOS': 'test-os', 'ImageVersion': '20261011.1'}), \
                    patch.object(runner.subprocess, 'run', side_effect=FileNotFoundError):
                runner.save_environment(Path(temporary))
            data = json.loads((Path(temporary) / 'chzzk-test-environment.json').read_text())
            self.assertEqual(data['image_version'], '20261011.1')
            self.assertEqual(data['image_os'], 'test-os')
            self.assertTrue(data['os'])
            self.assertTrue(data['python'])
            self.assertIsNone(data['ffmpeg_version'])

    def test_ci_messages_are_translated_in_every_locale(self):
        for key in (key for key in TRANSLATIONS['en'] if key.startswith('ci.')):
            for locale in SUPPORTED_LANGUAGES:
                value = translate(locale, key, minimum=5, maximum=20, seconds=1, status=7,
                                  channel='test', encoder='test', codec='test', actual='test',
                                  path='test', category='test', stage='test')
                self.assertNotEqual(value, key)
                if locale != 'en':
                    self.assertNotEqual(TRANSLATIONS[locale][key], TRANSLATIONS['en'][key])


if __name__ == '__main__':
    unittest.main()
