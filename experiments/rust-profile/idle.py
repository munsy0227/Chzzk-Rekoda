"""Sample idle CLI/Qt processes with an empty, synthetic configuration."""

import argparse
import json
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def rss(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (FileNotFoundError, ProcessLookupError):
        pass
    return None


def gui_worker(config, seconds):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from gui.appearance import apply_application_font
    from gui.common import HelpStyle
    from gui.window import MainWindow

    app = QApplication([])
    app.setStyle(HelpStyle())
    apply_application_font(app, "ko")
    window = MainWindow(str(config))
    window.show()
    QTimer.singleShot(int(seconds * 1000), app.quit)
    app.exec()
    window.preview.close()


def sample(kind, config, seconds):
    if kind == "cli":
        command = [
            sys.executable,
            str(ROOT / "chzzk_record.py"),
            "--gui-events",
            "--config",
            str(config),
        ]
    else:
        command = [
            sys.executable,
            __file__,
            "--gui-worker",
            str(config),
            "--seconds",
            str(seconds),
        ]
    with (
        tempfile.TemporaryFile() as output,
        tempfile.TemporaryFile() as errors,
    ):
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.perf_counter()
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=errors,
            start_new_session=True,
        )
        samples = []
        while process.poll() is None:
            elapsed = time.perf_counter() - started
            value = rss(process.pid)
            if value is not None:
                samples.append({"seconds": elapsed, "rss_kib": value})
            if elapsed >= seconds and kind == "cli":
                process.stdin.write(
                    b'{"version":1,"command":"stop",'
                    b'"reason":"application_exit"}\n'
                )
                process.stdin.flush()
                process.stdin.close()
                break
            if elapsed > seconds + 20:
                raise TimeoutError("Idle worker failed to finish")
            time.sleep(0.05)
        process.wait(timeout=90)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        assert process.returncode == 0, (kind, process.returncode)
    steady = [s["rss_kib"] for s in samples if s["seconds"] >= 2]
    return {
        "kind": kind,
        "seconds": time.perf_counter() - started,
        "steady_rss_median_kib": statistics.median(steady),
        "sampled_rss_peak_kib": max(s["rss_kib"] for s in samples),
        "wait_cpu_seconds": after.ru_utime
        + after.ru_stime
        - before.ru_utime
        - before.ru_stime,
        "samples": samples,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui-worker", type=Path)
    parser.add_argument("--seconds", type=float, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.gui_worker:
        gui_worker(args.gui_worker, args.seconds)
        return
    from config_store import normalize_config

    base = ROOT / ".cache" / "rust-profile"
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base, prefix="idle-") as directory:
        config = Path(directory) / "config.json"
        value = normalize_config(
            {
                "channels": [],
                "language": "en",
                "dns_settings": {"enable": False},
                "gui_settings": {"onboarding_completed": True},
            }
        )
        config.write_text(json.dumps(value))
        rows = [sample(kind, config, args.seconds) for kind in ("cli", "gui")]
    args.output.write_text(json.dumps({"rows": rows}, indent=2) + "\n")
    print([{k: v for k, v in row.items() if k != "samples"} for row in rows])


if __name__ == "__main__":
    main()
