"""Small, URL-free control protocol between the plugin and recorder."""

import json
import math
from datetime import datetime


EVENT_PREFIX = "CHZZK_REKODA_EVENT "
KINDS = {"start", "recovery_started", "recovery_completed", "gap", "boundary"}
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
    if (not isinstance(event, dict) or event.get("version") != 1
            or event.get("kind") not in KINDS
            or type(event.get("live_id")) is not int
            or not isinstance(event.get("rendition"), str)
            or len(event["rendition"]) > 32):
        return None
    if any(not valid_time(event.get(key)) for key in ("at", "from", "to", "resume_from")):
        return None
    if event["kind"] in {"gap", "boundary"} and event.get("reason") not in REASONS:
        return None
    if event["kind"] == "start":
        seconds = event.get("available_seconds")
        if (event.get("requested_seconds") not in (0, 3600)
                or type(seconds) not in (int, float)
                or not math.isfinite(seconds) or seconds < 0):
            return None
    return event


class RecordingContinuity:
    def __init__(self):
        self.live_id = None
        self.initial_handled = False
        self.resume = None
        self.boundary = False

    def begin(self, live_id):
        if live_id != self.live_id:
            self.live_id = live_id
            self.initial_handled = False
            self.resume = None
        self.boundary = False

    def arguments(self, previous_hour):
        args = ["--chzzk-start-lookback",
                "3600" if previous_hour and not self.initial_handled else "0"]
        if self.resume is not None:
            args.extend(["--chzzk-resume", json.dumps(self.resume)])
        return args

    def accept(self, event):
        kind = event["kind"]
        if kind == "start":
            if event["live_id"] != self.live_id:
                self.begin(event["live_id"])
            self.initial_handled = True
            self.resume = None
        elif event["live_id"] != self.live_id:
            return None
        if kind == "boundary":
            self.boundary = True
            self.initial_handled = True
            start = event.get("resume_from")
            self.resume = (dict(live_id=self.live_id, rendition=event["rendition"],
                                **{"from": start}) if start else None)
        if kind == "start":
            if event["requested_seconds"] == 0:
                return None
            short = event["available_seconds"] < 3599
            return ("record.history_short" if short else "record.history_start",
                    {"seconds": round(event["available_seconds"])}, short)
        if kind in {"recovery_started", "recovery_completed"}:
            return "record." + kind, {"at": event.get("at")}, False
        if kind == "gap":
            return "record.continuity_gap", {"start": event.get("from"),
                                              "end": event.get("to")}, True
        if kind == "boundary":
            return "record.continuity_boundary", {}, False
        return None
