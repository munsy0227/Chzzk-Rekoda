"""Oracle-check and benchmark Python vs Rust continuity report summarizers."""

import argparse
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PYTHON = Path("/tmp/chzzk-rust-env/bin/python")
DEFAULT_RUST = Path(
    "/tmp/chzzk-profile-report-target/release/continuity-report-rust"
)
EXISTING_REPORT = (
    ROOT / ".cache/rust-live-test-20261115-002510/continuity.jsonl"
)


def iso(value):
    return value.isoformat(timespec="microseconds").replace("+00:00", "+00:00")


def row(kind, **fields):
    return {"version": 1, "kind": kind, **fields}


def write_report(path, checkpoints, *, malformed=True, incomplete=False):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    channel = "synthetic-channel"
    live_id = 10001
    entries = [row("report_started")]
    entries.append(
        row(
            "source",
            live_id=live_id,
            rendition="1080p",
            cdn="korean",
            mode="llhls",
            state="selected",
            channel_id=channel,
        )
    )
    entries.append(
        row(
            "start",
            live_id=live_id,
            rendition="1080p",
            at=iso(base),
            requested_seconds=0,
            available_seconds=0.0,
            time_machine_active=False,
            channel_id=channel,
        )
    )
    first_checkpoint = None
    checkpoint = None
    for index in range(checkpoints):
        start = base + timedelta(seconds=index)
        checkpoint = row(
            "checkpoint",
            live_id=live_id,
            rendition="1080p",
            **{"from": iso(start), "to": iso(start + timedelta(seconds=1))},
            channel_id=channel,
        )
        if index == 1:
            entries.append(first_checkpoint.copy())
        else:
            entries.append(checkpoint)
            if index == 0:
                first_checkpoint = checkpoint
        if index == 0:
            entries.append(
                row(
                    "gap",
                    live_id=live_id,
                    rendition="1080p",
                    **{
                        "from": iso(start),
                        "to": iso(start + timedelta(milliseconds=20)),
                        "reason": "position_unknown",
                        "channel_id": channel,
                    },
                )
            )
            entries.append(
                row(
                    "gap",
                    live_id=live_id,
                    rendition="1080p",
                    **{
                        "from": iso(start),
                        "to": iso(start + timedelta(milliseconds=21)),
                        "reason": "position_unknown",
                        "channel_id": channel,
                    },
                )
            )
        if malformed and index == 2:
            entries.append("{not-json")
            entries.append("")
            entries.append(
                json.dumps(
                    row(
                        "checkpoint",
                        live_id=live_id,
                        rendition="1080p",
                        channel_id=channel,
                    )
                )
            )
    entries.append(
        row(
            "gap",
            live_id=live_id,
            rendition="1080p",
            **{
                "from": None,
                "to": None,
                "reason": "position_unknown",
                "channel_id": channel,
            },
        )
    )
    if not incomplete:
        entries.append(row("report_finished", complete=True))
    with path.open("w", encoding="utf-8", newline="\n") as target:
        for entry in entries:
            encoded = (
                entry
                if isinstance(entry, str)
                else json.dumps(entry, separators=(",", ":"))
            )
            target.write(encoded)
            target.write("\n")


def run_candidate(kind, executable, source, output):
    if kind in {"python", "python_orjson"}:
        command = [
            str(PYTHON),
            str(HERE / "python_runner.py"),
            str(source),
            str(output),
            "orjson" if kind == "python_orjson" else "stdlib",
        ]
    else:
        command = [str(executable), str(source), str(output)]
    started = time.perf_counter_ns()
    process = subprocess.Popen(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
    )
    _, status, usage = os.wait4(process.pid, 0)
    wall_ns = time.perf_counter_ns() - started
    process.returncode = os.waitstatus_to_exitcode(status)
    stderr = process.stderr.read()
    if process.returncode:
        raise RuntimeError(
            f"{kind} exited {process.returncode}: {stderr.strip()}"
        )
    stats = json.loads(stderr.strip().splitlines()[-1])
    memory_values = (
        stats.get("process_self_vm_hwm_kib"),
        stats.get("process_self_vm_rss_kib"),
    )
    if any(type(value) is not int for value in memory_values):
        raise RuntimeError(f"{kind} did not report its /proc memory metrics")
    if memory_values[0] < memory_values[1]:
        raise RuntimeError(
            f"{kind} reported VmRSS above VmHWM: {memory_values}"
        )
    summary = json.loads(output.read_text(encoding="utf-8"))
    return summary, {
        "process_wall_ns": wall_ns,
        "wait4_process_tree_cpu_seconds": usage.ru_utime + usage.ru_stime,
        "wait4_child_ru_maxrss_kib_raw": usage.ru_maxrss,
        "process_self_vm_hwm_kib": stats.get("process_self_vm_hwm_kib"),
        "process_self_vm_rss_kib": stats.get("process_self_vm_rss_kib"),
        "algorithm_wall_ns": stats["algorithm_wall_ns"],
        "algorithm_cpu_ns": stats.get("algorithm_cpu_ns"),
        "startup_and_output_wall_ns_estimate": max(
            0, wall_ns - stats["algorithm_wall_ns"]
        ),
        "input_bytes": stats["input_bytes"],
        "input_rows": stats["input_rows"],
    }


