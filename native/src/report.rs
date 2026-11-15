use chrono::{DateTime, Datelike};
use serde_json::{Map, Value};
use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{self, BufRead, BufReader, Read};
use std::path::Path;

const KINDS: &[&str] = &[
    "start",
    "checkpoint",
    "recovery_started",
    "recovery_completed",
    "gap",
    "boundary",
    "diagnostic",
    "source",
    "recovery_snapshot",
    "buffer_status",
];
const REASONS: &[&str] = &[
    "resume_unavailable",
    "playlist_stalled",
    "playlist_unavailable",
    "broadcast_changed",
    "initialization_changed",
    "discontinuity",
    "position_unknown",
    "interval_unavailable",
    "segment_unavailable",
    "output_stalled",
    "broadcast_ended",
];
const HASH_COMPONENTS: &[&str] = &[
    "plugin/chzzk.py",
    "hls_continuity.py",
    "recording_buffer.py",
];
const EVENT_FIELDS: &[&str] = &[
    "at",
    "from",
    "to",
    "resume_from",
    "recovery_deadline",
    "observed_at",
    "lookup_at",
    "window_from",
    "window_to",
    "target",
];
const MAX_LINE_BYTES: usize = 8192 * 4 + 1;
type Key = (String, i64, String);

fn int_value(v: Option<&Value>) -> Option<i64> {
    v.filter(|v| v.is_number()).and_then(Value::as_i64)
}

fn integer_outside_i64(v: Option<&Value>) -> bool {
    v.and_then(Value::as_number).is_some_and(|n| {
        let text = n.to_string();
        !text.chars().any(|c| c == '.' || c == 'e' || c == 'E') && n.as_i64().is_none()
    })
}

fn contains_wide_integer(v: &Value) -> bool {
    match v {
        Value::Number(n) => integer_outside_i64(Some(&Value::Number(n.clone()))),
        Value::Array(a) => a.iter().any(contains_wide_integer),
        Value::Object(o) => o.values().any(contains_wide_integer),
        _ => false,
    }
}

fn contains_uncertain_number(v: &Value) -> bool {
    match v {
        Value::Number(n) => {
            let text = n.to_string();
            text == "-0"
                || (text.contains('.') || text.contains('e') || text.contains('E'))
                    && n.as_f64().is_none_or(|value| !value.is_finite())
        }
        Value::Array(a) => a.iter().any(contains_uncertain_number),
        Value::Object(o) => o.values().any(contains_uncertain_number),
        _ => false,
    }
}

fn has_uncertain_timestamp(row: &Map<String, Value>) -> bool {
    EVENT_FIELDS
        .iter()
        .chain(["observed_at"].iter())
        .any(|field| {
            row.get(*field)
                .and_then(Value::as_str)
                .is_some_and(|s| s.chars().count() <= 40 && timestamp_micros(s).is_none())
        })
}

fn valid_time(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => true,
        Some(Value::String(s)) if s.chars().count() <= 40 => timestamp_micros(s).is_some(),
        _ => false,
    }
}

fn timestamp_micros(s: &str) -> Option<i64> {
    if s.ends_with('z') {
        return None;
    }
    let dt = DateTime::parse_from_rfc3339(s).ok()?;
    if !(1..=9999).contains(&dt.year()) || dt.timestamp_subsec_nanos() >= 1_000_000_000 {
        return None;
    }
    dt.timestamp()
        .checked_mul(1_000_000)?
        .checked_add(i64::from(dt.timestamp_subsec_micros()))
}

fn time_micros(v: &Value) -> Option<i64> {
    timestamp_micros(v.as_str()?)
}

fn finite_number(v: Option<&Value>, min: f64, max: f64) -> bool {
    v.and_then(Value::as_f64)
        .is_some_and(|n| n.is_finite() && min <= n && n <= max)
}

fn is_py_int(v: Option<&Value>) -> bool {
    v.is_some_and(Value::is_number) && v.and_then(Value::as_i64).is_some()
}

