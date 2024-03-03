import json
import subprocess
import time
import re
import os
import requests
import logging
from threading import Thread

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
STREAMLINK_PATH = os.path.join(os.path.dirname(__file__), "venv", "bin", "streamlink")
FFMPEG_PATH = "/usr/bin/ffmpeg"
LIVE_DETAIL_API = "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
TIME_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'time_sleep.txt')
THREAD_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thread.txt')
CHANNELS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'channels.json')
DELAYS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'delays.json')
COOKIE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookie.json')

# Load Configuration
def load_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

time_file_content = load_json(TIME_FILE_PATH)
TIMEOUT = time_file_content if isinstance(time_file_content, int) else int(time_file_content.get("timeout", 60))
thread_file_content = load_json(THREAD_FILE_PATH)
STREAM_SEGMENT_THREADS = thread_file_content if isinstance(thread_file_content, int) else int(thread_file_content.get("threads", 2))
CHANNELS = load_json(CHANNELS_FILE_PATH)
DELAYS = load_json(DELAYS_FILE_PATH)

# Helper Functions
def get_auth_headers(cookies):
    return {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
        'Cookie': f'NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}'
    }

def get_session_cookies():
    with open(COOKIE_FILE_PATH, 'r') as cookie_file:
        return json.load(cookie_file)

def get_live_info(channel, headers):
    try:
        response = requests.get(LIVE_DETAIL_API.format(channel_id=channel["id"]), headers=headers)
        response.raise_for_status()
        return response.json().get("content", {})
    except requests.RequestException as e:
        logger.error(f"Failed to fetch live info for {channel['name']}: {e}")
        return None

# Main Recording Function
def record_stream(channel, headers):
    delay = DELAYS.get(channel.get("identifier"), 0)
    time.sleep(delay)

    if channel.get("active", "on") == "off":
        logger.info(f"{channel['name']} channel is inactive. Skipping recording.")
        return

    while True:
        live_info = get_live_info(channel, headers)

        if live_info and live_info.get("status") == "OPEN":
            channel_name = live_info.get("channel", {}).get("channelName")
            live_title = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", '', live_info.get("liveTitle").rstrip())
            current_time = time.strftime("%Y-%m-%d_%H:%M:%S")

            output_file = f"[{current_time}] {channel_name} {live_title}.ts"
            live_playback_json = json.loads(live_info.get("livePlaybackJson") or "{}").get("media", [])

            if live_playback_json:
                stream_url = live_playback_json[0].get("path", "")

                if stream_url:
                    try:
                        process = subprocess.Popen([
                            STREAMLINK_PATH, stream_url, "best", "--hls-live-restart",
                            "--stream-segment-threads", str(STREAM_SEGMENT_THREADS), "-o",
                            os.path.join(channel['output_dir'], output_file), "--ffmpeg-ffmpeg",
                            FFMPEG_PATH, "--ffmpeg-copyts"
                        ], stdout=subprocess.PIPE, universal_newlines=True)

                        # Display standard output in the terminal
                        for line in iter(process.stdout.readline, ''):
                            print(line, end='')

                        process.stdout.close()
                        return_code = process.wait()

                        if return_code != 0:
                            logger.error(f"Error occurred while recording {channel['name']}: subprocess returned non-zero exit code {return_code}")
                    except Exception as e:
                        logger.error(f"Error occurred while recording {channel['name']}: {e}")
            else:
                logger.info(f"{channel['name']} channel has no media information. Assuming the broadcast has ended.")
        else:
            logger.info(f"{channel['name']} channel is not live.")

        time.sleep(TIMEOUT)

# Main Function
def main():
    headers = get_auth_headers(get_session_cookies())
    threads = [Thread(target=record_stream, args=(channel, headers)) for channel in CHANNELS]

    try:
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Recording stopped by user.")

if __name__ == "__main__":
    main()