def compare(source, rust_bin):
    with tempfile.TemporaryDirectory(
        prefix="continuity-check-", dir=HERE
    ) as temporary:
        folder = Path(temporary)
        expected = None
        for kind, executable in (
            ("python", None),
            ("python_orjson", None),
            ("rust", rust_bin),
        ):
            output = folder / f"{kind}.json"
            result, _ = run_candidate(kind, executable, source, output)
            if expected is None:
                expected = result
            elif result != expected:
                raise AssertionError(
                    f"oracle mismatch on {source.name} ({kind}): "
                    f"expected={expected!r}; actual={result!r}"
                )
        return expected


def self_check(rust_bin):
    if not PYTHON.is_file():
        raise FileNotFoundError(
            f"Python 3.12 environment is missing: {PYTHON}"
        )
    try:
        subprocess.run(
            [str(PYTHON), "-c", "import orjson"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            "orjson is unavailable in the Python 3.12 environment"
        ) from error
    if not rust_bin.is_file():
        raise FileNotFoundError(f"Build the Rust candidate first: {rust_bin}")
    if not EXISTING_REPORT.is_file():
        raise FileNotFoundError(
            f"Recorded report is missing: {EXISTING_REPORT}"
        )
    actual = compare(EXISTING_REPORT, rust_bin)
    cases = []
    with tempfile.TemporaryDirectory(
        prefix="continuity-fixtures-", dir=HERE
    ) as temporary:
        folder = Path(temporary)
        for count in (1_000, 10_000, 100_000):
            path = folder / f"synthetic-{count}.jsonl"
            write_report(path, count)
            cases.append({"checkpoints": count, **compare(path, rust_bin)})
        broken = folder / "incomplete.jsonl"
        write_report(broken, 3, incomplete=True)
        cases.append(
            {"case": "missing report footer", **compare(broken, rust_bin)}
        )
    return {
        "existing_report": actual,
        "synthetic_cases": cases,
        "oracle": "continuity_report.summarize",
    }


def benchmark(rust_bin, rounds, output_path):
    datasets = [("recorded", EXISTING_REPORT)]
    temp_context = tempfile.TemporaryDirectory(
        prefix="continuity-bench-", dir=HERE
    )
    folder = Path(temp_context.name)
    for count in (1_000, 10_000, 100_000):
        path = folder / f"synthetic-{count}.jsonl"
        write_report(path, count)
        datasets.append((f"synthetic-{count}", path))
    results = []
    for label, source in datasets:
        candidates = ("python", "python_orjson", "rust")
        samples = {kind: [] for kind in candidates}
        candidate_order = []
        for repetition in range(rounds):
            offset = repetition % len(candidates)
            order = list(candidates[offset:] + candidates[:offset])
            candidate_order.append(order)
            oracle = None
            for kind in order:
                output = folder / f"{label}-{kind}-{repetition}.json"
                executable = rust_bin if kind == "rust" else None
                summary, sample = run_candidate(
                    kind, executable, source, output
                )
                samples[kind].append(sample)
                if oracle is None:
                    oracle = summary
                elif summary != oracle:
                    raise AssertionError(
                        f"oracle mismatch in {label} round {repetition}: {kind}"
                    )
        results.append(
            {
                "dataset": label,
                "input_bytes": source.stat().st_size,
                "rounds": rounds,
                "candidate_order_per_round": candidate_order,
                "samples": samples,
            }
        )
    payload = {
        "schema_version": 1,
        "scope": (
            "whole NDJSON input -> summary JSON; Python stdlib is oracle, "
            "orjson replaces module-local loads/dumps only, Rust ports the report path"
        ),
        "candidates": ["python", "python_orjson", "rust"],
        "units": {
            "wall": "nanoseconds",
            "cpu": {
                "wait4_process_tree_cpu_seconds": (
                    "seconds; worker plus waited descendants on Linux"
                ),
                "algorithm_cpu_ns": (
                    "nanoseconds; worker-only processing CPU when available"
                ),
            },
            "rss": {
                "process_self_vm_hwm_kib": "KiB; /proc/self/status VmHWM after algorithm",
                "process_self_vm_rss_kib": "KiB; /proc/self/status VmRSS after algorithm",
                "wait4_child_ru_maxrss_kib_raw": "KiB; raw wait4 ru_maxrss, not used for candidate comparison",
            },
        },
        "datasets": results,
    }
    output_path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rust-bin", type=Path, default=DEFAULT_RUST)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="compare real and generated reports without timing benchmark rounds",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="run timed comparisons and write raw JSON samples",
    )
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument(
        "--output", type=Path, default=HERE / "benchmark-results.json"
    )
    args = parser.parse_args()
    if args.self_check == args.benchmark:
        parser.error("choose exactly one of --self-check or --benchmark")
    if args.self_check:
        print(json.dumps(self_check(args.rust_bin), indent=2))
    else:
        if args.rounds < 1:
            parser.error("--rounds must be positive")
        benchmark(args.rust_bin, args.rounds, args.output)


if __name__ == "__main__":
    main()