fn is_version_one(o: &Map<String, Value>) -> bool {
    is_py_int(o.get("version")) && int_value(o.get("version")) == Some(1)
}

fn parse_event(o: &Map<String, Value>) -> bool {
    if !is_version_one(o)
        || !o
            .get("kind")
            .and_then(Value::as_str)
            .is_some_and(|s| KINDS.contains(&s))
        || !is_py_int(o.get("live_id"))
        || !o
            .get("rendition")
            .and_then(Value::as_str)
            .is_some_and(|s| s.chars().count() <= 32)
        || EVENT_FIELDS.iter().any(|k| !valid_time(o.get(*k)))
    {
        return false;
    }
    let kind = o["kind"].as_str().unwrap();
    if ["gap", "boundary"].contains(&kind)
        && !o
            .get("reason")
            .and_then(Value::as_str)
            .is_some_and(|s| REASONS.contains(&s))
    {
        return false;
    }
    if o.get("after_gap").is_some_and(|v| !v.is_boolean()) {
        return false;
    }
    match kind {
        "source" => {
            let vals = ["cdn", "mode", "state"].map(|k| o.get(k).and_then(Value::as_str));
            if !vals.iter().all(Option::is_some)
                || !["korean", "akamai", "unknown"].contains(&vals[0].unwrap())
                || !["hls", "llhls"].contains(&vals[1].unwrap())
                || !["selected", "ready", "absent", "unavailable"].contains(&vals[2].unwrap())
                || o.get("independent_cdn").is_some_and(|v| !v.is_boolean())
            {
                return false;
            }
        }
        "buffer_status" if o.get("state").and_then(Value::as_str) != Some("unavailable") => {
            return false;
        }
        "recovery_snapshot" => {
            let fields = ["cdn", "mode", "role", "result", "lookup_result"];
            if fields
                .iter()
                .any(|k| o.get(*k).and_then(Value::as_str).is_none())
                || !["korean", "akamai", "unknown"].contains(&o["cdn"].as_str().unwrap())
                || !["hls", "llhls"].contains(&o["mode"].as_str().unwrap())
                || !["current", "history"].contains(&o["role"].as_str().unwrap())
                || ![
                    "started",
                    "waiting",
                    "completed",
                    "boundary",
                    "buffer_full",
                    "buffer_skipped",
                ]
                .contains(&o["result"].as_str().unwrap())
                || ![
                    "available",
                    "unavailable",
                    "http",
                    "network",
                    "timeout",
                    "truncated",
                    "invalid_media",
                    "initialization",
                    "dns",
                    "tls",
                    "connect",
                    "parse",
                ]
                .contains(&o["lookup_result"].as_str().unwrap())
                || o.get("observed_at").is_none_or(Value::is_null)
                || !finite_number(o.get("elapsed_ms"), 0.0, 86_400_000.0)
                || !is_bounded_int(o.get("buffered_count"), 0, 2048)
                || !is_bounded_int(o.get("buffered_bytes"), 0, 268_435_456)
                || o.get("buffer_reason").is_some_and(|v| {
                    !v.as_str().is_some_and(|s| {
                        ["already_output", "time_limit", "byte_limit", "count_limit"].contains(&s)
                    })
                })
            {
                return false;
            }
            let (a, b) = (o.get("window_from"), o.get("window_to"));
            if a.is_none_or(Value::is_null) != b.is_none_or(Value::is_null) {
                return false;
            }
            if let (Some(a), Some(b)) = (a.filter(|x| !x.is_null()), b.filter(|x| !x.is_null())) {
                if time_micros(b)
                    .zip(time_micros(a))
                    .is_none_or(|(end, start)| end <= start)
                {
                    return false;
                }
            }
        }
        "diagnostic" => {
            let (stage, role, category) = (
                o.get("stage").and_then(Value::as_str),
                o.get("role").and_then(Value::as_str),
                o.get("category").and_then(Value::as_str),
            );
            if !stage.is_some_and(|s| ["manifest", "api", "initialization", "media"].contains(&s))
                || !role
                    .is_some_and(|s| ["current", "history", "primary", "alternate"].contains(&s))
                || !category.is_some_and(|s| {
                    [
                        "http",
                        "network",
                        "timeout",
                        "truncated",
                        "invalid_media",
                        "initialization",
                        "unavailable",
                        "dns",
                        "tls",
                        "connect",
                        "parse",
                    ]
                    .contains(&s)
                })
                || o.get("status")
                    .filter(|v| !v.is_null())
                    .is_some_and(|v| !is_bounded_int(Some(v), 100, 599))
                || o.get("sequence")
                    .filter(|v| !v.is_null())
                    .is_some_and(|v| !is_bounded_int(Some(v), 0, i64::MAX))
            {
                return false;
            }
        }
        "start" => {
            if !is_py_int(o.get("requested_seconds"))
                || ![Some(0), Some(3600)].contains(&int_value(o.get("requested_seconds")))
                || !finite_number(o.get("available_seconds"), 0.0, f64::MAX)
                || o.get("time_machine_active")
                    .is_some_and(|v| !v.is_null() && !v.is_boolean())
            {
                return false;
            }
        }
        "checkpoint" => {
            let (a, b) = (o.get("from"), o.get("to"));
            if a.is_none()
                || b.is_none()
                || a.unwrap().is_null() != b.unwrap().is_null()
                || (!a.unwrap().is_null()
                    && time_micros(b.unwrap())
                        .zip(time_micros(a.unwrap()))
                        .is_none_or(|(end, start)| end <= start))
            {
                return false;
            }
        }
        _ => {}
    }
    true
}

