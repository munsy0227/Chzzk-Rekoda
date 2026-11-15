#!/usr/bin/env python3
"""Compare the Rust validator with hls_continuity.validate_media."""

import argparse
import ast
import hashlib
import json
import platform
import random
import statistics
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MESSAGES = {
    "empty": "Empty media response",
    "ts": "Incomplete transport stream",
    "header": "Incomplete MP4 box header",
    "extended": "Incomplete MP4 extended size",
    "box": "Incomplete MP4 box",
    "container": "Unexpected media container",
}


class Unavailable(Exception):
    def __init__(self, message, category=None):
        super().__init__(message)
        self.category = category


def python_validator():
    tree = ast.parse((ROOT / "hls_continuity.py").read_text(encoding="utf-8"))
    node = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "validate_media")
    module = ast.Module(body=[node], type_ignores=[])
    scope = {"struct": struct, "Unavailable": Unavailable}
    code = compile(
        ast.fix_missing_locations(module), "hls_continuity.py", "exec")
    exec(code, scope)
    return scope["validate_media"]


def result(function, data, is_map):
    try:
        function(data, is_map=is_map)
        return True, None
    except (Unavailable, ValueError) as error:
        return False, str(error)


def box(kind, payload=b"", mode="normal"):
    size = len(payload) + (16 if mode == "extended" else 8)
    if mode == "zero":
        return struct.pack(">I4s", 0, kind) + payload
    if mode == "extended":
        return struct.pack(">I4sQ", 1, kind, size) + payload
    return struct.pack(">I4s", size, kind) + payload


