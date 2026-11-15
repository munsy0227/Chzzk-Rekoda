# Optional Rust helper

The Rust binary is an optional optimization. Python remains the baseline and takes over when the binary is missing or its service cannot be used.

## Build and discovery

```bash
cargo build --release --locked --manifest-path native/Cargo.toml
```

The application discovers `native/target/release/chzzk-native` (`chzzk-native.exe` on Windows) or a manually installed binary at `native/bin/chzzk-native[.exe]`. Rust is not needed to run the Python implementation.

To verify which live-status path is active, start a recording with the helper present and DoH disabled, then check `log.log` for `Rust is checking broadcast status.`. Enabling DoH routes live-status lookups through the existing Python path. If the helper is missing at startup, Python is used without a fallback warning; the `Rust status checking is unavailable; switching to Python.` warning is logged only if a helper that was active later becomes unavailable. The optional helper does not take over the recording pipeline: the recorder still uses Streamlink and FFmpeg, and Python retains DoH.

The helper supports two commands:

- `chzzk-native serve` handles live-info requests over JSON Lines.
- `chzzk-native report <path>` summarizes supported continuity reports. Python invokes this only for reports at least 256 KiB and falls back to its own summarizer when the helper is missing, times out, fails, or reports unsupported data.

Rust performs only the live-detail HTTP request. Python retains polling schedules, authentication/header preparation, recording, Streamlink/FFmpeg, and DNS-over-HTTPS. A 3xx response disables the Rust helper and lets Python handle that request through its existing path. Ordinary HTTP 4xx/5xx, network, or invalid-response errors are returned as that poll's failure; they are not immediately retried through Python. A missing or broken helper can fall back to Python.

## Live request protocol

The Python process starts one helper and communicates through its stdin/stdout pipes. This is private process IPC; the helper does not open a listening port. Each message is one UTF-8 JSON object followed by a newline. Protocol version is `1`.

Requests:

```json
{"version":1,"id":1,"op":"hello"}
{"version":1,"id":2,"op":"live","channel_id":"0123456789abcdef0123456789abcdef","headers":{"Authorization":"..."}}
{"version":1,"id":2,"op":"cancel"}
```

`hello` replies with `{"version":1,"id":1,"ok":true,"service":"chzzk-native"}`. A successful `live` response returns the CHZZK live-detail JSON object in `data`. An error response has `ok:false`, with `error` set to `http`, `network`, `invalid_response`, or `invalid_request`; HTTP errors may include the numeric `status`. The fixed endpoint is `https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail`. Redirects are not followed.

Headers are passed from Python to the helper for that request and are never copied into replies. Error replies do not include URLs, request headers, cookies, or exception text. A `cancel` message uses the live request's ID and has no reply; it aborts that pending request. When stdin reaches EOF, outstanding work is aborted and the process shuts down.

A redirect response disables the optional live helper and returns to Python's existing redirect handling. Rust never forwards headers to a redirected address. Ordinary HTTP errors such as 429 are not immediately retried.

Limits: request lines are at most 64 KiB, HTTP response bodies and serialized replies are at most 8 MiB, HTTP requests time out after 30 seconds, and at most 16 HTTP requests run concurrently with up to 64 live requests in flight. Overlong input ends the service safely.

## Tests

```bash
cargo test --locked --manifest-path native/Cargo.toml
```

Tests cover the live JSON response and a dummy authentication header, HTTP errors, malformed and oversized responses, invalid channel IDs, oversized output handling, and continuity-report parsing.

## Manual GitHub Actions checks

To run a long recording check, open **Actions → Long recording test → Run workflow** and select the `codex/rust-features` branch. Choose:

- `native_backend`: `rust` (default) to require the helper, or `python` to exercise the Python implementation.
- `test_os`: `linux` (default), `windows`, `macos`, or `all` to use the corresponding latest stable GitHub runner images.
- `duration_minutes`: 270–330 minutes; the default is 300.
- `channel_uuid`: optionally provide a public channel UUID; blank uses the workflow's configured test channel.

For the short codec check, use **Actions → Codec smoke test → Run workflow** with the same branch and backend/OS choices. `duration_minutes` is 5–20 minutes per codec, defaulting to 10.

With `native_backend: rust`, the run builds and tests the helper, fails if it is absent or the recorder falls back to Python, and performs a separate public live-status query every minute while recording. The uploaded artifact includes `native-watch-summary.json` and the Rust test/build logs, along with the recording log and continuity reports. With `python`, the recording uses the Python implementation. The recording harness retains its existing five-minute file split and pruning of recordings older than 15 minutes. Artifacts are kept for seven days.

Use the uploaded environment metadata, logs, and summaries to assess each run; a workflow configuration alone does not establish a platform result. No five-hour Windows or macOS result is implied by these instructions. Profiling and benchmark context is documented under [`experiments/rust-profile`](../experiments/rust-profile/README.md).
