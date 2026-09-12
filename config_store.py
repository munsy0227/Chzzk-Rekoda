"""Shared CLI/GUI configuration. Importing never reads or writes files."""

import hashlib
import json
import os
import re
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

from i18n import DEFAULT_LANGUAGE, normalize_language, translate
from i18n import format_split_interval as localized_split_interval
from process_lock import FileLock
from recording_options import (
    H264_DEFAULTS,
    H264_ENCODERS,
    QUALITY_DEFAULTS,
    normalize_channel_options,
    normalize_quality,
)


class ConfigError(Exception):
    """A configuration operation failed safely."""


class ConfigConflict(ConfigError):
    """A different editor changed this file."""


def _ignore(message):
    pass


script_directory = os.path.dirname(os.path.abspath(__file__))

config_file_path = os.path.join(script_directory, "config.json")

DEFAULT_RESCAN_INTERVAL_SECONDS = 60

MIN_RESCAN_INTERVAL_SECONDS = 1

MAX_RESCAN_INTERVAL_SECONDS = 3600

DEFAULT_OUTPUT_FORMAT = "ts"

ALLOWED_OUTPUT_FORMATS = {"ts", "mkv", "webm"}

DEFAULT_RECORDING_SPLIT_MINUTES = 0

MAX_RECORDING_SPLIT_MINUTES = 10080

DEFAULT_DOH_URL = "https://dns.adguard-dns.com/dns-query"

NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"

CHZZK_CHANNEL_SEARCH_URL = "https://api.chzzk.naver.com/service/v1/search/channels"

CHZZK_CHANNEL_DETAIL_URL = (
    "https://api.chzzk.naver.com/service/v1/channels/{channel_id}"
)

CHZZK_API_TIMEOUT_SECONDS = 10

CHZZK_SEARCH_RESULT_LIMIT = 20

AUTH_COOKIE_NAMES = ("NID_AUT", "NID_SES")

BROWSER_LOGIN_OPTIONS = {
    "1": ("chrome", "Chrome"),
    "2": ("edge", "Microsoft Edge"),
    "3": ("firefox", "Firefox"),
}

CONFIG_REPLACE_ATTEMPTS = 5

CONFIG_REPLACE_RETRY_SECONDS = 0.2

default_config = {
    "channels": [],
    "delays": {},
    "timeout": DEFAULT_RESCAN_INTERVAL_SECONDS,
    "stream_segment_threads": 2,
    "output_format": DEFAULT_OUTPUT_FORMAT,
    "recording_split_minutes": DEFAULT_RECORDING_SPLIT_MINUTES,
    "quality_settings": deepcopy(QUALITY_DEFAULTS),
    "h264_settings": deepcopy(H264_DEFAULTS),
    "gui_settings": {"close_to_tray": True, "onboarding_completed": False},
    "hevc_settings": {
        "enable": False,
        "encoder": "libx265",
        "bitrate": "2500k",
        "max_bitrate": "10000k",
        "preset": "ultrafast",
    },
    "av1_settings": {
        "enable": False,
        "encoder": "libsvtav1",
        "bitrate": "2500k",
        "max_bitrate": "10000k",
        "preset": "8",
    },
    "log_enabled": True,
    "cookies": {"NID_SES": "", "NID_AUT": ""},
    "dns_settings": {
        "enable": False,
        "doh_url": DEFAULT_DOH_URL,
    },
    "language": DEFAULT_LANGUAGE,
}

SAFE_CHANNEL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

SAFE_FFMPEG_VALUE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")

SAFE_BITRATE = re.compile(r"^\d+[kKmM]?$")

CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

INVALID_FOLDER_CHARS = re.compile(r'[<>:"/\\|?*]')

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}

ALLOWED_ENCODERS = {
    "libx265",
    "hevc_nvenc",
    "hevc_qsv",
    "hevc_amf",
    "hevc_vaapi",
    "hevc_videotoolbox",
}

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

ALLOWED_AV1_ENCODERS = {
    "libsvtav1",
    "libaom-av1",
    "av1_nvenc",
    "av1_qsv",
    "av1_amf",
    "av1_vaapi",
}

