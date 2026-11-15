use std::{collections::HashMap, io, sync::Arc, time::Duration};

use reqwest::{Client, header::HeaderMap, redirect::Policy};
use serde_json::{Map, Value, json};
use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader},
    sync::{Semaphore, mpsc},
    task::{AbortHandle, JoinSet},
};

const MAX_LINE: usize = 64 * 1024;
const MAX_BODY: usize = 8 * 1024 * 1024;
const MAX_OUTPUT: usize = 8 * 1024 * 1024;
const MAX_CONCURRENT: usize = 16;
const MAX_PENDING: usize = 64;
const API_BASE: &str = "https://api.chzzk.naver.com/service/v2/channels";

pub async fn serve() -> io::Result<()> {
    let client = Client::builder()
        .timeout(Duration::from_secs(30))
        .no_proxy()
        .redirect(Policy::none())
        .build()
        .map_err(|_| io::Error::other("HTTP client initialization failed"))?;
    let (input_tx, mut input_rx) = mpsc::channel::<io::Result<Vec<u8>>>(16);
    let (output_tx, mut output_rx) = mpsc::channel::<Vec<u8>>(16);

    let reader = tokio::spawn(async move {
        let mut stdin = BufReader::new(tokio::io::stdin());
        loop {
            let mut line = Vec::with_capacity(1024);
            let count = match (&mut stdin)
                .take((MAX_LINE + 2) as u64)
                .read_until(b'\n', &mut line)
                .await
            {
                Ok(count) => count,
                Err(error) => {
                    let _ = input_tx.send(Err(error)).await;
                    return;
                }
            };
            if count == 0 {
                return;
            }
            let content_len = count - usize::from(line.last() == Some(&b'\n'));
            if content_len > MAX_LINE {
                let _ = input_tx
                    .send(Err(io::Error::new(
                        io::ErrorKind::InvalidData,
                        "input line exceeds limit",
                    )))
                    .await;
                return;
            }
            if line.last() == Some(&b'\n') {
                line.pop();
            }
            if input_tx.send(Ok(line)).await.is_err() {
                return;
            }
        }
    });

    let writer = tokio::spawn(async move {
        let mut stdout = tokio::io::stdout();
        while let Some(mut line) = output_rx.recv().await {
            line.push(b'\n');
            stdout.write_all(&line).await?;
            stdout.flush().await?;
        }
        Ok::<_, io::Error>(())
    });

    let permits = Arc::new(Semaphore::new(MAX_CONCURRENT));
    let mut tasks = JoinSet::new();
    let mut requests: HashMap<i64, AbortHandle> = HashMap::new();
    let mut input_open = true;
    let mut result = Ok(());

    while input_open {
        tokio::select! {
            message = input_rx.recv(), if input_open => match message {
                Some(Ok(line)) => {
                    let request = parse_request(&line);
                    let id = request.get("id").and_then(Value::as_i64);
                    match request.get("op").and_then(Value::as_str) {
                        Some("cancel") if request.get("version").and_then(Value::as_u64) == Some(1) => {
                            if let Some(id) = id {
                                if let Some(handle) = requests.remove(&id) {
                                    handle.abort();
                                }
                            }
                        }
                        Some("cancel") => send_error(&output_tx, id, "invalid_request", None).await?,
                        Some("hello") if request.get("version").and_then(Value::as_u64) == Some(1) => {
                            if let Some(id) = id {
                                if requests.contains_key(&id) {
                                    send_error(&output_tx, Some(id), "invalid_request", None).await?;
                                } else {
                                    let line = json!({"version":1,"id":id,"ok":true,"service":"chzzk-native"});
                                    send_value(&output_tx, line).await?;
                                }
                            } else {
                                send_error(&output_tx, None, "invalid_request", None).await?;
                            }
                        }
                        Some("live") if request.get("version").and_then(Value::as_u64) == Some(1) => {
                            if let Some(id) = id {
                                if requests.contains_key(&id) {
                                    send_error(&output_tx, Some(id), "invalid_request", None).await?;
                                } else if !valid_live_request(&request) {
                                    send_error(&output_tx, Some(id), "invalid_request", None).await?;
                                } else if requests.len() >= MAX_PENDING {
                                    send_error(&output_tx, Some(id), "network", None).await?;
                                } else {
                                    let client = client.clone();
                                    let output = output_tx.clone();
                                    let permits = permits.clone();
                                    let task = tasks.spawn(async move {
                                        let Ok(_permit) = permits.acquire_owned().await else {
                                            return id;
                                        };
                                        let response = fetch_live(&client, API_BASE, &request).await;
                                        let line = match response {
                                            Ok(data) => json!({"version":1,"id":id,"ok":true,"data":data}),
                                            Err((kind, status)) => error_value(Some(id), kind, status),
                                        };
                                        let _ = send_value(&output, line).await;
                                        id
                                    });
                                    requests.insert(id, task);
                                }
                            } else {
                                send_error(&output_tx, None, "invalid_request", None).await?;
                            }
                        }
                        _ => send_error(&output_tx, id, "invalid_request", None).await?,
                    }
                }
                Some(Err(error)) => {
                    result = Err(error);
                    input_open = false;
                }
                None => input_open = false,
            },
            joined = tasks.join_next(), if !tasks.is_empty() => {
                if let Some(Ok(id)) = joined {
                    requests.remove(&id);
                }
            }
        }
    }

    reader.abort();
    for handle in requests.into_values() {
        handle.abort();
    }
    while tasks.join_next().await.is_some() {}
    drop(output_tx);
    match writer.await {
        Ok(Ok(())) => result,
        Ok(Err(error)) => Err(error),
        Err(_) => Err(io::Error::other("stdout writer failed")),
    }
}

