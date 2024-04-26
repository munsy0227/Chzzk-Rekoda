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
from pathlib import Path

print("Chzzk Rekoda made by munsy0227\n##################################################################################################\n#If you encounter any bugs or errors, please report them on the Radiyu Shelther or GitHub issues!#\n#               버그나 에러가 발생하면 라디유 쉘터나 깃허브 이슈에 제보해 주세요!                #\n##################################################################################################")

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
async def setup_paths():
    global STREAMLINK_PATH, FFMPEG_PATH
    os_name = platform.system()
    base_dir = Path(__file__).parent

    if os_name == "Windows":
        STREAMLINK_PATH = base_dir / "venv/Scripts/streamlink.exe"
        FFMPEG_PATH = base_dir / "ffmpeg/bin/ffmpeg.exe"
        logger.info("Running on Windows.")
    elif os_name in ["Linux", "Darwin"]:
        STREAMLINK_PATH = base_dir / "venv/bin/streamlink"
        ffmpeg_command = "which ffmpeg"
        try:
            process = await asyncio.create_subprocess_shell(
                ffmpeg_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                FFMPEG_PATH = stdout.decode().strip()
                logger.info(f"Running on {os_name}. ffmpeg found at: {FFMPEG_PATH}")
            else:
                logger.error(f"ffmpeg not found in PATH on {os_name}.")
                FFMPEG_PATH = None
        except Exception as e:
            logger.error(f"Error finding ffmpeg on {os_name}: {e}")
            FFMPEG_PATH = None
    else:
        logger.error(f"Unsupported OS: {os_name}. Exiting.")
        await asyncio.sleep(5)
        exit()

    return STREAMLINK_PATH, FFMPEG_PATH

LIVE_DETAIL_API = "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
TIME_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'time_sleep.txt')
THREAD_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thread.txt')
CHANNELS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'channels.json')
DELAYS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'delays.json')
COOKIE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookie.json')
#PLUGIN_DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plugin')

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
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error occurred while fetching live info for {channel['name']}: {e}")
    except Exception as e:
        logger.error(f"Failed to fetch live info for {channel['name']}: {e}")
    return {}

async def fetch_stream_url(channel, headers, session):
    logger.debug(f"Attempting to fetch stream URL for channel: {channel['name']}")
    live_info = await get_live_info(channel, headers, session)
    if not live_info:
        logger.error(f"Failed to fetch live info for {channel['name']}.")
        return None

    try:
        live_playback_json_str = live_info.get('livePlaybackJson', '{}')
        logger.debug(f"livePlaybackJson string before parsing: {live_playback_json_str}")
        live_playback_json = json.loads(live_playback_json_str)
        logger.debug(f"Parsed livePlaybackJson: {live_playback_json}")

        media_list = live_playback_json.get("media", [])
        logger.debug(f"Media list: {media_list}")
        if media_list:
            stream_url = media_list[0].get("path", "")
            logger.debug(f"Selected stream URL: {stream_url}")
            if stream_url:
                return stream_url
            else:
                logger.error(f"No stream URL found in live info for {channel['name']}.")
        else:
            logger.error(f"No media info found in live info for {channel['name']}.")
    except Exception as e:
        logger.exception(f"Error parsing live playback JSON for {channel['name']}: {e}")

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
    stream_process = None
    ffmpeg_process = None

    while True:
        stream_url = await fetch_stream_url(channel, headers, session)
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
                        
                if ffmpeg_process is not None:  # Check if the process has been initialized
                    # Attempt to kill existing stream process before starting a new one
                    if ffmpeg_process.returncode is None:
                        ffmpeg_process.kill()
                        await ffmpeg_process.wait()
                        logger.info("Existing ffmpeg process killed successfully.")
                
                # Create a pipe for connecting streamlink to ffmpeg
                rpipe, wpipe = os.pipe()
                
                # Start the streamlink process
                stream_process = await asyncio.create_subprocess_exec(
                    STREAMLINK_PATH, "--stdout", stream_url, "best", "--hls-live-restart",
                    #"--plugin-dirs", PLUGIN_DIR_PATH,
                    "--stream-segment-threads", str(STREAM_SEGMENT_THREADS),
                    "--http-header", f'Cookie=NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}',
                    "--http-header", 'User-Agent=Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0',
                    "--ffmpeg-ffmpeg", FFMPEG_PATH, "--ffmpeg-copyts", "--hls-segment-stream-data",
                    stdout=wpipe
                )
                os.close(wpipe)  # Close the write end of the pipe in the parent

                # Start the ffmpeg process
                ffmpeg_process = await asyncio.create_subprocess_exec(
                    FFMPEG_PATH, "-i", "pipe:0", "-c", "copy", "-y", output_path,
                    stdin=rpipe,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                os.close(rpipe)  # Close the read end of the pipe in the parent

                # Wait for ffmpeg to finish
                stdout, stderr = await ffmpeg_process.communicate()
                if stderr:
                    logger.error(f"ffmpeg stderr: {stderr.decode()}")

                logger.info(f"ffmpeg process for {channel_name} exited with return code {ffmpeg_process.returncode}.")
                if recording_started:
                    logger.info(f"Recording stopped for {channel_name}.")
                    recording_started = False

                await stream_process.wait()
                logger.info(f"Stream recording process for {channel_name} exited with return code {stream_process.returncode}.")

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
    asyncio.run(setup_paths())
    asyncio.run(main())