fn is_bounded_int(v: Option<&Value>, min: i64, max: i64) -> bool {
    is_py_int(v) && int_value(v).is_some_and(|n| (min..=max).contains(&n))
}

fn py_json_length(value: &Value) -> Option<usize> {
    let compact = serde_json::to_string(value).ok()?;
    let mut len = 0usize;
    let (mut in_string, mut escaped) = (false, false);
    for ch in compact.chars() {
        if in_string {
            if !escaped && ch == '"' {
                in_string = false;
            }
            if !escaped && ch == '\u{7f}' {
                len += 6;
            } else if !escaped && !ch.is_ascii() {
                len += if ch as u32 <= 0xffff { 6 } else { 12 };
            } else {
                len += ch.len_utf8();
            }
            if escaped {
                escaped = false;
            } else if ch == '\\' {
                escaped = true;
            }
        } else {
            if ch == '"' {
                in_string = true;
            }
            if ch == ',' || ch == ':' {
                len += 1;
            } // Python's json.dumps uses a space after separators.
            len += ch.len_utf8();
        }
    }
    Some(len)
}

fn event_json_length_is_accepted(row: &Value) -> Option<bool> {
    let n = py_json_length(row)?.checked_add("CHZZK_REKODA_EVENT ".len())?;
    // Float spellings differ between Python and serde_json; defer near the cap.
    let floats = float_count(row).min(512) as isize;
    let float_margin = 32 * (floats + 1);
    if floats > 0 && (n as isize - 4096).abs() <= float_margin {
        return None;
    }
    Some(n <= 4096)
}

fn float_count(v: &Value) -> usize {
    match v {
        Value::Number(n) => usize::from(n.is_f64()),
        Value::Array(a) => a.iter().map(float_count).sum(),
        Value::Object(o) => o.values().map(float_count).sum(),
        _ => 0,
    }
}

fn add_gap(
    intervals: &mut HashMap<Key, Vec<(f64, f64)>>,
    order: &mut Vec<Key>,
    key: &Key,
    a: i64,
    b: i64,
) {
    if b - a <= 20_000 {
        return;
    }
    if !intervals.contains_key(key) {
        order.push(key.clone());
    }
    intervals
        .entry(key.clone())
        .or_default()
        .push((python_timestamp(a), python_timestamp(b)));
}

fn python_timestamp(micros: i64) -> f64 {
    micros.div_euclid(1_000_000) as f64 + micros.rem_euclid(1_000_000) as f64 / 1_000_000.0
}