fn parse_request(line: &[u8]) -> Value {
    serde_json::from_slice(line).unwrap_or(Value::Null)
}

fn valid_live_request(request: &Value) -> bool {
    let Some(channel_id) = request.get("channel_id").and_then(Value::as_str) else {
        return false;
    };
    if channel_id.len() != 32 || !channel_id.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return false;
    }
    request
        .get("headers")
        .and_then(Value::as_object)
        .is_some_and(|headers| {
            headers
                .iter()
                .all(|(name, value)| !name.is_empty() && value.as_str().is_some())
        })
}

async fn fetch_live(
    client: &Client,
    base_url: &str,
    request: &Value,
) -> Result<Value, (&'static str, Option<u16>)> {
    let channel_id = request["channel_id"]
        .as_str()
        .ok_or(("invalid_request", None))?;
    let url = format!("{base_url}/{channel_id}/live-detail");
    let mut headers = HeaderMap::new();
    if let Some(values) = request["headers"].as_object() {
        for (name, value) in values {
            let name = reqwest::header::HeaderName::from_bytes(name.as_bytes())
                .map_err(|_| ("invalid_request", None))?;
            let value = reqwest::header::HeaderValue::from_str(
                value.as_str().ok_or(("invalid_request", None))?,
            )
            .map_err(|_| ("invalid_request", None))?;
            headers.insert(name, value);
        }
    }
    let response = client
        .get(url)
        .headers(headers)
        .send()
        .await
        .map_err(|_| ("network", None))?;
    if !response.status().is_success() {
        return Err(("http", Some(response.status().as_u16())));
    }
    let mut response = response;
    let mut body = Vec::new();
    while let Some(chunk) = response.chunk().await.map_err(|_| ("network", None))? {
        if body.len().saturating_add(chunk.len()) > MAX_BODY {
            return Err(("invalid_response", None));
        }
        body.extend_from_slice(&chunk);
    }
    let data: Value = serde_json::from_slice(&body).map_err(|_| ("invalid_response", None))?;
    if !data.is_object() {
        return Err(("invalid_response", None));
    }
    Ok(data)
}

fn error_value(id: Option<i64>, error: &'static str, status: Option<u16>) -> Value {
    let mut value = Map::from_iter([
        ("version".into(), json!(1)),
        ("id".into(), id.map_or(Value::Null, |id| json!(id))),
        ("ok".into(), json!(false)),
        ("error".into(), json!(error)),
    ]);
    if let Some(status) = status {
        value.insert("status".into(), json!(status));
    }
    Value::Object(value)
}

async fn send_error(
    output: &mpsc::Sender<Vec<u8>>,
    id: Option<i64>,
    error: &'static str,
    status: Option<u16>,
) -> io::Result<()> {
    send_value(output, error_value(id, error, status)).await
}

