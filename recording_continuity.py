"""Small, URL-free control protocol between the plugin and recorder."""

import json
import math
from datetime import datetime, timedelta, timezone


EVENT_PREFIX = "CHZZK_REKODA_EVENT "
KINDS = {"start", "checkpoint", "recovery_started", "recovery_completed",
         "gap", "boundary", "diagnostic", "source"}
REASONS = {
    "resume_unavailable", "playlist_stalled", "playlist_unavailable",
    "broadcast_changed", "initialization_changed", "discontinuity",
    "position_unknown", "interval_unavailable", "segment_unavailable",
    "output_stalled", "broadcast_ended",
}


def valid_time(value):
    if value is None:
        return True
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def parse_event(line):
    if not line.startswith(EVENT_PREFIX) or len(line) > 4096:
        return None
    try:
        event = json.loads(line[len(EVENT_PREFIX):])
    except (ValueError, TypeError):
        return None
    if (not isinstance(event, dict) or type(event.get("version")) is not int or event.get("version") != 1
            or not isinstance(event.get("kind"), str) or event["kind"] not in KINDS
            or type(event.get("live_id")) is not int
            or not isinstance(event.get("rendition"), str)
            or len(event["rendition"]) > 32):
        return None
    if any(not valid_time(event.get(key)) for key in (
            "at", "from", "to", "resume_from", "recovery_deadline")):
        return None
    if event["kind"] in {"gap", "boundary"} and (
            not isinstance(event.get("reason"), str) or event["reason"] not in REASONS):
        return None
    if "after_gap" in event and type(event["after_gap"]) is not bool:
        return None
    if event["kind"] == "source":
        if (any(not isinstance(event.get(key), str) for key in ("cdn", "mode", "state"))
                or event.get("cdn") not in {"korean", "akamai", "unknown"}
                or event.get("mode") not in {"hls", "llhls"}
                or event.get("state") not in {"selected", "ready", "absent", "unavailable"}):
            return None
        return {key: event[key] for key in ("version", "kind", "live_id", "rendition", "cdn", "mode", "state")}
    if event["kind"] == "diagnostic":
        if (any(not isinstance(event.get(key), str) for key in ("stage", "role", "category"))
                or event["stage"] not in {"manifest", "api", "initialization", "media"}
                or event.get("role") not in {"current", "history", "primary", "alternate"}
                or event.get("category") not in {
                    "http", "network", "timeout", "truncated", "invalid_media",
                    "initialization", "unavailable", "dns", "tls", "connect", "parse"}):
            return None
        status, sequence = event.get("status"), event.get("sequence")
        if ((status is not None and (type(status) is not int or not 100 <= status <= 599))
                or (sequence is not None and (type(sequence) is not int or sequence < 0))):
            return None
    if event["kind"] == "start":
        seconds = event.get("available_seconds")
        if (type(event.get("requested_seconds")) is not int
                or event.get("requested_seconds") not in (0, 3600)
                or type(seconds) not in (int, float)
                or not math.isfinite(seconds) or seconds < 0):
            return None
        if event.get("time_machine_active") is not None and type(event["time_machine_active"]) is not bool:
            return None
    if event["kind"] == "checkpoint":
        if not {"from", "to"} <= event.keys():
            return None
        start, end = event["from"], event["to"]
        if (start is None) != (end is None):
            return None
        if start is not None and datetime.fromisoformat(end) <= datetime.fromisoformat(start):
            return None
    # Only protocol fields may reach the UI or an optional persistent report.
    fields = {
        "start": {"at", "requested_seconds", "available_seconds", "time_machine_active"},
        "checkpoint": {"from", "to"},
        "recovery_started": {"at"}, "recovery_completed": {"at"},
        "gap": {"from", "to", "reason"},
        "boundary": {"reason", "resume_from", "after_gap", "recovery_deadline"},
        "diagnostic": {"stage", "role", "category", "status", "sequence", "at"},
    }
    allowed = {"version", "kind", "live_id", "rendition"} | fields[event["kind"]]
    return {key: value for key, value in event.items() if key in allowed}


def format_log_time(value):
    """Show segment positions in the same local timezone as the log prefix."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value).astimezone().isoformat(
            sep=" ", timespec="milliseconds"
        )
    except (ValueError, OverflowError, OSError):
        return None


class RecordingContinuity:
    def __init__(self):
        self.live_id = None
        self.initial_handled = False
        self.resume = None
        self.boundary = False
        self.attempt_output = False
        self.checkpoint_resume = False

    def begin(self, live_id):
        if live_id != self.live_id:
            self.live_id = live_id
            self.initial_handled = False
            self.resume = None
            self.checkpoint_resume = False
        self.boundary = False
        self.attempt_output = False

    def arguments(self, previous_hour):
        args = ["--chzzk-start-lookback",
                "3600" if previous_hour and not self.initial_handled else "0"]
        if self.resume is not None:
            if self.checkpoint_resume and "recovery_deadline" not in self.resume:
                self.resume.update(after_gap=True, recovery_deadline=(
                    datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat())
            args.extend(["--chzzk-resume", json.dumps(self.resume)])
        return args

    def accept(self, event):
        kind = event["kind"]
        if kind == "start":
            if event["live_id"] != self.live_id:
                self.begin(event["live_id"])
            self.initial_handled = True
            # Selecting a start is not proof that any bytes were delivered.
        elif event["live_id"] != self.live_id:
            return None
        if kind == "boundary":
            self.boundary = True
            self.checkpoint_resume = False
            self.initial_handled = True
            start = event.get("resume_from")
            self.resume = (dict(live_id=self.live_id, rendition=event["rendition"],
                                **{"from": start}) if start else None)
            if self.resume is not None and event.get("after_gap", False):
                self.resume["after_gap"] = True
            if self.resume is not None and event.get("recovery_deadline") is not None:
                self.resume["recovery_deadline"] = event["recovery_deadline"]
        if kind == "checkpoint":
            self.initial_handled = True
            self.attempt_output = True
            self.checkpoint_resume = True
            if event["to"] is not None:
                self.resume = dict(live_id=self.live_id, rendition=event["rendition"],
                                   **{"from": event["to"]})
            return None
        if kind == "start":
            if event["requested_seconds"] == 0:
                return None
            short = event["available_seconds"] < 3599
            return ("record.history_short" if short else "record.history_start",
                    {"seconds": round(event["available_seconds"])}, short)
        if kind in {"recovery_started", "recovery_completed"}:
            return "record." + kind, {"at": format_log_time(event.get("at"))}, False
        if kind == "gap":
            return "record.continuity_gap", {
                "start": format_log_time(event.get("from")),
                "end": format_log_time(event.get("to")),
                "reason": event["reason"],
            }, True
        if kind == "boundary":
            if event.get("recovery_deadline") is not None:
                return "record.recovery_restart", {
                    "at": format_log_time(event.get("resume_from"))}, False
            return "record.continuity_boundary", {}, False
        if kind == "diagnostic":
            # Keep only validated, URL-free fields even if a child supplies
            # additional JSON properties containing exception text.
            details = {key: event.get(key) for key in (
                "stage", "role", "category", "status", "sequence", "at")}
            return "record.continuity_diagnostic", {"details": json.dumps(details)}, False
        if kind == "source":
            return "record.source_" + event["state"], {
                "cdn": event["cdn"], "mode": event["mode"]}, False
        return None
