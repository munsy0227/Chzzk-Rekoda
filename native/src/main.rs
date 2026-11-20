mod report;
mod watch;

use std::{env, path::Path};

fn main() {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("serve") if args.len() == 2 => {
            let result = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .and_then(|runtime| runtime.block_on(watch::serve()));
            if result.is_err() {
                std::process::exit(1);
            }
        }
        Some("report") if args.len() == 3 => {
            let reply = match report::summarize_file(Path::new(&args[2])) {
                Ok(Some(summary)) => serde_json::json!({
                    "version": 1, "ok": true, "summary": summary
                }),
                Ok(None) => serde_json::json!({
                    "version": 1, "ok": false, "error": "unsupported"
                }),
                Err(_) => serde_json::json!({
                    "version": 1, "ok": false, "error": "io"
                }),
            };
            println!("{reply}");
        }
        _ => std::process::exit(2),
    }
}
