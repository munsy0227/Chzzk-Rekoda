
import asyncio
from typing import Any, Dict, List, Tuple
import aiofiles
import orjson
from logger import log
import platform
from pathlib import Path
import hashlib
import os

async def setup_paths() -> Tuple[Path, Path]:
    base_dir = Path(__file__).parent.parent
    os_name = platform.system()

    if os_name == "Windows":
        streamlink_path = base_dir / "venv/Scripts/streamlink.exe"
        ffmpeg_path = base_dir / "ffmpeg/bin/ffmpeg.exe"
        log.info("Running on Windows.")
    else:
        streamlink_path = base_dir / "venv/bin/streamlink"
        ffmpeg_command = "which ffmpeg"
        try:
            process = await asyncio.create_subprocess_shell(
                ffmpeg_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            ffmpeg_path = (
                Path(stdout.decode().strip()) if process.returncode == 0 else None
            )
            log.info(f"Running on {os_name}. ffmpeg found at: {ffmpeg_path}")
        except Exception as e:
            log.error(f"Error finding ffmpeg on {os_name}: {e}")
            ffmpeg_path = None

    return streamlink_path, ffmpeg_path


async def load_json_async(file_path: Path) -> Any:
    try:
        async with aiofiles.open(file_path, "rb") as file:
            content = await file.read()
            return orjson.loads(content)
    except Exception as e:
        log.error(f"Error loading JSON from {file_path}: {e}")
        return None


async def load_settings(FILES: List[Path]) -> Tuple[int, int, List[Dict[str, Any]], Dict[str, int]]:
    listfiles = [load_json_async(FILE) for FILE in FILES] 
    settings = await asyncio.gather(*listfiles)

    timeout = (
        settings[0]
        if isinstance(settings[0], int)
        else int(settings[0].get("timeout", 60))
    )
    stream_segment_threads = (
        settings[1]
        if isinstance(settings[1], int)
        else int(settings[1].get("threads", 4))
    )
    channels = settings[2]
    delays = settings[3]

    return timeout, stream_segment_threads, channels, delays


def shorten_filename(filename: str) -> str:
    MAX_FILENAME_BYTES = 255
    MAX_HASH_LENGTH = 8
    RESERVED_BYTES = MAX_HASH_LENGTH + 1  # Hash length and one underscore

    filename_bytes = filename.encode("utf-8")
    if len(filename_bytes) > MAX_FILENAME_BYTES:
        hash_value = hashlib.sha256(filename_bytes).hexdigest()[:MAX_HASH_LENGTH]
        name, extension = os.path.splitext(filename)
        max_name_length = (
            MAX_FILENAME_BYTES - RESERVED_BYTES - len(extension.encode("utf-8"))
        )

        shortened_name = name.encode("utf-8")[:max_name_length].decode(
            "utf-8", "ignore"
        )
        shortened_filename = f"{shortened_name}_{hash_value}{extension}"
        log.warning(
            f"Filename {filename} is too long. Shortening to {shortened_filename}."
        )
        return shortened_filename

    return filename

