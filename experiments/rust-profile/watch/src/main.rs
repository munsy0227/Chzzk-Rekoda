use reqwest::Client;
use serde_json::Value;
use std::{
    collections::HashMap,
    env,
    io::{self, BufRead},
    sync::Arc,
    time::Instant,
};
use tokio::{
    sync::Semaphore,
    task::JoinSet,
    time::{Duration, sleep},
};

fn process_cpu_seconds() -> io::Result<f64> {
    let mut time = libc::timespec {
        tv_sec: 0,
        tv_nsec: 0,
    };
    let result = unsafe { libc::clock_gettime(libc::CLOCK_PROCESS_CPUTIME_ID, &mut time) };
    if result != 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(time.tv_sec as f64 + time.tv_nsec as f64 / 1_000_000_000.0)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    let (base, count, rounds, interval) = (
        &args[1],
        args[2].parse::<usize>()?,
        args[3].parse::<usize>()?,
        args[4].parse::<f64>()?,
    );
    let client = Client::builder()
        .no_proxy()
        .timeout(Duration::from_millis(100))
        .build()?;
    let limit = Arc::new(Semaphore::new(16));
    eprintln!("READY");
    let mut go = String::new();
    io::stdin().lock().read_line(&mut go)?;
    let cpu_started = process_cpu_seconds()?;
    let started = Instant::now();
    let mut requests = 0u64;
    let mut outcomes: HashMap<String, u64> = HashMap::new();
    let mut live_ids: HashMap<usize, i64> = HashMap::new();
    let mut first_open_response_ms = Vec::new();
    let mut starts = 0u64;

    for _ in 0..rounds {
        let round_started = Instant::now();
        let mut tasks = JoinSet::new();
        for id in 0..count {
            let permit = limit.clone().acquire_owned().await?;
            let client = client.clone();
            let url = format!("{base}/api/{id}");
            tasks.spawn(async move {
                let _permit = permit;
                let result = async {
                    let response = client.get(url).send().await.map_err(|e| {
                        if e.is_timeout() {
                            "TIMEOUT".to_string()
                        } else {
                            format!("REQUEST_ERROR:{e}")
                        }
                    })?;
                    let code = response.status().as_u16();
                    if code >= 400 {
                        return Err(format!("HTTP_{code}"));
                    }
                    let value: Value = response
                        .json()
                        .await
                        .map_err(|_| "INVALID_JSON".to_string())?;
                    Ok(value)
                }
                .await;
                (id, result)
            });
            requests += 1;
        }
        while let Some(result) = tasks.join_next().await {
            let (id, result) = result?;
            match result {
                Ok(json) => {
                    let status = json["content"]["status"].as_str().unwrap_or("INVALID_JSON");
                    *outcomes.entry(status.to_string()).or_default() += 1;
                    if status == "OPEN" {
                        if let Some(live_id) = json["content"]["liveId"].as_i64() {
                            if live_ids.get(&id) != Some(&live_id) {
                                live_ids.insert(id, live_id);
                                starts += 1;
                                first_open_response_ms
                                    .push((id, started.elapsed().as_secs_f64() * 1000.0));
                            }
                        }
                    }
                }
                Err(error) => {
                    let category = if error.starts_with("REQUEST_ERROR:") {
                        "REQUEST_ERROR"
                    } else if error.contains("HTTP_500") {
                        "HTTP_500"
                    } else if error.contains("HTTP_429") {
                        "HTTP_429"
                    } else if error.contains("INVALID_JSON") {
                        "INVALID_JSON"
                    } else {
                        "TIMEOUT"
                    };
                    *outcomes.entry(category.to_string()).or_default() += 1;
                }
            }
        }
        sleep(Duration::from_secs_f64(interval).saturating_sub(round_started.elapsed())).await;
    }
    let steady_cpu_seconds = process_cpu_seconds()? - cpu_started;
    println!(
        "{}",
        serde_json::json!({"requests": requests, "starts": starts,
        "outcomes": outcomes, "first_open_response_ms": first_open_response_ms,
        "elapsed_seconds": started.elapsed().as_secs_f64(),
        "steady_cpu_seconds": steady_cpu_seconds})
    );
    Ok(())
}
