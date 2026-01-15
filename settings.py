import os
import json

# File path settings
script_directory = os.path.dirname(os.path.abspath(__name__))
channel_count_file_path = os.path.join(script_directory, "channel_count.txt")
channels_file_path = os.path.join(script_directory, "channels.json")
delays_file_path = os.path.join(script_directory, "delays.json")
log_enabled_file_path = os.path.join(script_directory, "log_enabled.txt")
hevc_file_path = os.path.join(script_directory, "hevc.json")

# Define channels list
channels = []

# Initialize log enabled setting
if os.path.exists(log_enabled_file_path):
    with open(log_enabled_file_path, "r") as f:
        log_enabled = f.readline().strip().lower() == "true"
else:
    log_enabled = True  # Default to logging enabled


# Save cookie info variable
def save_cookie_info(SES, AUT):
    cookie_data = {"NID_SES": SES, "NID_AUT": AUT}
    cookie_file_path = "cookie.json"  # Cookie file path setting
    with open(cookie_file_path, "w") as cookie_file:
        json.dump(cookie_data, cookie_file, indent=2)
    print("Cookie information has been successfully saved.")


# Load the number of channels
if os.path.exists(channels_file_path):
    with open(channels_file_path, "r") as f:
        channels = json.load(f)
    channel_count = len(channels)
else:
    channel_count = 0

# Load existing delay information
if os.path.exists(delays_file_path):
    with open(delays_file_path, "r") as f:
        delays = json.load(f)
else:
    delays = {}


