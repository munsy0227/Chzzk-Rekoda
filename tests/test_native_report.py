import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

import native_backend
from continuity_report import summarize, summarize_file


class NativeReportDifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = native_backend.native_executable()
        if cls.binary is None:
            raise unittest.SkipTest("native release executable is not available")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.report = Path(self.temp.name) / "report.ndjson"

    @staticmethod
    def row(kind, **fields):
        return {"version": 1, "kind": kind, "channel_id": "a" * 32,
                "live_id": 1234, "rendition": "1080p", **fields}

    @staticmethod
    def report_rows(events, *, finish=True):
        rows = [{"version": 1, "kind": "report_started"}, *events]
        if finish:
            rows.append({"version": 1, "kind": "report_finished", "complete": True})
        return rows

    def run_native(self, rows=None, *, raw=None):
        if raw is None:
            raw = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()
        self.report.write_bytes(raw)
        result = subprocess.run(
            [str(self.binary), "report", str(self.report)],
            check=True, capture_output=True, timeout=10,
        )
        return json.loads(result.stdout)

    def assert_parity(self, rows):
        lines = [json.dumps(row, ensure_ascii=False) + "\n" for row in rows]
        expected = summarize(lines)
        reply = self.run_native(rows)
        if reply.get("ok") is True:
            self.assertEqual(reply["summary"], expected)
        else:
            self.assertEqual(reply, {"version": 1, "ok": False, "error": "unsupported"})
            self.assertEqual(summarize(lines), expected)
        return reply

    def test_seeded_event_mix_matches_python(self):
        rng = random.Random(823_611_715)
        kinds = ("start", "checkpoint", "recovery_started", "recovery_completed",
                 "gap", "boundary", "diagnostic", "source", "recovery_snapshot",
                 "buffer_status")
        events = []
        base = 1_800_000_000
        for index in range(100):
            kind = kinds[index % len(kinds)]
            sec = base + index * 3
            at = f"2027-01-15T{(sec // 3600) % 24:02d}:{(sec // 60) % 60:02d}:{sec % 60:02d}.123456Z"
            fields = {"live_id": 1234 + rng.randrange(3),
                      "channel_id": ("a" if rng.randrange(2) else "b") * 32,
                      "rendition": rng.choice(("720p", "1080p", "source"))}
            if kind == "start":
                fields.update(at=at, requested_seconds=rng.choice((0, 3600)),
                              available_seconds=rng.random() * 3600,
                              time_machine_active=rng.choice((None, True, False)))
            elif kind == "checkpoint":
                start = sec - rng.randrange(1, 100) / 1000
                fields.update(**{"from": f"2027-01-15T{(int(start) // 3600) % 24:02d}:{(int(start) // 60) % 60:02d}:{int(start) % 60:02d}.{int((start % 1) * 1_000_000):06d}Z",
                                 "to": f"2027-01-15T{(sec + 1) // 3600 % 24:02d}:{(sec + 1) // 60 % 60:02d}:{(sec + 1) % 60:02d}Z"})
            elif kind == "recovery_started" or kind == "recovery_completed":
                fields["at"] = at
            elif kind == "gap":
                fields.update(**{"from": at, "to": f"2027-01-15T{(sec + 1) // 3600 % 24:02d}:{(sec + 1) // 60 % 60:02d}:{(sec + 1) % 60:02d}Z",
                                 "reason": "output_stalled"})
            elif kind == "boundary":
                fields.update(reason="broadcast_ended", resume_from=at,
                              after_gap=rng.choice((True, False)))
            elif kind == "diagnostic":
                fields.update(stage="media", role="current", category="http",
                              status=503, sequence=index, at=at)
            elif kind == "source":
                fields.update(cdn="korean", mode="hls", state="ready",
                              independent_cdn=rng.choice((True, False)))
            elif kind == "recovery_snapshot":
                fields.update(observed_at=at, lookup_at=at, cdn="akamai", mode="llhls",
                              role="history", result="completed", lookup_result="available",
                              elapsed_ms=rng.random() * 1000,
                              window_from=at, window_to=f"2027-01-15T{(sec + 1) // 3600 % 24:02d}:{(sec + 1) // 60 % 60:02d}:{(sec + 1) % 60:02d}Z",
                              buffered_count=rng.randrange(2049), buffered_bytes=rng.randrange(268_435_457))
            else:
                fields["state"] = "unavailable"
            events.append(self.row(kind, **fields))
        # Ensure the generated report contains at least one valid checkpoint.
        events.append(self.row("checkpoint", **{"from": "2027-01-15T00:00:00Z",
                                                  "to": "2027-01-15T00:00:01Z"}))
        self.assertTrue(self.assert_parity(self.report_rows(events))["ok"])

    def test_threshold_other_channels_phase_errors_and_missing_footer(self):
        events = [
            self.row("checkpoint", **{"from": "2026-01-01T00:00:00Z",
                                       "to": "2026-01-01T00:00:01Z"}),
            self.row("checkpoint", **{"from": "2026-01-01T00:00:01.020000Z",
                                       "to": "2026-01-01T00:00:02Z"}),
            self.row("checkpoint", channel_id="b" * 32,
                     **{"from": "2026-01-01T00:00:00Z", "to": "2026-01-01T00:00:01Z"}),
            self.row("checkpoint", **{"from": "2026-01-01T00:00:02.020001Z",
                                       "to": "2026-01-01T00:00:03Z"}),
            self.row("checkpoint", **{"from": "2026-01-01T00:00:02.999999Z",
                                       "to": "2026-01-01T00:00:04Z"}),
            {"version": 1, "kind": "report_error"},
            self.row("output_error", category="forced_stop",
                     observed_at="2026-01-01T00:00:00Z"),
        ]
        self.assert_parity(self.report_rows(events))
        self.assert_parity(self.report_rows(events, finish=False))

    def test_python_iso_variants_and_leap_second_match_or_fall_back(self):
        values = (
            ("2026-01-01 00:00:00+00:00", False),        # space separator
            ("2026-W01-4T00:00:00+00:00", True),         # ISO week date
            ("20260101T000000+0000", True),              # compact spelling
            ("2026-01-01T00:00:00,123456+00:00", True),  # comma fraction
            ("2026-01-01T00:00:00+00:00:30", True),      # offset seconds
            ("2016-12-31T23:59:60Z", True),              # chrono leap second, Python rejects
            ("2026-01-01T00:00:00z", True),              # chrono accepts lowercase zone
        )
        for stamp, must_fallback in values:
            with self.subTest(stamp=stamp):
                event = self.row("checkpoint", **{"from": stamp,
                                                   "to": "2026-01-01T00:00:01Z"})
                reply = self.assert_parity(self.report_rows([event]))
                if must_fallback:
                    self.assertFalse(reply["ok"])

    def test_fractional_precision_and_epoch_float_ranges(self):
        for year, seconds in (("0001", "00:00:00"), ("2260", "00:00:00"),
                              ("9999", "00:00:00")):
            with self.subTest(year=year):
                start = f"{year}-01-01T{seconds}.123456789Z"
                end = f"{year}-01-01T00:00:01.123456789Z"
                events = [self.row("checkpoint", **{"from": start, "to": end})]
                if year == "2260":
                    events.append(self.row("checkpoint", **{
                        "from": "2260-01-01T00:00:01.143457Z",
                        "to": "2260-01-01T00:00:02Z",
                    }))
                rows = self.report_rows(events)
                self.assert_parity(rows)

    def test_wide_integer_and_oversized_line_use_python_file_fallback(self):
        header = json.dumps({"version": 1, "kind": "report_started"}) + "\n"
        wide = self.row("checkpoint", live_id=2**64,
                        **{"from": None, "to": None})
        ordinary = self.row("checkpoint", **{"from": "2026-01-01T00:00:00Z",
                                             "to": "2026-01-01T00:00:01Z"})
        footer = json.dumps({"version": 1, "kind": "report_finished", "complete": True}) + "\n"
        raw = (header + json.dumps(wide) + "\n" + json.dumps(ordinary) + "\n"
               + " " * (256 * 1024) + "\n" + footer).encode()
        self.report.write_bytes(raw)
        expected = summarize(raw.decode("utf-8").splitlines(keepends=True))
        reply = self.run_native(raw=raw)
        self.assertEqual(reply, {"version": 1, "ok": False, "error": "unsupported"})
        self.assertEqual(summarize_file(self.report), expected)

    def test_unicode_limits_and_bad_rows_match_or_fall_back(self):
        valid = self.row("checkpoint", rendition="한" * 32,
                         **{"from": "2026-01-01T00:00:00Z", "to": "2026-01-01T00:00:01Z"})
        self.assert_parity(self.report_rows([valid]))
        oversized = self.row("checkpoint", **{"from": "2026-01-01T00:00:00Z",
                                               "to": "2026-01-01T00:00:01Z",
                                               "extra": "한" * 2050})
        self.assert_parity(self.report_rows([oversized]))
        self.assert_parity(self.report_rows([self.row("checkpoint", **{"from": None, "to": None,
                                                                          "after_gap": 1})]))
        self.assert_parity(self.report_rows([self.row("checkpoint", **{"from": None, "to": None,
                                                                          "available_seconds": float("inf")})]))
        self.assert_parity(self.report_rows([]))

    def test_event_json_size_boundary_matches_python(self):
        from recording_continuity import EVENT_PREFIX

        for text in ("x", "\x7f", "한", "😀", '"\\\n'):
            event = self.row("checkpoint", **{"from": None, "to": None,
                                               "extra": text, "padding": ""})
            size = len(EVENT_PREFIX + json.dumps(event))
            for offset in (-1, 0, 1):
                with self.subTest(text=repr(text), offset=offset):
                    event["padding"] = "x" * (4096 - size + offset)
                    reply = self.assert_parity(self.report_rows([event]))
                    self.assertTrue(reply["ok"])
                    self.assertEqual(reply["summary"]["checkpoint_count"], int(offset <= 0))

    def test_missing_snapshot_window_matches_python(self):
        event = self.row("recovery_snapshot", observed_at="2026-01-01T00:00:00Z",
                         cdn="korean", mode="hls", role="current", result="completed",
                         lookup_result="available", elapsed_ms=1, buffered_count=0,
                         buffered_bytes=0, window_to="2026-01-01T00:00:01Z")
        checkpoint = self.row("checkpoint", **{"from": None, "to": None})
        for missing in ("window_from", "window_to"):
            with self.subTest(missing=missing):
                event.pop(missing, None)
                event["window_to" if missing == "window_from" else "window_from"] = (
                    "2026-01-01T00:00:01Z"
                )
                self.assertTrue(self.assert_parity(self.report_rows([checkpoint, event]))["ok"])

    def test_uncertain_number_spellings_use_python(self):
        rows = self.report_rows([self.row("checkpoint", **{"from": None, "to": None,
                                                          "extra": "PLACEHOLDER"})])
        text = "".join(json.dumps(row) + "\n" for row in rows)
        for number in ("-0", "1e999", "-1e999"):
            with self.subTest(number=number):
                reply = self.run_native(raw=text.replace('"PLACEHOLDER"', number).encode())
                self.assertFalse(reply["ok"])

    def test_universal_newline_file_behavior_matches_python(self):
        checkpoint = self.row("checkpoint", **{"from": "2026-01-01T00:00:00Z",
                                               "to": "2026-01-01T00:00:01Z"})
        header = {"version": 1, "kind": "report_started", "padding": ""}
        header["padding"] = "x" * (8191 - len(json.dumps(header)))
        rows = [header, checkpoint,
                {"version": 1, "kind": "report_finished", "complete": True}]
        for newline in ("\r\n", "\r"):
            with self.subTest(newline=repr(newline)):
                raw = (newline.join(json.dumps(row) for row in rows) + newline).encode()
                reply = self.run_native(raw=raw)
                with self.report.open(encoding="utf-8") as source:
                    expected = summarize(source)
                if newline == "\r\n":
                    self.assertTrue(reply["ok"])
                    self.assertEqual(reply["summary"], expected)
                else:
                    self.assertFalse(reply["ok"])
                self.assertTrue(expected["passed"])


if __name__ == "__main__":
    unittest.main()