ENCODER_PRESETS.update(
    {
        "libx264": LIBX265_PRESETS,
        "h264_nvenc": HEVC_NVENC_PRESETS,
        "h264_qsv": QSV_PRESETS,
        "h264_amf": HEVC_AMF_PRESETS,
    }
)
ENCODER_DEFAULT_PRESETS.update(
    {
        "libx264": "veryfast",
        "h264_nvenc": "p4",
        "h264_qsv": "medium",
        "h264_amf": "balanced",
        "h264_vaapi": "auto",
        "h264_videotoolbox": "auto",
    }
)


def normalize_encoder_preset(encoder, value):
    default = ENCODER_DEFAULT_PRESETS[encoder]
    preset = default if value is None else str(value).strip().lower()
    if not preset:
        preset = default
    options = ENCODER_PRESETS.get(encoder)
    if options is None:
        return default
    if encoder in {"hevc_nvenc", "av1_nvenc", "h264_nvenc"}:
        if preset in {"ultrafast", "superfast", "veryfast", "faster"}:
            return "p1"
        if preset in {"slower", "veryslow"}:
            return "p6"
    if encoder in {"hevc_amf", "h264_amf"} and "fast" in preset:
        return "speed"
    return preset if preset in options else default


def deep_merge_defaults(config, defaults):
    merged = deepcopy(defaults)
    if not isinstance(config, dict):
        return merged
    for key, value in config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_defaults(value, merged[key])
        else:
            merged[key] = deepcopy(value)
    return merged


