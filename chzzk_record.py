import asyncio
import collections
import contextlib
import hashlib
import logging
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import aiohttp
import orjson

if platform.system() != "Windows":
    import uvloop

    uvloop.install()

# Import Rich library components
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

# Global paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE_PATH = BASE_DIR / "config.json"
LOG_FILE_PATH = BASE_DIR / "log.log"

DEFAULT_RESCAN_INTERVAL_SECONDS = 60
MIN_RESCAN_INTERVAL_SECONDS = 1
MAX_RESCAN_INTERVAL_SECONDS = 3600
DEFAULT_OUTPUT_FORMAT = "ts"
SUPPORTED_OUTPUT_FORMATS = {"ts", "mkv", "webm"}

# Global console instance for Rich
console = Console()

# Shared data structure for channel progress
channel_progress: Dict[str, Dict[str, Any]] = {}
channel_progress_lock = asyncio.Lock()

# Create a queue for log messages
log_queue: asyncio.Queue = asyncio.Queue()


# Helper function to load log_enabled
def get_log_enabled() -> bool:
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "rb") as f:
                config = orjson.loads(f.read())
                return config.get("log_enabled", True)
        except Exception:
            pass
    return True


# Function to toggle log_enabled
def toggle_log_enabled():
    try:
        current_config = {}
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, "rb") as f:
                current_config = orjson.loads(f.read())

        current_state = current_config.get("log_enabled", True)
        new_state = not current_state
        current_config["log_enabled"] = new_state

        save_json_secure(CONFIG_FILE_PATH, current_config)

        print(f"Logging has been {'enabled' if new_state else 'disabled'}.")
    except Exception as e:
        print(f"Error toggling log: {e}")


# Custom logging handler to put log messages into the queue
class QueueHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        try:
            self.queue.put_nowait(msg)
        except asyncio.QueueFull:
            pass  # Handle the case where the queue is full


# Logger setup
class FfmpegStderrFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "ffmpeg stderr" in msg and "Invalid DTS" in msg:
            return False
        return True


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("Recorder")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # Check if logging is enabled
    log_enabled = get_log_enabled()

    if log_enabled:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(FfmpegStderrFilter())
        logger.addHandler(file_handler)

    # QueueHandler is always active (for UI display)
    queue_handler = QueueHandler(log_queue)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    logger.addHandler(queue_handler)

    logger.propagate = False

    return logger


logger = setup_logger()

print(
    "Chzzk Rekoda made by munsy0227\n"
    "If you encounter any bugs or errors, please report them on GitHub Issues!\n"
    "버그나 에러가 발생하면 깃허브 이슈에 제보해 주세요!"
)

