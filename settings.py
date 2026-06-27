import os
import json
import re
import tempfile
from copy import deepcopy
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    enabled_word,
    format_split_interval as localized_split_interval,
    language_display_name,
    language_options,
    normalize_language,
    on_off_label,
    state_label,
    translate,
)

# File path settings
script_directory = os.path.dirname(os.path.abspath(__file__))
config_file_path = os.path.join(script_directory, "config.json")

# Default Configuration
DEFAULT_RESCAN_INTERVAL_SECONDS = 60
MIN_RESCAN_INTERVAL_SECONDS = 1
MAX_RESCAN_INTERVAL_SECONDS = 3600
DEFAULT_OUTPUT_FORMAT = "ts"
ALLOWED_OUTPUT_FORMATS = {"ts", "mkv", "webm"}
DEFAULT_RECORDING_SPLIT_MINUTES = 0
MAX_RECORDING_SPLIT_MINUTES = 10080
DEFAULT_DOH_URL = "https://dns.adguard-dns.com/dns-query"
NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
CHZZK_CHANNEL_SEARCH_URL = (
    "https://api.chzzk.naver.com/service/v1/search/channels"
)
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

default_config = {
    "channels": [],
    "delays": {},
    "timeout": DEFAULT_RESCAN_INTERVAL_SECONDS,
    "stream_segment_threads": 2,
    "output_format": DEFAULT_OUTPUT_FORMAT,
    "recording_split_minutes": DEFAULT_RECORDING_SPLIT_MINUTES,
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
ALLOWED_AV1_ENCODERS = {
    "libsvtav1",
    "libaom-av1",
    "av1_nvenc",
    "av1_qsv",
    "av1_amf",
    "av1_vaapi",
}


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


def request_chzzk_api(url, language, params=None):
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Accept-Language": language,
            "Referer": "https://chzzk.naver.com/",
            "Origin": "https://chzzk.naver.com",
        },
    )
    try:
        with urlopen(request, timeout=CHZZK_API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as error:
        message = str(error).strip().splitlines()[0] or type(error).__name__
        return None, message

    if not isinstance(payload, dict) or payload.get("code") != 200:
        message = payload.get("message") if isinstance(payload, dict) else None
        return None, str(
            message or translate(language, "settings.api_invalid_response")
        )

    content = payload.get("content")
    if not isinstance(content, dict):
        return None, translate(language, "settings.api_missing_content")
    return content, None


def search_chzzk_channels(keyword, language):
    content, error = request_chzzk_api(
        CHZZK_CHANNEL_SEARCH_URL,
        language,
        {
            "keyword": keyword,
            "offset": 0,
            "size": CHZZK_SEARCH_RESULT_LIMIT,
            "withFirstChannelContent": "false",
        },
    )
    if error:
        return [], error

    data = content.get("data")
    if not isinstance(data, list):
        return [], translate(language, "settings.api_invalid_response")

    results = []
    seen_ids = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        channel = item.get("channel")
        if not isinstance(channel, dict):
            continue
        channel_id = str(channel.get("channelId", "")).strip()
        name = CONTROL_CHARS.sub(
            "", str(channel.get("channelName", ""))
        ).strip()
        if (
            not SAFE_CHANNEL_ID.fullmatch(channel_id)
            or not name
            or channel_id in seen_ids
        ):
            continue
        seen_ids.add(channel_id)
        results.append({"id": channel_id, "name": name})
    return results, None


def fetch_chzzk_channel(channel_id, language):
    content, error = request_chzzk_api(
        CHZZK_CHANNEL_DETAIL_URL.format(channel_id=channel_id),
        language,
    )
    if error:
        return None, error

    returned_id = str(content.get("channelId", "")).strip()
    name = CONTROL_CHARS.sub(
        "", str(content.get("channelName", ""))
    ).strip()
    if returned_id != channel_id or not name:
        return None, translate(language, "settings.api_invalid_channel_data")
    return {"id": returned_id, "name": name}, None


def find_channel_by_id(channels, channel_id):
    return next(
        (channel for channel in channels if channel.get("id") == channel_id),
        None,
    )


def channels_with_name(channels, name, exclude_id=None):
    normalized_name = name.casefold()
    return [
        channel
        for channel in channels
        if channel.get("id") != exclude_id
        and str(channel.get("name", "")).casefold() == normalized_name
    ]


def safe_channel_folder_name(name, channel_id):
    folder_name = INVALID_FOLDER_CHARS.sub("_", CONTROL_CHARS.sub("", name))
    folder_name = folder_name.strip().strip(".")
    if folder_name.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        folder_name = f"_{folder_name}"
    return folder_name[:120] or channel_id


def create_output_directory(output_dir):
    expanded_path = os.path.expanduser(output_dir)
    if not os.path.isabs(expanded_path):
        expanded_path = os.path.join(script_directory, expanded_path)
    try:
        os.makedirs(expanded_path, exist_ok=True)
    except OSError as error:
        print(t("settings.output_dir_create_error", error=error))
        return False
    return True


def format_split_interval(minutes, language=DEFAULT_LANGUAGE):
    return localized_split_interval(language, minutes)


def normalize_config(config):
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
        split_minutes = clamp_int(
            legacy_split_hours,
            DEFAULT_RECORDING_SPLIT_MINUTES,
            0,
            MAX_RECORDING_SPLIT_MINUTES // 60,
        ) * 60
    config["recording_split_minutes"] = clamp_int(
        split_minutes,
        DEFAULT_RECORDING_SPLIT_MINUTES,
        0,
        MAX_RECORDING_SPLIT_MINUTES,
    )

    channels = []
    for index, channel in enumerate(config.get("channels", []), start=1):
        if not isinstance(channel, dict):
            continue
        channel_id = str(channel.get("id", "")).strip()
        if not SAFE_CHANNEL_ID.fullmatch(channel_id):
            print(
                translate(
                    language,
                    "settings.invalid_channel_skipped",
                    channel_id=channel_id,
                )
            )
            continue
        channel["id"] = channel_id
        channel["name"] = CONTROL_CHARS.sub("", str(channel.get("name") or channel_id)).strip()
        channel["output_dir"] = str(channel.get("output_dir") or ".").strip() or "."
        channel["identifier"] = str(channel.get("identifier") or f"ch{index}").strip()
        channel["active"] = "off" if channel.get("active") == "off" else "on"
        channels.append(channel)
    config["channels"] = channels

    delays = config.get("delays", {})
    config["delays"] = {
        str(key): clamp_int(value, 0, 0, 3600)
        for key, value in delays.items()
    } if isinstance(delays, dict) else {}

    hevc = deep_merge_defaults(config.get("hevc_settings", {}), default_config["hevc_settings"])
    hevc["enable"] = bool(hevc.get("enable"))
    if hevc.get("encoder") not in ALLOWED_ENCODERS:
        hevc["encoder"] = "libx265"
    hevc["bitrate"] = normalize_bitrate(hevc.get("bitrate"), "2500k")
    hevc["max_bitrate"] = normalize_bitrate(hevc.get("max_bitrate"), "10000k")
    preset = str(hevc.get("preset") or "ultrafast").strip()
    hevc["preset"] = preset if SAFE_FFMPEG_VALUE.fullmatch(preset) else "ultrafast"
    config["hevc_settings"] = hevc

    av1 = deep_merge_defaults(config.get("av1_settings", {}), default_config["av1_settings"])
    av1["enable"] = bool(av1.get("enable"))
    if av1.get("encoder") not in ALLOWED_AV1_ENCODERS:
        av1["encoder"] = "libsvtav1"
    av1["bitrate"] = normalize_bitrate(av1.get("bitrate"), "2500k")
    av1["max_bitrate"] = normalize_bitrate(av1.get("max_bitrate"), "10000k")
    av1_preset = str(av1.get("preset") or "8").strip()
    av1["preset"] = av1_preset if SAFE_FFMPEG_VALUE.fullmatch(av1_preset) else "8"
    if av1["enable"]:
        hevc["enable"] = False
    config["av1_settings"] = av1

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


def load_config():
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)
                config = normalize_config(raw_config)
                if config != raw_config:
                    save_config(config)
                return config
        except (json.JSONDecodeError, OSError) as e:
            print(
                translate(
                    DEFAULT_LANGUAGE,
                    "settings.error_loading_config",
                    error=e,
                )
            )

    # Migration Logic (if config.json doesn't exist or failed to load)
    print(translate(DEFAULT_LANGUAGE, "settings.migrating_old_settings"))
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
                for k, v in hevc_data.items():
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
    save_config(config)
    return config


