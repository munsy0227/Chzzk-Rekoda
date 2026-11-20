"""Measure existing glue and native work without reading personal settings."""

import argparse
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def measure(name, function, count, rounds=5):
    function()
    samples = []
    for _ in range(rounds):
        child = resource.getrusage(resource.RUSAGE_CHILDREN)
        child_cpu = child.ru_utime + child.ru_stime
        wall, cpu = time.perf_counter(), time.process_time()
        for _ in range(count):
            function()
        child = resource.getrusage(resource.RUSAGE_CHILDREN)
        samples.append(
            {
                "wall_ns_per_call": (time.perf_counter() - wall) * 1e9 / count,
                "cpu_ns_per_call": (time.process_time() - cpu) * 1e9 / count,
                "child_cpu_ns_per_call": (
                    child.ru_utime + child.ru_stime - child_cpu
                )
                * 1e9
                / count,
            }
        )
    tracemalloc.start()
    function()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "name": name,
        "count_per_round": count,
        "samples": samples,
        "median_wall_us": statistics.median(
            x["wall_ns_per_call"] for x in samples
        )
        / 1000,
        "median_cpu_us": statistics.median(
            x["cpu_ns_per_call"] for x in samples
        )
        / 1000,
        "median_total_cpu_us": statistics.median(
            x["cpu_ns_per_call"] + x["child_cpu_ns_per_call"] for x in samples
        )
        / 1000,
        "one_call_python_traced_peak_bytes": peak,
    }


class SocketBytes:
    def __init__(self, data):
        self.data = io.BytesIO(data)

    def recv(self, size):
        return self.data.read(size)


def core_cases(directory):
    import browser_login
    import config_store as config
    import dns.message
    import dns.rrset
    import dns_over_https as doh
    import encoding_h264 as encoding
    from process_lock import FileLock
    from recording_continuity import EVENT_PREFIX, parse_event

    rows = []
    for channels in (1, 16, 64):
        value = deepcopy(config.default_config)
        value["channels"] = [
            {
                "id": f"{i:032x}",
                "name": f"test-{i}",
                "active": "on",
                "output_dir": str(directory),
                "identifier": f"channel-{i}",
            }
            for i in range(channels)
        ]
        normalized = config.normalize_config(value)
        assert len(normalized["channels"]) == channels
        rows.append(
            measure(
                f"config_normalize_{channels}_channels",
                lambda: config.normalize_config(value),
                100,
            )
        )
    path = directory / "synthetic-config.json"
    rows.append(
        measure(
            "config_save_fsync_replace_64_channels",
            lambda: config.save_config(deepcopy(value), path),
            20,
        )
    )
    rows.append(
        measure(
            "config_load_64_channels",
            lambda: config.load_config(path=path),
            100,
        )
    )
    lock_path = directory / "synthetic.lock"

    def lock_cycle():
        with FileLock(lock_path):
            pass

    rows.append(measure("os_file_lock_acquire_release", lock_cycle, 1000))
    resolver = doh.DnsOverHttpsResolver()
    resolver._cache[("bench.invalid", 1)] = (
        time.monotonic() + 3600,
        ("192.0.2.1",),
    )
    assert resolver.resolve("bench.invalid", socket.AF_INET) == ["192.0.2.1"]
    rows.append(
        measure(
            "dns_cache_hit_no_network",
            lambda: resolver.resolve("bench.invalid", socket.AF_INET),
            10000,
        )
    )
    query = dns.message.make_query("bench.invalid.", "A")
    answer = dns.message.make_response(query)
    answer.answer.append(
        dns.rrset.from_text("bench.invalid.", 60, "IN", "A", "192.0.2.1")
    )
    wire = answer.to_wire()
    rows.append(
        measure(
            "dns_wire_decode_and_validate_no_network",
            lambda: resolver._parse_response(dns.message.from_wire(wire), 1),
            1000,
        )
    )
    for size in (512, 32768):
        body = b"x" * size
        response = (
            b"HTTP/1.1 200 OK\r\nContent-Length: "
            + str(size).encode()
            + b"\r\n\r\n"
            + body
        )
        chunked = (
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
            + f"{size:x}\r\n".encode()
            + body
            + b"\r\n0\r\n\r\n"
        )
        for mode, raw in (("length", response), ("chunked", chunked)):

            def function():
                return resolver._read_http_response(SocketBytes(raw))

            assert function()[2] == body
            rows.append(
                measure(
                    f"doh_http_{mode}_{size}_bytes_no_network", function, 1000
                )
            )
    event = EVENT_PREFIX + json.dumps(
        {
            "version": 1,
            "kind": "checkpoint",
            "live_id": 1,
            "rendition": "1080p",
            "from": "2026-11-15T00:00:00+09:00",
            "to": "2026-11-15T00:00:02+09:00",
        }
    )
    assert parse_event(event) is not None
    rows.append(
        measure(
            "recording_event_parse_validate", lambda: parse_event(event), 5000
        )
    )
    fake_cookies = [
        {"domain": ".naver.com", "name": name, "value": "test-placeholder"}
        for name in ("NID_SES", "NID_AUT")
    ]
    assert len(browser_login.naver_cookies(fake_cookies)) == 2
    rows.append(
        measure(
            "login_cookie_filter_synthetic_only",
            lambda: browser_login.naver_cookies(fake_cookies),
            10000,
        )
    )
    settings = config.normalize_h264_settings(
        {"enable": True, "encoder": "libx264", "preset": "ultrafast"}
    )
    rows.append(
        measure(
            "encoder_argument_construction",
            lambda: encoding.build_h264_encoding_args(settings, "ts"),
            10000,
        )
    )

    def probe():
        encoding.PROBE_CACHE.clear()
        assert encoding.probe_h264_encoder("ffmpeg", settings)

    rows.append(measure("encoder_actual_ffmpeg_probe_uncached", probe, 1, 3))
    rows.append(
        measure(
            "encoder_probe_cached",
            lambda: encoding.probe_h264_encoder("ffmpeg", settings),
            10000,
        )
    )
    return rows


