#!/usr/bin/env bash

set -euo pipefail

if (( $# != 3 )); then
    echo "Usage: $0 DURATION_MINUTES STALL_SECONDS OUTPUT_DIR" >&2
    exit 2
fi

duration_minutes="$1"
stall_seconds="$2"
output_dir="$3"

if [[ ! "$duration_minutes" =~ ^[0-9]+$ ]] \
    || [[ ! "$stall_seconds" =~ ^[0-9]+$ ]] \
    || (( duration_minutes <= 0 || stall_seconds <= 0 )); then
    echo "Duration and stall timeout must be positive integers." >&2
    exit 2
fi

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failure_marker="$output_dir/.recording-stalled"
duration_seconds=$((duration_minutes * 60))
started_at=$(date +%s)
recorder_pid=""
monitor_pid=""
janitor_pid=""

find_recording_files() {
    find "$output_dir" \
        -type f \
        \( -name '*.ts' -o -name '*.mkv' -o -name '*.webm' \) \
        "$@"
}

stop_process() {
    local process_id="$1"
    if [[ -n "$process_id" ]] && kill -0 "$process_id" 2>/dev/null; then
        kill -TERM "$process_id" 2>/dev/null || true
        wait "$process_id" 2>/dev/null || true
    fi
}

cleanup() {
    stop_process "$janitor_pid"
    stop_process "$monitor_pid"
    stop_process "$recorder_pid"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

cd "$project_dir"

timeout \
    --preserve-status \
    --signal=TERM \
    --kill-after=120s \
    "${duration_seconds}s" \
    uv run --no-sync python chzzk_record.py &
recorder_pid=$!

(
    while kill -0 "$recorder_pid" 2>/dev/null; do
        find_recording_files -mmin +15 -delete
        sleep 60
    done
) &
janitor_pid=$!

(
    while kill -0 "$recorder_pid" 2>/dev/null; do
        latest_mtime="$({
            find_recording_files -printf '%T@\n'
        } | sort -nr | head -n 1)"
        current_time=$(date +%s)

        if [[ -z "$latest_mtime" ]]; then
            inactive_seconds=$((current_time - started_at))
        else
            latest_mtime=${latest_mtime%%.*}
            inactive_seconds=$((current_time - latest_mtime))
        fi

        if (( inactive_seconds > stall_seconds )); then
            echo "::error title=Recording stalled::No recording output was written for ${inactive_seconds} seconds."
            : > "$failure_marker"
            kill -TERM "$recorder_pid" 2>/dev/null || true
            exit 1
        fi

        sleep 15
    done
) &
monitor_pid=$!

set +e
wait "$recorder_pid"
recorder_status=$?
set -e
recorder_pid=""

stop_process "$monitor_pid"
monitor_pid=""
stop_process "$janitor_pid"
janitor_pid=""

elapsed_seconds=$(($(date +%s) - started_at))

if [[ -e "$failure_marker" ]]; then
    exit 1
fi

if (( recorder_status != 0 )); then
    echo "::error::Recorder exited with status $recorder_status."
    exit "$recorder_status"
fi

if (( elapsed_seconds + 60 < duration_seconds )); then
    echo "::error::Recorder exited before the requested duration."
    exit 1
fi

if ! grep -Fq "Recording started for " log.log; then
    echo "::error::The recorder never started writing the test channel."
    exit 1
fi

if grep -Eq \
    "Invalid NAL unit size|Error applying bitstream filters|ffmpeg failed for" \
    log.log; then
    echo "::error::FFmpeg reported corrupt input or a fatal failure."
    exit 1
fi

if [[ -z "$(find_recording_files -size +0c -print -quit)" ]]; then
    echo "::error::No non-empty recording segment remained after recording."
    exit 1
fi

echo "Recording test completed after ${elapsed_seconds} seconds without a detected stall."