def save_config(config):
    config = normalize_config(config)
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
        os.replace(temp_path, config_file_path)
        if os.name != "nt":
            try:
                os.chmod(config_file_path, 0o600)
            except OSError:
                pass
        language = normalize_language(config.get("language"))
        print(translate(language, "settings.config_saved"))
    except OSError as e:
        language = normalize_language(config.get("language"))
        print(
            translate(
                language,
                "settings.config_save_error",
                error=e,
            )
        )
    finally:
        if fd is not None:
            os.close(fd)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def try_again():
    print("Please try again.\n")


# Load config at startup
config = load_config()


def current_language():
    return normalize_language(config.get("language"))


def t(key, **kwargs):
    return translate(current_language(), key, **kwargs)


def try_again():
    print(t("settings.try_again"))


def print_codec_settings(codec, settings):
    print("\n" + t("settings.codec_title", codec=codec))
    print(t("settings.status", status=state_label(current_language(), settings["enable"])))
    print(t("settings.encoder", encoder=settings.get("encoder", "libx265")))
    print(t("settings.target_bitrate", bitrate=settings["bitrate"]))
    print(t("settings.max_bitrate", bitrate=settings["max_bitrate"]))
    print(t("settings.preset", preset=settings["preset"]))
    print("-" * 30)