def load_hevc_settings():
    default_settings = {
        "enable": False,
        "bitrate": "2500k",
        "max_bitrate": "10000k",
        "preset": "ultrafast",
    }
    if os.path.exists(hevc_file_path):
        try:
            with open(hevc_file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default_settings
    return default_settings


def save_hevc_settings(settings):
    with open(hevc_file_path, "w") as f:
        json.dump(settings, f, indent=2)
    print("HEVC settings have been saved.")


def try_again():
    print("Please try again.\n")


def toggle_logging():
    global log_enabled
    log_enabled = not log_enabled
    with open(log_enabled_file_path, "w") as f:
        f.write("true" if log_enabled else "false")
    print(f"Logging has been {'enabled' if log_enabled else 'disabled'}.")


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
                    if answer == "Y":
                        channel_count += 1
                        identifier = f"ch{channel_count}"
                        channels.append(
                            {
                                "id": id,
                                "name": name,
                                "output_dir": output_dir,
                                "identifier": identifier,
                                "active": "on",
                            }
                        )
                        delays[identifier] = channel_count - 1

                        # Add data to the file
                        with open(channels_file_path, "w") as f:
                            json.dump(channels, f, indent=2)
                        print("The channels.json file has been modified.")
                        with open(delays_file_path, "w") as f:
                            json.dump(delays, f, indent=2)
                        print("The delays.json file has been modified.")
                        with open(channel_count_file_path, "w") as f:
                            f.write(str(channel_count))
                        break
                    elif answer == "N":
                        print("Then please enter it again")
                        break
                    else:
                        try_again()

            elif choice1 == "2":
                # Delete channel
                if len(channels) == 0:
                    print("No channels to delete.")
                    continue

                print("Current channel list:")
                for idx, channel in enumerate(channels, start=1):
                    print(f"{idx}. id: {channel['id']}, name: {channel['name']}")

                try:
                    channel_to_delete_index = (
                        int(input("Enter the number of the channel to delete: ")) - 1
                    )
                    if 0 <= channel_to_delete_index < len(channels):
                        deleted_channel = channels.pop(channel_to_delete_index)
                        print(
                            f"The deleted channel: id: {deleted_channel['id']}, name: {deleted_channel['name']}"
                        )
                        # Add data to the file
                        with open(channels_file_path, "w") as f:
                            json.dump(channels, f, indent=2)
                        print("The channels.json file has been modified.")
                        # Modify channel_count
                        channel_count -= 1
                        with open(channel_count_file_path, "w") as f:
                            f.write(str(channel_count))
                        # Modify delays
                        delays.pop(deleted_channel["identifier"], None)
                        for idx, channel in enumerate(channels):
                            channel["identifier"] = (
                                f"ch{idx + 1}"  # Reorder channel numbers
                            )
                        with open(delays_file_path, "w") as f:
                            delays_data = {f"ch{i+1}": i for i in range(len(channels))}
                            json.dump(delays_data, f, indent=2)
                        print("The delays.json file has been modified.")
                        # Apply identifier changes in channels.json even after deleting the channel
                        with open(channels_file_path, "w") as f:
                            json.dump(channels, f, indent=2)
                        print("The channels.json file has been re-modified.")
                    else:
                        print("Invalid channel number.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            elif choice1 == "3":
                if len(channels) == 0:
                    print("No channels available to toggle.")
                    continue

                print("Current channel list:")
                for idx, channel in enumerate(channels, start=1):
                    print(
                        f"{idx}. id: {channel['id']}, name: {channel['name']}, recording status: {'On' if channel.get('active', True) == 'on' else 'Off'}"
                    )

                try:
                    channel_index = (
                        int(
                            input(
                                "Enter the number of the channel to toggle recording status: "
                            )
                        )
                        - 1
                    )
                    if 0 <= channel_index < len(channels):
                        channel = channels[channel_index]
                        current_state = channel.get("active", "on")
                        channel["active"] = "off" if current_state == "on" else "on"
                        print(
                            f"The recording status of {channel['name']} channel has been changed to {'Off' if current_state == 'on' else 'On'}."
                        )
                        # Add data to the file
                        with open(channels_file_path, "w") as f:
                            json.dump(channels, f, indent=2)
                        print("The channels.json file has been modified.")
                    else:
                        print("Invalid channel number.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            elif choice1 == "4":
                print("Returning to the menu")
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
                thread_file_path = os.path.join(script_directory, "thread.txt")
                if os.path.exists(thread_file_path):
                    with open(thread_file_path, "r") as thread_file:
                        threads = thread_file.readline().strip()
                else:
                    threads = "2"
                print(f"The current number of recording threads is {threads}.")
                print(
                    "Recommended 2~4 threads, 2 threads for low-end systems / 4 threads for high-end systems"
                )
                new_threads = str(input("Enter the number of threads to change: "))
                with open(thread_file_path, "w") as thread_file:
                    thread_file.write(new_threads)
                print("The number of threads has been changed.")

            elif choice2 == "2":
                rescan_interval_file_path = os.path.join(
                    script_directory, "time_sleep.txt"
                )
                if os.path.exists(rescan_interval_file_path):
                    with open(rescan_interval_file_path, "r") as time_sleep_file:
                        rescan_interval = time_sleep_file.readline().strip()
                else:
                    rescan_interval = "60"
                print(
                    f"The current broadcast rescan interval is {rescan_interval} seconds."
                )
                new_rescan_interval = str(
                    input("Enter the rescan interval to change (in seconds): ")
                )
                with open(rescan_interval_file_path, "w") as time_sleep_file:
                    time_sleep_file.write(new_rescan_interval)
                print("The broadcast rescan interval has been changed.")

            elif choice2 == "3":
                print("Returning to the menu")
                break

            else:
                try_again()

    elif choice == "3":
        while True:
            hevc_settings = load_hevc_settings()
            print("\n--- HEVC (H.265) Settings ---")
            print(f"Status: {'[Enabled]' if hevc_settings['enable'] else '[Disabled]'}")
            print(f"Target Bitrate: {hevc_settings['bitrate']}")
            print(f"Max Bitrate: {hevc_settings['max_bitrate']}")
            print(f"Preset: {hevc_settings['preset']}")
            print("-" * 30)
            print("1. Toggle Enable/Disable")
            print("2. Set Target Bitrate (e.g., 6000k)")
            print("3. Set Max Bitrate (e.g., 8000k)")
            print("4. Set Preset (ultrafast, superfast, etc.)")
            print("5. Go Back")

            choice3 = str(input("Enter the number you want to execute: "))

            if choice3 == "1":
                hevc_settings["enable"] = not hevc_settings["enable"]
                save_hevc_settings(hevc_settings)
                print(
                    f"HEVC encoding has been {'enabled' if hevc_settings['enable'] else 'disabled'}."
                )

            elif choice3 == "2":
                new_bitrate = input("Enter target bitrate (e.g., 6000k): ")
                if not new_bitrate.endswith("k"):
                    new_bitrate += "k"
                hevc_settings["bitrate"] = new_bitrate
                save_hevc_settings(hevc_settings)

            elif choice3 == "3":
                new_max = input("Enter max bitrate (e.g., 10000k): ")
                if not new_max.endswith("k"):
                    new_max += "k"
                hevc_settings["max_bitrate"] = new_max
                save_hevc_settings(hevc_settings)

            elif choice3 == "4":
                print(
                    "Options: ultrafast (rec), superfast, veryfast, faster, fast, medium"
                )
                new_preset = input("Enter preset name: ")
                hevc_settings["preset"] = new_preset
                save_hevc_settings(hevc_settings)

            elif choice3 == "5":
                break
            else:
                try_again()

    elif choice == "4":
        SES = str(input("Enter SES: "))
        AUT = str(input("Enter AUT: "))
        save_cookie_info(SES, AUT)

    elif choice == "5":
        toggle_logging()

    elif choice == "6":
        print("Exiting the settings.")
        break
    else:
        print("Please try again.\n")
