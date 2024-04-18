import asyncio
import orjson
import json
import os
import platform
import logging
import re
import aiohttp
import aiofiles
import hashlib
import time

print("Chzzk Rekoda made by munsy0227")

# Define logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logger to the lowest level

# File Handler for logging to a file
file_handler = logging.FileHandler('log.log')
file_handler.setLevel(logging.DEBUG)  # Log every level to the file
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Stream Handler for logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Only log INFO and above to the console
console_handler.setFormatter(formatter)  # You can use the same formatter or a different one
logger.addHandler(console_handler)

# Constants
# Check your current operating system
os_name = platform.system()

if os_name == "Windows":
    # Code for Windows
    STREAMLINK_PATH = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "streamlink.exe")
    FFMPEG_PATH = os.path.join(os.path.dirname(__file__), "ffmpeg", "bin", "ffmpeg.exe")
    print("Running on Windows.")
elif os_name == "Linux":
    # Code for Linux
    STREAMLINK_PATH = os.path.join(os.path.dirname(__file__), "venv", "bin", "streamlink")
    FFMPEG_PATH = "/usr/bin/ffmpeg"
    print("Running on Linux.")
elif os_name == "Darwin":
    # Code for macOS
    STREAMLINK_PATH = os.path.join(os.path.dirname(__file__), "venv", "bin", "streamlink")
    FFMPEG_PATH = "/usr/local/bin/ffmpeg"
    print("Running on macOS.")
else:
    # Code for other operating systems
    print(f"Running on {os_name}. The program will now exit.")
    time.sleep(5)
    exit()

LIVE_DETAIL_API = "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
TIME_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'time_sleep.txt')
THREAD_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thread.txt')
CHANNELS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'channels.json')
DELAYS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'delays.json')
COOKIE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookie.json')
PLUGIN_DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plugin')

MAX_FILENAME_BYTES = 150  # Maximum number of bytes for filename

# Compiled regex for reuse, improves performance
special_chars_remover = re.compile(r"[^\uAC00-\uD7A30-9a-zA-Z\s]")

# Use aiofiles for asynchronous file operations
async def load_json_async(file_path):
    async with aiofiles.open(file_path, "rb") as file:
        content = await file.read()
        return orjson.loads(content)

async def load_settings():
    time_file_content = await load_json_async(TIME_FILE_PATH)
    TIMEOUT = time_file_content if isinstance(time_file_content, int) else int(time_file_content.get("timeout", 60))
    thread_file_content = await load_json_async(THREAD_FILE_PATH)
    STREAM_SEGMENT_THREADS = thread_file_content if isinstance(thread_file_content, int) else int(thread_file_content.get("threads", 2))
    CHANNELS = await load_json_async(CHANNELS_FILE_PATH)
    DELAYS = await load_json_async(DELAYS_FILE_PATH)
    return TIMEOUT, STREAM_SEGMENT_THREADS, CHANNELS, DELAYS

# Helper Functions
def get_auth_headers(cookies):
    return {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0',
        'Cookie': f'NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}'
    }

async def get_session_cookies():
    return await load_json_async(COOKIE_FILE_PATH) # Change to asynchronous file loading

async def get_live_info(channel, headers, session):
    logger.debug(f"Fetching live info for channel: {channel['name']}")
    try:
        async with session.get(LIVE_DETAIL_API.format(channel_id=channel["id"]), headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
            logger.debug(f"Successfully fetched live info for channel: {channel['name']}, data: {data}")
            return data.get("content", {})
    except Exception as e:
        logger.error(f"Failed to fetch live info for {channel['name']}: {e}")
        return {}

def shorten_filename(filename):
    if len(filename.encode('utf-8')) > MAX_FILENAME_BYTES:
        hash_value = hashlib.sha256(filename.encode()).hexdigest()[:8]
        name, extension = os.path.splitext(filename)
        shortened_name = f"{name[:MAX_FILENAME_BYTES - 75]}_{hash_value}{extension}"
        logger.warning(f"Filename {filename} is too long. Shortening to {shortened_name}.")
        return shortened_name
    else:
        return filename

async def record_stream(channel, headers, session, delay, TIMEOUT):
    logger.info(f"Attempting to record stream for channel: {channel['name']}")
    await asyncio.sleep(delay)
    
    if channel.get("active", "on") == "off":
        logger.info(f"{channel['name']} channel is inactive. Skipping recording.")
        return

    recording_started = False
    stream_process = None  # Initialize stream_process variable

    while True:
        stream_url = f"https://chzzk.naver.com/live/{channel['id']}"
        if stream_url:
            logger.debug(f"Found stream URL for channel: {channel['name']}")
            try:
                cookies = await get_session_cookies()
                current_time = time.strftime("%Y-%m-%d_%H_%M_%S")
                channel_name = channel.get("name", "Unknown")
                live_info = await get_live_info(channel, headers, session)
                live_title = special_chars_remover.sub('', live_info.get("liveTitle", "").rstrip())
                output_dir = channel.get("output_dir", "./recordings")
                output_file = shorten_filename(f"[{current_time}] {channel_name} {live_title}.ts")
                output_path = os.path.join(output_dir, output_file)
                
                os.makedirs(output_dir, exist_ok=True)

                if not recording_started:
                    logger.info(f"Recording started for {channel_name} at {current_time}.")
                    recording_started = True

                if stream_process is not None:  # Check if the process has been initialized
                    # Attempt to kill existing stream process before starting a new one
                    if stream_process.returncode is None:
                        stream_process.kill()
                        await stream_process.wait()
                        logger.info("Existing stream process killed successfully.")

                # Start a new stream process
                stream_process = await asyncio.create_subprocess_exec(
                    STREAMLINK_PATH, stream_url, "best", "-o", output_path, "--hls-live-restart",
                    "--plugin-dirs", PLUGIN_DIR_PATH,
                    "--stream-segment-threads", str(STREAM_SEGMENT_THREADS),
                    "--http-header", f'Cookie=NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}',
                    "--http-header", 'User-Agent=Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0',
                    "--ffmpeg-ffmpeg", FFMPEG_PATH, "--ffmpeg-copyts", "--hls-segment-stream-data",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                await stream_process.wait()
                logger.info(f"Stream recording process for {channel_name} exited with return code {stream_process.returncode}.")
                if recording_started:
                    logger.info(f"Recording stopped for {channel_name}.")
                    recording_started = False

            except Exception as e:
                logger.exception(f"Error occurred while recording {channel_name}: {e}")
                if recording_started:
                    logger.info(f"Recording stopped for {channel_name}.")
                    recording_started = False
        else:
            logger.error(f"No stream URL available for {channel['name']}")
            if recording_started:
                logger.info(f"Recording stopped for {channel_name}.")
                recording_started = False

        await asyncio.sleep(TIMEOUT)

async def main():
    global TIMEOUT, STREAM_SEGMENT_THREADS, CHANNELS, DELAYS
    TIMEOUT, STREAM_SEGMENT_THREADS, CHANNELS, DELAYS = await load_settings()
    cookies = await get_session_cookies()
    headers = get_auth_headers(cookies)
    async with aiohttp.ClientSession() as session:
        tasks = [record_stream(channel, headers, session, DELAYS.get(channel.get("identifier"), 0), TIMEOUT) for channel in CHANNELS]
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Recording stopped by user.")

if __name__ == "__main__":
    asyncio.run(main())