def print_language_menu():
    print("\n" + t("settings.language_title"))
    print(t("settings.current_language", language=language_display_name(current_language())))
    for idx, (code, name) in enumerate(language_options(), start=1):
        print(f"{idx}. {name} ({code})")


def import_cookies_from_browser(browser):
    driver = None
    try:
        from selenium import webdriver

        driver_factories = {
            "chrome": webdriver.Chrome,
            "edge": webdriver.Edge,
            "firefox": webdriver.Firefox,
        }
        driver = driver_factories[browser]()
        driver.get(NAVER_LOGIN_URL)
        input(t("settings.browser_login_wait"))

        browser_cookies = {
            cookie.get("name"): sanitize_cookie(cookie.get("value"))
            for cookie in driver.get_cookies()
            if cookie.get("name") in AUTH_COOKIE_NAMES
        }
        missing = [
            name for name in AUTH_COOKIE_NAMES if not browser_cookies.get(name)
        ]
        if missing:
            print(
                t(
                    "settings.browser_cookies_missing",
                    cookies=", ".join(missing),
                )
            )
            return False

        config["cookies"] = {
            name: browser_cookies[name] for name in AUTH_COOKIE_NAMES
        }
        save_config(config)
        print(t("settings.browser_cookies_saved"))
        return True
    except Exception as error:
        message = str(error).strip().splitlines()[0] or type(error).__name__
        print(t("settings.browser_login_error", error=message))
        return False
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def select_language(value):
    text = value.strip()
    options = language_options()
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(options):
            return options[index][0]
        return None
    if text in SUPPORTED_LANGUAGES:
        return text
    normalized = normalize_language(text)
    if normalized != DEFAULT_LANGUAGE or text.lower() in {"ko", "kr", "kor", "korean", "한국어"}:
        return normalized
    return None


def print_duplicate_channel(channel):
    print(
        t(
            "settings.channel_already_registered",
            channel_id=channel["id"],
            name=channel["name"],
            output_dir=channel["output_dir"],
        )
    )


