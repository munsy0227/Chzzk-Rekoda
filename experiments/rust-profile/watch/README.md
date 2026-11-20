# Watcher profiling scratchpad

Local-only comparison of the current Python `get_live_info` call boundary and a small Rust `tokio`/`reqwest` watcher. This is a benchmark harness, not a production port: cookie/member handling, settings reload, shutdown coordination, recording ownership, and production API behavior are out of scope.

Python extracts the existing `get_live_info` function's AST from `chzzk_record.py` and injects only its logger/translation dependencies; this avoids importing the application and loading personal configuration. Both clients reuse one HTTP client/session, poll the same local fixture, and cap in-flight requests at 16. Fixture statuses are local and must never be replaced with real CHZZK endpoints for load testing.

The fixture exercises OPEN, CLOSE, HTTP 500, HTTP 429, timeout, and malformed JSON. The state check counts a start once per `(channel_id, liveId)`, even across repeated OPEN polls. Benchmark mode will use 1/16/64 channels, 0/20 ms fixture delay, fixed 0.3 s cadence, five rounds, and record wall time, process CPU/RSS, detection latency, request count, and raw samples. Startup and steady-state memory are reported separately; if Python GUI/manager remains resident, Rust RSS is an additional daemon cost.

Use the release executable at `/tmp/chzzk-profile-watch-target/release/watch-profile`:

```sh
/tmp/chzzk-rust-env/bin/python experiments/rust-profile/watch/watch.py selfcheck /tmp/chzzk-profile-watch-target/release/watch-profile
/tmp/chzzk-rust-env/bin/python experiments/rust-profile/watch/watch.py matrix /tmp/chzzk-profile-watch-target/release/watch-profile
```

The matrix covers 1/16/64 channels, 0/20 ms valid-JSON response delay, five fixed polling rounds at 0.3 s, concurrency 16, and three trials. It asserts equal requests, one start per channel, and exactly `channels * rounds` OPEN outcomes. It alternates client order, writes raw per-run JSON to `results.json`, and measures each watcher in a separate process from the fixture server. `wait4` CPU (user+system seconds) includes process startup; `steady_cpu_seconds` measures only the watcher from the GO gate until just before output (Python `time.process_time`, Rust `CLOCK_PROCESS_CPUTIME_ID`). RSS values are KiB (`wait4 ru_maxrss` and sampled `/proc/<pid>/status` VmRSS). Idle startup RSS is recorded after readiness and before the start gate; the steady peak is sampled every 10 ms.

The fixture server is a separate local process, so its CPU is excluded. `first_open_response_ms` is elapsed time from the start gate to the first OPEN response; matrix channels are already OPEN at startup, so this is startup first-response timing, not steady-state transition detection latency. The harness does not benchmark the user's Python GUI/manager process; if that stays resident in the proposed deployment, its RSS is the existing baseline and Rust watcher RSS is additional daemon cost.