# Constants
LIVE_DETAIL_API = (
    "https://api.chzzk.naver.com/service/v3/channels/{channel_id}/live-detail"
)
SPECIAL_CHARS_REMOVER = re.compile(r'[\\/:*?"<>|]')
CONTROL_CHARS_REMOVER = re.compile(r"[\x00-\x1f\x7f]")
SAFE_CHANNEL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SAFE_FFMPEG_VALUE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
SAFE_BITRATE = re.compile(r"^\d+[kKmM]?$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
KNOWN_HEVC_ENCODERS = {
    "libx265",
    "hevc_nvenc",
    "hevc_qsv",
    "hevc_amf",
    "hevc_vaapi",
    "hevc_videotoolbox",
}
HEVC_SOFTWARE_FALLBACK_ENCODERS = ("libx265",)
HEVC_ENCODER_PROBE_CACHE: Dict[Tuple[str, str, str, str, str], Tuple[bool, str]] = {}
KNOWN_AV1_ENCODERS = {
    "libsvtav1",
    "libaom-av1",
    "av1_nvenc",
    "av1_qsv",
    "av1_amf",
    "av1_vaapi",
}
AV1_SOFTWARE_FALLBACK_ENCODERS = ("libsvtav1", "libaom-av1")
AV1_ENCODER_PROBE_CACHE: Dict[Tuple[str, str, str, str, str], Tuple[bool, str]] = {}
PLUGIN_DIR_PATH = BASE_DIR / "plugin"

# Max filename length constants
MAX_FILENAME_BYTES = 255
MAX_HASH_LENGTH = 8
RESERVED_BYTES = MAX_HASH_LENGTH + 1  # Hash length and one underscore

# Global variables for graceful shutdown
shutdown_event = asyncio.Event()


# Helper functions
def save_json_secure(file_path: Path, data: Dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    if os.name != "nt":
        with contextlib.suppress(OSError):
            os.chmod(file_path, 0o600)


def sanitize_cookie_value(value: Any) -> str:
    text = CONTROL_CHARS_REMOVER.sub("", str(value or ""))
    return text.replace(";", "").strip()


def sanitize_filename_component(value: Any, fallback: str = "untitled") -> str:
    text = str(value or "").strip()
    text = SPECIAL_CHARS_REMOVER.sub("", text)
    text = CONTROL_CHARS_REMOVER.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    if not text:
        text = fallback
    if text.upper().split(".", 1)[0] in WINDOWS_RESERVED_NAMES:
        text = f"_{text}"
    return text


def resolve_output_dir(value: Any) -> Path:
    output_dir_text = str(value or ".").strip() or "."
    output_dir = Path(output_dir_text).expanduser()
    if not output_dir.is_absolute():
        output_dir = BASE_DIR / output_dir
    return output_dir


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not find an available filename for {path}")


def clamp_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def normalize_bitrate(value: Any, default: str) -> str:
    text = str(value or default).strip()
    if not SAFE_BITRATE.fullmatch(text):
        return default
    if text[-1].isdigit():
        text = f"{text}k"
    return text.lower()


def normalize_output_format(value: Any) -> str:
    text = str(value or DEFAULT_OUTPUT_FORMAT).strip().lower().lstrip(".")
    return text if text in SUPPORTED_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT


def normalize_hevc_settings(value: Any) -> Dict[str, Any]:
    defaults = {
        "enable": False,
        "encoder": "libx265",
        "bitrate": "2500k",
        "max_bitrate": "10000k",
        "preset": "ultrafast",
    }
    if not isinstance(value, dict):
        return defaults

    settings = defaults | value
    settings["enable"] = bool(settings.get("enable", False))
    encoder = str(settings.get("encoder", defaults["encoder"])).strip()
    if encoder not in KNOWN_HEVC_ENCODERS:
        logger.warning(f"Unknown HEVC encoder '{encoder}'. Falling back to libx265.")
        encoder = defaults["encoder"]
    settings["encoder"] = encoder
    settings["bitrate"] = normalize_bitrate(settings.get("bitrate"), defaults["bitrate"])
    settings["max_bitrate"] = normalize_bitrate(
        settings.get("max_bitrate"), defaults["max_bitrate"]
    )
    preset = str(settings.get("preset", defaults["preset"])).strip()
    settings["preset"] = preset if SAFE_FFMPEG_VALUE.fullmatch(preset) else defaults["preset"]
    return settings


def normalize_av1_settings(value: Any) -> Dict[str, Any]:
    defaults = {
        "enable": False,
        "encoder": "libsvtav1",
        "bitrate": "2500k",
        "max_bitrate": "10000k",
        "preset": "8",
    }
    if not isinstance(value, dict):
        return defaults

    settings = defaults | value
    settings["enable"] = bool(settings.get("enable", False))
    encoder = str(settings.get("encoder", defaults["encoder"])).strip()
    if encoder not in KNOWN_AV1_ENCODERS:
        logger.warning(f"Unknown AV1 encoder '{encoder}'. Falling back to libsvtav1.")
        encoder = defaults["encoder"]
    settings["encoder"] = encoder
    settings["bitrate"] = normalize_bitrate(settings.get("bitrate"), defaults["bitrate"])
    settings["max_bitrate"] = normalize_bitrate(
        settings.get("max_bitrate"), defaults["max_bitrate"]
    )
    preset = str(settings.get("preset", defaults["preset"])).strip()
    settings["preset"] = preset if SAFE_FFMPEG_VALUE.fullmatch(preset) else defaults["preset"]
    return settings


def normalize_channels(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []

    normalized = []
    for index, raw_channel in enumerate(value, start=1):
        if not isinstance(raw_channel, dict):
            logger.warning(f"Skipping invalid channel entry at index {index}.")
            continue

        channel_id = str(raw_channel.get("id", "")).strip()
        if not SAFE_CHANNEL_ID.fullmatch(channel_id):
            logger.warning(f"Skipping channel with invalid ID: {channel_id!r}")
            continue

        identifier = str(raw_channel.get("identifier") or f"ch{index}").strip()
        if not SAFE_FFMPEG_VALUE.fullmatch(identifier):
            identifier = f"ch{index}"

        normalized.append(
            {
                **raw_channel,
                "id": channel_id,
                "name": sanitize_filename_component(
                    raw_channel.get("name"), fallback=channel_id
                ),
                "output_dir": str(raw_channel.get("output_dir") or "."),
                "identifier": identifier,
                "active": "off" if raw_channel.get("active") == "off" else "on",
            }
        )
    return normalized


async def drain_task(task: asyncio.Task, timeout: float = 5.0) -> None:
    if task.done():
        await asyncio.gather(task, return_exceptions=True)
        return

    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
    except asyncio.TimeoutError:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    except asyncio.CancelledError:
        if task.cancelled():
            return
        raise


def isolated_subprocess_kwargs() -> Dict[str, Any]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


async def create_isolated_subprocess_exec(
    *cmd: str, **kwargs: Any
) -> asyncio.subprocess.Process:
    process_kwargs: Dict[str, Any] = {"cwd": str(BASE_DIR)}
    process_kwargs.update(isolated_subprocess_kwargs())
    process_kwargs.update(kwargs)
    return await asyncio.create_subprocess_exec(*cmd, **process_kwargs)


def signal_process_group(
    process: asyncio.subprocess.Process, force: bool = False
) -> None:
    if os.name != "nt":
        sig = signal.SIGKILL if force else signal.SIGTERM
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(os.getpgid(process.pid), sig)
            return

    with contextlib.suppress(ProcessLookupError):
        if force:
            process.kill()
        else:
            process.terminate()


async def terminate_process(
    process: Optional[asyncio.subprocess.Process], name: str, timeout: float = 5.0
) -> None:
    if process is None or process.returncode is not None:
        return

    signal_process_group(process)
    try:
        await asyncio.wait_for(process.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"{name} did not terminate in time. Killing it.")
        signal_process_group(process, force=True)
        await process.wait()


class RecordingProcessSandbox:
    def __init__(self, channel_name: str, channel_id: str) -> None:
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.stream_process: Optional[asyncio.subprocess.Process] = None
        self.ffmpeg_process: Optional[asyncio.subprocess.Process] = None
        self._tasks: List[asyncio.Task] = []
        self._cancel_on_cleanup: List[asyncio.Task] = []

    async def start_streamlink(
        self, command: List[str]
    ) -> asyncio.subprocess.Process:
        self.stream_process = await create_isolated_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return self.stream_process

    async def start_ffmpeg(self, command: List[str]) -> asyncio.subprocess.Process:
        self.ffmpeg_process = await create_isolated_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        return self.ffmpeg_process

    def create_task(
        self, coro: Any, cancel_on_cleanup: bool = False
    ) -> asyncio.Task:
        task = asyncio.create_task(coro)
        if cancel_on_cleanup:
            self._cancel_on_cleanup.append(task)
        else:
            self._tasks.append(task)
        return task

    async def cleanup(self) -> None:
        await terminate_process(
            self.ffmpeg_process, f"ffmpeg [{self.channel_name}/{self.channel_id}]"
        )
        await terminate_process(
            self.stream_process, f"streamlink [{self.channel_name}/{self.channel_id}]"
        )
        for task in self._cancel_on_cleanup:
            if not task.done():
                task.cancel()
        if self._cancel_on_cleanup:
            await asyncio.gather(*self._cancel_on_cleanup, return_exceptions=True)

        for task in self._tasks:
            await drain_task(task)
        self._tasks.clear()
        self._cancel_on_cleanup.clear()


async def pipe_stream_to_stdin(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, channel_name: str
) -> None:
    try:
        while not shutdown_event.is_set():
            chunk = await reader.read(256 * 1024)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    except (BrokenPipeError, ConnectionResetError):
        logger.debug(f"ffmpeg stdin closed while piping stream for {channel_name}.")
    except Exception as e:
        logger.error(f"Error piping stream to ffmpeg for {channel_name}: {e}")
    finally:
        if not writer.is_closing():
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()


async def read_log_stream(
    stream: Optional[asyncio.StreamReader], process_name: str, channel_id: str
) -> None:
    if stream is None:
        return

    while not stream.at_eof():
        line = await stream.readline()
        if not line:
            break
        line_str = line.decode(errors="replace").strip()
        if not line_str:
            continue

        if process_name == "streamlink":
            logger.info(f"{process_name} stderr [{channel_id}]: {line_str}")
        else:
            logger.debug(f"{process_name} stderr [{channel_id}]: {line_str}")


async def setup_paths() -> Optional[Path]:
    os_name = platform.system()

    if os_name == "Windows":
        logger.info("Running on Windows.")
        bundled_ffmpeg = BASE_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
        if bundled_ffmpeg.exists():
            logger.info(f"Using bundled ffmpeg at: {bundled_ffmpeg}")
            return bundled_ffmpeg

        ffmpeg_on_path = shutil.which("ffmpeg")
        if ffmpeg_on_path:
            ffmpeg_path = Path(ffmpeg_on_path)
            logger.info(f"Using ffmpeg from PATH at: {ffmpeg_path}")
            return ffmpeg_path

        logger.error("ffmpeg not found. Run install.bat or add ffmpeg to PATH.")
    else:
        ffmpeg_on_path = shutil.which("ffmpeg")
        if ffmpeg_on_path:
            ffmpeg_path = Path(ffmpeg_on_path)
            logger.info(f"Running on {os_name}. ffmpeg found at: {ffmpeg_path}")
            return ffmpeg_path

        logger.error("ffmpeg not found on the system PATH.")

    return None


async def load_json_async(file_path: Path) -> Any:
    if not file_path.exists():
        return None
    try:
        async with aiofiles.open(file_path, "rb") as file:
            content = await file.read()
            return orjson.loads(content)
    except orjson.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return None


async def load_config_async() -> Dict[str, Any]:
    config = await load_json_async(CONFIG_FILE_PATH)
    if not config:
        return {}
    return config


async def load_settings() -> (
    Tuple[
        int,
        int,
        List[Dict[str, Any]],
        Dict[str, int],
        Dict[str, Any],
        Dict[str, Any],
        str,
    ]
):
    config = await load_config_async()

    timeout = clamp_int(
        config.get("timeout"),
        default=DEFAULT_RESCAN_INTERVAL_SECONDS,
        min_value=MIN_RESCAN_INTERVAL_SECONDS,
        max_value=MAX_RESCAN_INTERVAL_SECONDS,
    )
    stream_segment_threads = clamp_int(
        config.get("stream_segment_threads"), default=2, min_value=1, max_value=16
    )
    channels = normalize_channels(config.get("channels", []))
    raw_delays = config.get("delays", {})
    delays = {
        str(key): clamp_int(value, default=0, min_value=0, max_value=3600)
        for key, value in raw_delays.items()
    } if isinstance(raw_delays, dict) else {}
    hevc_settings = normalize_hevc_settings(config.get("hevc_settings"))
    av1_settings = normalize_av1_settings(config.get("av1_settings"))
    if av1_settings.get("enable"):
        hevc_settings["enable"] = False
    output_format = normalize_output_format(config.get("output_format"))

    return (
        timeout,
        stream_segment_threads,
        channels,
        delays,
        hevc_settings,
        av1_settings,
        output_format,
    )


def cookie_header_from(cookies: Dict[str, str]) -> str:
    nid_aut = sanitize_cookie_value(cookies.get("NID_AUT", ""))
    nid_ses = sanitize_cookie_value(cookies.get("NID_SES", ""))
    return f"NID_AUT={nid_aut}; NID_SES={nid_ses}"


def get_auth_headers(cookies: Dict[str, str]) -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (X11; Unix x86_64)",
        "Cookie": cookie_header_from(cookies),
        "Origin": "https://chzzk.naver.com",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Referer": "",
    }


def streamlink_http_header_args(cookies: Dict[str, str]) -> List[str]:
    headers = [f"Cookie={cookie_header_from(cookies)}"]
    headers.extend(
        [
            "User-Agent=Mozilla/5.0 (X11; Unix x86_64)",
            "Origin=https://chzzk.naver.com",
            "DNT=1",
            "Sec-GPC=1",
            "Connection=keep-alive",
            "Referer=",
        ]
    )

    args = []
    for header in headers:
        args.extend(["--http-header", header])
    return args


async def get_session_cookies() -> Dict[str, str]:
    config = await load_config_async()
    cookies = config.get("cookies", {})
    if not isinstance(cookies, dict):
        return {"NID_AUT": "", "NID_SES": ""}
    return {
        "NID_AUT": sanitize_cookie_value(cookies.get("NID_AUT", "")),
        "NID_SES": sanitize_cookie_value(cookies.get("NID_SES", "")),
    }


async def get_live_info(
    channel: Dict[str, Any], headers: Dict[str, str], session: aiohttp.ClientSession
) -> Tuple[str, Dict[str, Any]]:
    logger.debug(f"Fetching live info for channel: {channel.get('name', 'Unknown')}")
    try:
        async with session.get(
            LIVE_DETAIL_API.format(channel_id=channel["id"]), headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            logger.debug(
                f"Successfully fetched live info for channel: {channel.get('name', 'Unknown')}"
            )

            content = data.get("content", {})
            status = content.get("status", "")
            if status == "CLOSE":
                logger.info(
                    f"The channel '{channel.get('name', 'Unknown')}' is not currently live."
                )
            if status == "BLOCK":
                logger.info(
                    f"The channel '{channel.get('name', 'Unknown')}' is blocked."
                )
                return status, {}
            return status, content
    except aiohttp.ClientError as e:
        logger.error(
            f"HTTP error occurred while fetching live info for {channel.get('name', 'Unknown')}: {e}"
        )
    except Exception as e:
        logger.error(
            f"Failed to fetch live info for {channel.get('name', 'Unknown')}: {e}"
        )
    return "", {}


def shorten_filename(filename: str) -> str:
    if filename.endswith(".part"):
        final_name = filename[: -len(".part")]
        name, final_ext = os.path.splitext(final_name)
        compound_ext = f"{final_ext}.part"
    else:
        name, compound_ext = os.path.splitext(filename)

    filename_bytes = filename.encode("utf-8")
    if len(filename_bytes) > MAX_FILENAME_BYTES:
        hash_value = hashlib.sha256(filename_bytes).hexdigest()[:MAX_HASH_LENGTH]
        max_name_length = MAX_FILENAME_BYTES - (
            len(compound_ext.encode("utf-8")) + MAX_HASH_LENGTH + 1
        )
        shortened_name_bytes = name.encode("utf-8")[:max_name_length]
        shortened_name = shortened_name_bytes.decode("utf-8", "ignore")
        shortened_filename = f"{shortened_name}_{hash_value}{compound_ext}"
        logger.warning(
            f"Filename '{filename}' is too long. Shortening to '{shortened_filename}'."
        )
        return shortened_filename

    return filename


def format_size(size_bytes: float) -> str:
    if size_bytes <= 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"


time_pattern = re.compile(r"(\d+):(\d+):(\d+)\.(\d+)")


def parse_time(time_str):
    logger.debug(f"Parsing out_time: {time_str}")
    match = time_pattern.match(time_str)
    if not match:
        return 0
    hours, minutes, seconds, fractions = match.groups()
    total_seconds = (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(fractions) / (10 ** len(fractions))
    )
    return total_seconds


async def read_stream(
    stream: asyncio.StreamReader, channel_id: str, stream_type: str
) -> None:
    summary: Dict[str, str] = {}
    speed_samples = collections.deque(maxlen=5)

    prev_total_size = None
    prev_time = None

    while not stream.at_eof():
        try:
            line = await stream.readline()
            if not line:
                break
            line_str = line.decode(errors="ignore").strip()

            # Add log
            logger.debug(f"ffmpeg {stream_type} [{channel_id}]: {line_str}")

            if "=" not in line_str:
                continue

            key, value = line_str.split("=", 1)
            summary[key.strip()] = value.strip()

            if key.strip() == "progress":
                total_size_str = summary.get("total_size", "0")
                out_time_str = summary.get("out_time", "0")

                try:
                    total_size = int(total_size_str)
                except ValueError:
                    total_size = 0

                total_size_formatted = format_size(total_size)

                # Convert out_time to seconds
                out_time_seconds = parse_time(out_time_str)

                # Calculate bitrate
                if out_time_seconds > 0:
                    bitrate = (total_size * 8) / out_time_seconds  # bits per second
                    bitrate_kbps = bitrate / 1000  # Convert to kbps
                    bitrate_formatted = f"{bitrate_kbps:.2f} kbps"
                else:
                    bitrate_formatted = "N/A"

                # Calculate download speed
                current_time = time.time()
                if prev_total_size is not None and prev_time is not None:
                    bytes_diff = total_size - prev_total_size
                    time_diff = current_time - prev_time
                    if time_diff > 0:
                        instant_speed = bytes_diff / time_diff  # Bytes per second
                        speed_samples.append(instant_speed)
                        average_speed = sum(speed_samples) / len(speed_samples)
                        download_speed_formatted = format_size(average_speed) + "/s"
                    else:
                        download_speed_formatted = "N/A"
                    prev_total_size = total_size
                    prev_time = current_time
                else:
                    download_speed_formatted = "N/A"
                    prev_total_size = total_size
                    prev_time = current_time

                # Update progress data
                async with channel_progress_lock:
                    if channel_id in channel_progress:
                        channel_progress[channel_id].update(
                            {
                                "bitrate": bitrate_formatted,
                                "download_speed": download_speed_formatted,
                                "total_size": total_size_formatted,
                                "out_time": out_time_str,
                            }
                        )

                summary.clear()
        except Exception as e:
            logger.error(f"Error occurred while reading stream for {channel_id}: {e}")
            break


def bitrate_to_kbps(value: Any) -> Optional[int]:
    text = str(value or "").strip().lower()
    if not text:
        return None

    try:
        if text.endswith("m"):
            return int(text[:-1]) * 1000
        if text.endswith("k"):
            return int(text[:-1])
        return int(text)
    except ValueError:
        return None


def calculate_bufsize(max_bitrate: str, fallback: str = "16000k") -> str:
    max_val = bitrate_to_kbps(max_bitrate)
    if max_val is None:
        return fallback
    return f"{max_val * 2}k"


def capped_vbr_args(bitrate: str, max_bitrate: str, bufsize: str) -> List[str]:
    bitrate_value = bitrate_to_kbps(bitrate)
    max_bitrate_value = bitrate_to_kbps(max_bitrate)
    if (
        bitrate_value is not None
        and max_bitrate_value is not None
        and max_bitrate_value <= bitrate_value
    ):
        return []
    return ["-maxrate", max_bitrate, "-bufsize", bufsize]


def numeric_preset(value: Any, default: str) -> str:
    text = str(value or default).strip()
    return text if text.isdigit() else default


def nvenc_preset(value: Any, default: str = "p4") -> str:
    text = str(value or default).strip().lower()
    if text.startswith("p") and len(text) == 2 and text[1].isdigit():
        return text
    if "fast" in text or "super" in text or "ultra" in text:
        return "p1"
    if "slow" in text:
        return "p6"
    return default


def audio_stripped_encoding_args(args: List[str]) -> List[str]:
    stripped = []
    skip_next = False
    audio_options = {"-c:a", "-b:a"}
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in audio_options:
            skip_next = True
            continue
        stripped.append(arg)
    return stripped


def summarize_probe_error(message: str) -> str:
    for line in message.splitlines():
        line = line.strip()
        if line:
            return line[:300]
    return "no diagnostic output"


def probe_av1_encoder(
    ffmpeg_path: Path, av1_settings: Dict[str, Any]
) -> Tuple[bool, str]:
    encoder = str(av1_settings.get("encoder", "libsvtav1"))
    cache_key = (
        str(ffmpeg_path),
        encoder,
        str(av1_settings.get("bitrate", "2500k")),
        str(av1_settings.get("max_bitrate", "10000k")),
        str(av1_settings.get("preset", "8")),
    )
    if cache_key in AV1_ENCODER_PROBE_CACHE:
        return AV1_ENCODER_PROBE_CACHE[cache_key]

    input_args = [str(ffmpeg_path), "-hide_banner", "-loglevel", "error"]
    if encoder == "av1_vaapi":
        input_args.extend(
            [
                "-init_hw_device",
                "vaapi=vaapi0:/dev/dri/renderD128",
                "-filter_hw_device",
                "vaapi0",
            ]
        )
    input_args.extend(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=1",
            "-frames:v",
            "1",
        ]
    )

    video_args = audio_stripped_encoding_args(
        build_av1_encoding_args(av1_settings, "mkv")
    )
    probe_cmd = input_args + video_args + ["-an", "-f", "null", "-"]

    try:
        result = subprocess.run(
            probe_cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        message = (result.stderr or result.stdout or "").strip()
        probe_result = (result.returncode == 0, message)
    except (OSError, subprocess.SubprocessError) as e:
        probe_result = (False, str(e))

    AV1_ENCODER_PROBE_CACHE[cache_key] = probe_result
    return probe_result


def resolve_av1_settings_for_recording(
    av1_settings: Dict[str, Any], ffmpeg_path: Path
) -> Dict[str, Any]:
    if not av1_settings.get("enable", False):
        return av1_settings

    active_settings = dict(av1_settings)
    selected_encoder = str(active_settings.get("encoder", "libsvtav1"))
    encoder_works, probe_message = probe_av1_encoder(ffmpeg_path, active_settings)
    if encoder_works:
        return active_settings

    logger.warning(
        f"AV1 encoder '{selected_encoder}' is not usable with the current "
        f"FFmpeg/hardware setup: {summarize_probe_error(probe_message)}"
    )

    for fallback_encoder in AV1_SOFTWARE_FALLBACK_ENCODERS:
        if fallback_encoder == selected_encoder:
            continue
        fallback_settings = dict(active_settings)
        fallback_settings["encoder"] = fallback_encoder
        fallback_works, fallback_message = probe_av1_encoder(
            ffmpeg_path, fallback_settings
        )
        if fallback_works:
            logger.warning(
                f"Using AV1 encoder '{fallback_encoder}' instead of "
                f"'{selected_encoder}' for this recording."
            )
            return fallback_settings
        logger.warning(
            f"AV1 fallback encoder '{fallback_encoder}' is not usable: "
            f"{summarize_probe_error(fallback_message)}"
        )

    disabled_settings = dict(active_settings)
    disabled_settings["enable"] = False
    logger.warning("No usable AV1 encoder found. Recording without AV1 encoding.")
    return disabled_settings


def build_hevc_probe_args(hevc_settings: Dict[str, Any]) -> List[str]:
    encoder = hevc_settings.get("encoder", "libx265")
    bitrate = hevc_settings.get("bitrate", "2500k")
    max_bitrate = hevc_settings.get("max_bitrate", "10000k")
    preset = str(hevc_settings.get("preset", "ultrafast")).strip()
    bufsize = calculate_bufsize(max_bitrate)

    if encoder == "hevc_nvenc":
        return [
            "-c:v",
            "hevc_nvenc",
            "-preset",
            nvenc_preset(preset),
            "-b:v",
            bitrate,
            "-maxrate",
            max_bitrate,
            "-bufsize",
            bufsize,
            "-rc",
            "vbr",
        ]
    if encoder == "hevc_qsv":
        return [
            "-c:v",
            "hevc_qsv",
            "-preset",
            preset,
            "-b:v",
            bitrate,
            "-maxrate",
            max_bitrate,
            "-bufsize",
            bufsize,
        ]
    if encoder == "hevc_amf":
        return [
            "-c:v",
            "hevc_amf",
            "-usage",
            "transcoding",
            "-rc",
            "vbr_peak",
            "-b:v",
            bitrate,
            "-maxrate",
            max_bitrate,
            "-bufsize",
            bufsize,
        ]
    if encoder == "hevc_vaapi":
        return [
            "-vf",
            "format=nv12,hwupload",
            "-c:v",
            "hevc_vaapi",
            "-b:v",
            bitrate,
            "-maxrate",
            max_bitrate,
            "-bufsize",
            bufsize,
        ]
    if encoder == "hevc_videotoolbox":
        return [
            "-c:v",
            "hevc_videotoolbox",
            "-allow_sw",
            "1",
            "-realtime",
            "true",
            "-b:v",
            bitrate,
            "-maxrate",
            max_bitrate,
            "-bufsize",
            bufsize,
        ]
    return [
        "-c:v",
        "libx265",
        "-preset",
        preset,
        "-b:v",
        bitrate,
        "-maxrate",
        max_bitrate,
        "-bufsize",
        bufsize,
        "-tune",
        "zerolatency",
    ]


def probe_hevc_encoder(
    ffmpeg_path: Path, hevc_settings: Dict[str, Any]
) -> Tuple[bool, str]:
    encoder = str(hevc_settings.get("encoder", "libx265"))
    cache_key = (
        str(ffmpeg_path),
        encoder,
        str(hevc_settings.get("bitrate", "2500k")),
        str(hevc_settings.get("max_bitrate", "10000k")),
        str(hevc_settings.get("preset", "ultrafast")),
    )
    if cache_key in HEVC_ENCODER_PROBE_CACHE:
        return HEVC_ENCODER_PROBE_CACHE[cache_key]

    input_args = [str(ffmpeg_path), "-hide_banner", "-loglevel", "error"]
    if encoder == "hevc_vaapi":
        input_args.extend(
            [
                "-init_hw_device",
                "vaapi=vaapi0:/dev/dri/renderD128",
                "-filter_hw_device",
                "vaapi0",
            ]
        )
    input_args.extend(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=1",
            "-frames:v",
            "1",
        ]
    )

    probe_cmd = input_args + build_hevc_probe_args(hevc_settings) + [
        "-an",
        "-f",
        "null",
        "-",
    ]

    try:
        result = subprocess.run(
            probe_cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        message = (result.stderr or result.stdout or "").strip()
        probe_result = (result.returncode == 0, message)
    except (OSError, subprocess.SubprocessError) as e:
        probe_result = (False, str(e))

    HEVC_ENCODER_PROBE_CACHE[cache_key] = probe_result
    return probe_result


def resolve_hevc_settings_for_recording(
    hevc_settings: Dict[str, Any], ffmpeg_path: Path
) -> Dict[str, Any]:
    if not hevc_settings.get("enable", False):
        return hevc_settings

    active_settings = dict(hevc_settings)
    selected_encoder = str(active_settings.get("encoder", "libx265"))
    encoder_works, probe_message = probe_hevc_encoder(ffmpeg_path, active_settings)
    if encoder_works:
        return active_settings

    logger.warning(
        f"HEVC encoder '{selected_encoder}' is not usable with the current "
        f"FFmpeg/hardware setup: {summarize_probe_error(probe_message)}"
    )

    for fallback_encoder in HEVC_SOFTWARE_FALLBACK_ENCODERS:
        if fallback_encoder == selected_encoder:
            continue
        fallback_settings = dict(active_settings)
        fallback_settings["encoder"] = fallback_encoder
        fallback_works, fallback_message = probe_hevc_encoder(
            ffmpeg_path, fallback_settings
        )
        if fallback_works:
            logger.warning(
                f"Using HEVC encoder '{fallback_encoder}' instead of "
                f"'{selected_encoder}' for this recording."
            )
            return fallback_settings
        logger.warning(
            f"HEVC fallback encoder '{fallback_encoder}' is not usable: "
            f"{summarize_probe_error(fallback_message)}"
        )

    disabled_settings = dict(active_settings)
    disabled_settings["enable"] = False
    logger.warning("No usable HEVC encoder found. Recording without HEVC encoding.")
    return disabled_settings


def build_av1_encoding_args(
    av1_settings: Dict[str, Any], recording_format: str
) -> List[str]:
    encoder = av1_settings.get("encoder", "libsvtav1")
    bitrate = av1_settings.get("bitrate", "2500k")
    max_bitrate = av1_settings.get("max_bitrate", "10000k")
    preset = str(av1_settings.get("preset", "8")).strip()
    bufsize = calculate_bufsize(max_bitrate)

    if encoder == "libaom-av1":
        encoding_args = [
            "-c:v",
            "libaom-av1",
            "-cpu-used",
            numeric_preset(preset, "6"),
            "-b:v",
            bitrate,
            *capped_vbr_args(bitrate, max_bitrate, bufsize),
        ]
    elif encoder == "av1_nvenc":
        encoding_args = [
            "-c:v",
            "av1_nvenc",
            "-preset",
            nvenc_preset(preset),
            "-b:v",
            bitrate,
            "-maxrate",
            max_bitrate,
            "-bufsize",
            bufsize,
            "-rc",
            "vbr",
        ]
    elif encoder == "av1_qsv":
        encoding_args = [
            "-c:v",
            "av1_qsv",
            "-preset",
            preset,
            "-b:v",
            bitrate,
            *capped_vbr_args(bitrate, max_bitrate, bufsize),
        ]
    elif encoder == "av1_amf":
        encoding_args = [
            "-c:v",
            "av1_amf",
            "-usage",
            "transcoding",
            "-rc",
            "vbr_peak",
            "-b:v",
            bitrate,
            *capped_vbr_args(bitrate, max_bitrate, bufsize),
        ]
    elif encoder == "av1_vaapi":
        encoding_args = [
            "-vf",
            "format=nv12,hwupload",
            "-c:v",
            "av1_vaapi",
            "-rc_mode",
            "VBR",
            "-b:v",
            bitrate,
            *capped_vbr_args(bitrate, max_bitrate, bufsize),
        ]
    else:
        encoding_args = [
            "-c:v",
            "libsvtav1",
            "-preset",
            numeric_preset(preset, "8"),
            "-b:v",
            bitrate,
            "-svtav1-params",
            "rc=1",
        ]

    if recording_format == "webm":
        encoding_args.extend(["-c:a", "libopus", "-b:a", "128k"])
    else:
        encoding_args.extend(["-c:a", "copy"])

    return encoding_args


async def record_stream(
    channel: Dict[str, Any],
    headers: Dict[str, str],
    session: aiohttp.ClientSession,
    delay: int,
    timeout: int,
    ffmpeg_path: Path,
    stream_segment_threads: int,
    hevc_settings: Dict[str, Any],
    av1_settings: Dict[str, Any],
    output_format: str,
) -> None:
    channel_name = channel.get("name", "Unknown")
    channel_id = str(channel.get("id", "Unknown"))
    output_format = normalize_output_format(output_format)
    logger.info(f"Attempting to record stream for channel: {channel_name}")
    await asyncio.sleep(delay)

    if channel.get("active", "on") == "off":
        logger.info(f"{channel_name} channel is inactive. Skipping recording.")
        return

    recording_started = False
    temp_output_path: Optional[Path] = None
    final_output_path: Optional[Path] = None
    active_attempt: Optional[RecordingProcessSandbox] = None

    try:
        while not shutdown_event.is_set():
            stream_url = f"https://chzzk.naver.com/live/{channel['id']}"
            if stream_url:
                logger.debug(f"Found stream URL for channel: {channel_name}")
                try:
                    cookies = await get_session_cookies()
                    while not shutdown_event.is_set():
                        cookies = await get_session_cookies()
                        headers = get_auth_headers(cookies)
                        status, live_info = await get_live_info(
                            channel, headers, session
                        )
                        if status == "OPEN":
                            break

                        logger.info(
                            f"Waiting for the channel '{channel_name}' to go live..."
                        )
                        try:
                            await asyncio.wait_for(
                                shutdown_event.wait(), timeout=timeout
                            )
                        except asyncio.TimeoutError:
                            continue

                    if shutdown_event.is_set():
                        break

                    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    live_title = sanitize_filename_component(
                        live_info.get("liveTitle", ""), fallback="untitled"
                    )
                    output_dir = resolve_output_dir(channel.get("output_dir", "."))
                    recording_format = output_format
                    if av1_settings.get("enable") and recording_format == "ts":
                        logger.warning(
                            f"AV1 output is not supported with TS for {channel_name}. Falling back to MKV."
                        )
                        recording_format = "mkv"
                    temp_output_file = shorten_filename(
                        f"[{current_time.replace(':', '_')}] {channel_name} {live_title}.{recording_format}.part"
                    )
                    final_output_file = temp_output_file[:-5]  # Remove '.part'
                    temp_output_path = output_dir / temp_output_file
                    final_output_path = output_dir / final_output_file

                    output_dir.mkdir(parents=True, exist_ok=True)

                    active_attempt = RecordingProcessSandbox(channel_name, channel_id)
                    try:
                        # Start streamlink process
                        streamlink_cmd = [
                            "streamlink",
                            "--stdout",
                            stream_url,
                            "best",
                            "--hls-live-restart",
                            "--plugin-dirs",
                            str(PLUGIN_DIR_PATH),
                            "--stream-segment-threads",
                            str(stream_segment_threads),
                            *streamlink_http_header_args(cookies),
                            "--ffmpeg-ffmpeg",
                            str(ffmpeg_path),
                            "--ffmpeg-copyts",
                            "--hls-segment-stream-data",
                        ]

                        stream_process = await active_attempt.start_streamlink(
                            streamlink_cmd
                        )
                        if stream_process.stdout is None:
                            raise RuntimeError("streamlink stdout pipe was not created")

                        # Start ffmpeg process
                        base_input_args = []
                        encoding_args = []

                        active_av1_settings = resolve_av1_settings_for_recording(
                            av1_settings, ffmpeg_path
                        )
                        enable_av1 = active_av1_settings.get("enable", False)
                        av1_encoder = (
                            active_av1_settings.get("encoder", "libsvtav1")
                            if enable_av1
                            else None
                        )
                        active_hevc_settings = hevc_settings
                        if not enable_av1:
                            active_hevc_settings = resolve_hevc_settings_for_recording(
                                hevc_settings, ffmpeg_path
                            )
                        enable_hevc = (
                            active_hevc_settings.get("enable", False)
                            and not enable_av1
                        )
                        encoder = (
                            active_hevc_settings.get("encoder", "libx265")
                            if enable_hevc
                            else None
                        )

                        # Handle VAAPI initialization before input
                        if (
                            enable_hevc
                            and recording_format != "webm"
                            and encoder == "hevc_vaapi"
                        ) or (enable_av1 and av1_encoder == "av1_vaapi"):
                            # Attempt to use the default render device
                            base_input_args = [
                                str(ffmpeg_path),
                                "-init_hw_device",
                                "vaapi=vaapi0:/dev/dri/renderD128",
                                "-filter_hw_device",
                                "vaapi0",
                                "-i",
                                "pipe:0",
                                "-y",
                            ]
                        else:
                            base_input_args = [str(ffmpeg_path), "-i", "pipe:0", "-y"]

                        metadata_args = [
                            "-map_metadata:s:a",
                            "0:s:a",
                            "-map_metadata:s:v",
                            "0:s:v",
                        ]

                        if enable_av1:
                            encoding_args = build_av1_encoding_args(
                                active_av1_settings, recording_format
                            )
                            encoding_args.extend(metadata_args)
                        elif recording_format == "webm":
                            if enable_hevc:
                                logger.warning(
                                    f"HEVC settings are ignored for WebM output on {channel_name}."
                                )
                            encoding_args = [
                                "-c:v",
                                "libvpx-vp9",
                                "-deadline",
                                "realtime",
                                "-cpu-used",
                                "5",
                                "-b:v",
                                "0",
                                "-crf",
                                "32",
                                "-c:a",
                                "libopus",
                                "-b:a",
                                "128k",
                            ]

                        elif enable_hevc:
                            bitrate = active_hevc_settings.get("bitrate", "2500k")
                            max_bitrate = active_hevc_settings.get(
                                "max_bitrate", "10000k"
                            )
                            preset = active_hevc_settings.get("preset", "ultrafast")

                            try:
                                max_val = int(max_bitrate.lower().replace("k", ""))
                                bufsize = f"{max_val * 2}k"
                            except ValueError:
                                bufsize = "16000k"

                            common_hevc_args = [*metadata_args]
                            if recording_format == "ts":
                                common_hevc_args.extend(
                                    [
                                        "-bsf:a",
                                        "aac_adtstoasc",
                                        "-bsf:v",
                                        "hevc_mp4toannexb",
                                    ]
                                )

                            if encoder == "libx265":
                                x265_params = (
                                    "rc-lookahead=20:b-adapt=2:bframes=3:scenecut=40"
                                )
                                encoding_args = [
                                    "-c:v",
                                    "libx265",
                                    "-preset",
                                    preset,
                                    "-b:v",
                                    bitrate,
                                    "-maxrate",
                                    max_bitrate,
                                    "-bufsize",
                                    bufsize,
                                    "-tune",
                                    "zerolatency",
                                    "-tag:v",
                                    "hvc1",
                                    "-x265-params",
                                    x265_params,
                                    "-c:a",
                                    "copy",
                                ]

                            elif encoder == "hevc_nvenc":
                                nv_preset = "p4"
                                if (
                                    "fast" in preset
                                    or "super" in preset
                                    or "ultra" in preset
                                ):
                                    nv_preset = "p1"
                                elif "slow" in preset:
                                    nv_preset = "p6"
                                elif (
                                    preset.startswith("p")
                                    and len(preset) == 2
                                    and preset[1].isdigit()
                                ):
                                    nv_preset = preset

                                encoding_args = [
                                    "-c:v",
                                    "hevc_nvenc",
                                    "-preset",
                                    nv_preset,
                                    "-b:v",
                                    bitrate,
                                    "-maxrate",
                                    max_bitrate,
                                    "-bufsize",
                                    bufsize,
                                    "-rc",
                                    "vbr",
                                    "-spatial-aq",
                                    "1",
                                    "-tag:v",
                                    "hvc1",
                                    "-c:a",
                                    "copy",
                                ]

                            elif encoder == "hevc_qsv":
                                encoding_args = [
                                    "-c:v",
                                    "hevc_qsv",
                                    "-preset",
                                    preset,
                                    "-b:v",
                                    bitrate,
                                    "-maxrate",
                                    max_bitrate,
                                    "-bufsize",
                                    bufsize,
                                    "-tag:v",
                                    "hvc1",
                                    "-c:a",
                                    "copy",
                                ]

                            elif encoder == "hevc_amf":
                                encoding_args = [
                                    "-c:v",
                                    "hevc_amf",
                                    "-usage",
                                    "transcoding",
                                    "-rc",
                                    "vbr_peak",
                                    "-b:v",
                                    bitrate,
                                    "-maxrate",
                                    max_bitrate,
                                    "-bufsize",
                                    bufsize,
                                    "-tag:v",
                                    "hvc1",
                                    "-c:a",
                                    "copy",
                                ]
                                if "fast" in preset:
                                    encoding_args.extend(["-quality", "speed"])
                                else:
                                    encoding_args.extend(["-quality", "balanced"])

                            elif encoder == "hevc_vaapi":
                                encoding_args = [
                                    "-vf",
                                    "format=nv12,hwupload",
                                    "-c:v",
                                    "hevc_vaapi",
                                    "-b:v",
                                    bitrate,
                                    "-maxrate",
                                    max_bitrate,
                                    "-bufsize",
                                    bufsize,
                                    "-tag:v",
                                    "hvc1",
                                    "-c:a",
                                    "copy",
                                ]

                            elif encoder == "hevc_videotoolbox":
                                encoding_args = [
                                    "-c:v",
                                    "hevc_videotoolbox",
                                    "-allow_sw",
                                    "1",
                                    "-realtime",
                                    "true",
                                    "-b:v",
                                    bitrate,
                                    "-maxrate",
                                    max_bitrate,
                                    "-bufsize",
                                    bufsize,
                                    "-tag:v",
                                    "hvc1",
                                    "-c:a",
                                    "copy",
                                ]

                            else:
                                x265_params = (
                                    "rc-lookahead=20:b-adapt=2:bframes=3:scenecut=40"
                                )
                                encoding_args = [
                                    "-c:v",
                                    "libx265",
                                    "-preset",
                                    preset,
                                    "-b:v",
                                    bitrate,
                                    "-maxrate",
                                    max_bitrate,
                                    "-bufsize",
                                    bufsize,
                                    "-tune",
                                    "zerolatency",
                                    "-tag:v",
                                    "hvc1",
                                    "-x265-params",
                                    x265_params,
                                    "-c:a",
                                    "copy",
                                ]

                            encoding_args.extend(common_hevc_args)

                        else:
                            encoding_args = ["-c", "copy", *metadata_args]
                            if recording_format == "ts":
                                encoding_args.extend(
                                    [
                                        "-bsf:v",
                                        "h264_mp4toannexb",
                                        "-bsf:a",
                                        "aac_adtstoasc",
                                    ]
                                )

                        output_args = ["-progress", "pipe:2"]
                        if recording_format in {"ts", "mkv"}:
                            output_args.append("-copy_unknown")

                        if recording_format == "ts":
                            output_args.extend(
                                [
                                    "-f",
                                    "mpegts",
                                    "-mpegts_flags",
                                    "resend_headers",
                                    "-bsf",
                                    "setts=pts=PTS-STARTPTS",
                                    "-fflags",
                                    "+genpts+discardcorrupt+nobuffer",
                                    "-avioflags",
                                    "direct",
                                    str(temp_output_path),
                                ]
                            )
                        elif recording_format == "mkv":
                            output_args.extend(["-f", "matroska", str(temp_output_path)])
                        elif recording_format == "webm":
                            output_args.extend(["-f", "webm", str(temp_output_path)])

                        ffmpeg_cmd = base_input_args + encoding_args + output_args

                        ffmpeg_process = await active_attempt.start_ffmpeg(ffmpeg_cmd)
                        if ffmpeg_process.stdin is None or ffmpeg_process.stderr is None:
                            raise RuntimeError("ffmpeg pipes were not created")

                        if not recording_started:
                            logger.info(
                                f"Recording started for {channel_name} at {current_time}."
                            )
                            recording_started = True
                            recording_start_time = current_time

                        # Initialize channel progress data
                        async with channel_progress_lock:
                            channel_progress[channel_id] = {
                                "channel_name": channel_name,
                                "bitrate": "N/A",
                                "download_speed": "N/A",
                                "total_size": "N/A",
                                "out_time": "N/A",
                                "recording_start_time": recording_start_time,
                            }

                        pipe_task = active_attempt.create_task(
                            pipe_stream_to_stdin(
                                stream_process.stdout, ffmpeg_process.stdin, channel_name
                            )
                        )
                        stream_stderr_task = active_attempt.create_task(
                            read_log_stream(stream_process.stderr, "streamlink", channel_id)
                        )
                        ffmpeg_stderr_task = active_attempt.create_task(
                            read_stream(ffmpeg_process.stderr, channel_id, "stderr")
                        )
                        ffmpeg_wait_task = active_attempt.create_task(ffmpeg_process.wait())
                        stream_wait_task = active_attempt.create_task(stream_process.wait())
                        shutdown_wait_task = active_attempt.create_task(
                            shutdown_event.wait(), cancel_on_cleanup=True
                        )

                        done, _ = await asyncio.wait(
                            [ffmpeg_wait_task, stream_wait_task, shutdown_wait_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        completed_by = None
                        if shutdown_wait_task in done:
                            completed_by = "shutdown"
                            await terminate_process(ffmpeg_process, "ffmpeg")
                            await terminate_process(stream_process, "streamlink")
                            break

                        if ffmpeg_wait_task in done:
                            completed_by = "ffmpeg"
                            await terminate_process(stream_process, "streamlink")
                        elif stream_wait_task in done:
                            completed_by = "streamlink"
                            try:
                                await asyncio.wait_for(ffmpeg_wait_task, timeout=30)
                            except asyncio.TimeoutError:
                                logger.warning(
                                    f"ffmpeg did not exit after streamlink ended for {channel_name}."
                                )
                                await terminate_process(ffmpeg_process, "ffmpeg")

                        if stream_wait_task and not stream_wait_task.done():
                            await terminate_process(stream_process, "streamlink")
                            await drain_task(stream_wait_task)
                        if ffmpeg_wait_task and not ffmpeg_wait_task.done():
                            await terminate_process(ffmpeg_process, "ffmpeg")
                            await drain_task(ffmpeg_wait_task)

                        ffmpeg_returncode = ffmpeg_process.returncode
                        stream_returncode = stream_process.returncode
                        logger.info(
                            f"ffmpeg process for {channel_name} exited with return code {ffmpeg_returncode}."
                        )
                        logger.info(
                            f"Stream recording process for {channel_name} exited with return code {stream_returncode}."
                        )
                        if ffmpeg_returncode not in (0, None):
                            logger.warning(
                                f"ffmpeg failed for {channel_name}; see the ffmpeg stderr lines above for the root cause."
                            )
                        if stream_returncode not in (0, None) and completed_by != "ffmpeg":
                            logger.warning(
                                f"streamlink failed for {channel_name}; see the streamlink stderr lines above for the root cause."
                            )
                        if recording_started:
                            logger.info(f"Recording stopped for {channel_name}.")
                            recording_started = False

                        # Atomically rename the temporary file to final output
                        if temp_output_path and final_output_path and temp_output_path.exists():
                            if temp_output_path.stat().st_size == 0:
                                temp_output_path.unlink(missing_ok=True)
                                logger.warning(
                                    f"Discarded empty recording file for {channel_name}."
                                )
                            else:
                                destination_path = unique_path(final_output_path)
                                temp_output_path.replace(destination_path)
                                final_output_path = destination_path
                                logger.info(f"Recording saved to {final_output_path}")

                        # Remove progress data
                        async with channel_progress_lock:
                            channel_progress.pop(channel_id, None)

                    finally:
                        if active_attempt is not None:
                            await active_attempt.cleanup()
                            active_attempt = None

                except asyncio.CancelledError:
                    logger.info(f"Recording task for {channel_name} was cancelled.")
                    break
                except Exception as e:
                    logger.exception(
                        f"Error occurred while recording {channel_name}: {e}"
                    )
                    if recording_started:
                        logger.info(f"Recording stopped for {channel_name}.")
                        recording_started = False
                    if active_attempt is not None:
                        await active_attempt.cleanup()
                        active_attempt = None
            else:
                logger.error(f"No stream URL available for {channel_name}")
                if recording_started:
                    logger.info(f"Recording stopped for {channel_name}.")
                    recording_started = False

            # Wait for shutdown event or timeout
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                continue

    finally:
        if active_attempt is not None:
            await active_attempt.cleanup()
        # Attempt to rename any remaining temp files
        if (
            recording_started
            and temp_output_path
            and final_output_path
            and temp_output_path.exists()
        ):
            destination_path = unique_path(final_output_path)
            temp_output_path.replace(destination_path)
            logger.info(f"Recording saved to {destination_path}")
        # Remove progress data
        async with channel_progress_lock:
            channel_progress.pop(channel_id, None)


async def manage_recording_tasks():
    active_tasks: Dict[str, asyncio.Task] = {}
    (
        timeout,
        stream_segment_threads,
        channels,
        delays,
        hevc_settings,
        av1_settings,
        output_format,
    ) = await load_settings()
    cookies = await get_session_cookies()
    headers = get_auth_headers(cookies)
    ffmpeg_path = await setup_paths()

    if not ffmpeg_path or not ffmpeg_path.exists():
        logger.error("ffmpeg executable not found. Exiting.")
        return

    request_timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=request_timeout) as session:
        try:
            while not shutdown_event.is_set():
                (
                    new_timeout,
                    new_stream_segment_threads,
                    new_channels,
                    new_delays,
                    new_hevc_settings,
                    new_av1_settings,
                    new_output_format,
                ) = await load_settings()
                active_channels = 0

                current_channel_ids = {
                    str(channel.get("id")) for channel in new_channels
                }

                # Cancel tasks for removed or deactivated channels
                for channel_id in list(active_tasks.keys()):
                    if channel_id not in current_channel_ids:
                        task = active_tasks.pop(channel_id)
                        task.cancel()
                        logger.info(
                            f"Cancelled recording task for deactivated channel: {channel_id}"
                        )
                        # Remove progress data
                        async with channel_progress_lock:
                            channel_progress.pop(channel_id, None)

                for channel in new_channels:
                    channel_id = str(channel.get("id"))
                    if not channel_id:
                        logger.warning("Channel ID is missing in configuration.")
                        continue
                    if channel_id not in active_tasks:
                        if channel.get("active", "on") == "on":
                            task = asyncio.create_task(
                                record_stream(
                                    channel,
                                    headers,
                                    session,
                                    new_delays.get(channel.get("identifier"), 0),
                                    new_timeout,
                                    ffmpeg_path,
                                    new_stream_segment_threads,
                                    new_hevc_settings,
                                    new_av1_settings,
                                    new_output_format,
                                )
                            )
                            active_tasks[channel_id] = task
                            active_channels += 1
                            logger.info(
                                f"Started recording task for new active channel: {channel.get('name', 'Unknown')}"
                            )
                    else:
                        if channel.get("active", "on") == "off":
                            task = active_tasks.pop(channel_id)
                            task.cancel()
                            logger.info(
                                f"Cancelled recording task for deactivated channel: {channel.get('name', 'Unknown')}"
                            )
                            # Remove progress data
                            async with channel_progress_lock:
                                channel_progress.pop(channel_id, None)
                        else:
                            active_channels += 1

                if active_channels == 0:
                    logger.info("All channels are inactive. No active recordings.")

                # Wait for shutdown event or 10 seconds
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=10)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info("Recording management task was cancelled.")
        finally:
            # Cancel all active recording tasks
            for task in active_tasks.values():
                task.cancel()
            await asyncio.gather(*active_tasks.values(), return_exceptions=True)


def handle_shutdown():
    logger.info("Received shutdown signal. Shutting down...")
    shutdown_event.set()


async def display_progress():
    layout = Layout()

    # Split the layout into upper and lower sections
    layout.split(
        Layout(name="upper", ratio=1),
        Layout(name="lower", ratio=3),
    )

    log_messages = []  # List for log messages

    with Live(layout, console=console, refresh_per_second=5, screen=False):
        while not shutdown_event.is_set() or not log_queue.empty():
            # Update display for channel progress
            channel_panels = []

            async with channel_progress_lock:
                if channel_progress:
                    for progress_data in channel_progress.values():
                        # Create a table for each channel
                        table = Table(show_header=True, header_style="bold magenta")
                        table.add_column("Channel", style="cyan", no_wrap=True)
                        table.add_column("Bitrate")
                        table.add_column("Download Speed")
                        table.add_column("Total Size")
                        table.add_column("Out Time")
                        table.add_column("Start Time")

                        table.add_row(
                            progress_data.get("channel_name", "Unknown"),
                            progress_data.get("bitrate", "N/A"),
                            progress_data.get("download_speed", "N/A"),
                            progress_data.get("total_size", "N/A"),
                            progress_data.get("out_time", "N/A"),
                            progress_data.get("recording_start_time", "N/A"),
                        )

                        # Wrap each channel's table in a panel
                        panel = Panel(
                            table, title=progress_data.get("channel_name", "Unknown")
                        )
                        channel_panels.append(panel)
                else:
                    # Show a message if no channels are recording
                    channel_panels.append(
                        Panel("No active recordings.", title="Recording Progress")
                    )

            # Group all channel panels together
            progress_display = Group(*channel_panels)

            layout["lower"].update(progress_display)

            # Update log messages
            try:
                while True:
                    msg = await asyncio.wait_for(log_queue.get(), timeout=0.1)
                    log_messages.append(msg)
                    # Keep only the last 15 log messages
                    log_messages = log_messages[-15:]
            except (asyncio.QueueEmpty, asyncio.TimeoutError):
                pass

            # Update the log panel
            log_text = Text("\n".join(log_messages))
            layout["upper"].update(Panel(log_text, title="Logs"))

            await asyncio.sleep(0.1)


async def main() -> None:
    # Register signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    if platform.system() != "Windows":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_shutdown)
    else:
        # On Windows, signals are not supported in the event loop.
        # We'll handle KeyboardInterrupt exception instead.
        pass

    display_task = asyncio.create_task(display_progress())

    try:
        await manage_recording_tasks()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt. Shutting down...")
        handle_shutdown()
        # Wait a moment to allow tasks to clean up
        await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Main task was cancelled.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        # Wait for display_progress to process remaining logs
        shutdown_event.set()
        await display_task
        logger.info("Recorder has been shut down.")


if __name__ == "__main__":
    asyncio.run(main())
