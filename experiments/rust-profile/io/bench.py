#!/usr/bin/env python3
"""Isolated I/O comparisons; full workloads are opt-in via --full."""

import argparse
import asyncio
import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
import tracemalloc
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
BIN = Path("/tmp/chzzk-profile-io-target/release/rust-profile-io")
CHUNK = 256 * 1024


def box(kind, payload):
    return (len(payload) + 8).to_bytes(4, "big") + kind + payload


def report(name, operation, repeats, trace_memory=False):
    wall, cpu, child_cpu, self_rss, child_rss, alloc, details = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for _ in range(repeats):
        child0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        c0, w0 = time.process_time(), time.perf_counter()
        details.append(operation())
        wall.append(time.perf_counter() - w0)
        cpu.append(time.process_time() - c0)
        self1, child1 = (
            resource.getrusage(resource.RUSAGE_SELF),
            resource.getrusage(resource.RUSAGE_CHILDREN),
        )
        child_cpu.append(
            (child1.ru_utime - child0.ru_utime)
            + (child1.ru_stime - child0.ru_stime)
        )
        self_rss.append(self1.ru_maxrss)
        child_rss.append(child1.ru_maxrss)
    if trace_memory:
        tracemalloc.start()
        current, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        operation()
        _, peak = tracemalloc.get_traced_memory()
        alloc.append(max(0, peak - current))
        tracemalloc.stop()
    return {
        "name": name,
        "wall_seconds": wall,
        "process_cpu_seconds": cpu,
        "child_cpu_seconds": child_cpu,
        "process_maxrss_kib": self_rss,
        "children_maxrss_kib_cumulative": child_rss,
        "tracemalloc_peak_delta_bytes": alloc,
        "details": details,
    }


def disk_case(size, root):
    from recording_buffer import MediaBuffer
    import hls_continuity

    init = box(b"ftyp", b"isom") + box(b"moov", b"test")
    media = box(b"moof", b"x") + box(b"mdat", b"m" * (size - len(init) - 17))
    meta = {
        "at": datetime.now(timezone.utc).isoformat(),
        "duration": 1.0,
        "number": 1,
        "discontinuity": False,
        "discontinuity_id": None,
        "cdn": "unknown",
        "mode": "hls",
    }
    buf = MediaBuffer(root, 1, "io-benchmark", max_bytes=size * 8 + 65536)
    row = buf.store(meta, init, media)
    start_at = datetime.now(timezone.utc)
    samples = [
        dict(meta, at=(start_at + timedelta(microseconds=i + 1)).isoformat())
        for i in range(4)
    ]
    next_sample = 0

    def store_sample():
        nonlocal next_sample
        row = buf.store(samples[next_sample], init, media)
        next_sample += 1
        return row["size"] == size

    store = report(
        "MediaBuffer.store (prebuilt buffer, metadata, payload; store call only)",
        store_sample,
        3,
        True,
    )
    download = hls_continuity.BufferedDownload(
        type("Located", (), {})(), buf, row, "hls"
    )
    load = report(
        "MediaBuffer.load", lambda: buf.load(row) == (init, media), 3, True
    )
    materialize = report(
        "BufferedDownload.materialize x2",
        lambda: (
            download.materialize().media == media,
            download.materialize().media == media,
        ),
        3,
        True,
    )
    return {"store": store, "load": load, "materialize_twice": materialize}


def child_source(size):
    block = bytes(range(256)) * 1024
    left = size
    while left:
        data = block[: min(left, len(block))]
        view = memoryview(data)
        while view:
            view = view[os.write(1, view) :]
        left -= len(data)


def child_sink(slow_ms):
    checksum, count = 0, 0
    while True:
        chunk = sys.stdin.buffer.read(CHUNK)
        if not chunk:
            break
        checksum = zlib.crc32(chunk, checksum)
        count += len(chunk)
        if slow_ms:
            time.sleep(slow_ms / 1000)
    print(f"{count} {checksum:08x}")


