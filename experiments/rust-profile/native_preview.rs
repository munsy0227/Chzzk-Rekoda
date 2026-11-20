use std::{
    env,
    io::{self, Write},
    process::{exit, Command},
};

fn main() {
    let result = Command::new("ffmpeg")
        .args(env::args().skip(1))
        .output()
        .expect("FFmpeg failed to start");
    io::stdout()
        .write_all(&result.stdout)
        .expect("JPEG pipe closed");
    io::stderr()
        .write_all(&result.stderr)
        .expect("Diagnostic pipe closed");
    exit(result.status.code().unwrap_or(1));
}