def clamp_int(value, default, min_value, max_value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def sanitize_cookie(value):
    return CONTROL_CHARS.sub("", str(value or "")).replace(";", "").strip()


def normalize_bitrate(value, default):
    text = str(value or default).strip()
    if not SAFE_BITRATE.fullmatch(text):
        return default
    if text[-1].isdigit():
        text += "k"
    return text.lower()


def normalize_output_format(value):
    text = str(value or DEFAULT_OUTPUT_FORMAT).strip().lower().lstrip(".")
    return text if text in ALLOWED_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT


def normalize_doh_url(value):
    text = CONTROL_CHARS.sub("", str(value or DEFAULT_DOH_URL)).strip()
    try:
        parsed = urlparse(text)
    except ValueError:
        return DEFAULT_DOH_URL
    if parsed.scheme != "https" or not parsed.hostname:
        return DEFAULT_DOH_URL
    return text


def normalize_dns_settings(value):
    settings = deep_merge_defaults(
        value if isinstance(value, dict) else {},
        default_config["dns_settings"],
    )
    settings["enable"] = bool(settings.get("enable"))
    settings["doh_url"] = normalize_doh_url(settings.get("doh_url"))
    return settings


def normalize_h264_settings(value):
    settings = deep_merge_defaults(value, H264_DEFAULTS)
    settings["enable"] = bool(settings["enable"])
    if settings["encoder"] not in H264_ENCODERS:
        settings["encoder"] = "libx264"
    for key in ("bitrate", "max_bitrate"):
        settings[key] = normalize_bitrate(settings[key], H264_DEFAULTS[key])
    settings["preset"] = normalize_encoder_preset(
        settings["encoder"], settings["preset"]
    )
    return settings


def backup_corrupt_config(config_file_path):
    directory = os.path.dirname(config_file_path)
    fd = None
    backup_path = None
    try:
        fd, backup_path = tempfile.mkstemp(
            prefix="config.", suffix=".corrupt", dir=directory
        )
        with open(config_file_path, "rb") as source:
            with os.fdopen(fd, "wb") as backup:
                fd = None
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    backup.write(chunk)
                backup.flush()
                os.fsync(backup.fileno())
        return backup_path
    except BaseException:
        if fd is not None:
            os.close(fd)
        if backup_path and os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                pass
        raise


def format_split_interval(minutes, language=DEFAULT_LANGUAGE):
    return localized_split_interval(language, minutes)


def normalize_channel_identifier(
    value,
    fallback_index,
    used_identifiers,
    reserved_identifiers=None,
):
    reserved_identifiers = reserved_identifiers or set()
    identifier = str(value or f"ch{fallback_index}").strip()
    if SAFE_FFMPEG_VALUE.fullmatch(identifier) and identifier not in used_identifiers:
        return identifier

    base_identifier = f"ch{fallback_index}"
    identifier = base_identifier
    suffix = 2
    while identifier in used_identifiers or identifier in reserved_identifiers:
        identifier = f"{base_identifier}_{suffix}"
        suffix += 1
    return identifier


def normalize_config(config, notify=None):
    notify = notify or _ignore
    config = deep_merge_defaults(config, default_config)
    config["language"] = normalize_language(config.get("language"))
    language = config["language"]
    config["timeout"] = clamp_int(
        config.get("timeout"),
        DEFAULT_RESCAN_INTERVAL_SECONDS,
        MIN_RESCAN_INTERVAL_SECONDS,
        MAX_RESCAN_INTERVAL_SECONDS,
    )
    config["stream_segment_threads"] = clamp_int(
        config.get("stream_segment_threads"), 2, 1, 16
    )
    config["output_format"] = normalize_output_format(config.get("output_format"))
    legacy_split_hours = config.pop("recording_split_hours", None)
    split_minutes = config.get("recording_split_minutes")
    if legacy_split_hours is not None and split_minutes in (
        None,
        DEFAULT_RECORDING_SPLIT_MINUTES,
    ):
        split_minutes = (
            clamp_int(
                legacy_split_hours,
                DEFAULT_RECORDING_SPLIT_MINUTES,
                0,
                MAX_RECORDING_SPLIT_MINUTES // 60,
            )
            * 60
        )
    config["recording_split_minutes"] = clamp_int(
        split_minutes,
        DEFAULT_RECORDING_SPLIT_MINUTES,
        0,
        MAX_RECORDING_SPLIT_MINUTES,
    )

    raw_delays = config.get("delays", {})
    delays = (
        {str(key): clamp_int(value, 0, 0, 3600) for key, value in raw_delays.items()}
        if isinstance(raw_delays, dict)
        else {}
    )

    raw_channels = config.get("channels", [])
    if not isinstance(raw_channels, list):
        notify(translate(language, "settings.invalid_channels_reset"))
        raw_channels = []

    reserved_identifiers = {
        str(channel.get("identifier", "")).strip()
        for channel in raw_channels
        if isinstance(channel, dict)
        and SAFE_FFMPEG_VALUE.fullmatch(str(channel.get("identifier", "")).strip())
    }
    channels = []
    channel_delays = {}
    seen_channel_ids = set()
    used_identifiers = set()
    for index, channel in enumerate(raw_channels, start=1):
        if not isinstance(channel, dict):
            continue
        channel_id = str(channel.get("id", "")).strip()
        if not SAFE_CHANNEL_ID.fullmatch(channel_id):
            notify(
                translate(
                    language,
                    "settings.invalid_channel_skipped",
                    channel_id=channel_id,
                )
            )
            continue
        if channel_id in seen_channel_ids:
            notify(
                translate(
                    language,
                    "settings.duplicate_channel_skipped",
                    channel_id=channel_id,
                )
            )
            continue

        seen_channel_ids.add(channel_id)
        original_identifier = str(channel.get("identifier") or f"ch{index}").strip()
        identifier = normalize_channel_identifier(
            original_identifier,
            index,
            used_identifiers,
            reserved_identifiers,
        )
        used_identifiers.add(identifier)
        channel["id"] = channel_id
        channel["name"] = CONTROL_CHARS.sub(
            "", str(channel.get("name") or channel_id)
        ).strip()
        channel["output_dir"] = str(channel.get("output_dir") or ".").strip() or "."
        channel["identifier"] = identifier
        channel["active"] = "off" if channel.get("active") == "off" else "on"
        channels.append(normalize_channel_options(channel))

        if original_identifier in delays:
            channel_delays[identifier] = delays[original_identifier]
        elif identifier in delays:
            channel_delays[identifier] = delays[identifier]

    config["channels"] = channels
    config["delays"] = channel_delays

    hevc = deep_merge_defaults(
        config.get("hevc_settings", {}), default_config["hevc_settings"]
    )
    hevc["enable"] = bool(hevc.get("enable"))
    if hevc.get("encoder") not in ALLOWED_ENCODERS:
        hevc["encoder"] = "libx265"
    hevc["bitrate"] = normalize_bitrate(hevc.get("bitrate"), "2500k")
    hevc["max_bitrate"] = normalize_bitrate(hevc.get("max_bitrate"), "10000k")
    hevc["preset"] = normalize_encoder_preset(hevc["encoder"], hevc.get("preset"))
    config["hevc_settings"] = hevc

    av1 = deep_merge_defaults(
        config.get("av1_settings", {}), default_config["av1_settings"]
    )
    av1["enable"] = bool(av1.get("enable"))
    if av1.get("encoder") not in ALLOWED_AV1_ENCODERS:
        av1["encoder"] = "libsvtav1"
    av1["bitrate"] = normalize_bitrate(av1.get("bitrate"), "2500k")
    av1["max_bitrate"] = normalize_bitrate(av1.get("max_bitrate"), "10000k")
    av1["preset"] = normalize_encoder_preset(av1["encoder"], av1.get("preset"))
    if av1["enable"]:
        hevc["enable"] = False
    config["av1_settings"] = av1
    h264 = normalize_h264_settings(config.get("h264_settings"))
    if h264["enable"]:
        hevc["enable"] = av1["enable"] = False
    config["h264_settings"] = h264
    config["quality_settings"] = normalize_quality(config.get("quality_settings"))
    gui = config.get("gui_settings")
    config["gui_settings"] = {
        **(gui if isinstance(gui, dict) else {}),
        "close_to_tray": bool(gui.get("close_to_tray", True))
        if isinstance(gui, dict)
        else True,
        "onboarding_completed": bool(gui.get("onboarding_completed", False))
        if isinstance(gui, dict)
        else False,
    }

    cookies = config.get("cookies", {})
    if not isinstance(cookies, dict):
        cookies = {}
    config["cookies"] = {
        "NID_SES": sanitize_cookie(cookies.get("NID_SES", "")),
        "NID_AUT": sanitize_cookie(cookies.get("NID_AUT", "")),
    }
    config["log_enabled"] = bool(config.get("log_enabled", True))
    config["dns_settings"] = normalize_dns_settings(config.get("dns_settings"))
    return config


def load_config(path=None, notify=None):
    notify = notify or _ignore
    config_file_path = str(Path(path or globals()["config_file_path"]).resolve())
    script_directory = str(Path(config_file_path).parent)
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)
            # Windows cannot replace a file while this reader still owns it.
            config = normalize_config(raw_config, notify)
            if config != raw_config:
                save_config(config, config_file_path, notify)
            return config
        except (json.JSONDecodeError, UnicodeError) as e:
            try:
                backup_path = backup_corrupt_config(config_file_path)
            except OSError as backup_error:
                notify(
                    translate(
                        DEFAULT_LANGUAGE,
                        "settings.corrupt_config_backup_error",
                        error=backup_error,
                    )
                )
                raise ConfigError(str(backup_error)) from backup_error
            notify(
                translate(
                    DEFAULT_LANGUAGE,
                    "settings.error_loading_config",
                    error=e,
                )
            )
            notify(
                translate(
                    DEFAULT_LANGUAGE,
                    "settings.corrupt_config_backed_up",
                    backup_path=backup_path,
                )
            )
        except OSError as e:
            notify(
                translate(
                    DEFAULT_LANGUAGE,
                    "settings.config_read_error",
                    error=e,
                )
            )
            raise ConfigError(str(e)) from e

    # Migration Logic (if config.json doesn't exist or failed to load)
    notify(translate(DEFAULT_LANGUAGE, "settings.migrating_old_settings"))
    config = deepcopy(default_config)

    # 1. Channels
    channels_path = os.path.join(script_directory, "channels.json")
    if os.path.exists(channels_path):
        try:
            with open(channels_path, "r") as f:
                config["channels"] = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Delays
    delays_path = os.path.join(script_directory, "delays.json")
    if os.path.exists(delays_path):
        try:
            with open(delays_path, "r") as f:
                config["delays"] = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # 3. Timeout (time_sleep.txt)
    time_path = os.path.join(script_directory, "time_sleep.txt")
    if os.path.exists(time_path):
        try:
            with open(time_path, "r") as f:
                val = f.readline().strip()
                if val.isdigit():
                    config["timeout"] = int(val)
        except (json.JSONDecodeError, OSError):
            pass

    # 4. Threads
    thread_path = os.path.join(script_directory, "thread.txt")
    if os.path.exists(thread_path):
        try:
            with open(thread_path, "r") as f:
                val = f.readline().strip()
                if val.isdigit():
                    config["stream_segment_threads"] = int(val)
        except (json.JSONDecodeError, OSError):
            pass

    # 5. HEVC
    hevc_path = os.path.join(script_directory, "hevc.json")
    if os.path.exists(hevc_path):
        try:
            with open(hevc_path, "r") as f:
                hevc_data = json.load(f)
                # Merge HEVC keys
                for k, v in hevc_data.items() if isinstance(hevc_data, dict) else []:
                    config["hevc_settings"][k] = v
        except (json.JSONDecodeError, OSError):
            pass

    # 6. Log Enabled
    log_path = os.path.join(script_directory, "log_enabled.txt")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                config["log_enabled"] = f.readline().strip().lower() == "true"
        except (json.JSONDecodeError, OSError):
            pass

    # 7. Cookies
    cookie_path = os.path.join(script_directory, "cookie.json")
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, "r") as f:
                cookie_data = json.load(f)
                config["cookies"] = cookie_data
        except (json.JSONDecodeError, OSError):
            pass

    # Save migrated config
    config = normalize_config(config, notify)
    save_config(config, config_file_path, notify)
    return config