def choose_channel_by_search():
    keyword = str(input(t("settings.prompt_search_keyword"))).strip()
    if not keyword:
        print(t("settings.empty_search_keyword"))
        return None

    results, error = search_chzzk_channels(keyword, current_language())
    if error:
        print(t("settings.channel_search_failed", error=error))
        return None
    if not results:
        print(t("settings.no_search_results"))
        return None

    print(t("settings.channel_search_results"))
    for index, channel in enumerate(results, start=1):
        registered = find_channel_by_id(config["channels"], channel["id"])
        status = t("settings.already_registered_marker") if registered else ""
        print(
            t(
                "settings.channel_search_result",
                index=index,
                name=channel["name"],
                channel_id=channel["id"],
                status=status,
            )
        )

    selection = str(input(t("settings.prompt_search_result"))).strip()
    if selection == "0":
        return None
    try:
        selected_index = int(selection)
    except ValueError:
        print(t("settings.invalid_channel_number"))
        return None
    if not 1 <= selected_index <= len(results):
        print(t("settings.invalid_channel_number"))
        return None
    selected = results[selected_index - 1]

    duplicate = find_channel_by_id(config["channels"], selected["id"])
    if duplicate:
        print_duplicate_channel(duplicate)
        return None
    return selected


def choose_channel_by_id():
    channel_id = str(input(t("settings.prompt_channel_id"))).strip()
    if not SAFE_CHANNEL_ID.fullmatch(channel_id):
        print(t("settings.invalid_channel_id"))
        return None

    duplicate = find_channel_by_id(config["channels"], channel_id)
    if duplicate:
        print_duplicate_channel(duplicate)
        return None

    print(t("settings.channel_lookup_in_progress"))
    channel, error = fetch_chzzk_channel(channel_id, current_language())
    if error:
        print(t("settings.channel_lookup_failed", error=error))
        return None
    print(
        t(
            "settings.channel_lookup_result",
            channel_id=channel["id"],
            name=channel["name"],
        )
    )
    return channel


def add_selected_channel(channel):
    channel_id = channel["id"]
    name = channel["name"]
    duplicate_names = channels_with_name(
        config["channels"], name, exclude_id=channel_id
    )
    if duplicate_names:
        duplicate_ids = ", ".join(item["id"] for item in duplicate_names)
        print(
            t(
                "settings.duplicate_channel_name_warning",
                name=name,
                channel_ids=duplicate_ids,
            )
        )

    default_output_dir = safe_channel_folder_name(name, channel_id)
    output_dir = str(
        input(
            t(
                "settings.prompt_output_dir",
                default_output_dir=default_output_dir,
            )
        )
    ).strip() or default_output_dir

    while True:
        answer = str(
            input(
                t(
                    "settings.confirm_channel",
                    channel_id=channel_id,
                    name=name,
                    output_dir=output_dir,
                )
            )
        ).strip()
        if answer.lower() == "y":
            duplicate = find_channel_by_id(config["channels"], channel_id)
            if duplicate:
                print_duplicate_channel(duplicate)
                return
            if not create_output_directory(output_dir):
                return

            current_count = len(config["channels"])
            identifier = f"ch{current_count + 1}"
            config["channels"].append(
                {
                    "id": channel_id,
                    "name": name,
                    "output_dir": output_dir,
                    "identifier": identifier,
                    "active": "on",
                }
            )
            config["delays"][identifier] = current_count
            save_config(config)
            print(t("settings.channel_added"))
            return
        if answer.lower() == "n":
            print(t("settings.reenter"))
            return
        try_again()


