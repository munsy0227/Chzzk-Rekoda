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
from urllib.parse import urlparse

import aiofiles
import aiohttp
import orjson

from dns_over_https import install_doh_dns
from i18n import (
    DEFAULT_LANGUAGE,
    format_split_interval as localized_split_interval,
    normalize_language,
    translate,
)

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
DEFAULT_DOH_URL = "https://dns.adguard-dns.com/dns-query"
STREAMLINK_DNS_PATCH_DIR = BASE_DIR / "streamlink_dns_patch"

DEFAULT_RESCAN_INTERVAL_SECONDS = 60
MIN_RESCAN_INTERVAL_SECONDS = 1
MAX_RESCAN_INTERVAL_SECONDS = 3600
DEFAULT_OUTPUT_FORMAT = "ts"
SUPPORTED_OUTPUT_FORMATS = {"ts", "mkv", "webm"}
DEFAULT_RECORDING_SPLIT_MINUTES = 0
MAX_RECORDING_SPLIT_MINUTES = 10080
FFMPEG_FINALIZE_TIMEOUT_SECONDS = 60
RECORDING_SHUTDOWN_TIMEOUT_SECONDS = 90
STREAMLINK_SEGMENT_ATTEMPTS = 6
STREAMLINK_SEGMENT_TIMEOUT_SECONDS = 15
STREAMLINK_PLAYLIST_RELOAD_ATTEMPTS = 6
STREAMLINK_OUTPUT_TIMEOUT_SECONDS = 90
STREAMLINK_RECONNECT_BASE_DELAY_SECONDS = 2
STREAMLINK_RECONNECT_MAX_DELAY_SECONDS = 30
STREAMLINK_STABLE_RECORDING_SECONDS = 60
STREAMLINK_SHUTDOWN_TIMEOUT_SECONDS = 20
ENCODER_PROBE_TESTSRC = "testsrc2=size=640x480:rate=1"
MAX_UI_LOG_MESSAGES = 1000
UI_LOG_HISTORY_SIZE = 15
UI_REFRESH_INTERVAL_SECONDS = 0.2

# Global console instance for Rich
console = Console()

# Shared data structure for channel progress
channel_progress: Dict[str, Dict[str, Any]] = {}
channel_progress_lock = asyncio.Lock()

# Create a queue for log messages
log_queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_UI_LOG_MESSAGES)

# Share the last valid configuration across channel polling tasks.
config_cache_path: Optional[Path] = None
config_cache_signature: Optional[Tuple[int, int, int]] = None
config_cache_value: Dict[str, Any] = {}
config_cache_lock = asyncio.Lock()
config_cache_unavailable = False

# Cache language lookups; the live UI asks for translated labels often.
language_cache_mtime_ns: Optional[int] = None
language_cache_value = DEFAULT_LANGUAGE


# Helper function to load log_enabled
def load_config_sync() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "rb") as f:
                config = orjson.loads(f.read())
                return config if isinstance(config, dict) else {}
        except Exception:
            pass
    return {}


def get_log_enabled() -> bool:
    return bool(load_config_sync().get("log_enabled", True))


def get_language_sync() -> str:
    global language_cache_mtime_ns, language_cache_value

    try:
        mtime_ns = CONFIG_FILE_PATH.stat().st_mtime_ns
    except OSError:
        language_cache_mtime_ns = None
        language_cache_value = DEFAULT_LANGUAGE
        return language_cache_value

    if language_cache_mtime_ns == mtime_ns:
        return language_cache_value

    language_cache_mtime_ns = mtime_ns
    language_cache_value = normalize_language(
        load_config_sync().get("language", DEFAULT_LANGUAGE)
    )
    return language_cache_value


def tr(key: str, **kwargs: Any) -> str:
    return translate(get_language_sync(), key, **kwargs)


def normalize_doh_url(value: Any) -> str:
    text = str(value or DEFAULT_DOH_URL).strip()
    try:
        parsed = urlparse(text)
    except ValueError:
        return DEFAULT_DOH_URL
    if parsed.scheme != "https" or not parsed.hostname:
        return DEFAULT_DOH_URL
    return text


def normalize_dns_settings(value: Any) -> Dict[str, Any]:
    defaults = {"enable": False, "doh_url": DEFAULT_DOH_URL}
    settings = defaults | value if isinstance(value, dict) else defaults
    return {
        "enable": bool(settings.get("enable")),
        "doh_url": normalize_doh_url(settings.get("doh_url")),
    }


def get_dns_settings_sync() -> Dict[str, Any]:
    return normalize_dns_settings(load_config_sync().get("dns_settings"))


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

        print(
            tr(
                "record.logging_toggled",
                state=tr("common.enabled" if new_state else "common.disabled"),
            )
        )
    except Exception as e:
        print(tr("record.logging_toggle_error", error=e))


# Custom logging handler to put log messages into the queue
class QueueHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        try:
            if self.queue.full():
                self.queue.get_nowait()
                self.queue.task_done()
            self.queue.put_nowait(msg)
        except asyncio.QueueFull:
            pass


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


logger = logging.getLogger("Recorder")


def install_internal_dns_resolver() -> None:
    dns_settings = get_dns_settings_sync()
    if not dns_settings["enable"]:
        return

    doh_url = dns_settings["doh_url"]
    try:
        install_doh_dns(url=doh_url)
        logger.info(tr("record.doh_using", url=doh_url))
    except Exception as e:
        logger.warning(tr("record.doh_install_failed", error=e))


# Runtime initialization belongs to main(), so imports have no file/UI effects.

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
HARDWARE_HEVC_ENCODERS = KNOWN_HEVC_ENCODERS - {"libx265"}
HEVC_SOFTWARE_FALLBACK_ENCODERS = ("libx265",)
HEVC_ENCODER_PROBE_CACHE: Dict[Tuple[str, str, str, str, str], Tuple[bool, str]] = {}
HEVC_ENCODER_PROBE_LOCK = asyncio.Lock()
LIBX265_PRESETS = {
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
    "placebo",
}
NVENC_P_LEVEL_PRESETS = {f"p{number}" for number in range(1, 8)}
HEVC_NVENC_PRESETS = NVENC_P_LEVEL_PRESETS | {
    "default",
    "slow",
    "medium",
    "fast",
    "hp",
    "hq",
    "bd",
    "ll",
    "llhq",
    "llhp",
    "lossless",
    "losslesshp",
}
AV1_NVENC_PRESETS = NVENC_P_LEVEL_PRESETS | {
    "default",
    "slow",
    "medium",
    "fast",
}
ALL_NVENC_PRESETS = HEVC_NVENC_PRESETS | AV1_NVENC_PRESETS
QSV_NAMED_PRESETS = {
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
}
QSV_PRESETS = QSV_NAMED_PRESETS | {str(number) for number in range(8)}
HEVC_AMF_PRESETS = {"speed", "balanced", "quality"}
AV1_AMF_PRESETS = {"speed", "balanced", "quality", "high_quality"}
SVT_AV1_PRESETS = {str(number) for number in range(-2, 14)}
LIBAOM_AV1_PRESETS = {str(number) for number in range(9)}
ENCODER_PRESETS = {
    "libx265": LIBX265_PRESETS,
    "hevc_nvenc": HEVC_NVENC_PRESETS,
    "hevc_qsv": QSV_PRESETS,
    "hevc_amf": HEVC_AMF_PRESETS,
    "libsvtav1": SVT_AV1_PRESETS,
    "libaom-av1": LIBAOM_AV1_PRESETS,
    "av1_nvenc": AV1_NVENC_PRESETS,
    "av1_qsv": QSV_PRESETS,
    "av1_amf": AV1_AMF_PRESETS,
}
ENCODER_DEFAULT_PRESETS = {
    "libx265": "ultrafast",
    "hevc_nvenc": "p4",
    "hevc_qsv": "medium",
    "hevc_amf": "balanced",
    "hevc_vaapi": "auto",
    "hevc_videotoolbox": "auto",
    "libsvtav1": "8",
    "libaom-av1": "6",
    "av1_nvenc": "p4",
    "av1_qsv": "medium",
    "av1_amf": "balanced",
    "av1_vaapi": "auto",
}
KNOWN_AV1_ENCODERS = {
    "libsvtav1",
    "libaom-av1",
    "av1_nvenc",
    "av1_qsv",
    "av1_amf",
    "av1_vaapi",
}
HARDWARE_AV1_ENCODERS = KNOWN_AV1_ENCODERS - {"libsvtav1", "libaom-av1"}
AV1_SOFTWARE_FALLBACK_ENCODERS = ("libsvtav1", "libaom-av1")
AV1_ENCODER_PROBE_CACHE: Dict[Tuple[str, str, str, str, str], Tuple[bool, str]] = {}
AV1_ENCODER_PROBE_LOCK = asyncio.Lock()
PLUGIN_DIR_PATH = BASE_DIR / "plugin"