def corpus(seed, random_cases, fixtures):
    rng = random.Random(seed)
    cases = [
        ("empty", b"", False, (False, MESSAGES["empty"])),
        ("one-ts-packet", b"\x47" + bytes(187), False, (True, None)),
        ("two-ts-packets", (b"\x47" + bytes(187)) * 2, False, (True, None)),
        ("ts-wrong-length", b"\x47" + bytes(186), False,
         (False, MESSAGES["ts"])),
        ("ts-bad-sync", (b"\x47" + bytes(187)) + b"\x00" + bytes(187),
         False, (False, MESSAGES["ts"])),
        ("init-normal", box(b"ftyp") + box(b"moov"), True, (True, None)),
        ("init-extended", box(b"moov", b"x", "extended"), True, (True, None)),
        ("map-size-zero", box(b"moov", b"x", "zero"), True, (True, None)),
        ("media-normal", box(b"moof") + box(b"mdat", bytes(128)), False,
         (True, None)),
        ("media-size-zero", box(b"moof") + box(b"mdat", b"tail", "zero"),
         False, (True, None)),
        ("trailing-unknown-box", box(b"moof") + box(b"mdat") + box(b"free"),
         False, (True, None)),
        ("short-header", b"1234567", False, (False, MESSAGES["header"])),
        ("short-extended", struct.pack(">I4s", 1, b"mdat"), False,
         (False, MESSAGES["extended"])),
        ("oversized-box", struct.pack(">I4s", 0xffffffff, b"mdat") + b"x",
         False, (False, MESSAGES["box"])),
        ("small-box", struct.pack(">I4s", 7, b"moof"), False,
         (False, MESSAGES["box"])),
        ("missing-moov", box(b"ftyp"), True, (False, MESSAGES["container"])),
        ("missing-moof", box(b"mdat"), False, (False, MESSAGES["container"])),
        ("missing-mdat", box(b"moof"), False, (False, MESSAGES["container"])),
        ("truncated-box", struct.pack(">I4s", 16, b"moof") + b"x",
         False, (False, MESSAGES["box"])),
        ("max-extended-size", struct.pack(">I4sQ", 1, b"moof", 2**64 - 1),
         False, (False, MESSAGES["box"])),
        ("small-extended-size", struct.pack(">I4sQ", 1, b"moof", 15),
         False, (False, MESSAGES["box"])),
        ("ts-as-init", b"\x47" + bytes(187), True, (False, MESSAGES["box"])),
    ]
    for original in (box(b"moov", bytes(32), "extended"),
                     box(b"moof") + box(b"mdat", bytes(64))):
        for end in range(len(original) + 1):
            for is_map in (False, True):
                cases.append((f"prefix-{len(original)}-{end}-{is_map}",
                              original[:end], is_map, None))
    for index in range(random_cases):
        size = rng.randrange(0, 2049)
        cases.append((f"random-bytes-{index}", rng.randbytes(size),
                      bool(rng.getrandbits(1)), None))
    for index in range(max(100, random_cases // 4)):
        packets = rng.randrange(1, 10)
        data = bytearray(rng.randbytes(packets * 188))
        for offset in range(0, len(data), 188):
            data[offset] = 0x47
        if rng.randrange(2):
            data[rng.randrange(0, len(data), 188)] = 0
        cases.append((f"generated-ts-{index}", bytes(data), False, None))
        kinds = [b"moov", b"moof", b"mdat", b"free", b"skip"]
        boxes = [box(rng.choice(kinds), rng.randbytes(rng.randrange(32)),
                     rng.choice(("normal", "extended", "zero")))
                 for _ in range(rng.randrange(1, 7))]
        cases.append((f"generated-mp4-{index}", b"".join(boxes),
                      bool(rng.getrandbits(1)), None))
    if fixtures:
        for path in sorted(Path(fixtures).rglob("*")):
            if (path.is_file()
                    and path.suffix.lower() in {".ts", ".m4s", ".mp4"}):
                cases.append((f"fixture:{path.name}", path.read_bytes(),
                              path.name.lower() == "init.mp4", None))
    return cases


def benchmarks():
    ts_packet = b"\x47" + bytes(187)

    def ts_bytes(target):
        return ts_packet * ((target + 187) // 188)

    return [
        ("ts-188", ts_bytes(188), False),
        ("ts-64k", ts_bytes(64 * 1024), False),
        ("ts-1m", ts_bytes(1024 * 1024), False),
        ("ts-8m", ts_bytes(8 * 1024 * 1024), False),
        ("fmp4-init", box(b"ftyp") + box(b"moov", bytes(256)), True),
        ("fmp4-media-1m", box(b"moof") + box(b"mdat", bytes(1024 * 1024)),
         False),
        ("fmp4-many-small", box(b"moof") + box(b"mdat") +
         b"".join(box(b"free", bytes(8)) for _ in range(512)), False),
    ]


def benchmark(py, rust, seconds, fixtures):
    output = []
    jobs = benchmarks()
    if fixtures:
        jobs.extend((name, data, is_map) for name, data, is_map, _
                    in corpus(0, 0, fixtures) if name.startswith("fixture:"))
    rounds = 5
    for name, data, is_map in jobs:
        py_fn = lambda: py(data, is_map=is_map)
        rs_fn = lambda: rust(data, is_map=is_map)
        py_fn()
        py_fn()
        rs_fn()
        rs_fn()
        start = time.perf_counter()
        py_fn()
        py_one = time.perf_counter() - start
        start = time.perf_counter()
        rs_fn()
        rs_one = time.perf_counter() - start
        count = min(1000000, max(1, int(seconds / len(jobs) / rounds /
                                        max(py_one + rs_one, 1e-9))))
        py_times, rs_times = [], []
        for round_index in range(rounds):
            order = ((py_fn, rs_fn) if round_index % 2 == 0
                     else (rs_fn, py_fn))
            measured = []
            for function in order:
                start = time.perf_counter()
                for _ in range(count):
                    function()
                measured.append((time.perf_counter() - start) / count)
            if round_index % 2 == 0:
                py_times.append(measured[0])
                rs_times.append(measured[1])
            else:
                rs_times.append(measured[0])
                py_times.append(measured[1])
        py_ns = statistics.median(py_times) * 1e9
        rs_ns = statistics.median(rs_times) * 1e9
        output.append({"name": name, "bytes": len(data), "is_map": is_map,
                       "count_per_round": count, "rounds": rounds,
                       "python_ns_per_call": round(py_ns, 1),
                       "rust_ns_per_call": round(rs_ns, 1),
                       "speedup": round(py_ns / rs_ns, 3)})
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261115)
    parser.add_argument("--random-cases", type=int, default=500)
    parser.add_argument("--seconds", type=float, default=20)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0 or args.random_cases < 0:
        parser.error("--seconds must be positive; --random-cases nonnegative")
    py = python_validator()
    import rust_media_validator

    rust = rust_media_validator.validate_media
    cases = corpus(args.seed, args.random_cases, args.fixtures)
    for name, data, is_map, expected in cases:
        actual = result(py, data, is_map)
        if expected is not None:
            assert actual == expected, f"Python hand-check: {name}: {actual}"
        if actual != result(rust, data, is_map):
            raise AssertionError(f"implementation mismatch: {name}")
    report = {
        "metadata": {
            "python": sys.version.split()[0], "platform": platform.platform(),
            "cpu": platform.processor() or platform.machine(),
            "source_sha256": hashlib.sha256(
                (ROOT / "hls_continuity.py").read_bytes()).hexdigest(),
            "seed": args.seed, "compared_inputs": len(cases),
            "accepted_inputs": sum(
                result(py, d, m)[0] for _, d, m, _ in cases),
        },
        "benchmarks": benchmark(py, rust, args.seconds, args.fixtures),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(cases)} inputs matched; report: {args.output}")
    for item in report["benchmarks"]:
        print(f"{item['name']}: {item['python_ns_per_call']:.0f} ns Python / "
              f"{item['rust_ns_per_call']:.0f} ns Rust "
              f"({item['speedup']:.2f}x)")


if __name__ == "__main__":
    main()
