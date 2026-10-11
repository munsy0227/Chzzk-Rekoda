"""Portable manual Actions recording tests and the legacy monitor entrypoint."""

import argparse
import contextlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from continuity_report import summarize  # noqa: E402
from i18n import SUPPORTED_LANGUAGES, translate  # noqa: E402


DEFAULT_CHANNEL = "64a90ba95d1f9feb0a798a20bbf0f40c"
MEDIA_SUFFIXES = {".ts", ".mkv", ".webm"}
LANGUAGE = "en"


class TestFailure(Exception):
    pass


def message(key, **fields):
    return translate(LANGUAGE, "ci." + key, **fields)


def error(key, **fields):
    print("::error::" + message(key, **fields), flush=True)


def channel_id(value):
    value = value.strip() or DEFAULT_CHANNEL
    if not re.fullmatch(r"[0-9a-fA-F]{32}", value):
        raise TestFailure(message("invalid_channel"))
    return value.lower()


def positive_integer(value):
    if not re.fullmatch(r"[0-9]+", str(value)) or int(value) <= 0:
        raise TestFailure(message("positive_integer"))
    return int(value)


def test_inputs(kind):
    default, minimum, maximum = (300, 270, 330) if kind == "long" else (10, 5, 20)
    duration = positive_integer(os.environ.get("DURATION_MINUTES", str(default)))
    if not minimum <= duration <= maximum:
        raise TestFailure(message("duration_range", minimum=minimum, maximum=maximum))
    return channel_id(os.environ.get("CHANNEL_ID", "")), duration


def recording_files(directory):
    for path in Path(directory).rglob("*"):
        if path.suffix.lower() in MEDIA_SUFFIXES:
            try:
                if path.is_file():
                    yield path, path.stat()
            except FileNotFoundError:
                pass


def prune_recordings(directory, now):
    for path, stat in recording_files(directory):
        if now - stat.st_mtime > 15 * 60:
            with contextlib.suppress(FileNotFoundError):
                path.unlink()


