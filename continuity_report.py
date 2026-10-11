"""Optional URL-free NDJSON recording evidence and end-of-run CI verdict."""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from recording_continuity import EVENT_PREFIX, parse_event


class ContinuityReport:
    def __init__(self, path):
        self.file = Path(path).open("w", encoding="utf-8")
        self.failed = False
        self.write({"version": 1, "kind": "report_started"})

    def write(self, row):
        try:
            self.file.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.file.flush()
        except OSError:
            self.failed = True

    def record(self, channel_id, event):
        clean = parse_event(EVENT_PREFIX + json.dumps(event))
        if clean is None:
            self.write({"version": 1, "kind": "report_error"})
        else:
            self.write(dict(clean, channel_id=channel_id))

    def finish(self, complete):
        self.write({"version": 1, "kind": "report_finished",
                    "complete": bool(complete and not self.failed)})
        try:
            self.file.close()
        except OSError:
            self.failed = True


def summarize(lines):
    intervals = defaultdict(list)
    ends = {}
    pending = set()
    undated = set()
    checkpoints = duplicates = errors = 0
    started = finished = False
    for line in lines:
        try:
            if len(line) > 8192:
                raise ValueError("Oversized row")
            row = json.loads(line)
            if not isinstance(row, dict) or type(row.get("version")) is not int or row["version"] != 1:
                raise ValueError("Invalid report")
            kind = row.get("kind")
            if kind == "report_started":
                if started or finished:
                    errors += 1
                started = True
                continue
            if kind == "report_finished":
                if not started or finished or row.get("complete") is not True:
                    errors += 1
                finished = True
                continue
            if not started or finished:
                errors += 1
            if kind == "report_error":
                errors += 1
                continue
            channel_id = row.get("channel_id")
            if not isinstance(channel_id, str) or len(channel_id) > 128:
                raise ValueError("Invalid channel")
            event = parse_event(EVENT_PREFIX + json.dumps(row))
            if event is None:
                raise ValueError("Invalid event")
            key = (channel_id, event["live_id"], event["rendition"])

            def add_gap(start, end):
                if start and end:
                    first, last = datetime.fromisoformat(start), datetime.fromisoformat(end)
                    if (last - first).total_seconds() > 0.02:
                        intervals[key].append((first.timestamp(), last.timestamp()))

            if kind == "gap":
                if event.get("from") is None or event.get("to") is None:
                    pending.add(key)
                else:
                    add_gap(event["from"], event["to"])
            elif kind == "boundary":
                reason = event["reason"]
                if reason in {"broadcast_ended", "broadcast_changed"}:
                    pending.discard(key)
                elif reason in {"initialization_changed", "discontinuity"}:
                    resume = event.get("resume_from")
                    if resume and key in ends and datetime.fromisoformat(resume) < ends[key]:
                        # Explicit clock reset starts a new media timeline.
                        ends.pop(key)
                else:
                    pending.add(key)
            elif kind == "checkpoint":
                checkpoints += 1
                start, end = event["from"], event["to"]
                if start is None:
                    undated.add(key)
                    continue
                first, last = datetime.fromisoformat(start), datetime.fromisoformat(end)
                if key in ends:
                    delta = (first - ends[key]).total_seconds()
                    if delta < -0.02:
                        duplicates += 1
                    elif delta > 0.02:
                        add_gap(ends[key].isoformat(), start)
                ends[key] = last
                pending.discard(key)
        except (ValueError, TypeError, KeyError, OverflowError):
            errors += 1
    if not started or not finished or not checkpoints:
        errors += 1
    merged = []
    for key, ranges in intervals.items():
        combined = []
        for first, last in sorted(ranges):
            if combined and first <= combined[-1][1] + 0.02:
                combined[-1][1] = max(last, combined[-1][1])
            else:
                combined.append([first, last])
        merged.extend(dict(channel_id=key[0], live_id=key[1], rendition=key[2],
                           start=first, end=last) for first, last in combined)
    unresolved = len(pending | undated)
    return dict(version=1, passed=not (merged or unresolved or errors or duplicates),
                gap_count=len(merged), gap_seconds=round(sum(r["end"] - r["start"] for r in merged), 6),
                unresolved_count=unresolved, checkpoint_count=checkpoints,
                duplicate_count=duplicates, error_count=errors, gaps=merged)


def main():
    from i18n import SUPPORTED_LANGUAGES, translate

    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--language", choices=SUPPORTED_LANGUAGES, default="en")
    args = parser.parse_args()
    try:
        with args.report.open(encoding="utf-8") as source:
            result = summarize(source)
    except (OSError, UnicodeError):
        result = summarize([])
    args.summary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(translate(args.language, "record.continuity_summary",
                    gaps=result["gap_count"], seconds=result["gap_seconds"],
                    unresolved=result["unresolved_count"], errors=result["error_count"],
                    duplicates=result["duplicate_count"]))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
