#!/usr/bin/env python3
"""Local fixture, Python watcher worker, and ordered Python/Rust matrix runner."""

import argparse
import ast
import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import aiohttp
from aiohttp import web

ROOT = Path(__file__).resolve().parents[3]


def load_get_live_info(base):
    source = ast.parse((ROOT / "chzzk_record.py").read_text(encoding="utf-8"))
    node = next(
        n
        for n in source.body
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "get_live_info"
    )
    node.returns = None
    for arg in (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ):
        arg.annotation = None
    logger = type(
        "Log",
        (),
        {
            name: (lambda self, *a, **k: None)
            for name in ("debug", "info", "warning", "error")
        },
    )()
    scope = {
        "aiohttp": aiohttp,
        "logger": logger,
        "tr": lambda key, **kwargs: f"{key} {kwargs.get('error', '')}",
        "has_auth_cookies": lambda _cookies: False,
        "LIVE_DETAIL_API": f"{base}/api/{{channel_id}}",
    }
    exec(
        compile(
            ast.fix_missing_locations(ast.Module([node], [])),
            "chzzk_record.py",
            "exec",
        ),
        scope,
    )
    return scope["get_live_info"]


async def fixture(request):
    app = request.app
    channel = int(request.match_info["channel"])
    app["calls"][channel] = app["calls"].get(channel, 0) + 1
    if app["scenario"] == "cases":
        if channel == 2:
            raise web.HTTPInternalServerError()
        if channel == 3:
            raise web.HTTPTooManyRequests()
        if channel == 4:
            await asyncio.sleep(0.25)
        if channel == 5:
            return web.Response(text="{")
    if app["delay"]:
        await asyncio.sleep(app["delay"])
    status = (
        "CLOSE"
        if app["scenario"] == "cases"
        and (channel == 1 or (channel == 0 and app["calls"][channel] == 1))
        else "OPEN"
    )
    return web.json_response(
        {"content": {"status": status, "liveId": 1000 + channel}}
    )


async def serve(args):
    app = web.Application()
    app["delay"] = args.delay_ms / 1000
    app["scenario"] = args.scenario
    app["calls"] = {}
    app.router.add_get("/api/{channel}", fixture)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    print(site._server.sockets[0].getsockname()[1], flush=True)
    await asyncio.Event().wait()


async def python_worker(args):
    get_live_info = load_get_live_info(args.base)
    semaphore = asyncio.Semaphore(16)
    outcomes = {}
    live_ids = {}
    starts = 0
    first_open_response_ms = []
    requests = 0
    timeout = aiohttp.ClientTimeout(total=0.1)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("READY", file=sys.stderr, flush=True)
        await asyncio.get_running_loop().run_in_executor(
            None, sys.stdin.readline
        )
        started = time.perf_counter()
        cpu_started = time.process_time()
        for _ in range(args.rounds):
            round_started = time.perf_counter()

            async def poll(channel):
                nonlocal starts, requests
                async with semaphore:
                    requests += 1
                    status, data = await get_live_info(
                        {"id": str(channel), "name": str(channel)},
                        {},
                        {},
                        session,
                    )
                    if status:
                        category = status
                    elif args.scenario == "cases":
                        category = {
                            2: "HTTP_500",
                            3: "HTTP_429",
                            4: "TIMEOUT",
                            5: "INVALID_JSON",
                        }.get(channel, "ERROR")
                    else:
                        category = "ERROR"
                    outcomes[category] = outcomes.get(category, 0) + 1
                    if status == "OPEN" and data.get("liveId"):
                        live_id = data["liveId"]
                        if live_ids.get(channel) != live_id:
                            live_ids[channel] = live_id
                            starts += 1
                            first_open_response_ms.append(
                                {
                                    "channel": channel,
                                    "ms": (time.perf_counter() - started)
                                    * 1000,
                                }
                            )

            await asyncio.gather(*(poll(i) for i in range(args.channels)))
            remaining = args.interval - (time.perf_counter() - round_started)
            if remaining > 0:
                await asyncio.sleep(remaining)
    steady_cpu_seconds = time.process_time() - cpu_started
    print(
        json.dumps(
            {
                "requests": requests,
                "starts": starts,
                "outcomes": outcomes,
                "first_open_response_ms": first_open_response_ms,
                "elapsed_seconds": time.perf_counter() - started,
                "steady_cpu_seconds": steady_cpu_seconds,
            }
        )
    )