def force_stop_tree(process):
    """Include recorder children, which deliberately have separate sessions."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid="], check=True, capture_output=True,
        text=True, timeout=5,
    )
    children = {}
    for line in result.stdout.splitlines():
        pid, parent = map(int, line.split())
        children.setdefault(parent, []).append(pid)
    descendants = [process.pid]
    for pid in descendants:
        descendants.extend(children.get(pid, ()))
    groups = set()
    for pid in descendants:
        with contextlib.suppress(ProcessLookupError):
            group = os.getpgid(pid)
            if group == pid or group == process.pid:
                groups.add(group)
    for group in groups:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(group, signal.SIGKILL)
    for pid in reversed(descendants):
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)


def stop_recorder(process, timeout):
    if process.poll() is not None:
        return False
    try:
        process.stdin.write(b'{"version":1,"command":"stop","reason":"application_exit"}\n')
        process.stdin.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        with contextlib.suppress(BrokenPipeError, OSError):
            process.stdin.close()
    try:
        process.wait(timeout=timeout)
        return False
    except subprocess.TimeoutExpired:
        error("shutdown_timeout", seconds=timeout)
        try:
            force_stop_tree(process)
        except (OSError, subprocess.SubprocessError):
            error("cleanup_failed")
            process.kill()
        process.wait(timeout=10)
        return True


def drain_events(stream):
    try:
        while stream.read(65536):
            pass
    finally:
        stream.close()


def save_summary(report, destination):
    try:
        with report.open(encoding="utf-8") as source:
            result = summarize(source)
    except (OSError, UnicodeError):
        result = summarize([])
    destination.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(translate(
        LANGUAGE, "record.continuity_summary", gaps=result["gap_count"],
        seconds=result["gap_seconds"], unresolved=result["unresolved_count"],
        errors=result["error_count"], duplicates=result["duplicate_count"],
    ), flush=True)
    return result["passed"]


def monitor_recording(duration_seconds, stall_seconds, output_dir, config_path,
                      *, poll_interval=15, janitor_interval=60,
                      stop_timeout=120, early_exit_tolerance=60):
    output_dir = Path(output_dir).resolve()
    config_path = Path(config_path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = output_dir / "continuity.jsonl"
    summary = output_dir / "continuity-summary.json"
    log_path = config_path.parent / "log.log"
    started = time.monotonic()
    next_janitor = started
    process = consumer = None
    stalled = forced = interrupted = False
    continuity_passed = False
    try:
        kwargs = {"start_new_session": True} if os.name != "nt" else {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
        }
        process = subprocess.Popen(
            [sys.executable, str(PROJECT_DIR / "chzzk_record.py"), "--gui-events",
             "--config", str(config_path), "--continuity-report", str(report)],
            cwd=PROJECT_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, **kwargs,
        )
        consumer = threading.Thread(target=drain_events, args=(process.stdout,), daemon=True)
        consumer.start()
        while process.poll() is None:
            now = time.monotonic()
            if now - started >= duration_seconds:
                break
            if now >= next_janitor:
                prune_recordings(output_dir, time.time())
                next_janitor = now + janitor_interval
            latest = max((stat.st_mtime for _, stat in recording_files(output_dir)), default=None)
            inactive = now - started if latest is None else max(0, time.time() - latest)
            if inactive > stall_seconds:
                error("stalled", seconds=int(inactive))
                (output_dir / ".recording-stalled").touch()
                stalled = True
                break
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=min(poll_interval, duration_seconds - (now - started)))
    except KeyboardInterrupt:
        interrupted = True
    finally:
        elapsed = time.monotonic() - started
        try:
            if process is not None:
                forced = stop_recorder(process, stop_timeout)
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
                if consumer is not None:
                    consumer.join(timeout=5)
        finally:
            # Startup failures and forced exits must also leave a failed summary.
            continuity_passed = save_summary(report, summary)
    if interrupted:
        return 130
    if stalled or forced:
        return 1
    if process.returncode != 0:
        error("recorder_exit", status=process.returncode)
        return process.returncode if process.returncode > 0 else 1
    if elapsed + early_exit_tolerance < duration_seconds:
        error("early_exit")
        return 1
    try:
        log = log_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        log = ""
    if "Recording started for " not in log:
        error("never_started")
        return 1
    if re.search(r"Invalid NAL unit size|Error applying bitstream filters|ffmpeg failed for", log):
        error("ffmpeg_failure")
        return 1
    if not any(stat.st_size > 0 for _, stat in recording_files(output_dir)):
        error("empty_output")
        return 1
    if not continuity_passed:
        return 1
    print(message("completed", seconds=int(elapsed)), flush=True)
    return 0


def write_config(channel, output_dir, codec=None):
    identifier = "codec_smoke" if codec else "long_recording"
    config = {
        "channels": [{"id": channel, "name": "GitHub Actions " + (codec or "long recording"),
                      "output_dir": str(output_dir), "identifier": identifier, "active": "on"}],
        "delays": {identifier: 0}, "timeout": 30, "stream_segment_threads": 2,
        "output_format": "mkv" if codec == "av1" else "ts", "recording_split_minutes": 5,
        "h264_settings": {"enable": False}, "hevc_settings": {"enable": False},
        "av1_settings": {"enable": False}, "log_enabled": True,
        "cookies": {"NID_SES": "", "NID_AUT": ""},
        "dns_settings": {"enable": False}, "language": "en",
    }
    if codec in {"hevc", "av1"}:
        config[codec + "_settings"] = {
            "enable": True, "encoder": "libx265" if codec == "hevc" else "libsvtav1",
            "bitrate": "2500k", "max_bitrate": "10000k",
            "preset": "ultrafast" if codec == "hevc" else "13",
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "config.json"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def verify_live(channel):
    result = subprocess.run(
        [sys.executable, "-m", "streamlink", "--plugin-dirs", str(PROJECT_DIR / "plugin"),
         "--stream-url", "https://chzzk.naver.com/live/" + channel, "best"],
        cwd=PROJECT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
    )
    if result.returncode:
        raise TestFailure(message("live_failed", channel=channel))


def probe_encoders(log_dir):
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "encoder-probes.log").open("w", encoding="utf-8") as log:
        for encoder, preset in (("libx265", "ultrafast"), ("libsvtav1", "13")):
            log.write(encoder + "\n")
            log.flush()
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                 "color=c=black:s=128x128:r=5", "-frames:v", "2", "-pix_fmt", "yuv420p",
                 "-c:v", encoder, "-preset", preset, "-f", "null", "-"],
                stdout=log, stderr=log, timeout=60,
            )
            if result.returncode:
                raise TestFailure(message("encoder_failed", encoder=encoder))


def verify_codec(output_dir, expected):
    files = [(path, stat) for path, stat in recording_files(output_dir) if stat.st_size > 0]
    if not files:
        raise TestFailure(message("empty_output"))
    latest, _ = max(files, key=lambda item: (item[1].st_mtime_ns, str(item[0])))
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
         "stream=codec_name", "-of", "json", str(latest)],
        check=True, capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    actual = sorted({stream["codec_name"] for stream in json.loads(result.stdout).get("streams", [])
                     if stream.get("codec_name")})
    if not actual:
        raise TestFailure(message("missing_video", codec=expected))
    if actual != [expected]:
        raise TestFailure(message(
            "codec_mismatch", codec=expected, actual=",".join(actual),
        ))
    print(message("codec_verified", codec=expected, path=latest), flush=True)


def save_environment(root):
    root.mkdir(parents=True, exist_ok=True)
    data = {
        "os": platform.platform(), "architecture": platform.machine(),
        "python": sys.version, "python_executable": sys.executable,
        "runner_os": os.environ.get("RUNNER_OS"), "runner_arch": os.environ.get("RUNNER_ARCH"),
        "image_os": os.environ.get("ImageOS"), "image_version": os.environ.get("ImageVersion"),
    }
    if sys.platform.startswith("linux"):
        try:
            release = platform.freedesktop_os_release()
            data["linux_distribution"] = {
                key: release.get(key) for key in ("ID", "PRETTY_NAME", "VERSION_ID")
            }
        except OSError:
            data["linux_distribution"] = None
    for tool in ("ffmpeg", "ffprobe"):
        data[tool + "_path"] = shutil.which(tool)
        try:
            result = subprocess.run([tool, "-version"], check=True, capture_output=True,
                                    text=True, encoding="utf-8", errors="replace", timeout=15)
            data[tool + "_version"] = result.stdout.splitlines()[0]
        except (OSError, subprocess.SubprocessError, IndexError):
            data[tool + "_version"] = None
    (root / "chzzk-test-environment.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


def run_suite(kind, root):
    channel, duration = test_inputs(kind)
    save_environment(root)
    if kind == "codec":
        probe_encoders(root / "chzzk-codec-logs")
    verify_live(channel)
    for codec in ("h264", "hevc", "av1") if kind == "codec" else (None,):
        directory = root / ("chzzk-codec-" + codec if codec else "chzzk-long-recording")
        config_path = write_config(channel, directory, codec)
        try:
            result = monitor_recording(duration * 60, 180, directory, config_path)
        finally:
            if codec and (directory / "log.log").exists():
                shutil.copy2(directory / "log.log", root / "chzzk-codec-logs" / (codec + ".log"))
        if result:
            return result
        if codec:
            verify_codec(directory, codec)
    return 0


def interrupt_test(*_):
    raise KeyboardInterrupt


def main():
    global LANGUAGE
    parser = argparse.ArgumentParser(description=message("description"))
    parser.add_argument("--language", choices=SUPPORTED_LANGUAGES, default="en")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("long", "codec", "environment"):
        commands.add_parser(command)
    validate = commands.add_parser("validate")
    validate.add_argument("kind", choices=("long", "codec"))
    install_error = commands.add_parser("windows-error")
    install_error.add_argument("stage")
    monitor = commands.add_parser("monitor")
    monitor.add_argument("duration_minutes")
    monitor.add_argument("stall_seconds")
    monitor.add_argument("output_dir", type=Path)
    monitor.add_argument("--config", type=Path, default=PROJECT_DIR / "config.json")
    args = parser.parse_args()
    LANGUAGE = args.language
    previous_handler = signal.signal(signal.SIGTERM, interrupt_test)
    try:
        if args.command == "windows-error":
            error("windows_install_failed", stage=args.stage)
            return 1
        if args.command == "monitor":
            return monitor_recording(
                positive_integer(args.duration_minutes) * 60,
                positive_integer(args.stall_seconds), args.output_dir, args.config,
            )
        if args.command == "validate":
            test_inputs(args.kind)
            return 0
        default_root = PROJECT_DIR / ".cache" / "recording-test"
        root = Path(os.environ.get("RUNNER_TEMP", str(default_root))).resolve()
        if args.command == "environment":
            save_environment(root)
            return 0
        return run_suite(args.command, root)
    except TestFailure as failure:
        print("::error::" + str(failure), flush=True)
        return 1
    except (OSError, subprocess.SubprocessError, ValueError) as failure:
        error("test_failed", category=type(failure).__name__)
        return 1
    except KeyboardInterrupt:
        return 130
    finally:
        signal.signal(signal.SIGTERM, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())
