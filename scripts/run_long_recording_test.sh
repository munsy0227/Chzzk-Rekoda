#!/usr/bin/env bash

# Preserve the original DURATION_MINUTES STALL_SECONDS OUTPUT_DIR interface.
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
exec uv run --no-sync python scripts/run_recording_test.py monitor "$@"