def save_config(config, path=None, notify=None):
    notify = notify or _ignore
    config_file_path = str(Path(path or globals()["config_file_path"]).resolve())
    normalized_config = normalize_config(config, notify)
    if isinstance(config, dict):
        config.clear()
        config.update(normalized_config)
    else:
        config = normalized_config

    directory = os.path.dirname(config_file_path)
    fd = None
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix="config.", suffix=".tmp", dir=directory, text=True
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = None
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(CONFIG_REPLACE_ATTEMPTS):
            try:
                os.replace(temp_path, config_file_path)
                temp_path = None
                break
            except PermissionError:
                if attempt == CONFIG_REPLACE_ATTEMPTS - 1:
                    # Keep the last valid file when replacement is blocked.
                    raise
                time.sleep(CONFIG_REPLACE_RETRY_SECONDS)
        if os.name != "nt":
            try:
                os.chmod(config_file_path, 0o600)
            except OSError:
                pass
        language = normalize_language(config.get("language"))
        notify(translate(language, "settings.config_saved"))
    except OSError as e:
        language = normalize_language(config.get("language"))
        notify(
            translate(
                language,
                "settings.config_save_error",
                error=e,
            )
        )
        raise ConfigError(str(e)) from e
    finally:
        if fd is not None:
            os.close(fd)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


class ConfigStore:
    """Revision-checked read/modify/write for both settings interfaces."""

    def __init__(self, path=None, notify=None):
        self.path = Path(path or config_file_path).resolve()
        self.notify = notify
        self.revision = None

    def _revision(self):
        try:
            return hashlib.sha256(self.path.read_bytes()).digest()
        except FileNotFoundError:
            return None

    def load(self):
        with FileLock(self.path.with_name(self.path.name + ".lock")):
            config = load_config(self.path, self.notify)
            self.revision = self._revision()
            return config

    def save(self, config):
        with FileLock(self.path.with_name(self.path.name + ".lock")):
            if self._revision() != self.revision:
                raise ConfigConflict(
                    translate(config.get("language"), "gui.config_conflict")
                )
            candidate = deepcopy(config)
            save_config(candidate, self.path, self.notify)
            self.revision = self._revision()
            config.clear()
            config.update(candidate)
