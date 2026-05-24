import os
import json
import re
import tempfile
from copy import deepcopy

# File path settings
script_directory = os.path.dirname(os.path.abspath(__file__))
config_file_path = os.path.join(script_directory, "config.json")

# Default Configuration
DEFAULT_RESCAN_INTERVAL_SECONDS = 60
MIN_RESCAN_INTERVAL_SECONDS = 1
MAX_RESCAN_INTERVAL_SECONDS = 3600
DEFAULT_OUTPUT_FORMAT = "ts"
ALLOWED_OUTPUT_FORMATS = {"ts", "mkv", "webm"}

default_config = {
    "channels": [],
    "delays": {},
    "timeout": DEFAULT_RESCAN_INTERVAL_SECONDS,
    "stream_segment_threads": 2,
    "output_format": DEFAULT_OUTPUT_FORMAT,
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
}


SAFE_CHANNEL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SAFE_FFMPEG_VALUE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
SAFE_BITRATE = re.compile(r"^\d+[kKmM]?$")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
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


def normalize_config(config):
    config = deep_merge_defaults(config, default_config)
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

    channels = []
    for index, channel in enumerate(config.get("channels", []), start=1):
        if not isinstance(channel, dict):
            continue
        channel_id = str(channel.get("id", "")).strip()
        if not SAFE_CHANNEL_ID.fullmatch(channel_id):
            print(f"Skipping invalid channel id: {channel_id}")
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
            print(f"Error loading config.json: {e}. Using defaults/migration.")

    # Migration Logic (if config.json doesn't exist or failed to load)
    print("Migrating settings from old files...")
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
        print("Configuration saved to config.json")
    except OSError as e:
        print(f"Error saving configuration: {e}")
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

