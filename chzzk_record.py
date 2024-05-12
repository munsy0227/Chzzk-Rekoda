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

print("Chzzk Rekoda made by munsy0227\nIf you encounter any bugs or errors, please report them on the Radiyu Shelter or GitHub issues!\n버그나 에러가 발생하면 라디유 쉘터나 깃허브 이슈에 제보해 주세요!")

# Define logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logger to the lowest level

# File Handler for logging to a file
file_handler = logging.FileHandler('log.log', encoding='utf-8')
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

MAX_FILENAME_BYTES = 150  # Maximum number of bytes for filename

# Compiled regex for reuse, improves performance
special_chars_remover = re.compile(r"[\\/:*?\"<>|\u2600-\u26FF\u2700-\u27BF\u1F600-\u1F64F]")

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
        'User-Agent': 'Mozilla/5.0 (X11; Unix x86_64)',
        'Cookie': f'NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}',
        'Origin': 'https://chzzk.naver.com',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Referer': ''
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

def shorten_filename(filename):
    if len(filename.encode('utf-8')) > MAX_FILENAME_BYTES:
        hash_value = hashlib.sha256(filename.encode()).hexdigest()[:8]
        name, extension = os.path.splitext(filename)
        shortened_name = f"{name[:MAX_FILENAME_BYTES - 75]}_{hash_value}{extension}"
        logger.warning(f"Filename {filename} is too long. Shortening to {shortened_name}.")
        return shortened_name
    else:
        return filename

# Function to add color to log messages
def colorize_log(message, color_code):
    return f"\033[{color_code}m{message}\033[0m"

# ANSI color codes: 32 is green, 31 is red
GREEN = 32
RED = 31

# Define the pattern for repeated messages
repeated_message_pattern = re.compile(r"\[mpegts @ [0-9a-fx]+] Invalid DTS: \d+ PTS: \d+ in output stream 0:0, replacing by guess")

async def read_stream(stream, channel_name, stream_type):
    """Asynchronously read stream data and record it in the log."""
    summary = {}
    last_logged_time = {}  # Initialize as an empty dictionary
    # Minimum interval between repeated messages (e.g., 10 seconds)
    min_interval = 10
    
    while True:
        line = await stream.readline()
        if not line:
            break
        line_str = line.decode().strip()
        
       # Filter specific repeated messages in the stderr stream
        if stream_type == "stderr" and line_str:
            current_time = time.time()
            match = repeated_message_pattern.match(line_str)
            if match:
                # Generate a generic message pattern ignoring specific numbers
                generic_message = "Invalid DTS and PTS in output stream 0:0, replacing by guess"
                # Check if the same type of message was logged recently
                if (generic_message not in last_logged_time or
                    current_time - last_logged_time[generic_message] > min_interval):
                    logger.debug(f"{channel_name} ffmpeg stderr: {generic_message}")
                    last_logged_time[generic_message] = current_time
            else:
                # Always log other messages
                logger.debug(f"{channel_name} ffmpeg stderr: {line_str}")

        parts = line_str.split('=')
        if len(parts) == 2:
            key, value = parts
            summary[key.strip()] = value.strip()
        if 'progress' in summary:
            # Convert total size to a human-readable format and colorize the log message
            total_size = summary.get('total_size', '0')
            total_size_formatted = format_size(int(total_size))
            log_message = (f"Bitrate={summary.get('bitrate', 'N/A')} " +
                           f"Total Size={total_size_formatted} " +
                           f"Out Time={summary.get('out_time', 'N/A')} " +
                           f"Speed={summary.get('speed', 'N/A')} " +
                           f"Progress={summary.get('progress', 'N/A')}")
            colored_message = colorize_log(log_message, GREEN)
            logger.info(f"{channel_name} {stream_type}: {colored_message}")
            summary.clear()

def format_size(size_bytes):
    """Convert the size in bytes to an appropriate unit (B, KB, MB, GB, TB)."""
    if size_bytes < 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

async def record_stream(channel, headers, session, delay, TIMEOUT):
    """Main function to record stream based on channel information."""
    logger.info(f"Attempting to record stream for channel: {channel['name']}")
    await asyncio.sleep(delay)
    
    if channel.get("active", "on") == "off":
        logger.info(f"{channel['name']} channel is inactive. Skipping recording.")
        return

    recording_started = False
    stream_process = None
    ffmpeg_process = None

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
                        
                if ffmpeg_process is not None:  # Check if the process has been initialized
                    # Attempt to kill existing stream process before starting a new one
                    if ffmpeg_process.returncode is None:
                        ffmpeg_process.kill()
                        await ffmpeg_process.wait()
                        logger.info("Existing ffmpeg process killed successfully.")
                
                # Create a pipe to connect streamlink to ffmpeg
                rpipe, wpipe = os.pipe()
                
                # Start the streamlink process
                stream_process = await asyncio.create_subprocess_exec(
                    STREAMLINK_PATH, "--stdout", stream_url, "best", "--hls-live-restart",
                    "--stream-segment-threads", str(STREAM_SEGMENT_THREADS),
                    "--http-header", f'Cookie=NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}',
                    "--http-header", 'User-Agent=Mozilla/5.0 (X11; Unix x86_64)',
                    "--http-header", "Origin=https://chzzk.naver.com", "--http-header", "DNT=1", "--http-header", "Sec-GPC=1", "--http-header", "Connection=keep-alive", "--http-header", "Referer=",
                    "--ffmpeg-ffmpeg", FFMPEG_PATH, "--ffmpeg-copyts", "--hls-segment-stream-data",
                    stdout=wpipe
                )
                os.close(wpipe)  # Close the write end of the pipe in the parent

                # Start the ffmpeg process
                ffmpeg_process = await asyncio.create_subprocess_exec(
                    FFMPEG_PATH, "-i", "pipe:0", "-c", "copy", "-progress", "pipe:1", "-copy_unknown", "-map_metadata:s:a", "0:g", "-bsf", "setts=pts=PTS-STARTPTS", "-y", output_path,
                    stdin=rpipe,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                os.close(rpipe)  # Close the read end of the pipe in the parent
                
                # Asynchronously read stdout and stderr
                stdout_task = asyncio.create_task(read_stream(ffmpeg_process.stdout, channel_name, "stdout"))
                stderr_task = asyncio.create_task(read_stream(ffmpeg_process.stderr, channel_name, "stderr"))

                await asyncio.gather(stdout_task, stderr_task)
                await ffmpeg_process.wait()

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
