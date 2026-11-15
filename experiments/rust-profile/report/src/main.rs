use chrono::{DateTime, SecondsFormat};
use serde_json::{Value, json};
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::time::Instant;

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
const OUTPUT_ERRORS: &[&str] = &["corrupt_packet", "partial_input", "forced_stop"];
const HASH_COMPONENTS: &[&str] = &[
    "plugin/chzzk.py",
    "hls_continuity.py",
    "recording_buffer.py",
];

type Key = (String, i64, String);

fn is_int(v: Option<&Value>) -> bool {
    v.is_some_and(Value::is_i64) || v.is_some_and(Value::is_u64)
}

fn int_value(v: &Value) -> Option<i64> {
    v.as_i64()
        .or_else(|| v.as_u64().and_then(|n| i64::try_from(n).ok()))
}

fn valid_time(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => true,
        Some(Value::String(s)) if s.chars().count() <= 40 => {
            DateTime::parse_from_rfc3339(s).is_ok()
        }
        _ => false,
    }
}

fn time_micros(v: &Value) -> Result<i64, ()> {
    let s = v.as_str().ok_or(())?;
    DateTime::parse_from_rfc3339(s)
        .map(|t| t.timestamp_micros())
        .map_err(|_| ())
}

fn finite_number(v: Option<&Value>, min: f64, max: f64) -> bool {
    v.and_then(Value::as_f64)
        .is_some_and(|n| n.is_finite() && min <= n && n <= max)
}

fn parse_event(v: &Value) -> bool {
    let Some(o) = v.as_object() else { return false };
    if !is_int(o.get("version")) || o.get("version").and_then(int_value) != Some(1) {
        return false;
    }
    let Some(kind) = o.get("kind").and_then(Value::as_str) else {
        return false;
    };
    if !KINDS.contains(&kind) || !is_int(o.get("live_id")) {
        return false;
    }
    let Some(rendition) = o.get("rendition").and_then(Value::as_str) else {
        return false;
    };
    if rendition.chars().count() > 32 {
        return false;
    }
    for field in [
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
    ] {
        if !valid_time(o.get(field)) {
            return false;
        }
    }
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
            if !["cdn", "mode", "state"]
                .iter()
                .all(|k| o.get(*k).and_then(Value::as_str).is_some())
            {
                return false;
            }
            if !["korean", "akamai", "unknown"].contains(&o["cdn"].as_str().unwrap())
                || !["hls", "llhls"].contains(&o["mode"].as_str().unwrap())
                || !["selected", "ready", "absent", "unavailable"]
                    .contains(&o["state"].as_str().unwrap())
            {
                return false;
            }
            if o.get("independent_cdn").is_some_and(|v| !v.is_boolean()) {
                return false;
            }
        }
        "buffer_status" if o.get("state").and_then(Value::as_str) != Some("unavailable") => {
            return false;
        }
        "recovery_snapshot" => {
            for k in ["cdn", "mode", "role", "result", "lookup_result"] {
                if !o.get(k).and_then(Value::as_str).is_some() {
                    return false;
                }
            }
            if !["korean", "akamai", "unknown"].contains(&o["cdn"].as_str().unwrap())
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
                || !o.get("buffered_count").is_some_and(|v| {
                    is_int(Some(v)) && int_value(v).is_some_and(|n| (0..=2048).contains(&n))
                })
                || !o.get("buffered_bytes").is_some_and(|v| {
                    is_int(Some(v)) && int_value(v).is_some_and(|n| (0..=268_435_456).contains(&n))
                })
            {
                return false;
            }
            if o.get("buffer_reason").is_some_and(|v| {
                !v.as_str().is_some_and(|s| {
                    ["already_output", "time_limit", "byte_limit", "count_limit"].contains(&s)
                })
            }) {
                return false;
            }
            let (a, b) = (o.get("window_from"), o.get("window_to"));
            if a.is_some_and(Value::is_null) != b.is_some_and(Value::is_null) {
                return false;
            }
            if let (Some(a), Some(b)) = (a.filter(|x| !x.is_null()), b.filter(|x| !x.is_null())) {
                if time_micros(b)
                    .ok()
                    .zip(time_micros(a).ok())
                    .is_none_or(|(end, start)| end <= start)
                {
                    return false;
                }
            }
        }
        "diagnostic" => {
            for k in ["stage", "role", "category"] {
                if !o.get(k).and_then(Value::as_str).is_some() {
                    return false;
                }
            }
            if !["manifest", "api", "initialization", "media"]
                .contains(&o["stage"].as_str().unwrap())
                || !["current", "history", "primary", "alternate"]
                    .contains(&o["role"].as_str().unwrap())
                || ![
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
                .contains(&o["category"].as_str().unwrap())
            {
                return false;
            }
            if let Some(status) = o.get("status").filter(|v| !v.is_null()) {
                if !is_int(Some(status))
                    || !int_value(status).is_some_and(|n| (100..=599).contains(&n))
                {
                    return false;
                }
            }
            if let Some(seq) = o.get("sequence").filter(|v| !v.is_null()) {
                if !is_int(Some(seq)) || !int_value(seq).is_some_and(|n| n >= 0) {
                    return false;
                }
            }
        }
        "start" => {
            if !is_int(o.get("requested_seconds"))
                || ![Some(0), Some(3600)].contains(&o.get("requested_seconds").and_then(int_value))
                || !finite_number(o.get("available_seconds"), 0.0, f64::MAX)
            {
                return false;
            }
            if o.get("time_machine_active")
                .is_some_and(|v| !v.is_null() && !v.is_boolean())
            {
                return false;
            }
        }
        "checkpoint" => {
            let (a, b) = (o.get("from"), o.get("to"));
            if a.is_none() || b.is_none() || a.unwrap().is_null() != b.unwrap().is_null() {
                return false;
            }
            if !a.unwrap().is_null()
                && time_micros(b.unwrap())
                    .ok()
                    .zip(time_micros(a.unwrap()).ok())
                    .is_none_or(|(end, start)| end <= start)
            {
                return false;
            }
        }
        _ => {}
    }
    true
}

