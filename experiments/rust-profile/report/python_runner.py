"""Python continuity-report adapter used by the isolated Rust comparison."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import continuity_report  # noqa: E402


class OrjsonShim:
    """The JSON operations exercised by summarize and parse_event."""

    def __init__(self, backend):
        self.backend = backend

    def loads(self, value):
        if isinstance(value, str):
            value = value.encode("utf-8")
        return self.backend.loads(value)

    def dumps(self, value):
        return self.backend.dumps(value).decode("utf-8")


def process_memory_kib():
    values = {}
    for line in (
        Path("/proc/self/status").read_text(encoding="ascii").splitlines()
    ):
        name, _, value = line.partition(":")
        if name in {"VmHWM", "VmRSS"}:
            values[name] = int(value.split()[0])
    return values


def main():
    source_path, summary_path = map(Path, sys.argv[1:3])
    backend_name = sys.argv[3] if len(sys.argv) > 3 else "stdlib"
    if backend_name == "orjson":
        import orjson
        import recording_continuity

        shim = OrjsonShim(orjson)
        continuity_report.json = shim
        recording_continuity.json = shim
    elif backend_name != "stdlib":
        raise ValueError(f"unknown JSON backend: {backend_name}")
    summarize = continuity_report.summarize
    started_wall = time.perf_counter_ns()
    started_cpu = time.process_time_ns()
    rows = 0
    with source_path.open(encoding="utf-8") as source:

        def counted_lines():
            nonlocal rows
            for line in source:
                rows += 1
                yield line

        result = summarize(counted_lines())
    algorithm_wall_ns = time.perf_counter_ns() - started_wall
    algorithm_cpu_ns = time.process_time_ns() - started_cpu
    memory = process_memory_kib()
    summary_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "algorithm_wall_ns": algorithm_wall_ns,
                "algorithm_cpu_ns": algorithm_cpu_ns,
                "input_bytes": source_path.stat().st_size,
                "input_rows": rows,
                "process_self_vm_hwm_kib": memory.get("VmHWM"),
                "process_self_vm_rss_kib": memory.get("VmRSS"),
            }
        ),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
