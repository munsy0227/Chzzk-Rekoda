import subprocess

# Define the list of channel IDs
channels = [
   "22406972"
]

# Function to run a command and capture its output
def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode().strip()
    except subprocess.CalledProcessError as e:
        print(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.")
        return None

# Iterate over the channels
for channel in channels:
    # Run streamlink, pipe to ffprobe, and filter with jq
    streamlink_command = (
        f"streamlink --stdout -l none \"https://live.bilibili.com/{channel}?live_from=78001\" best  "
        f"| ffprobe -v error -of json -show_streams - "
        f"| jq -r '.streams[] | select(.codec_name == \"h264\") | \"\\(.width)x\\(.height)\"'"
    )
    resolution = run_command(streamlink_command)
    if resolution:
        print(f"Channel {channel} resolution: {resolution}")