fn add_gap(
    intervals: &mut HashMap<Key, Vec<(f64, f64)>>,
    key: &Key,
    start: Option<&Value>,
    end: Option<&Value>,
) {
    let (Some(start), Some(end)) = (start.filter(|v| !v.is_null()), end.filter(|v| !v.is_null()))
    else {
        return;
    };
    let (Ok(a), Ok(b)) = (time_micros(start), time_micros(end)) else {
        return;
    };
    if b - a > 20_000 {
        intervals
            .entry(key.clone())
            .or_default()
            .push((a as f64 / 1e6, b as f64 / 1e6));
    }
}

fn summarize(input: &str) -> Value {
    let mut intervals: HashMap<Key, Vec<(f64, f64)>> = HashMap::new();
    let mut key_order: Vec<Key> = Vec::new();
    let mut ends: HashMap<Key, i64> = HashMap::new();
    let mut pending: HashSet<Key> = HashSet::new();
    let mut undated: HashSet<Key> = HashSet::new();
    let (mut checkpoints, mut duplicates, mut errors) = (0u64, 0u64, 0u64);
    let (mut started, mut finished) = (false, false);

    for line in input.split_inclusive('\n') {
        let result = (|| -> Result<(), ()> {
            if line.chars().count() > 8192 {
                return Err(());
            }
            let row: Value = serde_json::from_str(line).map_err(|_| ())?;
            let o = row.as_object().ok_or(())?;
            if !is_int(o.get("version")) || o.get("version").and_then(int_value) != Some(1) {
                return Err(());
            }
            let kind = o.get("kind").and_then(Value::as_str).ok_or(())?;
            if kind == "report_started" {
                let components = o
                    .get("components_sha256")
                    .cloned()
                    .unwrap_or_else(|| json!({}));
                let components = components.as_object().ok_or(())?;
                for (name, value) in components {
                    let hash = value.as_str().ok_or(())?;
                    if !HASH_COMPONENTS.contains(&name.as_str())
                        || hash.len() != 64
                        || !hash
                            .bytes()
                            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
                    {
                        return Err(());
                    }
                }
                if started || finished {
                    errors += 1;
                }
                started = true;
                return Ok(());
            }
            if kind == "report_finished" {
                if !started || finished || o.get("complete") != Some(&Value::Bool(true)) {
                    errors += 1;
                }
                finished = true;
                return Ok(());
            }
            if !started || finished {
                errors += 1;
            }
            if kind == "report_error" {
                errors += 1;
                return Ok(());
            }
            let channel = o
                .get("channel_id")
                .and_then(Value::as_str)
                .filter(|s| s.chars().count() <= 128)
                .ok_or(())?
                .to_string();
            if kind == "output_error" {
                if !o
                    .get("category")
                    .and_then(Value::as_str)
                    .is_some_and(|s| OUTPUT_ERRORS.contains(&s))
                    || o.get("observed_at").is_none_or(Value::is_null)
                    || !valid_time(o.get("observed_at"))
                {
                    return Err(());
                }
                errors += 1;
                return Ok(());
            }
            if !parse_event(&row) {
                return Err(());
            }
            let key = (
                channel,
                int_value(&o["live_id"]).ok_or(())?,
                o["rendition"].as_str().ok_or(())?.to_string(),
            );
            if !key_order.contains(&key) {
                key_order.push(key.clone());
            }
            match kind {
                "gap" => {
                    if o.get("from").is_none_or(Value::is_null)
                        || o.get("to").is_none_or(Value::is_null)
                    {
                        pending.insert(key);
                    } else {
                        add_gap(&mut intervals, &key, o.get("from"), o.get("to"));
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
                            .and_then(|v| time_micros(v).ok())
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
                        return Ok(());
                    }
                    let first = time_micros(&o["from"])?;
                    let last = time_micros(&o["to"])?;
                    if let Some(previous) = ends.get(&key).copied() {
                        let delta = first - previous;
                        if delta < -20_000 {
                            duplicates += 1;
                        } else if delta > 20_000 {
                            let a = json!(
                                DateTime::from_timestamp_micros(previous)
                                    .ok_or(())?
                                    .to_rfc3339_opts(SecondsFormat::AutoSi, true)
                            );
                            add_gap(&mut intervals, &key, Some(&a), Some(&o["from"]));
                        }
                    }
                    ends.insert(key.clone(), last);
                    pending.remove(&key);
                }
                _ => {}
            }
            Ok(())
        })();
        if result.is_err() {
            errors += 1;
        }
    }
    if !started || !finished || checkpoints == 0 {
        errors += 1;
    }
    let mut gaps = Vec::new();
    let mut total = 0.0f64;
    for key in key_order {
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
            gaps.push(json!({"channel_id": key.0, "live_id": key.1, "rendition": key.2, "start": start, "end": end}));
        }
    }
    let unresolved = pending.union(&undated).count();
    json!({
        "version": 1,
        "passed": gaps.is_empty() && unresolved == 0 && errors == 0 && duplicates == 0,
        "gap_count": gaps.len(),
        "gap_seconds": (total * 1_000_000.0).round_ties_even() / 1_000_000.0,
        "unresolved_count": unresolved,
        "checkpoint_count": checkpoints,
        "duplicate_count": duplicates,
        "error_count": errors,
        "gaps": gaps
    })
}