async def python_pipe(size, slow_ms=0):
    import chzzk_record

    args = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child-source",
        str(size),
    ]
    sink_args = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child-sink",
        str(slow_ms),
    ]
    source = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE
    )
    sink = await asyncio.create_subprocess_exec(
        *sink_args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    count = await chzzk_record.pipe_stream_to_stdin(
        source.stdout, sink.stdin, "io-benchmark"
    )
    await source.wait()
    output, _ = await sink.communicate()
    return count, output.decode().strip(), source.returncode, sink.returncode


def rust_pipe(size, slow_ms=0):
    script = str(Path(__file__).resolve())
    source = subprocess.Popen(
        [sys.executable, script, "--child-source", str(size)],
        stdout=subprocess.PIPE,
    )
    relay = subprocess.Popen(
        [str(BIN), "relay"], stdin=source.stdout, stdout=subprocess.PIPE
    )
    sink = subprocess.Popen(
        [sys.executable, script, "--child-sink", str(slow_ms)],
        stdin=relay.stdout,
        stdout=subprocess.PIPE,
        text=True,
    )
    source.stdout.close()
    relay.stdout.close()
    output, _ = sink.communicate()
    return size, output.strip(), source.wait(), relay.wait(), sink.returncode


def direct_pipe(size):
    script = str(Path(__file__).resolve())
    source = subprocess.Popen(
        [sys.executable, script, "--child-source", str(size)],
        stdout=subprocess.PIPE,
    )
    sink = subprocess.Popen(
        [sys.executable, script, "--child-sink", "0"],
        stdin=source.stdout,
        stdout=subprocess.PIPE,
        text=True,
    )
    source.stdout.close()
    output, _ = sink.communicate()
    return size, output.strip(), source.wait(), sink.returncode


def verify_pipe(result, size):
    # Compare independently with an incrementally computed checksum for arbitrary sizes.
    crc = 0
    block = bytes(range(256)) * 1024
    left = size
    while left:
        piece = block[: min(left, len(block))]
        crc = zlib.crc32(piece, crc)
        left -= len(piece)
    wanted = f"{size} {crc:08x}"
    assert (
        result[0] == size
        and result[1] == wanted
        and all(code == 0 for code in result[2:])
    ), result


def segment_case(count, root):
    import chzzk_record

    directory = root / f"segments-{count}"
    directory.mkdir()
    template = "clip-%03d.ts"
    for i in range(count):
        path = directory / f"clip-{i + 1:03}.ts"
        if i < 3:
            path.write_bytes(bytes([i]) * (i * 128))
        else:
            path.touch()
    for bad in (
        "clip-.ts",
        "clip-x.ts",
        "clip-1.ts.tmp",
        "clip-+2.ts",
        "other-1.ts",
    ):
        (directory / bad).touch()
    empty = directory / "clip-0000000000000.ts"
    empty.touch()
    huge_index = directory / f"clip-{'9' * 60}.ts"
    huge_index.touch()
    old_name = directory / "clip-1.ts"
    old_name.touch()
    renamed = directory / "clip-100001.ts"
    old_name.replace(renamed)
    p = report(
        "Python.segment_output_files",
        lambda: [
            p.name
            for p in chzzk_record.segment_output_files(directory, template)
        ],
        3,
    )
    cmd = [str(BIN), "files", str(directory), "clip-", ".ts"]
    rust = report(
        "Rust.segment_scan_sort",
        lambda: subprocess.check_output(cmd, text=True).splitlines(),
        3,
    )
    python_names, rust_names = p["details"][0], rust["details"][0]
    assert python_names == rust_names, (python_names[:5], rust_names[:5])
    progress = {"segment_template": template, "output_dir": str(directory)}
    total = report(
        "Python.recording_output_size",
        lambda: chzzk_record.recording_output_size(progress),
        3,
    )
    rust_total = report(
        "Rust.segment_scan_sort_stat_sum",
        lambda: int(
            subprocess.check_output(
                [str(BIN), "size", str(directory), "clip-", ".ts"], text=True
            ).strip()
        ),
        3,
    )
    cached_paths = chzzk_record.segment_output_files(directory, template)

    def cached_total():
        total_bytes = 0
        for path in cached_paths:
            try:
                total_bytes += path.stat().st_size
            except FileNotFoundError:
                continue
        return total_bytes

    cached = report("Python cached path stat sum (snapshot)", cached_total, 3)
    expected_size = sum(
        (directory / name).stat().st_size for name in python_names
    )
    assert (
        total["details"]
        == rust_total["details"]
        == cached["details"]
        == [expected_size] * 3
    )
    return {
        "list": p,
        "rust": rust,
        "total_size": total,
        "rust_total_size": rust_total,
        "cached_python_snapshot": cached,
        "edge_cases": {
            "empty_file_size": empty.stat().st_size,
            "huge_index_name": huge_index.name,
            "renamed_name": renamed.name,
            "function_matches_renamed": renamed
            in chzzk_record.segment_output_files(directory, template),
        },
    }


def hash_case(init, media, root):
    init_path, media_path = root / "init-bytes", root / "media-bytes"
    init_path.write_bytes(init)
    media_path.write_bytes(media)
    copied = report(
        "Python SHA256(init + media)",
        lambda: hashlib.sha256(init + media).hexdigest(),
        3,
    )

    def update_twice():
        hasher = hashlib.sha256()
        hasher.update(init)
        hasher.update(media)
        return hasher.hexdigest()

    updated = report(
        "Python SHA256.update(init); update(media)", update_twice, 3
    )
    rust = report(
        "Rust sha2 internal-repeat batch (process wall includes startup+file read)",
        lambda: subprocess.check_output(
            [str(BIN), "hash", str(init_path), str(media_path), "20"],
            text=True,
        ).strip(),
        1,
    )
    digest, raw_ns = rust["details"][0].split()
    rust_ns = [int(value) for value in raw_ns.split(",")]
    expected = copied["details"][0]
    assert all(value == expected for value in updated["details"])
    assert digest == expected and len(rust_ns) == 20
    return {
        "concat": copied,
        "update_twice": updated,
        "rust_batch": rust,
        "rust_sha256_internal_ns_each_repeat": rust_ns,
        "digest_match": True,
        "rust_process_wall_seconds": rust["wall_seconds"][0],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="run the requested 256 MiB and large directory cases",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="only run small correctness checks",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--child-source", type=int)
    parser.add_argument("--child-sink", type=int)
    args = parser.parse_args()
    if args.child_source is not None:
        child_source(args.child_source)
        return
    if args.child_sink is not None:
        child_sink(args.child_sink)
        return
    if not BIN.exists():
        raise SystemExit(
            f"build first: cargo build --release --manifest-path {HERE}/Cargo.toml --target-dir /tmp/chzzk-profile-io-target"
        )

    results = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "rust": subprocess.check_output(
            ["rustc", "--version"], text=True
        ).strip(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "warm_cache": True,
        "flush": "not attempted; no privileged cache flush",
        "cases": [],
    }
    scale = [1024 * 1024, 8 * 1024 * 1024] if not args.quick else [64 * 1024]
    tmpfs = Path(tempfile.gettempdir())
    cache = HERE / ".cache"
    cache.mkdir(exist_ok=True)
    for label, base in (("tmpfs", tmpfs), ("ssd-cache", cache)):
        if not base.is_dir() or not os.access(base, os.W_OK):
            results["cases"].append(
                {"name": label, "skipped": "unavailable or not writable"}
            )
            continue
        with tempfile.TemporaryDirectory(prefix="io-bench-", dir=base) as temp:
            root = Path(temp)
            for size in scale:
                init = box(b"ftyp", b"isom") + box(b"moov", b"test")
                media = box(b"moof", b"x") + box(
                    b"mdat", b"m" * (size - len(init) - 17)
                )
                local = root / f"media-{size}"
                local.mkdir()
                measure = disk_case(size, local)
                rust_src, rust_dst = root / "payload", root / "rust-copy"
                rust_src.write_bytes(init + media)
                rust = report(
                    "Rust buffered copy+verify",
                    lambda: subprocess.check_output(
                        [str(BIN), "copy", str(rust_src), str(rust_dst)],
                        text=True,
                    ).strip(),
                    3,
                )
                py = report(
                    "Python buffered copy+CRC32",
                    lambda: (
                        (local / "python-copy").write_bytes(
                            rust_src.read_bytes()
                        ),
                        f"{zlib.crc32((local / 'python-copy').read_bytes()):08x}",
                    ),
                    3,
                )
                assert (
                    rust["details"]
                    and rust_dst.read_bytes() == rust_src.read_bytes()
                )
                assert all(
                    d[1] == rust["details"][0].split()[1]
                    for d in py["details"]
                )
                results["cases"].append(
                    {
                        "medium": label,
                        "size": size,
                        "python_media_buffer": measure,
                        "rust_file_roundtrip": rust,
                        "python_file_roundtrip": py,
                        "media_buffer_comparison": "Rust raw payload I/O only; MediaBuffer validation, locks, metadata, SHA256, and eviction are Python-only",
                    }
                )

    with tempfile.TemporaryDirectory(prefix="io-hash-", dir=cache) as temp:
        root = Path(temp)
        for size in scale:
            init = box(b"ftyp", b"isom") + box(b"moov", b"test")
            media = b"m" * (size - len(init))
            results["cases"].append(
                {"sha256_size": size, "sha256": hash_case(init, media, root)}
            )

    pipe_size = 256 * 1024 * 1024 if args.full else 1024 * 1024
    __import__("chzzk_record")  # Warm the production helper before timing.

    for name, operation in (
        (
            "Python pipe_stream_to_stdin",
            lambda: asyncio.run(python_pipe(pipe_size)),
        ),
        ("Rust relay, OS-connected processes", lambda: rust_pipe(pipe_size)),
        ("direct OS pipe", lambda: direct_pipe(pipe_size)),
    ):
        row = report(name, operation, 3)
        for result in row["details"]:
            verify_pipe(result, pipe_size)
        results["cases"].append(row)
    slow = asyncio.run(python_pipe(8 * 1024 * 1024, slow_ms=1))
    verify_pipe(slow, 8 * 1024 * 1024)
    slow_rust = rust_pipe(8 * 1024 * 1024, slow_ms=1)
    verify_pipe(slow_rust, 8 * 1024 * 1024)
    results["pipe_backpressure_selfcheck"] = {
        "python_slow_sink": slow,
        "rust_slow_sink": slow_rust,
        "eof": "source exit + sink digest/exit verified",
    }
    for count in [100, 1000, 10000] if args.full else [100]:
        with tempfile.TemporaryDirectory(
            prefix="io-segments-", dir=cache
        ) as temp:
            results["cases"].append(
                {
                    "segment_count": count,
                    "measurements": segment_case(count, Path(temp)),
                }
            )
    results["completed_utc"] = datetime.now(timezone.utc).isoformat()
    out = json.dumps(results, indent=2)
    if args.output:
        args.output.write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