# Max filename length constants
MAX_FILENAME_BYTES = 255
MAX_HASH_LENGTH = 8
RESERVED_BYTES = MAX_HASH_LENGTH + 1  # Hash length and one underscore

# Global variables for graceful shutdown
shutdown_event = asyncio.Event()


def normalize_encoder_preset(encoder: str, value: Any) -> str:
    default = ENCODER_DEFAULT_PRESETS[encoder]
    preset = default if value is None else str(value).strip().lower()
    if not preset:
        preset = default
    options = ENCODER_PRESETS.get(encoder)
    if options is None:
        return default
    if encoder in {"hevc_nvenc", "av1_nvenc"}:
        if preset in {"ultrafast", "superfast", "veryfast", "faster"}:
            return "p1"
        if preset in {"slower", "veryslow"}:
            return "p6"
    if encoder == "hevc_amf" and "fast" in preset:
        return "speed"
    return preset if preset in options else default


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


def streamlink_reconnect_delay(failure_count: int) -> int:
    capped_failure_count = min(max(failure_count, 1), 5)
    delay = STREAMLINK_RECONNECT_BASE_DELAY_SECONDS * (
        2 ** (capped_failure_count - 1)
    )
    return min(delay, STREAMLINK_RECONNECT_MAX_DELAY_SECONDS)


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


def normalize_recording_split_minutes(
    value: Any, legacy_hours: Any = None
) -> int:
    if value is None and legacy_hours is not None:
        legacy_minutes = clamp_int(
            legacy_hours,
            default=DEFAULT_RECORDING_SPLIT_MINUTES,
            min_value=0,
            max_value=MAX_RECORDING_SPLIT_MINUTES // 60,
        ) * 60
        return min(legacy_minutes, MAX_RECORDING_SPLIT_MINUTES)

    return clamp_int(
        value,
        default=DEFAULT_RECORDING_SPLIT_MINUTES,
        min_value=0,
        max_value=MAX_RECORDING_SPLIT_MINUTES,
    )


def format_recording_split_interval(minutes: int) -> str:
    return localized_split_interval(get_language_sync(), minutes)


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
        logger.warning(tr("record.unknown_hevc_encoder", encoder=encoder))
        encoder = defaults["encoder"]
    settings["encoder"] = encoder
    settings["bitrate"] = normalize_bitrate(settings.get("bitrate"), defaults["bitrate"])
    settings["max_bitrate"] = normalize_bitrate(
        settings.get("max_bitrate"), defaults["max_bitrate"]
    )
    settings["preset"] = normalize_encoder_preset(
        encoder, settings.get("preset")
    )
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
        logger.warning(tr("record.unknown_av1_encoder", encoder=encoder))
        encoder = defaults["encoder"]
    settings["encoder"] = encoder
    settings["bitrate"] = normalize_bitrate(settings.get("bitrate"), defaults["bitrate"])
    settings["max_bitrate"] = normalize_bitrate(
        settings.get("max_bitrate"), defaults["max_bitrate"]
    )
    settings["preset"] = normalize_encoder_preset(
        encoder, settings.get("preset")
    )
    return settings