fn process_memory_kib() -> (Option<u64>, Option<u64>) {
    let Ok(status) = fs::read_to_string("/proc/self/status") else {
        return (None, None);
    };
    let mut hwm = None;
    let mut rss = None;
    for line in status.lines() {
        let Some((name, value)) = line.split_once(':') else {
            continue;
        };
        let Some(kib) = value.split_whitespace().next().and_then(|v| v.parse().ok()) else {
            continue;
        };
        match name {
            "VmHWM" => hwm = Some(kib),
            "VmRSS" => rss = Some(kib),
            _ => {}
        }
    }
    (hwm, rss)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("usage: continuity-report-rust INPUT.ndjson OUTPUT.json");
        std::process::exit(2);
    }
    let started = Instant::now();
    let input = fs::read_to_string(&args[1]).unwrap_or_default();
    let rows = input.split_inclusive('\n').count();
    let summary = summarize(&input);
    let algorithm_wall_ns = started.elapsed().as_nanos();
    let (process_self_vm_hwm_kib, process_self_vm_rss_kib) = process_memory_kib();
    if let Err(e) = fs::write(&args[2], serde_json::to_vec_pretty(&summary).unwrap()) {
        eprintln!("write summary: {e}");
        std::process::exit(2);
    }
    eprintln!(
        "{}",
        json!({
            "algorithm_wall_ns": algorithm_wall_ns,
            "input_bytes": input.len(),
            "input_rows": rows,
            "process_self_vm_hwm_kib": process_self_vm_hwm_kib,
            "process_self_vm_rss_kib": process_self_vm_rss_kib
        })
    );
}
