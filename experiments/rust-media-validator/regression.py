"""Run existing tests with an experiment backend, including Python children."""

import argparse
import atexit
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def install():
    sys.path.insert(0, str(ROOT))
    import hls_continuity as continuity

    backend = os.environ["CHZZK_VALIDATOR_BACKEND"]
    if backend == "rust":
        from rust_media_validator import validate_media as validate
    else:
        validate = continuity.validate_media
    counts = {"pid": os.getpid(), "backend": backend, "calls": 0,
              "bytes": 0, "validation_ns": 0}

    def checked(data, is_map=False):
        counts["calls"] += 1
        counts["bytes"] += len(data)
        started = time.perf_counter_ns()
        try:
            return validate(data, is_map)
        except ValueError as error:
            if backend != "rust":
                raise
            raise continuity.Unavailable(
                str(error), category="invalid_media") from None
        finally:
            counts["validation_ns"] += time.perf_counter_ns() - started

    continuity.validate_media = checked
    directory = Path(os.environ["CHZZK_VALIDATOR_PROFILE"])
    target = directory / f"{os.getpid()}.json"
    atexit.register(
        lambda: target.write_text(json.dumps(counts), encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("python", "rust"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="chzzk-validator-") as directory:
        startup = Path(directory)
        (startup / "sitecustomize.py").write_text(
            "try:\n    from regression import install\n    install()\n"
            "except Exception as error:\n"
            "    raise SystemExit('Validator injection failed') from error\n",
            encoding="utf-8")
        environment = dict(os.environ, CHZZK_VALIDATOR_BACKEND=args.backend,
                           CHZZK_VALIDATOR_PROFILE=directory)
        environment["PYTHONPATH"] = os.pathsep.join(
            [directory, str(Path(__file__).resolve().parent), str(ROOT),
             environment.get("PYTHONPATH", "")])
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests",
             "-v"],
            cwd=ROOT, env=environment, check=False)
        elapsed = time.perf_counter() - started
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        profiles = [json.loads(path.read_text(encoding="utf-8"))
                    for path in sorted(startup.glob("*.json"))]
        report = {"backend": args.backend, "returncode": result.returncode,
                  "wall_seconds": elapsed,
                  "child_cpu_seconds": after.ru_utime + after.ru_stime
                  - before.ru_utime - before.ru_stime, "processes": profiles}
        if not profiles or not any(item["calls"] for item in profiles):
            raise RuntimeError("Validator injection was not exercised")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
