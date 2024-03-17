import json
import asyncio
import os
import requests
import logging
import re
import aiohttp
import time
import subprocess
import hashlib
from threading import Thread

# Logging Configuration
# Set logging level to DEBUG to display all logs
logging.basicConfig(level=logging.DEBUG)
# Get logger for the current module
logger = logging.getLogger(__name__)
# Set logger's level to DEBUG
logger.setLevel(logging.DEBUG)

# Add a file handler to save logs to a file
file_handler = logging.FileHandler('log.log')
# Set file handler's level to DEBUG
file_handler.setLevel(logging.DEBUG)
# Define log message format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Set formatter for the file handler
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

# Add file handler to logger
logger.addHandler(file_handler)

# Constants
STREAMLINK_PATH = os.path.join(os.path.dirname(__file__), "venv", "bin", "streamlink")
FFMPEG_PATH = "/usr/bin/ffmpeg"
LIVE_DETAIL_API = "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
TIME_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'time_sleep.txt')
THREAD_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thread.txt')
CHANNELS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'channels.json')
DELAYS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'delays.json')
COOKIE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookie.json')

MAX_FILENAME_BYTES = 254  # Maximum number of bytes for filename

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

async def get_live_info(channel, headers):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(LIVE_DETAIL_API.format(channel_id=channel["id"]), headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("content", {})
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch live info for {channel['name']}: {e}")
        return {}  # Return an empty dictionary instead of None

async def fetch_stream_url(channel, headers):
    live_info = await get_live_info(channel, headers)
    if not live_info:  # Check if live_info is empty
        logger.error(f"Failed to fetch live info for {channel['name']}.")
        return None

    live_playback_json = json.loads(live_info.get("livePlaybackJson") or "{}")
    media_list = live_playback_json.get("media", [])
    
    for media in media_list:
        stream_url = media.get("path", "")
        if stream_url:
            return stream_url

    return None

def shorten_filename(filename):
    if len(filename.encode('utf-8')) > MAX_FILENAME_BYTES:
        hash_value = hashlib.sha256(filename.encode()).hexdigest()[:8]
        name, extension = os.path.splitext(filename)
        shortened_name = f"{name[:MAX_FILENAME_BYTES - 20]}_{hash_value}{extension}"
        logger.warning(f"Filename {filename} is too long. Shortening to {shortened_name}.")
        return shortened_name
    else:
        return filename

async def record_stream(channel, headers):
    delay = DELAYS.get(channel.get("identifier"), 0)
    await asyncio.sleep(delay)

    if channel.get("active", "on") == "off":
        logger.info(f"{channel['name']} channel is inactive. Skipping recording.")
        return

    recording_started = False
    stream_process = None

    while True:
        stream_url = await fetch_stream_url(channel, headers)
        
        if stream_url:
            try:
                current_time = time.strftime("%Y-%m-%d_%H:%M:%S")
                channel_name = channel.get("name", "Unknown")
                live_info = await get_live_info(channel, headers)
                live_title = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", '', live_info.get("liveTitle", "").rstrip())
                output_dir = channel.get("output_dir", "./recordings")
                output_file = shorten_filename(f"[{current_time}] {channel_name} {live_title}.ts")
                output_path = os.path.join(output_dir, output_file)
                
                # Ensure output directory exists
                os.makedirs(output_dir, exist_ok=True)

                if not recording_started:
                    logger.info(f"Recording started for {channel_name} at {current_time}.")
                    recording_started = True

                if stream_process:
                    # Check if the process has already terminated
                    if stream_process.returncode is None:
                        stream_process.kill()  # Ends the previous streaming process
                        await stream_process.wait()  # Ensure the process is fully terminated
                        logger.info("Stream process killed successfully.")
                    else:
                        # Process has already terminated
                        logger.info(f"Streaming process for {channel_name} already terminated with return code {stream_process.returncode}.")

                stream_process = await asyncio.create_subprocess_exec(
                    STREAMLINK_PATH, stream_url, "best", "-o", output_path, "--hls-live-restart",
                    "--stream-segment-threads", str(STREAM_SEGMENT_THREADS),
                    "--ffmpeg-ffmpeg", FFMPEG_PATH, "--ffmpeg-copyts", "--hls-segment-stream-data",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                await stream_process.wait()  # Wait for streaming to end

                logger.info(f"streamlink process exited for {channel_name}.")
                if recording_started:
                    logger.info(f"Recording stopped for {channel_name}.")
                    recording_started = False

            except Exception as e:
                logger.error(f"Error occurred while recording {channel_name}: {e}")
                logger.info(f"Recording stopped for {channel_name}.")
                recording_started = False
        else:
            logger.info(f"No stream URL available for {channel.get('name', 'Unknown')}")
            if recording_started:
                logger.info(f"Recording stopped for {channel_name}.")
                recording_started = False

        await asyncio.sleep(TIMEOUT)  # Wait for streaming to restart

async def main():
    headers = get_auth_headers(get_session_cookies())
    tasks = [record_stream(channel, headers) for channel in CHANNELS]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Recording stopped by user.")

if __name__ == "__main__":
    asyncio.run(main())

