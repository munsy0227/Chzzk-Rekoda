import os
import json

# File path settings
script_directory = os.path.dirname(os.path.abspath(__name__))
channel_count_file_path = os.path.join(script_directory, "channel_count.txt")
channels_file_path = os.path.join(script_directory, "channels.json")
delays_file_path = os.path.join(script_directory, "delays.json")

# Define channels list
channels = []


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


def try_again():
    print("Please try again.\n")


while True:
    print("Chzzk Auto-Recording Settings")
    print(
        "\n1. Channel Settings\n2. Recording Settings\n3. Cookie Settings (for adult verification)\n4. Quit"
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
                            f.write(
                                "\n"
                            )  # Add a newline character to save each channel as a separate line
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
                print("Current channel list:")
                for channel in channels:
                    print(f"id: {channel['id']}, name: {channel['name']}")

                channel_to_delete_ID = input("Enter the ID of the channel to delete: ")
                channel_to_delete_index = -1
                for index, channel in enumerate(channels):
                    if channel["id"] == channel_to_delete_ID:
                        channel_to_delete_index = index
                        break
                if channel_to_delete_index != -1:
                    deleted_channel = channels.pop(channel_to_delete_index)
                    print(
                        f"The deleted channel: id: {deleted_channel['id']}, name: {deleted_channel['name']}"
                    )
                    # Add data to the file
                    with open(channels_file_path, "w") as f:
                        json.dump(channels, f, indent=2)
                        f.write(
                            "\n"
                        )  # Add a newline character to save each channel as a separate line
                    print("The channels.json file has been modified.")
                    # Modify channel_count
                    channel_count -= 1
                    with open(channel_count_file_path, "w") as f:
                        f.write(str(channel_count))
                    # Modify delays
                    delays.pop(
                        channel_to_delete_ID, None
                    )  # Remove dictionary item corresponding to the deleted channel ID
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
                        f.write(
                            "\n"
                        )  # Add a newline character to save each channel as a separate line
                    print("The channels.json file has been re-modified.")
                else:
                    print(f"The channel with ID {channel_to_delete_ID} does not exist.")

            elif choice1 == "3":
                print("Current channel list:")
                for channel in channels:
                    print(
                        f"id: {channel['id']}, name: {channel['name']}, recording status: {'On' if channel.get('active', True) == 'on' else 'Off'}"
                    )

                channel_ID = input("Change the recording status of the channel ID:  ")
                for channel in channels:
                    if channel["id"] == channel_ID:
                        current_state = channel.get("active", "on")
                        channel["active"] = "off" if current_state == "on" else "on"
                        print(
                            f"The recording status of {channel['name']} channel has been changed to {'Off' if current_state == 'on' else 'On'}."
                        )
                        # Add data to the file
                        with open(channels_file_path, "w") as f:
                            json.dump(channels, f, indent=2)
                            f.write(
                                "\n"
                            )  # Add a newline character to save each channel as a separate line
                        print("The channels.json file has been modified.")
                        break
                else:
                    print(f"The channel with ID {channel_ID} could not be found.")

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
                with open(thread_file_path, "r") as thread_file:
                    threads = thread_file.readline().strip()
                print(f"The current number of recording threads is {threads}.")
                print(
                    "Recommended 2~4 threads, 2 threads for low-end systems / 4 threads for high-end systems"
                )
                new_threads = str(input("Enter the number of threads to change: "))
                # TODO: Apply the entered value to the threads variable
                with open(thread_file_path, "w") as thread_file:
                    thread_file.write(new_threads)
                print("The number of threads has been changed.")

            elif choice2 == "2":
                rescan_interval_file_path = os.path.join(
                    script_directory, "time_sleep.txt"
                )
                with open(rescan_interval_file_path, "r") as time_sleep_file:
                    rescan_interval = time_sleep_file.readline().strip()
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
        SES = str(input("Enter SES: "))
        AUT = str(input("Enter AUT: "))
        save_cookie_info(SES, AUT)

    elif choice == "4":
        print("Exiting the settings.")
        break
    else:
        print("Please try again.\n")