while True:
    print(t("settings.main_title"))
    print(t("settings.main_menu"))
    choice = str(input(t("settings.prompt_choice"))).strip()

    if choice == "1":
        while True:
            print(t("settings.channel_menu"))
            choice1 = str(input(t("settings.prompt_choice"))).strip()
            if choice1 == "1":
                print(t("settings.add_channel_menu"))
                add_choice = str(input(t("settings.prompt_choice"))).strip()
                if add_choice == "1":
                    selected_channel = choose_channel_by_search()
                elif add_choice == "2":
                    selected_channel = choose_channel_by_id()
                elif add_choice == "3":
                    continue
                else:
                    try_again()
                    continue

                if selected_channel is not None:
                    add_selected_channel(selected_channel)

            elif choice1 == "2":
                if not config["channels"]:
                    print(t("settings.no_channels_delete"))
                    continue

                print(t("settings.current_channel_list"))
                for idx, channel in enumerate(config["channels"], start=1):
                    print(
                        t(
                            "settings.channel_list_item",
                            idx=idx,
                            channel_id=channel["id"],
                            name=channel["name"],
                        )
                    )

                try:
                    idx_to_del = int(input(t("settings.prompt_delete_channel"))) - 1
                    if 0 <= idx_to_del < len(config["channels"]):
                        deleted_channel = config["channels"].pop(idx_to_del)
                        print(
                            t(
                                "settings.deleted_channel",
                                channel_id=deleted_channel["id"],
                                name=deleted_channel["name"],
                            )
                        )

                        new_delays = {}
                        for i, channel in enumerate(config["channels"]):
                            new_identifier = f"ch{i + 1}"
                            channel["identifier"] = new_identifier
                            new_delays[new_identifier] = i

                        config["delays"] = new_delays
                        save_config(config)
                        print(t("settings.channel_deleted"))
                    else:
                        print(t("settings.invalid_channel_number"))
                except ValueError:
                    print(t("settings.invalid_number"))

            elif choice1 == "3":
                if not config["channels"]:
                    print(t("settings.no_channels_toggle"))
                    continue

                print(t("settings.current_channel_list"))
                for idx, channel in enumerate(config["channels"], start=1):
                    status = on_off_label(
                        current_language(), channel.get("active", "on") == "on"
                    )
                    print(
                        t(
                            "settings.channel_list_item_status",
                            idx=idx,
                            channel_id=channel["id"],
                            name=channel["name"],
                            status=status,
                        )
                    )

                try:
                    idx_to_toggle = int(input(t("settings.prompt_toggle_channel"))) - 1
                    if 0 <= idx_to_toggle < len(config["channels"]):
                        channel = config["channels"][idx_to_toggle]
                        current_state = channel.get("active", "on")
                        channel["active"] = "off" if current_state == "on" else "on"
                        status = on_off_label(current_language(), current_state != "on")
                        print(
                            t(
                                "settings.channel_status_changed",
                                name=channel["name"],
                                status=status,
                            )
                        )
                        save_config(config)
                    else:
                        print(t("settings.invalid_channel_number"))
                except ValueError:
                    print(t("settings.invalid_number"))

            elif choice1 == "4":
                break
            else:
                try_again()

    elif choice == "2":
        while True:
            print(t("settings.recording_menu"))
            choice2 = str(input(t("settings.prompt_choice"))).strip()

            if choice2 == "1":
                print(
                    t(
                        "settings.current_threads",
                        count=config.get("stream_segment_threads", 2),
                    )
                )
                print(t("settings.thread_recommendation"))
                new_threads = clamp_int(input(t("settings.prompt_threads")), 2, 1, 16)
                config["stream_segment_threads"] = new_threads
                save_config(config)
                print(t("settings.threads_changed"))

            elif choice2 == "2":
                print(
                    t(
                        "settings.current_timeout",
                        seconds=config.get("timeout", DEFAULT_RESCAN_INTERVAL_SECONDS),
                    )
                )
                new_timeout = clamp_int(
                    input(t("settings.prompt_timeout")),
                    DEFAULT_RESCAN_INTERVAL_SECONDS,
                    MIN_RESCAN_INTERVAL_SECONDS,
                    MAX_RESCAN_INTERVAL_SECONDS,
                )
                config["timeout"] = new_timeout
                save_config(config)
                print(t("settings.timeout_changed"))

            elif choice2 == "3":
                current_format = config.get("output_format", DEFAULT_OUTPUT_FORMAT)
                print(t("settings.current_output_format", format=current_format))
                print(t("settings.available_formats"))
                new_format = normalize_output_format(input(t("settings.prompt_output_format")))
                config["output_format"] = new_format
                save_config(config)
                print(t("settings.output_format_changed", format=new_format))

            elif choice2 == "4":
                current_split = clamp_int(
                    config.get("recording_split_minutes"),
                    DEFAULT_RECORDING_SPLIT_MINUTES,
                    0,
                    MAX_RECORDING_SPLIT_MINUTES,
                )
                print(
                    t(
                        "settings.current_split",
                        interval=format_split_interval(current_split, current_language()),
                    )
                )
                print(t("settings.choose_split_unit"))
                print(t("settings.unit_hours"))
                print(t("settings.unit_minutes"))
                print(t("settings.unit_disable"))
                unit_choice = input(t("settings.prompt_choice")).strip()

                if unit_choice == "1":
                    split_hours = clamp_int(
                        input(t("settings.prompt_split_hours")),
                        DEFAULT_RECORDING_SPLIT_MINUTES,
                        0,
                        MAX_RECORDING_SPLIT_MINUTES // 60,
                    )
                    new_split = split_hours * 60
                elif unit_choice == "2":
                    new_split = clamp_int(
                        input(t("settings.prompt_split_minutes")),
                        DEFAULT_RECORDING_SPLIT_MINUTES,
                        0,
                        MAX_RECORDING_SPLIT_MINUTES,
                    )
                elif unit_choice == "3":
                    new_split = 0
                else:
                    try_again()
                    continue

                config["recording_split_minutes"] = new_split
                save_config(config)
                if new_split == 0:
                    print(t("settings.split_disabled"))
                else:
                    print(
                        t(
                            "settings.split_changed",
                            interval=format_split_interval(new_split, current_language()),
                        )
                    )

            elif choice2 == "5":
                break
            else:
                try_again()

    elif choice == "3":
        while True:
            hevc = config["hevc_settings"]
            print_codec_settings("HEVC (H.265)", hevc)
            print(t("settings.hevc_menu"))
            choice3 = str(input(t("settings.prompt_choice"))).strip()

            if choice3 == "1":
                hevc["enable"] = not hevc["enable"]
                if hevc["enable"]:
                    config["av1_settings"]["enable"] = False
                save_config(config)
                print(
                    t(
                        "settings.encoding_toggled",
                        codec="HEVC",
                        state=enabled_word(current_language(), hevc["enable"]),
                    )
                )

            elif choice3 == "2":
                print(t("settings.available_encoders"))
                print(" - libx265 (CPU, Default)")
                print(" - hevc_nvenc (NVIDIA GPU)")
                print(" - hevc_qsv (Intel GPU)")
                print(" - hevc_amf (AMD GPU)")
                print(" - hevc_vaapi (Linux VAAPI)")
                print(" - hevc_videotoolbox (macOS)")
                new_encoder = input(t("settings.prompt_encoder")).strip()
                if new_encoder in ALLOWED_ENCODERS:
                    hevc["encoder"] = new_encoder
                    save_config(config)
                else:
                    print(t("settings.invalid_encoder"))

            elif choice3 == "3":
                hevc["bitrate"] = normalize_bitrate(
                    input(t("settings.prompt_target_bitrate")), hevc["bitrate"]
                )
                save_config(config)

            elif choice3 == "4":
                hevc["max_bitrate"] = normalize_bitrate(
                    input(t("settings.prompt_max_bitrate")), hevc["max_bitrate"]
                )
                save_config(config)

            elif choice3 == "5":
                print(t("settings.hevc_preset_options"))
                print(t("settings.hevc_preset_note"))
                new_preset = input(t("settings.prompt_preset")).strip()
                if SAFE_FFMPEG_VALUE.fullmatch(new_preset):
                    hevc["preset"] = new_preset
                    save_config(config)
                else:
                    print(t("settings.invalid_preset"))

            elif choice3 == "6":
                break
            else:
                try_again()

    elif choice == "4":
        while True:
            av1 = config["av1_settings"]
            print_codec_settings("AV1", av1)
            print(t("settings.av1_menu"))
            choice4 = str(input(t("settings.prompt_choice"))).strip()

            if choice4 == "1":
                av1["enable"] = not av1["enable"]
                if av1["enable"]:
                    config["hevc_settings"]["enable"] = False
                save_config(config)
                print(
                    t(
                        "settings.encoding_toggled",
                        codec="AV1",
                        state=enabled_word(current_language(), av1["enable"]),
                    )
                )

            elif choice4 == "2":
                print(t("settings.available_encoders"))
                print(" - libsvtav1 (CPU, Default)")
                print(" - libaom-av1 (CPU)")
                print(" - av1_nvenc (NVIDIA GPU)")
                print(" - av1_qsv (Intel GPU)")
                print(" - av1_amf (AMD GPU)")
                print(" - av1_vaapi (Linux VAAPI)")
                new_encoder = input(t("settings.prompt_encoder")).strip()
                if new_encoder in ALLOWED_AV1_ENCODERS:
                    av1["encoder"] = new_encoder
                    save_config(config)
                else:
                    print(t("settings.invalid_encoder"))

            elif choice4 == "3":
                av1["bitrate"] = normalize_bitrate(
                    input(t("settings.prompt_target_bitrate")), av1["bitrate"]
                )
                save_config(config)

            elif choice4 == "4":
                av1["max_bitrate"] = normalize_bitrate(
                    input(t("settings.prompt_max_bitrate")), av1["max_bitrate"]
                )
                save_config(config)

            elif choice4 == "5":
                new_preset = input(t("settings.prompt_preset")).strip()
                if SAFE_FFMPEG_VALUE.fullmatch(new_preset):
                    av1["preset"] = new_preset
                    save_config(config)
                else:
                    print(t("settings.invalid_preset"))

            elif choice4 == "6":
                break
            else:
                try_again()

    elif choice == "5":
        while True:
            has_cookies = all(
                config["cookies"].get(name) for name in AUTH_COOKIE_NAMES
            )
            print("\n" + t("settings.cookie_title"))
            print(
                t(
                    "settings.cookie_status",
                    status=state_label(current_language(), has_cookies),
                )
            )
            print(t("settings.cookie_menu"))
            cookie_choice = str(input(t("settings.prompt_choice"))).strip()

            if cookie_choice == "1":
                print(t("settings.browser_menu"))
                browser_choice = str(
                    input(t("settings.prompt_choice"))
                ).strip()
                browser_option = BROWSER_LOGIN_OPTIONS.get(browser_choice)
                if browser_option is None:
                    if browser_choice != "4":
                        try_again()
                    continue

                browser, browser_name = browser_option
                print(
                    t(
                        "settings.browser_login_notice",
                        browser=browser_name,
                    )
                )
                import_cookies_from_browser(browser)

            elif cookie_choice == "2":
                ses = sanitize_cookie(input(t("settings.prompt_ses")))
                aut = sanitize_cookie(input(t("settings.prompt_aut")))
                config["cookies"]["NID_SES"] = ses
                config["cookies"]["NID_AUT"] = aut
                save_config(config)
                print(t("settings.cookies_saved"))

            elif cookie_choice == "3":
                config["cookies"] = {"NID_SES": "", "NID_AUT": ""}
                save_config(config)
                print(t("settings.cookies_deleted"))

            elif cookie_choice == "4":
                break
            else:
                try_again()

    elif choice == "6":
        while True:
            dns_settings = config["dns_settings"]
            print("\n" + t("settings.dns_title"))
            print(t("settings.status", status=state_label(current_language(), dns_settings["enable"])))
            print(t("settings.doh_url", url=dns_settings["doh_url"]))
            print("-" * 30)
            print(t("settings.dns_menu"))

            choice6 = str(input(t("settings.prompt_choice"))).strip()

            if choice6 == "1":
                dns_settings["enable"] = not dns_settings["enable"]
                save_config(config)
                print(
                    t(
                        "settings.dns_toggled",
                        state=enabled_word(current_language(), dns_settings["enable"]),
                    )
                )

            elif choice6 == "2":
                new_url = normalize_doh_url(input(t("settings.prompt_doh_url")))
                dns_settings["doh_url"] = new_url
                save_config(config)
                print(t("settings.doh_url_changed", url=new_url))

            elif choice6 == "3":
                dns_settings["doh_url"] = DEFAULT_DOH_URL
                save_config(config)
                print(t("settings.doh_url_reset", url=DEFAULT_DOH_URL))

            elif choice6 == "4":
                break
            else:
                try_again()

    elif choice == "7":
        config["log_enabled"] = not config["log_enabled"]
        save_config(config)
        print(
            t(
                "settings.logging_toggled",
                state=enabled_word(current_language(), config["log_enabled"]),
            )
        )

    elif choice == "8":
        print_language_menu()
        selected_language = select_language(input(t("settings.prompt_language")))
        if selected_language is None:
            print(t("settings.invalid_language"))
            continue
        config["language"] = selected_language
        save_config(config)
        print(
            t(
                "settings.language_changed",
                language=language_display_name(selected_language),
            )
        )

    elif choice == "9":
        print(t("settings.exiting"))
        break
    else:
        try_again()