def preview_cases(video, native):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from gui.services import Preview, image_from_bytes

    app = QApplication.instance() or QApplication([])
    preview = Preview()
    preview.timer.stop()
    target = {
        "id": "measurement",
        "output_path": str(video),
        "preview_seconds": 30,
    }

    def capture(command):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            data, errors = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
        if process.returncode:
            raise RuntimeError(errors.decode(errors="replace"))
        return data

    reference_jpeg = capture(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-threads",
            "1",
            "-ss",
            "30.000",
            "-i",
            str(video),
            "-map",
            "0:v:0",
            "-frames:v",
            "1",
            "-an",
            "-sn",
            "-threads",
            "1",
            "-vf",
            "scale=640:360:force_original_aspect_ratio=decrease",
            "-c:v",
            "mjpeg",
            "-f",
            "image2pipe",
            "pipe:1",
        ]
    )
    expected = hashlib.sha256(reference_jpeg).hexdigest()
    assert not image_from_bytes(reference_jpeg).isNull()
    rows = [
        measure(
            "preview_qt_jpeg_decode_only",
            lambda: image_from_bytes(reference_jpeg),
            100,
        )
    ]
    loop = QEventLoop()
    success = []
    preview.frame.connect(
        lambda pixmap: (success.append(not pixmap.isNull()), loop.quit())
    )
    preview.unavailable.connect(
        lambda reason: loop.quit() if reason == "failed" else None
    )
    guard = QTimer()
    guard.setSingleShot(True)
    guard.timeout.connect(loop.quit)

    def qt_preview():
        success.clear()
        preview.target = target
        preview.refresh()
        guard.start(15000)
        loop.exec()
        guard.stop()
        assert success == [True]
        assert hashlib.sha256(bytes(preview.data)).hexdigest() == expected

    rows.append(
        measure("preview_existing_qt_ffmpeg_and_decode", qt_preview, 1, 5)
    )
    if native:
        command = [
            str(native),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-threads",
            "1",
            "-ss",
            "30.000",
            "-i",
            str(video),
            "-map",
            "0:v:0",
            "-frames:v",
            "1",
            "-an",
            "-sn",
            "-threads",
            "1",
            "-vf",
            "scale=640:360:force_original_aspect_ratio=decrease",
            "-c:v",
            "mjpeg",
            "-f",
            "image2pipe",
            "pipe:1",
        ]

        def rust_preview():
            data = capture(command)
            assert hashlib.sha256(data).hexdigest() == expected
            assert not image_from_bytes(data).isNull()

        rows.append(
            measure(
                "preview_rust_launcher_ffmpeg_and_qt_decode",
                rust_preview,
                1,
                5,
            )
        )
    preview.close()
    app.processEvents()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--native-preview", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = ROOT / ".cache" / "rust-profile"
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base, prefix="glue-") as folder:
        rows = core_cases(Path(folder))
    rows.extend(preview_cases(args.video.resolve(), args.native_preview))
    report = {
        "python": sys.version,
        "scope": "existing Linux glue and Qt/FFmpeg",
        "rows": rows,
        "python_run_wide_peak_rss_kib": resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss,
        "notes": [
            "tracemalloc excludes native allocations",
            "CPU is Python-process CPU and excludes FFmpeg children",
            "total CPU adds waited descendant CPU on Linux",
            "RSS is Python run-wide high-water; children excluded",
            "Rust preview launches the same FFmpeg, not a Rust decoder",
            "DNS tests exclude transport/TLS latency",
            "login uses synthetic cookies; no account/browser login",
            "Windows overlapped pipe is not measured on Linux",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Measured {len(rows)} glue/native cases: {args.output}")
    for row in rows:
        print(f"{row['name']}: {row['median_wall_us']:.3f} us/call")


if __name__ == "__main__":
    main()