def normalize_channels(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []

    reserved_identifiers = {
        str(channel.get("identifier", "")).strip()
        for channel in value
        if isinstance(channel, dict)
        and SAFE_FFMPEG_VALUE.fullmatch(
            str(channel.get("identifier", "")).strip()
        )
    }
    normalized = []
    seen_channel_ids = set()
    used_identifiers = set()
    for index, raw_channel in enumerate(value, start=1):
        if not isinstance(raw_channel, dict):
            logger.warning(tr("record.skip_invalid_channel_entry", index=index))
            continue

        channel_id = str(raw_channel.get("id", "")).strip()
        if not SAFE_CHANNEL_ID.fullmatch(channel_id):
            logger.warning(tr("record.skip_invalid_channel_id", channel_id=channel_id))
            continue

        if channel_id in seen_channel_ids:
            logger.warning(
                tr("settings.duplicate_channel_skipped", channel_id=channel_id)
            )
            continue
        seen_channel_ids.add(channel_id)

        identifier = str(raw_channel.get("identifier") or f"ch{index}").strip()
        if (
            not SAFE_FFMPEG_VALUE.fullmatch(identifier)
            or identifier in used_identifiers
        ):
            base_identifier = f"ch{index}"
            identifier = base_identifier
            suffix = 2
            while (
                identifier in used_identifiers
                or identifier in reserved_identifiers
            ):
                identifier = f"{base_identifier}_{suffix}"
                suffix += 1
        used_identifiers.add(identifier)

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


def streamlink_subprocess_env() -> Dict[str, str]:
    env = os.environ.copy()
    dns_settings = get_dns_settings_sync()
    if not dns_settings["enable"]:
        return env

    python_paths = [str(STREAMLINK_DNS_PATCH_DIR), str(BASE_DIR)]
    existing_python_path = env.get("PYTHONPATH")
    if existing_python_path:
        python_paths.append(existing_python_path)

    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    env["CHZZK_REKODA_ENABLE_DOH_DNS"] = "1"
    env["CHZZK_REKODA_DOH_DNS_URL"] = dns_settings["doh_url"]
    return env


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
        logger.warning(tr("record.process_timeout_kill", name=name))
        signal_process_group(process, force=True)
        await process.wait()


async def wait_for_task_completion(
    task: Optional[asyncio.Task], name: str, timeout: float
) -> bool:
    if task is None or task.done():
        return True

    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        logger.warning(tr("record.task_timeout", name=name, timeout=timeout))
        return False


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
            env=streamlink_subprocess_env(),
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
        while True:
            chunk = await reader.read(256 * 1024)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    except (BrokenPipeError, ConnectionResetError):
        logger.debug(tr("record.pipe_closed", channel_name=channel_name))
    except Exception as e:
        logger.error(tr("record.pipe_error", channel_name=channel_name, error=e))
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
        logger.info(tr("record.running_windows"))
        bundled_ffmpeg = BASE_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
        if bundled_ffmpeg.exists():
            logger.info(tr("record.using_bundled_ffmpeg", path=bundled_ffmpeg))
            return bundled_ffmpeg

        ffmpeg_on_path = shutil.which("ffmpeg")
        if ffmpeg_on_path:
            ffmpeg_path = Path(ffmpeg_on_path)
            logger.info(tr("record.using_path_ffmpeg", path=ffmpeg_path))
            return ffmpeg_path

        logger.error(tr("record.ffmpeg_not_found_windows"))
    else:
        ffmpeg_on_path = shutil.which("ffmpeg")
        if ffmpeg_on_path:
            ffmpeg_path = Path(ffmpeg_on_path)
            logger.info(tr("record.running_os_ffmpeg_found", os_name=os_name, path=ffmpeg_path))
            return ffmpeg_path

        logger.error(tr("record.ffmpeg_not_found_path"))

    return None


async def load_json_async(file_path: Path) -> Any:
    try:
        async with aiofiles.open(file_path, "rb") as file:
            content = await file.read()
            return orjson.loads(content)
    except FileNotFoundError:
        return None
    except orjson.JSONDecodeError as e:
        logger.error(tr("record.json_decode_error", file_path=file_path, error=e))
        return None
    except Exception as e:
        logger.error(tr("record.json_load_error", file_path=file_path, error=e))
        return None


async def load_config_async() -> Dict[str, Any]:
    global config_cache_path, config_cache_signature, config_cache_value
    global config_cache_unavailable

    async with config_cache_lock:
        if config_cache_path != CONFIG_FILE_PATH:
            config_cache_path = CONFIG_FILE_PATH
            config_cache_signature = None
            config_cache_value = {}
            config_cache_unavailable = False

        try:
            stat = await asyncio.to_thread(CONFIG_FILE_PATH.stat)
            signature = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
        except OSError:
            signature = None

        if signature is not None and signature == config_cache_signature:
            return config_cache_value

        config = (
            await load_json_async(CONFIG_FILE_PATH)
            if signature is not None else None
        )
        if isinstance(config, dict):
            config_cache_value = config
            config_cache_signature = signature
            config_cache_unavailable = False
        else:
            # A partial save or temporarily inaccessible file must not cancel
            # active recordings or drop the authentication cookies.
            if not config_cache_unavailable:
                logger.warning(
                    tr("record.config_reload_kept", file_path=CONFIG_FILE_PATH)
                )
            config_cache_unavailable = True
            config_cache_signature = None
        return config_cache_value


async def load_settings() -> (
    Tuple[
        int,
        int,
        List[Dict[str, Any]],
        Dict[str, int],
        Dict[str, Any],
        Dict[str, Any],
        str,
        int,
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
    recording_split_minutes = normalize_recording_split_minutes(
        config.get("recording_split_minutes"),
        config.get("recording_split_hours"),
    )

    return (
        timeout,
        stream_segment_threads,
        channels,
        delays,
        hevc_settings,
        av1_settings,
        output_format,
        recording_split_minutes,
    )


def cookie_header_from(cookies: Dict[str, str]) -> str:
    nid_aut = sanitize_cookie_value(cookies.get("NID_AUT", ""))
    nid_ses = sanitize_cookie_value(cookies.get("NID_SES", ""))
    return f"NID_AUT={nid_aut}; NID_SES={nid_ses}"


def has_auth_cookies(cookies: Dict[str, str]) -> bool:
    return all(
        sanitize_cookie_value(cookies.get(name, ""))
        for name in ("NID_AUT", "NID_SES")
    )


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
    channel: Dict[str, Any],
    headers: Dict[str, str],
    cookies: Dict[str, str],
    session: aiohttp.ClientSession,
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
            is_member_only = (
                content.get("membershipBenefitType") == "MEMBER_ONLY"
            )
            if (
                status == "OPEN"
                and is_member_only
                and not has_auth_cookies(cookies)
            ):
                logger.warning(
                    tr(
                        "record.member_only_cookies_required",
                        channel_name=channel.get("name", tr("common.unknown")),
                    )
                )
                return "MEMBER_ONLY_AUTH_REQUIRED", {}
            if (
                status == "OPEN"
                and is_member_only
                and content.get("livePlaybackJson") is None
            ):
                logger.warning(
                    tr(
                        "record.member_only_access_required",
                        channel_name=channel.get("name", tr("common.unknown")),
                    )
                )
                return "MEMBER_ONLY_ACCESS_REQUIRED", {}
            if status == "CLOSE":
                logger.info(
                    tr("record.channel_not_live", channel_name=channel.get("name", tr("common.unknown")))
                )
            if status == "BLOCK":
                logger.info(
                    tr("record.channel_blocked", channel_name=channel.get("name", tr("common.unknown")))
                )
                return status, {}
            return status, content
    except aiohttp.ClientError as e:
        logger.error(
            tr("record.http_live_info_error", channel_name=channel.get("name", tr("common.unknown")), error=e)
        )
    except Exception as e:
        logger.error(
            tr("record.live_info_failed", channel_name=channel.get("name", tr("common.unknown")), error=e)
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
            tr("record.filename_too_long", filename=filename, shortened=shortened_filename)
        )
        return shortened_filename

    return filename


def unique_recording_paths(
    output_dir: Path, base_name: str, extension: str
) -> Tuple[Path, Path]:
    for index in range(1000):
        candidate_base = base_name if index == 0 else f"{base_name}_{index}"
        temp_name = shorten_filename(f"{candidate_base}.{extension}.part")
        final_name = temp_name[: -len(".part")]
        temp_path = output_dir / temp_name
        final_path = output_dir / final_name
        try:
            with temp_path.open("xb"):
                pass
        except FileExistsError:
            continue
        if final_path.exists():
            temp_path.unlink(missing_ok=True)
            continue
        return temp_path, final_path

    raise FileExistsError(base_name)


def shorten_segment_template(base_name: str, extension: str) -> str:
    suffix = f"_%03d.{extension}"
    filename = f"{base_name}{suffix}"
    filename_bytes = filename.encode("utf-8")
    if len(filename_bytes) <= MAX_FILENAME_BYTES:
        return filename

    hash_value = hashlib.sha256(filename_bytes).hexdigest()[:MAX_HASH_LENGTH]
    max_name_length = MAX_FILENAME_BYTES - (
        len(suffix.encode("utf-8")) + MAX_HASH_LENGTH + 1
    )
    shortened_name_bytes = base_name.encode("utf-8")[:max_name_length]
    shortened_name = shortened_name_bytes.decode("utf-8", "ignore").strip(" .")
    if not shortened_name:
        shortened_name = "recording"
    shortened_filename = f"{shortened_name}_{hash_value}{suffix}"
    logger.warning(
        tr(
            "record.segment_template_too_long",
            filename=filename,
            shortened=shortened_filename,
        )
    )
    return shortened_filename


def segment_template_regex(template_name: str) -> re.Pattern:
    prefix, _, suffix = template_name.rpartition("%03d")
    pattern = re.escape(prefix) + r"(?P<index>\d+)" + re.escape(suffix)
    return re.compile(f"^{pattern}$")


def segment_filename(template_name: str, index: int) -> str:
    prefix, _, suffix = template_name.rpartition("%03d")
    return f"{prefix}{index:03d}{suffix}"


def segment_output_files(output_dir: Path, template_name: str) -> List[Path]:
    if not output_dir.exists():
        return []

    pattern = segment_template_regex(template_name)

    def sort_key(path: Path) -> int:
        match = pattern.match(path.name)
        if not match:
            return 0
        return int(match.group("index"))

    return sorted(
        (path for path in output_dir.iterdir() if pattern.match(path.name)),
        key=sort_key,
    )


def unique_segment_template(
    output_dir: Path, base_name: str, extension: str
) -> Tuple[Path, str]:
    for index in range(1000):
        candidate_base = base_name if index == 0 else f"{base_name}_{index}"
        template_name = shorten_segment_template(candidate_base, extension)
        first_segment = output_dir / segment_filename(template_name, 1)
        try:
            with first_segment.open("xb"):
                pass
        except FileExistsError:
            continue

        existing_segments = segment_output_files(output_dir, template_name)
        if existing_segments != [first_segment]:
            first_segment.unlink(missing_ok=True)
            continue
        return output_dir / template_name, template_name
    raise FileExistsError(base_name)


def build_output_args(
    recording_format: str, output_path: Path, split_seconds: int = 0
) -> List[str]:
    output_args = ["-progress", "pipe:2"]
    if recording_format in {"ts", "mkv"}:
        output_args.append("-copy_unknown")

    if split_seconds > 0:
        segment_format = {
            "ts": "mpegts",
            "mkv": "matroska",
            "webm": "webm",
        }[recording_format]
        output_args.extend(
            [
                "-f",
                "segment",
                "-segment_time",
                str(split_seconds),
                "-segment_start_number",
                "1",
                "-reset_timestamps",
                "1",
                "-segment_format",
                segment_format,
            ]
        )
        if recording_format == "ts":
            output_args.extend(
                [
                    "-segment_format_options",
                    "mpegts_flags=resend_headers:mpegts_copyts=0",
                ]
            )
        # Only the final placeholder belongs to the segment muxer. Percent
        # signs in the directory, channel name, or title are literal text.
        prefix, placeholder, suffix = str(output_path).rpartition("%03d")
        output_args.append(
            prefix.replace("%", "%%") + placeholder + suffix.replace("%", "%%")
        )
        return output_args

    if recording_format == "ts":
        output_args.extend(
            [
                "-f",
                "mpegts",
                "-mpegts_flags",
                "resend_headers",
                "-mpegts_copyts",
                "0",
                "-avoid_negative_ts",
                "make_zero",
                "-muxpreload",
                "0",
                "-muxdelay",
                "0",
                "-avioflags",
                "direct",
                str(output_path),
            ]
        )
    elif recording_format == "mkv":
        output_args.extend(["-f", "matroska", str(output_path)])
    elif recording_format == "webm":
        output_args.extend(["-f", "webm", str(output_path)])

    return output_args


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
) -> str:
    summary: Dict[str, str] = {}
    speed_samples = collections.deque(maxlen=5)
    diagnostics = collections.deque(maxlen=200)

    prev_total_size = None
    prev_time = None

    while not stream.at_eof():
        try:
            line = await stream.readline()
            if not line:
                break
            line_str = line.decode(errors="replace").strip()
            if line_str:
                diagnostics.append(line_str[:1000])

            # Add log
            logger.debug(f"ffmpeg {stream_type} [{channel_id}]: {line_str}")

            if "=" not in line_str:
                continue

            key, value = line_str.split("=", 1)
            key = key.strip()
            if key not in {"total_size", "out_time", "progress"}:
                continue
            summary[key] = value.strip()

            if key == "progress":
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
                current_time = time.monotonic()
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
            logger.error(tr("record.read_stream_error", channel_id=channel_id, error=e))
            break

    return "\n".join(diagnostics)


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
    text = default if value is None else str(value).strip()
    if not text:
        return default
    is_integer = text.isdigit() or (
        text.startswith("-") and text[1:].isdigit()
    )
    return text if is_integer else default


def nvenc_preset(value: Any, default: str = "p4") -> str:
    text = default if value is None else str(value).strip().lower()
    if text in ALL_NVENC_PRESETS:
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


ENCODER_BACKEND_MARKERS = {
    "hevc_nvenc": ("hevc_nvenc", "nvenc", "cuda", "nvidia"),
    "av1_nvenc": ("av1_nvenc", "nvenc", "cuda", "nvidia"),
    "hevc_qsv": ("hevc_qsv", "qsv", "mfx", "quick sync"),
    "av1_qsv": ("av1_qsv", "qsv", "mfx", "quick sync"),
    "hevc_amf": ("hevc_amf", "amf"),
    "av1_amf": ("av1_amf", "amf"),
    "hevc_vaapi": ("hevc_vaapi", "vaapi", "/dev/dri", "va display"),
    "av1_vaapi": ("av1_vaapi", "vaapi", "/dev/dri", "va display"),
    "hevc_videotoolbox": ("hevc_videotoolbox", "videotoolbox"),
}
ENCODER_FAILURE_MARKERS = (
    "cannot",
    "could not",
    "does not support",
    "error",
    "failed",
    "failure",
    "no capable",
    "no device",
    "no nvenc",
    "no va",
    "not available",
    "not found",
    "too many concurrent",
    "unable",
    "unsupported",
)
NON_ENCODER_FAILURE_MARKERS = (
    "broken pipe",
    "could not write header",
    "error opening output",
    "error writing trailer",
    "muxer",
    "no space left on device",
    "permission denied",
    "read-only file system",
)


def runtime_encoder_failure_diagnostic(
    message: str, encoder: Optional[str]
) -> Optional[str]:
    if encoder not in HARDWARE_HEVC_ENCODERS | HARDWARE_AV1_ENCODERS:
        return None

    backend_markers = ENCODER_BACKEND_MARKERS.get(encoder, (encoder,))
    for line in message.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in NON_ENCODER_FAILURE_MARKERS):
            continue
        if (
            any(marker in lowered for marker in backend_markers)
            and any(marker in lowered for marker in ENCODER_FAILURE_MARKERS)
        ):
            return line.strip()[:300]
    return None


def latest_progress_time(message: str) -> float:
    latest = 0.0
    for line in message.splitlines():
        if line.startswith("out_time="):
            latest = max(latest, parse_time(line.partition("=")[2]))
    return latest


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
            ENCODER_PROBE_TESTSRC,
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


async def probe_av1_encoder_nonblocking(
    ffmpeg_path: Path, av1_settings: Dict[str, Any]
) -> Tuple[bool, str]:
    async with AV1_ENCODER_PROBE_LOCK:
        probe_task = asyncio.create_task(
            asyncio.to_thread(
                probe_av1_encoder, ffmpeg_path, av1_settings
            )
        )
        try:
            return await asyncio.shield(probe_task)
        except asyncio.CancelledError:
            await asyncio.shield(probe_task)
            raise


async def resolve_av1_settings_for_recording(
    av1_settings: Dict[str, Any],
    ffmpeg_path: Path,
    runtime_failures: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    if not av1_settings.get("enable", False):
        return av1_settings

    active_settings = dict(av1_settings)
    selected_encoder = str(active_settings.get("encoder", "libsvtav1"))
    runtime_failures = runtime_failures or {}
    if selected_encoder in runtime_failures:
        encoder_works = False
        probe_message = runtime_failures[selected_encoder]
    else:
        encoder_works, probe_message = await probe_av1_encoder_nonblocking(
            ffmpeg_path, active_settings
        )
    if encoder_works:
        return active_settings

    logger.warning(
        tr(
            "record.av1_unusable",
            encoder=selected_encoder,
            message=summarize_probe_error(probe_message),
        )
    )

    for fallback_encoder in AV1_SOFTWARE_FALLBACK_ENCODERS:
        if fallback_encoder == selected_encoder:
            continue
        fallback_settings = dict(active_settings)
        fallback_settings["encoder"] = fallback_encoder
        fallback_settings["preset"] = ENCODER_DEFAULT_PRESETS[
            fallback_encoder
        ]
        fallback_works, fallback_message = await probe_av1_encoder_nonblocking(
            ffmpeg_path, fallback_settings
        )
        if fallback_works:
            logger.warning(
                tr(
                    "record.av1_fallback",
                    fallback=fallback_encoder,
                    selected=selected_encoder,
                )
            )
            return fallback_settings
        logger.warning(
            tr(
                "record.av1_fallback_unusable",
                encoder=fallback_encoder,
                message=summarize_probe_error(fallback_message),
            )
        )

    disabled_settings = dict(active_settings)
    disabled_settings["enable"] = False
    logger.warning(tr("record.av1_no_encoder"))
    return disabled_settings


def build_hevc_probe_args(hevc_settings: Dict[str, Any]) -> List[str]:
    encoder = hevc_settings.get("encoder", "libx265")
    bitrate = hevc_settings.get("bitrate", "2500k")
    max_bitrate = hevc_settings.get("max_bitrate", "10000k")
    preset = str(hevc_settings.get("preset", "ultrafast")).strip()
    bufsize = calculate_bufsize(max_bitrate)
    if encoder == "libx265" and preset not in LIBX265_PRESETS:
        preset = "ultrafast"

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
            "-quality",
            preset,
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
            ENCODER_PROBE_TESTSRC,
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


async def probe_hevc_encoder_nonblocking(
    ffmpeg_path: Path, hevc_settings: Dict[str, Any]
) -> Tuple[bool, str]:
    async with HEVC_ENCODER_PROBE_LOCK:
        probe_task = asyncio.create_task(
            asyncio.to_thread(
                probe_hevc_encoder, ffmpeg_path, hevc_settings
            )
        )
        try:
            return await asyncio.shield(probe_task)
        except asyncio.CancelledError:
            await asyncio.shield(probe_task)
            raise


async def resolve_hevc_settings_for_recording(
    hevc_settings: Dict[str, Any],
    ffmpeg_path: Path,
    runtime_failures: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    if not hevc_settings.get("enable", False):
        return hevc_settings

    active_settings = dict(hevc_settings)
    selected_encoder = str(active_settings.get("encoder", "libx265"))
    runtime_failures = runtime_failures or {}
    if selected_encoder in runtime_failures:
        encoder_works = False
        probe_message = runtime_failures[selected_encoder]
    else:
        encoder_works, probe_message = await probe_hevc_encoder_nonblocking(
            ffmpeg_path, active_settings
        )
    if encoder_works:
        return active_settings

    logger.warning(
        tr(
            "record.hevc_unusable",
            encoder=selected_encoder,
            message=summarize_probe_error(probe_message),
        )
    )

    for fallback_encoder in HEVC_SOFTWARE_FALLBACK_ENCODERS:
        if fallback_encoder == selected_encoder:
            continue
        fallback_settings = dict(active_settings)
        fallback_settings["encoder"] = fallback_encoder
        if fallback_encoder == "libx265":
            fallback_preset = str(fallback_settings.get("preset", ""))
            if fallback_preset not in LIBX265_PRESETS:
                fallback_settings["preset"] = "ultrafast"
        fallback_works, fallback_message = await probe_hevc_encoder_nonblocking(
            ffmpeg_path, fallback_settings
        )
        if fallback_works:
            logger.warning(
                tr(
                    "record.hevc_fallback",
                    fallback=fallback_encoder,
                    selected=selected_encoder,
                )
            )
            return fallback_settings
        logger.warning(
            tr(
                "record.hevc_fallback_unusable",
                encoder=fallback_encoder,
                message=summarize_probe_error(fallback_message),
            )
        )

    disabled_settings = dict(active_settings)
    disabled_settings["enable"] = False
    logger.warning(tr("record.hevc_no_encoder"))
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
            "-quality",
            preset,
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
    recording_split_minutes: int,
) -> None:
    channel_name = channel.get("name", "Unknown")
    channel_id = str(channel.get("id", "Unknown"))
    output_format = normalize_output_format(output_format)
    recording_split_minutes = normalize_recording_split_minutes(recording_split_minutes)
    split_seconds = recording_split_minutes * 60
    logger.info(tr("record.attempting_channel", channel_name=channel_name))
    if delay > 0:
        try:
            await asyncio.wait_for(
                shutdown_event.wait(), timeout=delay
            )
            return
        except asyncio.TimeoutError:
            pass

    if channel.get("active", "on") == "off":
        logger.info(tr("record.channel_inactive", channel_name=channel_name))
        return

    recording_started = False
    temp_output_path: Optional[Path] = None
    final_output_path: Optional[Path] = None
    segment_output_template: Optional[str] = None
    active_attempt: Optional[RecordingProcessSandbox] = None
    runtime_av1_failures: Dict[str, str] = {}
    runtime_hevc_failures: Dict[str, str] = {}
    consecutive_streamlink_failures = 0

    try:
        while not shutdown_event.is_set():
            stream_url = f"https://chzzk.naver.com/live/{channel['id']}"
            if stream_url:
                logger.debug(f"Found stream URL for channel: {channel_name}")
                try:
                    while not shutdown_event.is_set():
                        cookies = await get_session_cookies()
                        headers = get_auth_headers(cookies)
                        status, live_info = await get_live_info(
                            channel, headers, cookies, session
                        )
                        if status == "OPEN":
                            break
                        if status == "CLOSE":
                            runtime_av1_failures.clear()
                            runtime_hevc_failures.clear()

                        logger.info(
                            tr("record.waiting_live", channel_name=channel_name)
                        )
                        try:
                            await asyncio.wait_for(
                                shutdown_event.wait(), timeout=timeout
                            )
                        except asyncio.TimeoutError:
                            continue

                    if shutdown_event.is_set():
                        break

                    active_av1_settings = (
                        await resolve_av1_settings_for_recording(
                            av1_settings,
                            ffmpeg_path,
                            runtime_av1_failures,
                        )
                    )
                    enable_av1 = active_av1_settings.get("enable", False)
                    av1_encoder = (
                        active_av1_settings.get("encoder", "libsvtav1")
                        if enable_av1
                        else None
                    )
                    active_hevc_settings = hevc_settings
                    if not enable_av1 and output_format != "webm":
                        active_hevc_settings = (
                            await resolve_hevc_settings_for_recording(
                                hevc_settings,
                                ffmpeg_path,
                                runtime_hevc_failures,
                            )
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

                    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    live_title = sanitize_filename_component(
                        live_info.get("liveTitle", ""), fallback="untitled"
                    )
                    output_dir = resolve_output_dir(channel.get("output_dir", "."))
                    recording_format = output_format
                    if enable_av1 and recording_format == "ts":
                        logger.warning(
                            tr("record.av1_ts_fallback", channel_name=channel_name)
                        )
                        recording_format = "mkv"
                    safe_current_time = current_time.replace(":", "_")
                    base_output_name = (
                        f"[{safe_current_time}] {channel_name} {live_title}"
                    )
                    output_dir.mkdir(parents=True, exist_ok=True)
                    segment_output_template = None
                    reserved_output_path: Optional[Path] = None
                    if split_seconds > 0:
                        segment_output_path, segment_output_template = (
                            unique_segment_template(
                                output_dir, base_output_name, recording_format
                            )
                        )
                        reserved_output_path = output_dir / (
                            segment_filename(segment_output_template, 1)
                        )
                        temp_output_path = None
                        final_output_path = None
                        logger.info(
                            tr(
                                "record.split_enabled",
                                channel_name=channel_name,
                                interval=format_recording_split_interval(
                                    recording_split_minutes
                                ),
                            )
                        )
                    else:
                        temp_output_path, final_output_path = (
                            unique_recording_paths(
                                output_dir, base_output_name, recording_format
                            )
                        )
                        reserved_output_path = temp_output_path

                    active_attempt = RecordingProcessSandbox(channel_name, channel_id)
                    streamlink_retry_delay: Optional[int] = None
                    attempt_started_at = time.monotonic()
                    try:
                        # Start streamlink process
                        streamlink_cmd = [
                            "streamlink",
                            "--stdout",
                            stream_url,
                            "best",
                            "--hls-live-restart",
                            "--stream-segment-attempts",
                            str(STREAMLINK_SEGMENT_ATTEMPTS),
                            "--stream-segment-timeout",
                            str(STREAMLINK_SEGMENT_TIMEOUT_SECONDS),
                            "--hls-playlist-reload-attempts",
                            str(STREAMLINK_PLAYLIST_RELOAD_ATTEMPTS),
                            "--stream-timeout",
                            str(STREAMLINK_OUTPUT_TIMEOUT_SECONDS),
                            "--plugin-dirs",
                            str(PLUGIN_DIR_PATH),
                            "--stream-segment-threads",
                            str(stream_segment_threads),
                            *streamlink_http_header_args(cookies),
                            "--ffmpeg-ffmpeg",
                            str(ffmpeg_path),
                            "--ffmpeg-copyts",
                            "--ffmpeg-start-at-zero",
                            # Keep segment streaming disabled so Streamlink can
                            # retry a timed-out download before forwarding any
                            # partial HLS data to ffmpeg.
                        ]

                        stream_process = await active_attempt.start_streamlink(
                            streamlink_cmd
                        )
                        if stream_process.stdout is None:
                            raise RuntimeError("streamlink stdout pipe was not created")

                        # Start ffmpeg process
                        base_input_args = []
                        encoding_args = []

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
                                "-fflags",
                                "+genpts+discardcorrupt",
                                "-i",
                                "pipe:0",
                                "-y",
                            ]
                        else:
                            base_input_args = [
                                str(ffmpeg_path),
                                "-fflags",
                                "+genpts+discardcorrupt",
                                "-i",
                                "pipe:0",
                                "-y",
                            ]

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
                                    tr("record.hevc_ignored_webm", channel_name=channel_name)
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

                            bufsize = calculate_bufsize(max_bitrate)

                            common_hevc_args = [*metadata_args]
                            if recording_format == "ts":
                                common_hevc_args.extend(
                                    [
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
                                encoding_args = [
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
                                    "-quality",
                                    preset,
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
                                    ]
                                )

                        output_path = (
                            segment_output_path
                            if split_seconds > 0
                            else temp_output_path
                        )
                        if output_path is None:
                            raise RuntimeError("recording output path was not created")
                        output_args = build_output_args(
                            recording_format, output_path, split_seconds
                        )

                        ffmpeg_cmd = base_input_args + encoding_args + output_args

                        ffmpeg_process = await active_attempt.start_ffmpeg(ffmpeg_cmd)
                        if ffmpeg_process.stdin is None or ffmpeg_process.stderr is None:
                            raise RuntimeError("ffmpeg pipes were not created")

                        if not recording_started:
                            logger.info(
                                tr("record.recording_started", channel_name=channel_name, current_time=current_time)
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
                                "output_path": str(temp_output_path or ""),
                                "output_dir": str(output_dir),
                                "segment_template": segment_output_template,
                                "split_seconds": split_seconds,
                                "title": live_title,
                            }

                        pipe_task = active_attempt.create_task(
                            pipe_stream_to_stdin(
                                stream_process.stdout, ffmpeg_process.stdin, channel_name
                            )
                        )
                        active_attempt.create_task(
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

                        task_cancelled = False
                        try:
                            done, _ = await asyncio.wait(
                                [
                                    ffmpeg_wait_task,
                                    stream_wait_task,
                                    shutdown_wait_task,
                                ],
                                return_when=asyncio.FIRST_COMPLETED,
                            )
                        except asyncio.CancelledError:
                            task_cancelled = True
                            done = set()
                            logger.info(
                                tr(
                                    "record.task_cancelled",
                                    channel_name=channel_name,
                                )
                            )

                        completed_by = None
                        stop_after_attempt = False
                        stream_was_running = not stream_wait_task.done()
                        if task_cancelled or shutdown_wait_task in done:
                            completed_by = (
                                "cancelled" if task_cancelled else "shutdown"
                            )
                            stop_after_attempt = True
                            await terminate_process(
                                stream_process,
                                "streamlink",
                                timeout=STREAMLINK_SHUTDOWN_TIMEOUT_SECONDS,
                            )
                            await drain_task(pipe_task, timeout=10)
                            if not await wait_for_task_completion(
                                ffmpeg_wait_task,
                                f"ffmpeg finalize for {channel_name}",
                                FFMPEG_FINALIZE_TIMEOUT_SECONDS,
                            ):
                                await terminate_process(ffmpeg_process, "ffmpeg")

                        elif ffmpeg_wait_task in done:
                            completed_by = "ffmpeg"
                            await terminate_process(stream_process, "streamlink")
                        elif stream_wait_task in done:
                            completed_by = "streamlink"
                            if not await wait_for_task_completion(
                                ffmpeg_wait_task,
                                f"ffmpeg after streamlink ended for {channel_name}",
                                FFMPEG_FINALIZE_TIMEOUT_SECONDS,
                            ):
                                await terminate_process(ffmpeg_process, "ffmpeg")

                        if stream_wait_task and not stream_wait_task.done():
                            await terminate_process(stream_process, "streamlink")
                            await drain_task(stream_wait_task)
                        if ffmpeg_wait_task and not ffmpeg_wait_task.done():
                            await terminate_process(ffmpeg_process, "ffmpeg")
                            await drain_task(ffmpeg_wait_task)

                        await drain_task(ffmpeg_stderr_task)
                        ffmpeg_diagnostics = ""
                        if (
                            ffmpeg_stderr_task.done()
                            and not ffmpeg_stderr_task.cancelled()
                        ):
                            ffmpeg_diagnostics = ffmpeg_stderr_task.result()

                        ffmpeg_returncode = ffmpeg_process.returncode
                        stream_returncode = stream_process.returncode
                        if (
                            completed_by == "streamlink"
                            and stream_returncode not in (0, None)
                            and not shutdown_event.is_set()
                        ):
                            attempt_duration = time.monotonic() - attempt_started_at
                            if attempt_duration >= STREAMLINK_STABLE_RECORDING_SECONDS:
                                consecutive_streamlink_failures = 0
                            consecutive_streamlink_failures += 1
                            streamlink_retry_delay = streamlink_reconnect_delay(
                                consecutive_streamlink_failures
                            )
                        elif completed_by != "shutdown":
                            consecutive_streamlink_failures = 0

                        retry_with_software = False
                        if (
                            ffmpeg_returncode not in (0, None)
                            and completed_by == "ffmpeg"
                            and stream_was_running
                        ):
                            runtime_failure = (
                                runtime_encoder_failure_diagnostic(
                                    ffmpeg_diagnostics,
                                    av1_encoder if enable_av1 else encoder,
                                )
                            )
                            if runtime_failure and enable_av1 and av1_encoder:
                                runtime_av1_failures[av1_encoder] = runtime_failure
                            elif runtime_failure and enable_hevc and encoder:
                                runtime_hevc_failures[encoder] = runtime_failure

                            retry_with_software = (
                                runtime_failure is not None
                                and latest_progress_time(ffmpeg_diagnostics) <= 5
                            )

                        logger.info(
                            tr("record.ffmpeg_exited", channel_name=channel_name, returncode=ffmpeg_returncode)
                        )
                        logger.info(
                            tr("record.stream_process_exited", channel_name=channel_name, returncode=stream_returncode)
                        )
                        if ffmpeg_returncode not in (0, None):
                            logger.warning(
                                tr("record.ffmpeg_failed", channel_name=channel_name)
                            )
                        if (
                            stream_returncode not in (0, None)
                            and completed_by not in {"cancelled", "ffmpeg", "shutdown"}
                        ):
                            logger.warning(
                                tr("record.streamlink_failed", channel_name=channel_name)
                            )
                        if recording_started:
                            logger.info(tr("record.recording_stopped", channel_name=channel_name))
                            recording_started = False

                        if split_seconds > 0 and segment_output_template:
                            segment_paths = segment_output_files(
                                output_dir, segment_output_template
                            )
                            saved_segments = []
                            for segment_path in segment_paths:
                                if segment_path.stat().st_size == 0:
                                    segment_path.unlink(missing_ok=True)
                                    logger.warning(
                                        tr(
                                            "record.empty_segment_discarded",
                                            channel_name=channel_name,
                                            path=segment_path,
                                        )
                                    )
                                else:
                                    saved_segments.append(segment_path)

                            if not saved_segments:
                                logger.warning(
                                    tr("record.no_segments", channel_name=channel_name)
                                )
                            elif ffmpeg_returncode != 0:
                                logger.warning(
                                    tr(
                                        "record.split_left_incomplete",
                                        output_dir=output_dir,
                                        returncode=ffmpeg_returncode,
                                    )
                                )

                            for segment_path in saved_segments:
                                logger.info(
                                    tr("record.segment_saved", path=segment_path)
                                )

                        # Atomically rename the temporary file to final output
                        elif (
                            temp_output_path
                            and final_output_path
                            and temp_output_path.exists()
                        ):
                            if temp_output_path.stat().st_size == 0:
                                temp_output_path.unlink(missing_ok=True)
                                logger.warning(
                                    tr("record.empty_file_discarded", channel_name=channel_name)
                                )
                            elif ffmpeg_returncode != 0:
                                logger.warning(
                                    tr(
                                        "record.incomplete_file_left",
                                        path=temp_output_path,
                                        returncode=ffmpeg_returncode,
                                    )
                                )
                            else:
                                destination_path = unique_path(final_output_path)
                                temp_output_path.replace(destination_path)
                                final_output_path = destination_path
                                logger.info(tr("record.saved", path=final_output_path))

                        # Remove progress data
                        async with channel_progress_lock:
                            channel_progress.pop(channel_id, None)

                        if stop_after_attempt:
                            break
                        if retry_with_software:
                            try:
                                await asyncio.wait_for(
                                    shutdown_event.wait(), timeout=1
                                )
                                break
                            except asyncio.TimeoutError:
                                continue

                    finally:
                        try:
                            if active_attempt is not None:
                                await active_attempt.cleanup()
                        finally:
                            active_attempt = None
                            if reserved_output_path is not None:
                                with contextlib.suppress(OSError):
                                    if reserved_output_path.stat().st_size == 0:
                                        reserved_output_path.unlink()

                    if streamlink_retry_delay is not None:
                        logger.info(
                            tr(
                                "record.streamlink_reconnect",
                                channel_name=channel_name,
                                delay=streamlink_retry_delay,
                                attempt=consecutive_streamlink_failures,
                            )
                        )
                        try:
                            await asyncio.wait_for(
                                shutdown_event.wait(),
                                timeout=streamlink_retry_delay,
                            )
                            break
                        except asyncio.TimeoutError:
                            continue

                except asyncio.CancelledError:
                    logger.info(tr("record.task_cancelled", channel_name=channel_name))
                    if recording_started:
                        logger.info(tr("record.recording_stopped", channel_name=channel_name))
                        recording_started = False
                    break
                except Exception as e:
                    logger.exception(
                        tr("record.recording_error", channel_name=channel_name, error=e)
                    )
                    if recording_started:
                        logger.info(tr("record.recording_stopped", channel_name=channel_name))
                        recording_started = False
                    if active_attempt is not None:
                        await active_attempt.cleanup()
                        active_attempt = None
            else:
                logger.error(tr("record.no_stream_url", channel_name=channel_name))
                if recording_started:
                    logger.info(tr("record.recording_stopped", channel_name=channel_name))
                    recording_started = False

            # Wait for shutdown event or timeout
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                continue

    finally:
        if active_attempt is not None:
            await active_attempt.cleanup()
        if recording_started and temp_output_path and temp_output_path.exists():
            logger.warning(
                tr("record.unfinished_file_left", path=temp_output_path)
            )
        # Remove progress data
        async with channel_progress_lock:
            channel_progress.pop(channel_id, None)


async def manage_recording_tasks():
    active_tasks: Dict[str, asyncio.Task] = {}
    cookies = await get_session_cookies()
    headers = get_auth_headers(cookies)
    ffmpeg_path = await setup_paths()

    if not ffmpeg_path or not ffmpeg_path.exists():
        logger.error(tr("record.ffmpeg_executable_missing"))
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
                    new_recording_split_minutes,
                ) = await load_settings()
                active_channels = 0
                stopping_tasks: List[asyncio.Task] = []

                for channel_id, task in list(active_tasks.items()):
                    if task.done():
                        active_tasks.pop(channel_id)
                        await asyncio.gather(task, return_exceptions=True)

                current_channel_ids = {
                    str(channel.get("id")) for channel in new_channels
                }

                # Cancel tasks for removed or deactivated channels
                for channel_id in list(active_tasks.keys()):
                    if channel_id not in current_channel_ids:
                        task = active_tasks.pop(channel_id)
                        task.cancel()
                        stopping_tasks.append(task)
                        logger.info(
                            tr("record.cancelled_deactivated_id", channel_id=channel_id)
                        )
                        # Remove progress data
                        async with channel_progress_lock:
                            channel_progress.pop(channel_id, None)

                for channel in new_channels:
                    channel_id = str(channel.get("id"))
                    if not channel_id:
                        logger.warning(tr("record.channel_id_missing"))
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
                                    new_recording_split_minutes,
                                )
                            )
                            active_tasks[channel_id] = task
                            active_channels += 1
                            logger.info(
                                tr("record.started_new_active_channel", channel_name=channel.get("name", tr("common.unknown")))
                            )
                    else:
                        if channel.get("active", "on") == "off":
                            task = active_tasks.pop(channel_id)
                            task.cancel()
                            stopping_tasks.append(task)
                            logger.info(
                                tr("record.cancelled_deactivated_name", channel_name=channel.get("name", tr("common.unknown")))
                            )
                            # Remove progress data
                            async with channel_progress_lock:
                                channel_progress.pop(channel_id, None)
                        else:
                            active_channels += 1

                if stopping_tasks:
                    await asyncio.gather(
                        *stopping_tasks, return_exceptions=True
                    )

                if active_channels == 0:
                    logger.info(tr("record.all_inactive"))

                # Wait for shutdown event or 10 seconds
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=10)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info(tr("record.management_cancelled"))
            shutdown_event.set()
        finally:
            active_recording_tasks = list(active_tasks.values())
            if active_recording_tasks:
                done, pending = await asyncio.wait(
                    active_recording_tasks,
                    timeout=RECORDING_SHUTDOWN_TIMEOUT_SECONDS,
                )
                if done:
                    await asyncio.gather(*done, return_exceptions=True)
                if pending:
                    logger.warning(
                        tr("record.shutdown_wait_timeout")
                    )
                    for task in pending:
                        task.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)


