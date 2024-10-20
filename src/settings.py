import os
import json

# File path settings
script_directory = os.path.dirname(os.path.abspath(__name__)) + "/files"
channel_count_file_path = os.path.join(script_directory, "channel_count.txt")
channels_file_path = os.path.join(script_directory, "channels.json")
delays_file_path = os.path.join(script_directory, "delays.json")

# Define channels list
channels = []

# Save cookie info variable
def save_cookie_info(SES, AUT):
    cookie_data = {"NID_SES": SES, "NID_AUT": AUT}
    cookie_file_path = os.path.join(script_directory, "cookie.json")  # Fixed cookie file path
    with open(cookie_file_path, "w") as cookie_file:
        json.dump(cookie_data, cookie_file, indent=2)
    print("Cookie information has been successfully saved.")

# Load the number of channels
def load_channels():
    if os.path.exists(channels_file_path):
        with open(channels_file_path, "r") as f:
            channels = json.load(f)
            return channels, len(channels)
    return [], 0

# Load existing delay information
def load_delays():
    if os.path.exists(delays_file_path):
        with open(delays_file_path, "r") as f:
            return json.load(f)
    return {}

def try_again():
    print("Please try again.\n")

def add_channel(channel_count):    
    print("""Available Platform is: 
            1. twitch
            2. chzzk
          """)
    platform = int(input(": "))
    if platform == 1: 
        platform = "twitch"
        name = str(input("Enter the streamer name:  "))
        id = name
    elif platform == 2: 
        platform = "chzzk"
        id = str(input("Enter the unique ID of the streamer channel you want to add: "))
        name = str(input("Enter the streamer name:  "))

    while True:
        answer = str(input(f"id: {id}, name: {name} Is this correct? (Y/N): "))
        if answer == "Y":
            channel_count += 1
            identifier = f"ch{channel_count}"
            channels.append({
                "platform": platform,
                "id": id,
                "name": name,
                "output_dir": f"./recorded/{name}",
                "identifier": identifier,
                "active": "on",
            })
            delays[identifier] = channel_count - 1
            update_files(channel_count)
            break
        elif answer == "N":
            print("Then please enter it again")
            break
        else:
            try_again()

def delete_channel():
    print("Current channel list:")
    for channel in channels:
        print(f"id: {channel['id']}, name: {channel['name']}")

    channel_to_delete_ID = input("Enter the ID of the channel to delete: ")
    channel_to_delete_index = next((index for index, channel in enumerate(channels) if channel["id"] == channel_to_delete_ID), -1)

    if channel_to_delete_index != -1:
        deleted_channel = channels.pop(channel_to_delete_index)
        print(f"The deleted channel: id: {deleted_channel['id']}, name: {deleted_channel['name']}")
        update_files_after_deletion(channel_to_delete_ID)
    else:
        print(f"The channel with ID {channel_to_delete_ID} does not exist.")

def toggle_channel_recording():
    print("Current channel list:")
    for channel in channels:
        print(f"id: {channel['id']}, name: {channel['name']}, recording status: {'On' if channel.get('active', True) == 'on' else 'Off'}")

    channel_ID = input("Change the recording status of the channel ID:  ")
    for channel in channels:
        if channel["id"] == channel_ID:
            current_state = channel.get("active", "on")
            channel["active"] = "off" if current_state == "on" else "on"
            print(f"The recording status of {channel['name']} channel has been changed to {'Off' if current_state == 'on' else 'On'}.")
            update_channels_file()
            break
    else:
        print(f"The channel with ID {channel_ID} could not be found.")

def update_files(channel_count):
    with open(channels_file_path, "w") as f:
        json.dump(channels, f, indent=2)
    print("The channels.json file has been modified.")
    
    with open(delays_file_path, "w") as f:
        json.dump(delays, f, indent=2)
    
    print("The delays.json file has been modified.")
    
    with open(channel_count_file_path, "w") as f:
        f.write(str(channel_count))

def update_files_after_deletion(channel_to_delete_ID):
    global channel_count
    channel_count -= 1
    with open(channel_count_file_path, "w") as f:
        f.write(str(channel_count))
    delays.pop(channel_to_delete_ID, None)

    for idx, channel in enumerate(channels):
        channel["identifier"] = f"ch{idx + 1}"  # Reorder channel numbers

    with open(delays_file_path, "w") as f:
        delays_data = {f"ch{i+1}": i for i in range(len(channels))}
        json.dump(delays_data, f, indent=2)
    print("The delays.json file has been modified.")

    update_channels_file()

def update_channels_file():
    with open(channels_file_path, "w") as f:
        json.dump(channels, f, indent=2)
    print("The channels.json file has been re-modified.")

def recording_settings():
    while True:
        print("\n1. Set Recording Threads\n2. Set Broadcast Rescan Interval\n3. Go Back")
        choice2 = str(input("Enter the number you want to execute: "))

        if choice2 == "1":
            set_recording_threads()
        elif choice2 == "2":
            set_broadcast_rescan_interval()
        elif choice2 == "3":
            print("Returning to the menu")
            break
        else:
            try_again()

def set_recording_threads():
    thread_file_path = os.path.join(script_directory, "thread.txt")
    with open(thread_file_path, "r") as thread_file:
        threads = thread_file.readline().strip()
    print(f"The current number of recording threads is {threads}.")
    new_threads = str(input("Enter the number of threads to change: "))
    with open(thread_file_path, "w") as thread_file:
        thread_file.write(new_threads)
    print("The number of threads has been changed.")

def set_broadcast_rescan_interval():
    rescan_interval_file_path = os.path.join(script_directory, "time_sleep.txt")
    with open(rescan_interval_file_path, "r") as time_sleep_file:
        rescan_interval = time_sleep_file.readline().strip()
    print(f"The current broadcast rescan interval is {rescan_interval} seconds.")
    new_rescan_interval = str(input("Enter the rescan interval to change (in seconds): "))
    with open(rescan_interval_file_path, "w") as time_sleep_file:
        time_sleep_file.write(new_rescan_interval)
    print("The broadcast rescan interval has been changed.")

def main():
    global channels, delays, channel_count
    channels, channel_count = load_channels()
    delays = load_delays()

    while True:
        print(" Auto-Recording Settings")
        print("\n1. Channel Settings\n2. Recording Settings\n3. Cookie Settings (for adult verification)\n4. Quit")
        choice = str(input("Enter the number you want to execute: "))
        if choice == "1":
            while True:
                print("\n1. Add Channel\n2. Delete Channel\n3. Toggle Channel Recording\n4. Go Back")
                choice1 = str(input("Enter the number you want to execute: "))
                if choice1 == "1":
                    add_channel(channel_count)
                elif choice1 == "2":
                    delete_channel()
                elif choice1 == "3":
                    toggle_channel_recording()
                elif choice1 == "4":
                    print("Returning to the menu")
                    break
                else:
                    try_again()
        elif choice == "2":
            recording_settings()
        elif choice == "3":
            SES = str(input("Enter SES: "))
            AUT = str(input("Enter AUT: "))
            save_cookie_info(SES, AUT)
        elif choice == "4":
            print("Exiting the settings.")
            break
        else:
            print("Please try again.\n")

if __name__ == "__main__":
    main()