def rss_kib(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (FileNotFoundError, ProcessLookupError):
        pass
    return None


def sample_peak(pid, samples):
    while True:
        value = rss_kib(pid)
        if value is None:
            return
        samples.append(value)
        time.sleep(0.01)


def run_worker(command):
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    ready = process.stderr.readline().strip()
    if ready != "READY":
        raise RuntimeError(f"Watcher did not become ready: {ready}")
    startup_rss = rss_kib(process.pid)
    samples = []
    process.stdin.write("GO\n")
    process.stdin.flush()
    sampler = threading.Thread(
        target=sample_peak, args=(process.pid, samples), daemon=True
    )
    sampler.start()
    stdout = process.stdout.readline()
    waited_pid, wait_status, usage = os.wait4(process.pid, 0)
    assert waited_pid == process.pid
    process.returncode = os.waitstatus_to_exitcode(wait_status)
    sampler.join(timeout=1)
    stderr = process.stderr.read()
    if process.returncode:
        raise RuntimeError(stderr)
    result = json.loads(stdout)
    result.update(
        {
            "startup_rss_kib": startup_rss,
            "steady_peak_rss_kib": max(samples, default=startup_rss),
            "rss_samples_kib": samples,
            "cpu_seconds": usage.ru_utime + usage.ru_stime,
            "cpu_user_seconds": usage.ru_utime,
            "cpu_system_seconds": usage.ru_stime,
            "rss_peak_kib": usage.ru_maxrss,
        }
    )
    return result


def server_process(delay_ms, scenario):
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--server",
        str(delay_ms),
        scenario,
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    port = int(process.stdout.readline())
    return process, f"http://127.0.0.1:{port}"


def sample_case(
    binary, channels, delay_ms, rounds, interval, scenario, language
):
    server, base = server_process(delay_ms, scenario)
    try:
        if language == "python":
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--python-worker",
                base,
                str(channels),
                str(rounds),
                str(interval),
                scenario,
            ]
        else:
            command = [
                str(binary),
                base,
                str(channels),
                str(rounds),
                str(interval),
            ]
        before = time.perf_counter()
        result = run_worker(command)
        result["wall_seconds_including_startup"] = time.perf_counter() - before
        result["cpu_unit"] = "seconds (wait4 child user + system CPU)"
        result["steady_cpu_unit"] = (
            "seconds (GO gate to pre-output; watcher process only)"
        )
        result["rss_unit"] = "KiB (wait4 ru_maxrss and Linux /proc VmRSS)"
        return result
    finally:
        server.terminate()
        server.wait()


def selfcheck(binary):
    py = sample_case(binary, 6, 0, 3, 0.2, "cases", "python")
    rs = sample_case(binary, 6, 0, 3, 0.2, "cases", "rust")
    expected = {
        "OPEN": 2,
        "CLOSE": 4,
        "HTTP_500": 3,
        "HTTP_429": 3,
        "TIMEOUT": 3,
        "INVALID_JSON": 3,
    }
    assert py["requests"] == rs["requests"] == 18, (py, rs)
    assert py["starts"] == rs["starts"] == 1, (py, rs)
    assert py["outcomes"] == rs["outcomes"] == expected, (py, rs)
    return {"python": py, "rust": rs, "expected": expected}


def matrix(binary, output):
    results = []
    for channels in (1, 16, 64):
        for delay_ms in (0, 20):
            for trial in range(3):
                samples = {}
                # Alternating order limits systematic warm-up/order bias.
                order = (
                    ("python", "rust")
                    if trial % 2 == 0
                    else ("rust", "python")
                )
                for language in order:
                    samples[language] = sample_case(
                        binary, channels, delay_ms, 5, 0.3, "open", language
                    )
                assert samples["python"]["requests"] == channels * 5
                assert samples["rust"]["requests"] == channels * 5
                expected_outcomes = {"OPEN": channels * 5}
                for sample in samples.values():
                    assert sample["starts"] == channels, sample
                    assert sample["outcomes"] == expected_outcomes, sample
                results.append(
                    {
                        "channels": channels,
                        "response_delay_ms": delay_ms,
                        "trial": trial + 1,
                        "samples": samples,
                    }
                )
    Path(output).write_text(json.dumps({"results": results}, indent=2) + "\n")
    print(json.dumps({"output": str(output), "samples": len(results)}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", nargs=2, metavar=("DELAY_MS", "SCENARIO"))
    parser.add_argument(
        "--python-worker",
        nargs=5,
        metavar=("BASE", "CHANNELS", "ROUNDS", "INTERVAL", "SCENARIO"),
    )
    parser.add_argument("mode", nargs="?", choices=("selfcheck", "matrix"))
    parser.add_argument("binary", nargs="?", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("results.json")
    )
    args = parser.parse_args()
    if args.server:
        args.delay_ms, args.scenario = int(args.server[0]), args.server[1]
        asyncio.run(serve(args))
    elif args.python_worker:
        (base, channels, rounds, interval, scenario) = args.python_worker
        args.base, args.channels = base, int(channels)
        args.rounds, args.interval, args.scenario = (
            int(rounds),
            float(interval),
            scenario,
        )
        asyncio.run(python_worker(args))
    elif args.mode == "selfcheck":
        print(json.dumps(selfcheck(args.binary), sort_keys=True))
    elif args.mode == "matrix":
        matrix(args.binary.resolve(), args.output)


if __name__ == "__main__":
    main()