def handle_shutdown():
    if shutdown_event.is_set():
        return
    logger.info(tr("record.shutdown_signal"))
    shutdown_event.set()


async def display_progress(stop_event: asyncio.Event):
    layout = Layout()

    # Split the layout into upper and lower sections
    layout.split(
        Layout(name="upper", ratio=1),
        Layout(name="lower", ratio=3),
    )

    log_messages = collections.deque(maxlen=UI_LOG_HISTORY_SIZE)

    with Live(layout, console=console, refresh_per_second=5, screen=False):
        while not stop_event.is_set() or not log_queue.empty():
            # Update display for channel progress
            channel_panels = []
            language = get_language_sync()
            column_labels = [
                translate(language, f"record.table_{column}")
                for column in (
                    "channel", "bitrate", "download_speed", "total_size",
                    "out_time", "start_time",
                )
            ]

            async with channel_progress_lock:
                if channel_progress:
                    for progress_data in channel_progress.values():
                        # Create a table for each channel
                        table = Table(show_header=True, header_style="bold magenta")
                        table.add_column(column_labels[0], style="cyan", no_wrap=True)
                        for label in column_labels[1:]:
                            table.add_column(label)

                        channel_name = Text(
                            progress_data.get(
                                "channel_name", translate(language, "common.unknown")
                            )
                        )

                        table.add_row(
                            channel_name,
                            progress_data.get("bitrate", "N/A"),
                            progress_data.get("download_speed", "N/A"),
                            progress_data.get("total_size", "N/A"),
                            progress_data.get("out_time", "N/A"),
                            progress_data.get("recording_start_time", "N/A"),
                        )

                        # Wrap each channel's table in a panel
                        panel = Panel(table, title=channel_name)
                        channel_panels.append(panel)
                else:
                    # Show a message if no channels are recording
                    channel_panels.append(
                        Panel(
                            translate(language, "record.no_active_recordings"),
                            title=translate(language, "record.progress_title"),
                        )
                    )

            # Group all channel panels together
            progress_display = Group(*channel_panels)

            layout["lower"].update(progress_display)

            # Update log messages
            for _ in range(MAX_UI_LOG_MESSAGES):
                try:
                    log_messages.extend(log_queue.get_nowait().splitlines())
                    log_queue.task_done()
                except asyncio.QueueEmpty:
                    break

            # Update the log panel
            visible_log_lines = max(1, console.size.height // 4 - 2)
            log_text = Text(
                "\n".join(list(log_messages)[-visible_log_lines:]),
                overflow="ellipsis",
                no_wrap=True,
            )
            layout["upper"].update(
                Panel(log_text, title=translate(language, "record.logs_title"))
            )

            await asyncio.sleep(UI_REFRESH_INTERVAL_SECONDS)


async def main(gui_events: bool = False) -> int:
    setup_logger()
    install_internal_dns_resolver()
    if not gui_events:
        print(tr("record.startup_banner"))
    # Register signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    if platform.system() != "Windows":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_shutdown)
    else:
        # On Windows, signals are not supported in the event loop.
        # We'll handle KeyboardInterrupt exception instead.
        pass

    display_stop_event = asyncio.Event()
    if gui_events:
        from recorder_bridge import JsonBridge

        bridge = JsonBridge(sys.modules[__name__], loop)
        display_task = asyncio.create_task(bridge.display(display_stop_event))
    else:
        display_task = asyncio.create_task(display_progress(display_stop_event))
    exit_code = 0

    try:
        await manage_recording_tasks()
    except KeyboardInterrupt:
        logger.info(tr("record.keyboard_interrupt"))
        handle_shutdown()
        # Wait a moment to allow tasks to clean up
        await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info(tr("record.main_cancelled"))
        handle_shutdown()
    except Exception as e:
        exit_code = 1
        logger.exception(tr("record.unhandled_error", error=e))
    finally:
        # Wait for display_progress to process remaining logs
        shutdown_event.set()
        logger.info(tr("record.shutdown_complete"))
        display_stop_event.set()
        await display_task
    return exit_code


def run():
    import argparse
    import json

    from process_lock import FileLock

    global CONFIG_FILE_PATH, LOG_FILE_PATH
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui-events", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--config", type=Path, default=CONFIG_FILE_PATH)
    args = parser.parse_args()
    CONFIG_FILE_PATH = args.config.resolve()
    LOG_FILE_PATH = CONFIG_FILE_PATH.parent / "log.log"
    if platform.system() != "Windows":
        import uvloop

        uvloop.install()
    lock = FileLock(BASE_DIR / ".recorder.lock")
    try:
        lock.__enter__()
    except OSError:
        message = tr("gui.recorder_busy")
        if args.gui_events:
            print(json.dumps({"version": 1, "event": "error", "message": message}), flush=True)
        else:
            print(message, file=sys.stderr)
        return 1
    try:
        return asyncio.run(main(args.gui_events))
    finally:
        lock.__exit__(None, None, None)


if __name__ == "__main__":
    raise SystemExit(run())