async fn send_value(output: &mpsc::Sender<Vec<u8>>, value: Value) -> io::Result<()> {
    let line = serde_json::to_vec(&value).map_err(io::Error::other)?;
    let line = if line.len() > MAX_OUTPUT {
        serde_json::to_vec(&error_value(
            value.get("id").and_then(Value::as_i64),
            "invalid_response",
            None,
        ))
        .map_err(io::Error::other)?
    } else {
        line
    };
    output
        .send(line)
        .await
        .map_err(|_| io::Error::new(io::ErrorKind::BrokenPipe, "stdout closed"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::{
        io::{AsyncReadExt, AsyncWriteExt},
        net::TcpListener,
        sync::oneshot,
    };

    async fn server(response: Vec<u8>) -> (String, oneshot::Receiver<Vec<u8>>) {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let (request_tx, request_rx) = oneshot::channel();
        tokio::spawn(async move {
            let (mut stream, _) = listener.accept().await.unwrap();
            let mut request = Vec::new();
            let mut buffer = [0; 1024];
            loop {
                let count = stream.read(&mut buffer).await.unwrap();
                if count == 0 {
                    break;
                }
                request.extend_from_slice(&buffer[..count]);
                if request.windows(4).any(|part| part == b"\r\n\r\n") {
                    break;
                }
            }
            let _ = request_tx.send(request);
            stream.write_all(&response).await.unwrap();
        });
        (format!("http://{address}"), request_rx)
    }

    fn live_request(headers: Value) -> Value {
        json!({"version":1,"id":7,"op":"live","channel_id":"0123456789abcdef0123456789abcdef","headers":headers})
    }

    #[tokio::test]
    async fn fetches_json_and_sends_auth_header() {
        let (base, request_rx) = server(
            b"HTTP/1.1 200 OK\r\nContent-Length: 13\r\nConnection: close\r\n\r\n{\"live\":true}"
                .to_vec(),
        )
        .await;
        let client = Client::builder()
            .no_proxy()
            .redirect(Policy::none())
            .build()
            .unwrap();
        assert_eq!(
            fetch_live(
                &client,
                &base,
                &live_request(json!({"Authorization":"Bearer dummy"}))
            )
            .await
            .unwrap(),
            json!({"live":true})
        );
        let request = String::from_utf8(request_rx.await.unwrap()).unwrap();
        assert!(request.contains("authorization: Bearer dummy\r\n"));
    }

    #[tokio::test]
    async fn reports_http_and_invalid_json_errors() {
        let client = Client::builder().no_proxy().build().unwrap();
        let (base, _) = server(
            b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
                .to_vec(),
        )
        .await;
        assert_eq!(
            fetch_live(&client, &base, &live_request(json!({})))
                .await
                .unwrap_err(),
            ("http", Some(500))
        );
        let (base, _) = server(
            b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nno!".to_vec(),
        )
        .await;
        assert_eq!(
            fetch_live(&client, &base, &live_request(json!({})))
                .await
                .unwrap_err(),
            ("invalid_response", None)
        );
    }

    #[tokio::test]
    async fn rejects_oversized_responses() {
        let body = vec![b' '; MAX_BODY + 1];
        let mut response = format!(
            "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        )
        .into_bytes();
        response.extend_from_slice(&body);
        let (base, _) = server(response).await;
        let client = Client::builder().no_proxy().build().unwrap();
        assert_eq!(
            fetch_live(&client, &base, &live_request(json!({})))
                .await
                .unwrap_err(),
            ("invalid_response", None)
        );
    }

    #[tokio::test]
    async fn replaces_oversized_output_with_error_response() {
        let (output, mut lines) = mpsc::channel(1);
        send_value(
            &output,
            json!({"version":1,"id":23,"ok":true,"data":"x".repeat(MAX_OUTPUT)}),
        )
        .await
        .unwrap();
        let response: Value = serde_json::from_slice(&lines.recv().await.unwrap()).unwrap();
        assert_eq!(response["id"], 23);
        assert_eq!(response["ok"], false);
        assert_eq!(response["error"], "invalid_response");
    }

    #[test]
    fn rejects_invalid_channel_ids() {
        assert!(!valid_live_request(
            &json!({"channel_id":"short","headers":{}})
        ));
        assert!(valid_live_request(&live_request(json!({}))));
    }
}