fn record_error(errors: &mut u64) {
    *errors += 1;
}

/// Summarize a continuity NDJSON file while keeping memory bounded by its output state.
/// Returns `None` when the input uses syntax or timestamp forms whose Python behavior is uncertain.
pub fn summarize_file(path: &Path) -> io::Result<Option<Value>> {
    let file = File::open(path)?;
    summarize_reader(BufReader::new(file))
}

fn summarize_reader<R: BufRead>(mut reader: R) -> io::Result<Option<Value>> {
    let mut intervals: HashMap<Key, Vec<(f64, f64)>> = HashMap::new();
    let mut gap_order = Vec::new();
    let mut ends: HashMap<Key, i64> = HashMap::new();
    let mut pending = HashSet::new();
    let mut undated = HashSet::new();
    let (mut checkpoints, mut duplicates, mut errors) = (0u64, 0u64, 0u64);
    let (mut started, mut finished) = (false, false);
    let mut bytes = Vec::new();
    loop {
        bytes.clear();
        let read = (&mut reader)
            .take(MAX_LINE_BYTES as u64)
            .read_until(b'\n', &mut bytes)?;
        if read == 0 {
            break;
        }
        if read == MAX_LINE_BYTES && bytes.last() != Some(&b'\n') {
            return Ok(None);
        }
        let line = match std::str::from_utf8(&bytes) {
            Ok(s) => s,
            Err(_) => return Ok(None),
        };
        let content = line.strip_suffix("\r\n").unwrap_or(line);
        if content.contains('\r') {
            return Ok(None);
        }
        let normalized_len = line.chars().count() - usize::from(line.ends_with("\r\n"));
        if normalized_len > 8192 {
            record_error(&mut errors);
            continue;
        }
        let row: Value = match serde_json::from_str(line) {
            Ok(v) => v,
            Err(_) => return Ok(None),
        };
        let Some(o) = row.as_object() else {
            record_error(&mut errors);
            continue;
        };
        if contains_wide_integer(&row) || contains_uncertain_number(&row) {
            return Ok(None);
        }
        if !is_version_one(o) {
            record_error(&mut errors);
            continue;
        }
        let Some(kind) = o.get("kind").and_then(Value::as_str) else {
            record_error(&mut errors);
            continue;
        };
        if kind == "report_started" {
            let components = o
                .get("components_sha256")
                .cloned()
                .unwrap_or_else(|| Value::Object(Map::new()));
            let valid = components.as_object().is_some_and(|m| {
                m.iter().all(|(name, value)| {
                    HASH_COMPONENTS.contains(&name.as_str())
                        && value.as_str().is_some_and(|s| {
                            s.len() == 64
                                && s.bytes()
                                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
                        })
                })
            });
            if !valid {
                record_error(&mut errors);
                continue;
            }
            if started || finished {
                record_error(&mut errors);
            }
            started = true;
            continue;
        }
        if kind == "report_finished" {
            if !started || finished || o.get("complete") != Some(&Value::Bool(true)) {
                record_error(&mut errors);
            }
            finished = true;
            continue;
        }
        if !started || finished {
            record_error(&mut errors);
        }
        if kind == "report_error" {
            record_error(&mut errors);
            continue;
        }
        let Some(channel) = o
            .get("channel_id")
            .and_then(Value::as_str)
            .filter(|s| s.chars().count() <= 128)
        else {
            record_error(&mut errors);
            continue;
        };
        if has_uncertain_timestamp(o) {
            return Ok(None);
        }
        if kind == "output_error" {
            record_error(&mut errors);
            continue;
        }
        if integer_outside_i64(o.get("live_id")) {
            return Ok(None);
        }
        match event_json_length_is_accepted(&row) {
            Some(true) => {}
            Some(false) => {
                record_error(&mut errors);
                continue;
            }
            None => return Ok(None),
        }
        if !parse_event(o) {
            record_error(&mut errors);
            continue;
        }
        let (Some(live_id), Some(rendition)) = (
            int_value(o.get("live_id")),
            o.get("rendition").and_then(Value::as_str),
        ) else {
            return Ok(None);
        };
        let key = (channel.to_owned(), live_id, rendition.to_owned());
        match kind {
            "gap" => {
                if o.get("from").is_none_or(Value::is_null)
                    || o.get("to").is_none_or(Value::is_null)
                {
                    pending.insert(key);
                } else {
                    let (Some(a), Some(b)) = (time_micros(&o["from"]), time_micros(&o["to"]))
                    else {
                        return Ok(None);
                    };
                    add_gap(&mut intervals, &mut gap_order, &key, a, b);
                }
            }
            "boundary" => match o["reason"].as_str().unwrap() {
                "broadcast_ended" | "broadcast_changed" => {
                    pending.remove(&key);
                }
                "initialization_changed" | "discontinuity" => {
                    if let Some(resume) = o
                        .get("resume_from")
                        .filter(|v| !v.is_null())
                        .and_then(time_micros)
                    {
                        if ends.get(&key).is_some_and(|end| resume < *end) {
                            ends.remove(&key);
                        }
                    }
                }
                _ => {
                    pending.insert(key);
                }
            },
            "checkpoint" => {
                checkpoints += 1;
                if o["from"].is_null() {
                    undated.insert(key);
                    continue;
                }
                let (Some(first), Some(last)) = (time_micros(&o["from"]), time_micros(&o["to"]))
                else {
                    return Ok(None);
                };
                if let Some(previous) = ends.get(&key).copied() {
                    let delta = first - previous;
                    if delta < -20_000 {
                        duplicates += 1;
                    } else if delta > 20_000 {
                        add_gap(&mut intervals, &mut gap_order, &key, previous, first);
                    }
                }
                ends.insert(key.clone(), last);
                pending.remove(&key);
            }
            _ => {}
        }
    }
    if !started || !finished || checkpoints == 0 {
        record_error(&mut errors);
    }
    let mut gaps = Vec::new();
    let mut total = 0.0f64;
    for key in gap_order {
        let mut ranges = intervals.remove(&key).unwrap_or_default();
        ranges.sort_by(|a, b| a.0.total_cmp(&b.0));
        let mut combined: Vec<(f64, f64)> = Vec::new();
        for (first, last) in ranges {
            if let Some(prev) = combined.last_mut().filter(|p| first <= p.1 + 0.02) {
                prev.1 = prev.1.max(last);
            } else {
                combined.push((first, last));
            }
        }
        for (start, end) in combined {
            total += end - start;
            gaps.push(serde_json::json!({"channel_id": key.0, "live_id": key.1, "rendition": key.2, "start": start, "end": end}));
        }
    }
    let unresolved = pending.union(&undated).count();
    Ok(Some(serde_json::json!({
        "version": 1,
        "passed": gaps.is_empty() && unresolved == 0 && errors == 0 && duplicates == 0,
        "gap_count": gaps.len(),
        "gap_seconds": (total * 1_000_000.0).round_ties_even() / 1_000_000.0,
        "unresolved_count": unresolved,
        "checkpoint_count": checkpoints,
        "duplicate_count": duplicates,
        "error_count": errors,
        "gaps": gaps
    })))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    fn summarize(text: &str) -> Option<Value> {
        summarize_reader(Cursor::new(text)).unwrap()
    }
    fn event(kind: &str, rest: &str) -> String {
        format!(
            "{{\"version\":1,\"kind\":\"{kind}\",\"channel_id\":\"channel\",\"live_id\":1,\"rendition\":\"1080p\"{rest}}}\n"
        )
    }
    fn report(rows: &[String]) -> String {
        let mut s = String::from("{\"version\":1,\"kind\":\"report_started\"}\n");
        s.push_str(&rows.concat());
        s.push_str("{\"version\":1,\"kind\":\"report_finished\",\"complete\":true}\n");
        s
    }
    fn ck(a: &str, b: &str) -> String {
        event("checkpoint", &format!(",\"from\":\"{a}\",\"to\":\"{b}\""))
    }

    #[test]
    fn normal_checkpoint_gap_and_duplicate_match_protocol() {
        let rows = [
            ck(
                "2026-01-01T00:00:00.000000+00:00",
                "2026-01-01T00:00:01+00:00",
            ),
            ck(
                "2026-01-01T00:00:01.020001+00:00",
                "2026-01-01T00:00:02+00:00",
            ),
            ck(
                "2026-01-01T00:00:01.900000+00:00",
                "2026-01-01T00:00:03+00:00",
            ),
        ];
        let got = summarize(&report(&rows)).unwrap();
        assert_eq!(got["checkpoint_count"], 3);
        assert_eq!(got["gap_count"], 1);
        assert_eq!(got["duplicate_count"], 1);
    }

    #[test]
    fn merges_explicit_and_derived_gaps_and_tracks_unresolved() {
        let rows = [
            ck("2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"),
            event(
                "gap",
                ",\"from\":\"2026-01-01T00:00:01.010000Z\",\"to\":\"2026-01-01T00:00:02Z\",\"reason\":\"output_stalled\"",
            ),
            event(
                "gap",
                ",\"from\":null,\"to\":null,\"reason\":\"output_stalled\"",
            ),
        ];
        let got = summarize(&report(&rows)).unwrap();
        assert_eq!(got["gap_count"], 1);
        assert_eq!(got["unresolved_count"], 1);
    }

    #[test]
    fn invalid_json_types_count_errors_and_unsupported_values_fallback() {
        let bad = event(
            "checkpoint",
            ",\"from\":\"2026-01-01T00:00:00Z\",\"to\":\"2026-01-01T00:00:01Z\",\"after_gap\":1",
        );
        let got = summarize(&report(&[
            bad,
            ck("2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"),
        ]))
        .unwrap();
        assert_eq!(got["error_count"], 1);
        assert!(
            summarize(&report(&[event(
                "checkpoint",
                ",\"from\":null,\"to\":null,\"live_id\":9223372036854775808"
            )]))
            .is_none()
        );
        assert!(
            summarize(&report(&[ck(
                "2026-W01-1T00:00:00+00:00",
                "2026-01-01T00:00:01Z"
            )]))
            .is_none()
        );
    }

    #[test]
    fn report_error_and_incomplete_footer_increment_errors() {
        let error_row = "{\"version\":1,\"kind\":\"report_error\"}\n".to_owned();
        let got = summarize(&report(&[error_row])).unwrap();
        assert_eq!(got["error_count"], 2); // event error plus missing checkpoint
        let incomplete = "{\"version\":1,\"kind\":\"report_started\"}\n{\"version\":1,\"kind\":\"report_finished\",\"complete\":false}\n";
        assert_eq!(summarize(incomplete).unwrap()["error_count"], 2);
    }

    #[test]
    fn exact_twenty_millisecond_edges_and_unicode_limits() {
        let rows = [
            ck("2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"),
            ck("2026-01-01T00:00:01.020000Z", "2026-01-01T00:00:02Z"),
        ];
        assert_eq!(summarize(&report(&rows)).unwrap()["gap_count"], 0);
        let long = event(
            "checkpoint",
            &format!(
                ",\"from\":\"2026-01-01T00:00:00Z\",\"to\":\"2026-01-01T00:00:01Z\",\"extra\":\"{}\"",
                "한".repeat(2050)
            ),
        );
        assert_eq!(summarize(&report(&[long])).unwrap()["error_count"], 2);
        assert!(
            summarize(
                &report(&[ck("2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z")])
                    .replace("\n", "\r\n")
            )
            .is_some()
        );
    }

    #[test]
    fn streaming_reader_rejects_truncation_and_empty_report_summarizes() {
        assert!(summarize("{\"version\":1,\"kind\":\"report_started\"}\n{").is_none());
        assert_eq!(summarize("").unwrap()["error_count"], 1);
        assert!(summarize(&" ".repeat(100_000)).is_none());
    }

    #[test]
    fn leap_seconds_are_left_for_python_datetime() {
        assert!(timestamp_micros("2016-12-31T23:59:60Z").is_none());
    }
}
