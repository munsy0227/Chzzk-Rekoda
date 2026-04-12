import os
import json

# File path settings
script_directory = os.path.dirname(os.path.abspath(__file__))
config_file_path = os.path.join(script_directory, "config.json")

# Default Configuration
default_config = {
    "channels": [],
    "delays": {},
    "timeout": 60,
    "stream_segment_threads": 2,
    "hevc_settings": {
        "enable": False,
        "encoder": "libx265",
        "bitrate": "2500k",
        "max_bitrate": "10000k",
        "preset": "ultrafast",
    },
    "log_enabled": True,
    "cookies": {"NID_SES": "", "NID_AUT": ""},
}


def load_config():
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Merge with default config to ensure all keys exist
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading config.json: {e}. Using defaults/migration.")

    # Migration Logic (if config.json doesn't exist or failed to load)
    print("Migrating settings from old files...")
    config = default_config.copy()

    # 1. Channels
    channels_path = os.path.join(script_directory, "channels.json")
    if os.path.exists(channels_path):
        try:
            with open(channels_path, "r") as f:
                config["channels"] = json.load(f)
        except:
            pass

    # 2. Delays
    delays_path = os.path.join(script_directory, "delays.json")
    if os.path.exists(delays_path):
        try:
            with open(delays_path, "r") as f:
                config["delays"] = json.load(f)
        except:
            pass

    # 3. Timeout (time_sleep.txt)
    time_path = os.path.join(script_directory, "time_sleep.txt")
    if os.path.exists(time_path):
        try:
            with open(time_path, "r") as f:
                val = f.readline().strip()
                if val.isdigit():
                    config["timeout"] = int(val)
        except:
            pass

    # 4. Threads
    thread_path = os.path.join(script_directory, "thread.txt")
    if os.path.exists(thread_path):
        try:
            with open(thread_path, "r") as f:
                val = f.readline().strip()
                if val.isdigit():
                    config["stream_segment_threads"] = int(val)
        except:
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
        except:
            pass

    # 6. Log Enabled
    log_path = os.path.join(script_directory, "log_enabled.txt")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                config["log_enabled"] = f.readline().strip().lower() == "true"
        except:
            pass

    # 7. Cookies
    cookie_path = os.path.join(script_directory, "cookie.json")
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, "r") as f:
                cookie_data = json.load(f)
                config["cookies"] = cookie_data
        except:
            pass

    # Save migrated config
    save_config(config)
    return config


def save_config(config):
    try:
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("Configuration saved to config.json")
    except OSError as e:
        print(f"Error saving configuration: {e}")


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
        "\n4. Cookie Settings (for adult verification)"
        "\n5. Toggle Logging"
        "\n6. Quit"
    )
    choice = str(input("Enter the number you want to execute: "))

    if choice == "1":
        while True:
            print(
                "\n1. Add Channel\n2. Delete Channel\n3. Toggle Channel Recording\n4. Go Back"
            )
            choice1 = str(input("Enter the number you want to execute: "))
            if choice1 == "1":
                id = str(
                    input(
                        "Enter the unique ID of the streamer channel you want to add: "
                    )
                )
                name = str(input("Enter the streamer name:  "))
                output_dir = str(
                    input(
                        "Specify the storage path (just type the name to save it in the same location as the program): "
                    )
                )

                while True:
                    answer = str(
                        input(
                            f"id: {id}, name: {name}, storage path: {output_dir} Is this correct? (Y/N): "
                        )
                    )
                    if answer == "Y" or answer == "y":
                        # Determine next channel identifier
                        current_count = len(config["channels"])
                        identifier = f"ch{current_count + 1}"

                        config["channels"].append(
                            {
                                "id": id,
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
                "\n1. Set Recording Threads\n2. Set Broadcast Rescan Interval\n3. Go Back"
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
                    new_threads = int(input("Enter the number of threads to change: "))
                    config["stream_segment_threads"] = new_threads
                    save_config(config)
                    print("The number of threads has been changed.")
                except ValueError:
                    print("Invalid input.")

            elif choice2 == "2":
                print(
                    f"The current broadcast rescan interval is {config.get('timeout', 60)} seconds."
                )
                try:
                    new_timeout = int(
                        input("Enter the rescan interval to change (in seconds): ")
                    )
                    config["timeout"] = new_timeout
                    save_config(config)
                    print("The broadcast rescan interval has been changed.")
                except ValueError:
                    print("Invalid input.")

            elif choice2 == "3":
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
                if new_encoder:
                    hevc["encoder"] = new_encoder
                    save_config(config)

            elif choice3 == "3":
                new_bitrate = input("Enter target bitrate (e.g., 6000k): ")
                if not new_bitrate.endswith("k"):
                    new_bitrate += "k"
                hevc["bitrate"] = new_bitrate
                save_config(config)

            elif choice3 == "4":
                new_max = input("Enter max bitrate (e.g., 10000k): ")
                if not new_max.endswith("k"):
                    new_max += "k"
                hevc["max_bitrate"] = new_max
                save_config(config)

            elif choice3 == "5":
                print(
                    "Options: ultrafast (rec), superfast, veryfast, faster, fast, medium"
                )
                print("Note: For NVENC, use p1-p7. For QSV, use veryfast-veryslow.")
                new_preset = input("Enter preset name: ")
                hevc["preset"] = new_preset
                save_config(config)

            elif choice3 == "6":
                break
            else:
                try_again()

    elif choice == "4":
        SES = str(input("Enter SES: "))
        AUT = str(input("Enter AUT: "))
        config["cookies"]["NID_SES"] = SES
        config["cookies"]["NID_AUT"] = AUT
        save_config(config)
        print("Cookie information has been successfully saved.")

    elif choice == "5":
        config["log_enabled"] = not config["log_enabled"]
        save_config(config)
        print(f"Logging has been {'enabled' if config['log_enabled'] else 'disabled'}.")

    elif choice == "6":
        print("Exiting the settings.")
        break
    else:
        print("Please try again.\n")