while True:
    print("Chzzk Auto-Recording Settings")
    print(
        "\n1. Channel Settings"
        "\n2. Recording Settings"
        "\n3. HEVC Settings (High Efficiency Video Coding)"
        "\n4. AV1 Settings"
        "\n5. Cookie Settings (for adult verification)"
        "\n6. Toggle Logging"
        "\n7. Quit"
    )
    choice = str(input("Enter the number you want to execute: "))

    if choice == "1":
        while True:
            print(
                "\n1. Add Channel\n2. Delete Channel\n3. Toggle Channel Recording\n4. Go Back"
            )
            choice1 = str(input("Enter the number you want to execute: "))
            if choice1 == "1":
                channel_id = str(
                    input(
                        "Enter the unique ID of the streamer channel you want to add: "
                    )
                ).strip()
                if not SAFE_CHANNEL_ID.fullmatch(channel_id):
                    print("Invalid channel ID. Use only letters, numbers, '_' or '-'.")
                    continue
                name = CONTROL_CHARS.sub("", str(input("Enter the streamer name:  "))).strip() or channel_id
                output_dir = str(
                    input(
                        "Specify the storage path (just type the name to save it in the same location as the program): "
                    )
                ).strip() or "."

                while True:
                    answer = str(
                        input(
                            f"id: {channel_id}, name: {name}, storage path: {output_dir} Is this correct? (Y/N): "
                        )
                    )
                    if answer == "Y" or answer == "y":
                        # Determine next channel identifier
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

                        # Add delay entry
                        config["delays"][
                            identifier
                        ] = current_count  # default delay logic

                        save_config(config)
                        print("Channel added and config saved.")
                        break
                    elif answer == "N" or answer == "n":
                        print("Then please enter it again")
                        break
                    else:
                        try_again()

            elif choice1 == "2":
                if not config["channels"]:
                    print("No channels to delete.")
                    continue

                print("Current channel list:")
                for idx, channel in enumerate(config["channels"], start=1):
                    print(f"{idx}. id: {channel['id']}, name: {channel['name']}")

                try:
                    idx_to_del = (
                        int(input("Enter the number of the channel to delete: ")) - 1
                    )
                    if 0 <= idx_to_del < len(config["channels"]):
                        deleted_channel = config["channels"].pop(idx_to_del)
                        print(
                            f"The deleted channel: id: {deleted_channel['id']}, name: {deleted_channel['name']}"
                        )

                        # Rebuild delays and identifiers
                        new_delays = {}
                        for i, channel in enumerate(config["channels"]):
                            new_identifier = f"ch{i + 1}"
                            channel["identifier"] = new_identifier
                            new_delays[new_identifier] = i

                        config["delays"] = new_delays
                        save_config(config)
                        print("Channel deleted and config re-indexed.")
                    else:
                        print("Invalid channel number.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            elif choice1 == "3":
                if not config["channels"]:
                    print("No channels available to toggle.")
                    continue

                print("Current channel list:")
                for idx, channel in enumerate(config["channels"], start=1):
                    print(
                        f"{idx}. id: {channel['id']}, name: {channel['name']}, recording status: {'On' if channel.get('active', 'on') == 'on' else 'Off'}"
                    )

                try:
                    idx_to_toggle = (
                        int(
                            input(
                                "Enter the number of the channel to toggle recording status: "
                            )
                        )
                        - 1
                    )
                    if 0 <= idx_to_toggle < len(config["channels"]):
                        channel = config["channels"][idx_to_toggle]
                        current_state = channel.get("active", "on")
                        channel["active"] = "off" if current_state == "on" else "on"
                        print(
                            f"The recording status of {channel['name']} channel has been changed to {'Off' if current_state == 'on' else 'On'}."
                        )
                        save_config(config)
                    else:
                        print("Invalid channel number.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            elif choice1 == "4":
                break
            else:
                try_again()

    elif choice == "2":
        while True:
            print(
                "\n1. Set Recording Threads\n2. Set Broadcast Rescan Interval\n3. Set Output Format\n4. Go Back"
            )
            choice2 = str(input("Enter the number you want to execute: "))

            if choice2 == "1":
                print(
                    f"The current number of recording threads is {config.get('stream_segment_threads', 2)}."
                )
                print(
                    "Recommended 2~4 threads, 2 threads for low-end systems / 4 threads for high-end systems"
                )
                try:
                    new_threads = clamp_int(
                        input("Enter the number of threads to change: "), 2, 1, 16
                    )
                    config["stream_segment_threads"] = new_threads
                    save_config(config)
                    print("The number of threads has been changed.")
                except ValueError:
                    print("Invalid input.")

            elif choice2 == "2":
                print(
                    f"The current broadcast rescan interval is {config.get('timeout', DEFAULT_RESCAN_INTERVAL_SECONDS)} seconds."
                )
                try:
                    new_timeout = clamp_int(
                        input("Enter the rescan interval to change (in seconds): "),
                        DEFAULT_RESCAN_INTERVAL_SECONDS,
                        MIN_RESCAN_INTERVAL_SECONDS,
                        MAX_RESCAN_INTERVAL_SECONDS,
                    )
                    config["timeout"] = new_timeout
                    save_config(config)
                    print("The broadcast rescan interval has been changed.")
                except ValueError:
                    print("Invalid input.")

            elif choice2 == "3":
                current_format = config.get("output_format", DEFAULT_OUTPUT_FORMAT)
                print(f"The current output format is {current_format}.")
                print("Available formats: ts, mkv, webm")
                new_format = normalize_output_format(
                    input("Enter the output format to change: ")
                )
                config["output_format"] = new_format
                save_config(config)
                print(f"The output format has been changed to {new_format}.")

            elif choice2 == "4":
                break
            else:
                try_again()

    elif choice == "3":
        while True:
            hevc = config["hevc_settings"]
            print("\n--- HEVC (H.265) Settings ---")
            print(f"Status: {'[Enabled]' if hevc['enable'] else '[Disabled]'}")
            print(f"Encoder: {hevc.get('encoder', 'libx265')}")
            print(f"Target Bitrate: {hevc['bitrate']}")
            print(f"Max Bitrate: {hevc['max_bitrate']}")
            print(f"Preset: {hevc['preset']}")
            print("-" * 30)
            print("1. Toggle Enable/Disable")
            print("2. Set Encoder (libx265, hevc_nvenc, hevc_qsv, etc.)")
            print("3. Set Target Bitrate (e.g., 6000k)")
            print("4. Set Max Bitrate (e.g., 8000k)")
            print("5. Set Preset (ultrafast, superfast, etc.)")
            print("6. Go Back")

            choice3 = str(input("Enter the number you want to execute: "))

            if choice3 == "1":
                hevc["enable"] = not hevc["enable"]
                if hevc["enable"]:
                    config["av1_settings"]["enable"] = False
                save_config(config)
                print(
                    f"HEVC encoding has been {'enabled' if hevc['enable'] else 'disabled'}."
                )

            elif choice3 == "2":
                print("\nAvailable Encoders:")
                print(" - libx265 (CPU, Default)")
                print(" - hevc_nvenc (NVIDIA GPU)")
                print(" - hevc_qsv (Intel GPU)")
                print(" - hevc_amf (AMD GPU)")
                print(" - hevc_vaapi (Linux VAAPI)")
                print(" - hevc_videotoolbox (macOS)")
                new_encoder = input("Enter encoder name: ").strip()
                if new_encoder in ALLOWED_ENCODERS:
                    hevc["encoder"] = new_encoder
                    save_config(config)
                else:
                    print("Invalid encoder name.")

            elif choice3 == "3":
                new_bitrate = normalize_bitrate(
                    input("Enter target bitrate (e.g., 6000k): "), hevc["bitrate"]
                )
                hevc["bitrate"] = new_bitrate
                save_config(config)

            elif choice3 == "4":
                new_max = normalize_bitrate(
                    input("Enter max bitrate (e.g., 10000k): "), hevc["max_bitrate"]
                )
                hevc["max_bitrate"] = new_max
                save_config(config)

            elif choice3 == "5":
                print(
                    "Options: ultrafast (rec), superfast, veryfast, faster, fast, medium"
                )
                print("Note: For NVENC, use p1-p7. For QSV, use veryfast-veryslow.")
                new_preset = input("Enter preset name: ").strip()
                if SAFE_FFMPEG_VALUE.fullmatch(new_preset):
                    hevc["preset"] = new_preset
                    save_config(config)
                else:
                    print("Invalid preset name.")

            elif choice3 == "6":
                break
            else:
                try_again()

    elif choice == "4":
        while True:
            av1 = config["av1_settings"]
            print("\n--- AV1 Settings ---")
            print(f"Status: {'[Enabled]' if av1['enable'] else '[Disabled]'}")
            print(f"Encoder: {av1.get('encoder', 'libsvtav1')}")
            print(f"Target Bitrate: {av1['bitrate']}")
            print(f"Max Bitrate: {av1['max_bitrate']}")
            print(f"Preset: {av1['preset']}")
            print("-" * 30)
            print("1. Toggle Enable/Disable")
            print("2. Set Encoder (libsvtav1, libaom-av1, av1_nvenc, etc.)")
            print("3. Set Target Bitrate (e.g., 6000k)")
            print("4. Set Max Bitrate (e.g., 8000k)")
            print("5. Set Preset (libsvtav1/libaom-av1: 0-13, NVENC: p1-p7)")
            print("6. Go Back")

            choice4 = str(input("Enter the number you want to execute: "))

            if choice4 == "1":
                av1["enable"] = not av1["enable"]
                if av1["enable"]:
                    config["hevc_settings"]["enable"] = False
                save_config(config)
                print(
                    f"AV1 encoding has been {'enabled' if av1['enable'] else 'disabled'}."
                )

            elif choice4 == "2":
                print("\nAvailable Encoders:")
                print(" - libsvtav1 (CPU, Default)")
                print(" - libaom-av1 (CPU)")
                print(" - av1_nvenc (NVIDIA GPU)")
                print(" - av1_qsv (Intel GPU)")
                print(" - av1_amf (AMD GPU)")
                print(" - av1_vaapi (Linux VAAPI)")
                new_encoder = input("Enter encoder name: ").strip()
                if new_encoder in ALLOWED_AV1_ENCODERS:
                    av1["encoder"] = new_encoder
                    save_config(config)
                else:
                    print("Invalid encoder name.")

            elif choice4 == "3":
                new_bitrate = normalize_bitrate(
                    input("Enter target bitrate (e.g., 6000k): "), av1["bitrate"]
                )
                av1["bitrate"] = new_bitrate
                save_config(config)

            elif choice4 == "4":
                new_max = normalize_bitrate(
                    input("Enter max bitrate (e.g., 10000k): "), av1["max_bitrate"]
                )
                av1["max_bitrate"] = new_max
                save_config(config)

            elif choice4 == "5":
                new_preset = input("Enter preset name: ").strip()
                if SAFE_FFMPEG_VALUE.fullmatch(new_preset):
                    av1["preset"] = new_preset
                    save_config(config)
                else:
                    print("Invalid preset name.")

            elif choice4 == "6":
                break
            else:
                try_again()

    elif choice == "5":
        SES = sanitize_cookie(input("Enter SES: "))
        AUT = sanitize_cookie(input("Enter AUT: "))
        config["cookies"]["NID_SES"] = SES
        config["cookies"]["NID_AUT"] = AUT
        save_config(config)
        print("Cookie information has been successfully saved.")

    elif choice == "6":
        config["log_enabled"] = not config["log_enabled"]
        save_config(config)
        print(f"Logging has been {'enabled' if config['log_enabled'] else 'disabled'}.")

    elif choice == "7":
        print("Exiting the settings.")
        break
    else:
        print("Please try again.\n")
