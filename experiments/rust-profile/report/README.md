# Continuity report Rust comparison

This is an isolated experiment. It reads the same NDJSON report format as
`continuity_report.py:summarize`, applies report-row and event checks represented
from `recording_continuity.py:parse_event`, and writes a summary JSON. It is not
wired into the recorder or project dependencies.

The Rust candidate uses `serde_json` and `chrono`; its timestamps accept the
RFC3339 subset. Python `datetime.fromisoformat` accepts additional spellings,
and Python integers are unbounded while this experiment stores `live_id` in
`i64`. Results are only claimed as equivalent for the recorded report and the
standard RFC3339 fixtures checked by `bench.py`.

`bench.py` compares three whole-process candidates: Python with the standard
library JSON module, Python with an `orjson` shim, and Rust. The shim replaces
only `json.loads`/`json.dumps` inside `continuity_report` and
`recording_continuity`; it converts input strings to UTF-8 bytes and decodes
`orjson.dumps` bytes back to strings, so those boundary conversions are timed.
Harness output and summary-file serialization keep using standard-library
`json`. The `orjson` run checks parity only for these fixtures: differences in
accepted inputs such as integer range or NaN handling mean this shim is not
claimed as a production drop-in replacement.

With the task's isolated Rust/Python toolchains:

```sh
export RUSTUP_HOME=/tmp/chzzk-rust-rustup
export CARGO_HOME=/tmp/chzzk-rust-cargo
export PATH="$CARGO_HOME/bin:$PATH"
cargo build --release --manifest-path experiments/rust-profile/report/Cargo.toml \
  --target-dir /tmp/chzzk-profile-report-target
/tmp/chzzk-rust-env/bin/python experiments/rust-profile/report/bench.py --self-check
```

`--self-check` compares all three candidates against the Python standard JSON
oracle for the recorded report, 1,000, 10,000, and 100,000-checkpoint generated
reports, and a missing-footer report. It includes valid, blank, malformed,
duplicate, unresolved, and 20 ms threshold rows. It does not collect benchmark
timings.

After choosing benchmark order and CPU availability, run:

```sh
/tmp/chzzk-rust-env/bin/python experiments/rust-profile/report/bench.py \
  --benchmark --rounds 5 --output experiments/rust-profile/report/benchmark-results.json
```

The raw output records five repetitions per candidate and dataset, worker wall
time, Linux `wait4` worker-tree CPU time, in-process algorithm wall time, and
candidate-local memory. `algorithm_cpu_ns` is worker-only CPU and is available
for the two Python runners; the Rust binary does not report a separate
algorithm CPU counter.
`startup_and_output_wall_ns_estimate` is the child wall time minus measured
input processing; it is an estimate, not a separate process-start measurement.
After processing, each worker samples its own `/proc/self/status`:
`process_self_vm_hwm_kib` is peak resident memory so far, and
`process_self_vm_rss_kib` is current resident memory, both in KiB. The raw
`wait4_child_ru_maxrss_kib_raw` is retained for diagnosis but excluded from
candidate comparisons because the parent can affect that high-water reading.
These process-local measurements do not include child processes such as FFmpeg.
