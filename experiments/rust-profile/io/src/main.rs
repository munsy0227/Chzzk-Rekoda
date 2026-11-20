use crc32fast::Hasher as Crc32Hasher;
use sha2::{Digest, Sha256};
use std::env;
use std::fs::{self, File};
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::path::Path;

fn crc32<R: Read>(mut input: R) -> io::Result<(u64, u32)> {
    let mut buf = [0u8; 256 * 1024];
    let mut bytes = 0u64;
    let mut hasher = Crc32Hasher::new();
    loop {
        let n = input.read(&mut buf)?;
        if n == 0 {
            break;
        }
        bytes += n as u64;
        hasher.update(&buf[..n]);
    }
    Ok((bytes, hasher.finalize()))
}

fn copy_roundtrip(src: &Path, dst: &Path) -> io::Result<()> {
    let mut input = BufReader::new(File::open(src)?);
    let mut output = BufWriter::new(File::create(dst)?);
    io::copy(&mut input, &mut output)?;
    output.flush()?;
    let (bytes, crc) = crc32(BufReader::new(File::open(dst)?))?;
    println!("{bytes} {crc:08x}");
    Ok(())
}

fn hash_parts(init_path: &Path, media_path: &Path, repeats: usize) -> io::Result<()> {
    let init = fs::read(init_path)?;
    let media = fs::read(media_path)?;
    let mut timings = Vec::with_capacity(repeats);
    let mut expected = String::new();
    for _ in 0..repeats {
        let start = std::time::Instant::now();
        let mut hasher = Sha256::new();
        hasher.update(std::hint::black_box(init.as_slice()));
        hasher.update(std::hint::black_box(media.as_slice()));
        let digest = std::hint::black_box(hasher.finalize());
        timings.push(start.elapsed().as_nanos());
        expected = format!("{digest:x}");
    }
    println!(
        "{expected} {}",
        timings
            .iter()
            .map(u128::to_string)
            .collect::<Vec<_>>()
            .join(",")
    );
    Ok(())
}

fn numeric_cmp(left: &str, right: &str) -> std::cmp::Ordering {
    let left = left.trim_start_matches('0');
    let right = right.trim_start_matches('0');
    left.len().cmp(&right.len()).then_with(|| left.cmp(right))
}

fn segment_names(dir: &Path, prefix: &str, suffix: &str) -> io::Result<Vec<(String, String)>> {
    let mut out = Vec::new();
    for entry in fs::read_dir(dir)? {
        let name = entry?.file_name().to_string_lossy().into_owned();
        if let Some(middle) = name
            .strip_prefix(prefix)
            .and_then(|s| s.strip_suffix(suffix))
        {
            if !middle.is_empty() && middle.bytes().all(|b| b.is_ascii_digit()) {
                out.push((middle.to_owned(), name));
            }
        }
    }
    out.sort_by(|left, right| numeric_cmp(&left.0, &right.0));
    Ok(out)
}

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("relay") => {
            io::copy(&mut io::stdin().lock(), &mut io::stdout().lock())?;
            io::stdout().flush()?;
        }
        Some("copy") if args.len() == 4 => {
            copy_roundtrip(Path::new(&args[2]), Path::new(&args[3]))?
        }
        Some("hash") if args.len() == 5 => hash_parts(
            Path::new(&args[2]),
            Path::new(&args[3]),
            args[4].parse().unwrap_or(1),
        )?,
        Some("files") if args.len() == 5 => {
            let names = segment_names(Path::new(&args[2]), &args[3], &args[4])?;
            println!(
                "{}",
                names
                    .iter()
                    .map(|item| item.1.as_str())
                    .collect::<Vec<_>>()
                    .join("\n")
            );
        }
        Some("size") if args.len() == 5 => {
            let dir = Path::new(&args[2]);
            let names = segment_names(dir, &args[3], &args[4])?;
            let mut total = 0u64;
            for (_, name) in names {
                match fs::metadata(dir.join(name)) {
                    Ok(metadata) => total += metadata.len(),
                    Err(error) if error.kind() == io::ErrorKind::NotFound => {}
                    Err(error) => return Err(error),
                }
            }
            println!("{total}");
        }
        _ => {
            eprintln!(
                "usage: rust-profile-io copy SRC DST | hash INIT MEDIA N | files DIR PREFIX SUFFIX | size DIR PREFIX SUFFIX | relay"
            );
            std::process::exit(2);
        }
    }
    Ok(())
}
