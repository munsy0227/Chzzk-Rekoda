import asyncio
import hashlib
import logging
import os
import platform
import re
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import aiohttp
import orjson

if platform.system() != "Windows":
    import uvloop

    uvloop.install()

# Import Rich library components
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

# Global console instance for Rich
console = Console()

# Shared data structure for channel progress
channel_progress: Dict[str, Dict[str, Any]] = {}
channel_progress_lock = asyncio.Lock()

# Create a queue for log messages
log_queue: asyncio.Queue = asyncio.Queue()

# Custom logging handler to put log messages into the queue
class QueueHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        # Directly put the message into the queue
        try:
            self.queue.put_nowait(msg)
        except asyncio.QueueFull:
            pass  # Handle the case where the queue is full

# Logger setup
def setup_logger() -> logging.Logger:
    logger = logging.getLogger("Recorder")
    logger.setLevel(logging.DEBUG)

    # Create formatter for file handler
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler("log.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Queue handler for real-time log updates
    queue_handler = QueueHandler(log_queue)
    queue_handler.setLevel(logging.INFO)
    # Include timestamp in the console logs
    queue_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    logger.addHandler(queue_handler)

    # Avoid duplicate logs
    logger.propagate = False

    return logger


logger = setup_logger()

print(
    "Chzzk Rekoda made by munsy0227\n"
    "If you encounter any bugs or errors, please report them on the Radiyu Shelter or GitHub issues!\n"
    "버그나 에러가 발생하면 라디유 쉘터나 깃허브 이슈에 제보해 주세요!"
)

# Constants
LIVE_DETAIL_API = (
    "https://api.chzzk.naver.com/service/v3/channels/{channel_id}/live-detail"
)
TIME_FILE_PATH = Path("time_sleep.txt")
THREAD_FILE_PATH = Path("thread.txt")
CHANNELS_FILE_PATH = Path("channels.json")
DELAYS_FILE_PATH = Path("delays.json")
COOKIE_FILE_PATH = Path("cookie.json")
PLUGIN_DIR_PATH = Path("plugin")
SPECIAL_CHARS_REMOVER = re.compile(r'[\\/:*?"<>|]')

# Max filename length constants
MAX_FILENAME_BYTES = 255
MAX_HASH_LENGTH = 8
RESERVED_BYTES = MAX_HASH_LENGTH + 1  # Hash length and one underscore

# Global variables for graceful shutdown
shutdown_event = asyncio.Event()

# Helper functions
async def setup_paths() -> Tuple[Optional[Path], Optional[Path]]:
    base_dir = Path(__file__).parent
    os_name = platform.system()
    streamlink_path: Optional[Path] = None
    ffmpeg_path: Optional[Path] = None

    if os_name == "Windows":
        streamlink_path = base_dir / "venv/Scripts/streamlink.exe"
        ffmpeg_path = base_dir / "ffmpeg/bin/ffmpeg.exe"
        logger.info("Running on Windows.")
    else:
        streamlink_path = base_dir / "venv/bin/streamlink"
        try:
            process = await asyncio.create_subprocess_exec(
                "which",
                "ffmpeg",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            if process.returncode == 0:
                ffmpeg_path = Path(stdout.decode().strip())
                logger.info(f"Running on {os_name}. ffmpeg found at: {ffmpeg_path}")
            else:
                logger.error("ffmpeg not found on the system PATH.")
        except Exception as e:
            logger.error(f"Error finding ffmpeg on {os_name}: {e}")

    return streamlink_path, ffmpeg_path


async def load_json_async(file_path: Path) -> Any:
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None
    try:
        async with aiofiles.open(file_path, "rb") as file:
            content = await file.read()
            return orjson.loads(content)
    except orjson.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return None


async def load_settings() -> Tuple[int, int, List[Dict[str, Any]], Dict[str, int]]:
    settings = await asyncio.gather(
        load_json_async(TIME_FILE_PATH),
        load_json_async(THREAD_FILE_PATH),
        load_json_async(CHANNELS_FILE_PATH),
        load_json_async(DELAYS_FILE_PATH),
    )

    # Validate and set defaults
    timeout = settings[0] if isinstance(settings[0], int) else 60
    stream_segment_threads = settings[1] if isinstance(settings[1], int) else 2
    channels = settings[2] if isinstance(settings[2], list) else []
    delays = settings[3] if isinstance(settings[3], dict) else {}

    return timeout, stream_segment_threads, channels, delays


def get_auth_headers(cookies: Dict[str, str]) -> Dict[str, str]:
    nid_aut = cookies.get("NID_AUT", "")
    nid_ses = cookies.get("NID_SES", "")
    return {
        "User-Agent": "Mozilla/5.0 (X11; Unix x86_64)",
        "Cookie": f"NID_AUT={nid_aut}; NID_SES={nid_ses}",
        "Origin": "https://chzzk.naver.com",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Referer": "",
    }


async def get_session_cookies() -> Dict[str, str]:
    cookies = await load_json_async(COOKIE_FILE_PATH)
    if not cookies:
        logger.error(
            "No cookies found. Please ensure 'cookie.json' exists and is valid."
        )
        return {}
    return cookies


async def get_live_info(
    channel: Dict[str, Any], headers: Dict[str, str], session: aiohttp.ClientSession
) -> Tuple[str, Dict[str, Any]]:
    logger.debug(f"Fetching live info for channel: {channel.get('name', 'Unknown')}")
    try:
        async with session.get(
            LIVE_DETAIL_API.format(channel_id=channel["id"]), headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            logger.debug(
                f"Successfully fetched live info for channel: {channel.get('name', 'Unknown')}, data: {data}"
            )

            content = data.get("content", {})
            status = content.get("status", "")
            if status == "CLOSE":
                logger.info(
                    f"The channel '{channel.get('name', 'Unknown')}' is not currently live."
                )
                return status, {}
            return status, content
    except aiohttp.ClientError as e:
        logger.error(
            f"HTTP error occurred while fetching live info for {channel.get('name', 'Unknown')}: {e}"
        )
    except Exception as e:
        logger.error(
            f"Failed to fetch live info for {channel.get('name', 'Unknown')}: {e}"
        )
    return "", {}


def shorten_filename(filename: str) -> str:
    filename_bytes = filename.encode("utf-8")
    if len(filename_bytes) > MAX_FILENAME_BYTES:
        hash_value = hashlib.sha256(filename_bytes).hexdigest()[:MAX_HASH_LENGTH]
        name, extension = os.path.splitext(filename)
        max_name_length = (
            MAX_FILENAME_BYTES - RESERVED_BYTES - len(extension.encode("utf-8"))
        )

        shortened_name_bytes = name.encode("utf-8")[:max_name_length]
        shortened_name = shortened_name_bytes.decode("utf-8", "ignore")
        shortened_filename = f"{shortened_name}_{hash_value}{extension}"
        logger.warning(
            f"Filename '{filename}' is too long. Shortening to '{shortened_filename}'."
        )
        return shortened_filename

    return filename


def format_size(size_bytes: float) -> str:
    if size_bytes <= 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"


async def read_stream(
    stream: asyncio.StreamReader, channel_id: str, stream_type: str
) -> None:
    summary: Dict[str, str] = {}
    last_log_time = time.time()
    buffer = ""

    prev_total_size = None
    prev_time = None

    while not stream.at_eof():
        try:
            chunk = await stream.read(2048)
            if not chunk:
                break
            buffer += chunk.decode(errors="ignore")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line_str = line.strip()

                if stream_type == "stderr" and line_str:
                    if "Invalid DTS" in line_str or "Invalid PTS" in line_str:
                        continue
                    logger.debug(f"ffmpeg stderr [{channel_id}]: {line_str}")

                parts = line_str.split("=")
                if len(parts) == 2:
                    key, value = parts
                    summary[key.strip()] = value.strip()

                current_time = time.time()
                if "progress" in summary and (current_time - last_log_time >= 1):
                    total_size_str = summary.get("total_size", "0")
                    try:
                        total_size = int(total_size_str)
                    except ValueError:
                        total_size = 0

                    total_size_formatted = format_size(total_size)

                    if prev_total_size is not None and prev_time is not None:
                        bytes_diff = total_size - prev_total_size
                        time_diff = current_time - prev_time
                        if time_diff > 0:
                            download_speed = bytes_diff / time_diff  # Bytes per second
                            download_speed_formatted = format_size(download_speed) + "/s"
                        else:
                            download_speed_formatted = "N/A"
                    else:
                        download_speed_formatted = "N/A"

                    prev_total_size = total_size
                    prev_time = current_time

                    # Update shared progress data
                    async with channel_progress_lock:
                        if channel_id in channel_progress:
                            channel_progress[channel_id].update({
                                "bitrate": summary.get("bitrate", "N/A"),
                                "download_speed": download_speed_formatted,
                                "total_size": total_size_formatted,
                                "out_time": summary.get("out_time", "N/A"),
                            })

                    last_log_time = current_time
                    summary.clear()
        except Exception as e:
            logger.error(f"Error occurred while reading stream for {channel_id}: {e}")
            break


async def record_stream(
    channel: Dict[str, Any],
    headers: Dict[str, str],
    session: aiohttp.ClientSession,
    delay: int,
    timeout: int,
    streamlink_path: Path,
    ffmpeg_path: Path,
    stream_segment_threads: int,
) -> None:
    channel_name = channel.get("name", "Unknown")
    channel_id = str(channel.get("id", "Unknown"))
    logger.info(f"Attempting to record stream for channel: {channel_name}")
    await asyncio.sleep(delay)

    if channel.get("active", "on") == "off":
        logger.info(f"{channel_name} channel is inactive. Skipping recording.")
        return

    recording_started = False
    stream_process: Optional[asyncio.subprocess.Process] = None
    ffmpeg_process: Optional[asyncio.subprocess.Process] = None

    try:
        while not shutdown_event.is_set():
            stream_url = f"https://chzzk.naver.com/live/{channel['id']}"
            if stream_url:
                logger.debug(f"Found stream URL for channel: {channel_name}")
                try:
                    cookies = await get_session_cookies()
                    while not shutdown_event.is_set():
                        status, live_info = await get_live_info(
                            channel, headers, session
                        )

                        if status != "CLOSE":
                            break

                        logger.info(
                            f"The channel '{channel_name}' is not currently live."
                        )
                        logger.info(
                            f"Waiting for the channel '{channel_name}' to go live..."
                        )
                        try:
                            await asyncio.wait_for(
                                shutdown_event.wait(), timeout=timeout
                            )
                        except asyncio.TimeoutError:
                            continue

                    if shutdown_event.is_set():
                        break

                    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    live_title = SPECIAL_CHARS_REMOVER.sub(
                        "", live_info.get("liveTitle", "").rstrip()
                    )
                    output_dir = Path(
                        channel.get("output_dir", "./recordings")
                    ).expanduser()
                    temp_output_file = shorten_filename(
                        f"[{current_time.replace(':', '_')}] {channel_name} {live_title}.ts.part"
                    )
                    final_output_file = temp_output_file[:-5]  # Remove '.part'
                    temp_output_path = output_dir / temp_output_file
                    final_output_path = output_dir / final_output_file

                    output_dir.mkdir(parents=True, exist_ok=True)

                    if not recording_started:
                        logger.info(
                            f"Recording started for {channel_name} at {current_time}."
                        )
                        recording_started = True
                        recording_start_time = current_time

                    if stream_process and stream_process.returncode is None:
                        stream_process.kill()
                        await stream_process.wait()
                        logger.info("Existing stream process killed successfully.")

                    if ffmpeg_process and ffmpeg_process.returncode is None:
                        ffmpeg_process.kill()
                        await ffmpeg_process.wait()
                        logger.info("Existing ffmpeg process killed successfully.")

                    # Create pipes safely
                    read_pipe, write_pipe = os.pipe()
                    try:
                        # Start streamlink process
                        streamlink_cmd = [
                            str(streamlink_path),
                            "--stdout",
                            stream_url,
                            "best",
                            "--hls-live-restart",
                            "--plugin-dirs",
                            str(PLUGIN_DIR_PATH),
                            "--stream-segment-threads",
                            str(stream_segment_threads),
                            "--http-header",
                            f'Cookie=NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}',
                            "--http-header",
                            "User-Agent=Mozilla/5.0 (X11; Unix x86_64)",
                            "--http-header",
                            "Origin=https://chzzk.naver.com",
                            "--http-header",
                            "DNT=1",
                            "--http-header",
                            "Sec-GPC=1",
                            "--http-header",
                            "Connection=keep-alive",
                            "--http-header",
                            "Referer=",
                            "--ffmpeg-ffmpeg",
                            str(ffmpeg_path),
                            "--ffmpeg-copyts",
                            "--hls-segment-stream-data",
                        ]

                        stream_process = await asyncio.create_subprocess_exec(
                            *streamlink_cmd,
                            stdout=write_pipe,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        os.close(write_pipe)  # Close the write end in the parent

                        # Start ffmpeg process
                        ffmpeg_cmd = [
                            str(ffmpeg_path),
                            "-i",
                            "pipe:0",
                            "-c",
                            "copy",
                            "-progress",
                            "pipe:1",
                            "-copy_unknown",
                            "-map_metadata:s:a",
                            "0:s:a",
                            "-map_metadata:s:v",
                            "0:s:v",
                            "-bsf:v",
                            "h264_mp4toannexb",
                            "-bsf:a",
                            "aac_adtstoasc",
                            "-f",
                            "mpegts",
                            "-mpegts_flags",
                            "resend_headers",
                            "-bsf",
                            "setts=pts=PTS-STARTPTS",
                            "-fflags",
                            "+genpts+discardcorrupt+nobuffer",
                            "-avioflags",
                            "direct",
                            "-y",
                            str(temp_output_path),
                        ]

                        ffmpeg_process = await asyncio.create_subprocess_exec(
                            *ffmpeg_cmd,
                            stdin=read_pipe,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        os.close(read_pipe)  # Close the read end in the parent

                        # Initialize channel progress data
                        async with channel_progress_lock:
                            channel_progress[channel_id] = {
                                "channel_name": channel_name,
                                "bitrate": "N/A",
                                "download_speed": "N/A",
                                "total_size": "N/A",
                                "out_time": "N/A",
                                "recording_start_time": recording_start_time,
                            }

                        stdout_task = asyncio.create_task(
                            read_stream(ffmpeg_process.stdout, channel_id, "stdout")
                        )
                        stderr_task = asyncio.create_task(
                            read_stream(ffmpeg_process.stderr, channel_id, "stderr")
                        )
                        ffmpeg_wait_task = asyncio.create_task(ffmpeg_process.wait())

                        await asyncio.wait(
                            [stdout_task, stderr_task, ffmpeg_wait_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        # If shutdown event is set, terminate processes
                        if shutdown_event.is_set():
                            if ffmpeg_process.returncode is None:
                                ffmpeg_process.kill()
                                await ffmpeg_process.wait()
                            if stream_process.returncode is None:
                                stream_process.kill()
                                await stream_process.wait()
                            break

                        logger.info(
                            f"ffmpeg process for {channel_name} exited with return code {ffmpeg_process.returncode}."
                        )
                        if recording_started:
                            logger.info(f"Recording stopped for {channel_name}.")
                            recording_started = False

                        await stream_process.wait()
                        logger.info(
                            f"Stream recording process for {channel_name} exited with return code {stream_process.returncode}."
                        )

                        # Atomically rename the temporary file to final output
                        if temp_output_path.exists():
                            temp_output_path.rename(final_output_path)
                            logger.info(f"Recording saved to {final_output_path}")

                        # Remove progress data
                        async with channel_progress_lock:
                            channel_progress.pop(channel_id, None)

                    finally:
                        # Ensure pipes are closed
                        for fd in (read_pipe, write_pipe):
                            try:
                                os.close(fd)
                            except OSError:
                                pass

                except asyncio.CancelledError:
                    logger.info(f"Recording task for {channel_name} was cancelled.")
                    break
                except Exception as e:
                    logger.exception(
                        f"Error occurred while recording {channel_name}: {e}"
                    )
                    if recording_started:
                        logger.info(f"Recording stopped for {channel_name}.")
                        recording_started = False
            else:
                logger.error(f"No stream URL available for {channel_name}")
                if recording_started:
                    logger.info(f"Recording stopped for {channel_name}.")
                    recording_started = False

            # Wait for shutdown event or timeout
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                continue

    finally:
        if stream_process and stream_process.returncode is None:
            stream_process.kill()
            await stream_process.wait()
        if ffmpeg_process and ffmpeg_process.returncode is None:
            ffmpeg_process.kill()
            await ffmpeg_process.wait()
        # Attempt to rename any remaining temp files
        if recording_started and temp_output_path.exists():
            temp_output_path.rename(final_output_path)
            logger.info(f"Recording saved to {final_output_path}")
        # Remove progress data
        async with channel_progress_lock:
            channel_progress.pop(channel_id, None)


async def manage_recording_tasks():
    active_tasks: Dict[str, asyncio.Task] = {}
    timeout, stream_segment_threads, channels, delays = await load_settings()
    cookies = await get_session_cookies()
    headers = get_auth_headers(cookies)
    streamlink_path, ffmpeg_path = await setup_paths()

    if not streamlink_path or not streamlink_path.exists():
        logger.error("Streamlink executable not found. Exiting.")
        return
    if not ffmpeg_path or not ffmpeg_path.exists():
        logger.error("ffmpeg executable not found. Exiting.")
        return

    async with aiohttp.ClientSession() as session:
        try:
            while not shutdown_event.is_set():
                (
                    new_timeout,
                    new_stream_segment_threads,
                    new_channels,
                    new_delays,
                ) = await load_settings()
                active_channels = 0

                current_channel_ids = {str(channel.get("id")) for channel in new_channels}

                # Cancel tasks for removed or deactivated channels
                for channel_id in list(active_tasks.keys()):
                    if channel_id not in current_channel_ids:
                        task = active_tasks.pop(channel_id)
                        task.cancel()
                        logger.info(
                            f"Cancelled recording task for deactivated channel: {channel_id}"
                        )
                        # Remove progress data
                        async with channel_progress_lock:
                            channel_progress.pop(channel_id, None)

                for channel in new_channels:
                    channel_id = str(channel.get("id"))
                    if not channel_id:
                        logger.warning("Channel ID is missing in configuration.")
                        continue
                    if channel_id not in active_tasks:
                        if channel.get("active", "on") == "on":
                            task = asyncio.create_task(
                                record_stream(
                                    channel,
                                    headers,
                                    session,
                                    new_delays.get(channel.get("identifier"), 0),
                                    new_timeout,
                                    streamlink_path,
                                    ffmpeg_path,
                                    new_stream_segment_threads,
                                )
                            )
                            active_tasks[channel_id] = task
                            active_channels += 1
                            logger.info(
                                f"Started recording task for new active channel: {channel.get('name', 'Unknown')}"
                            )
                    else:
                        if channel.get("active", "on") == "off":
                            task = active_tasks.pop(channel_id)
                            task.cancel()
                            logger.info(
                                f"Cancelled recording task for deactivated channel: {channel.get('name', 'Unknown')}"
                            )
                            # Remove progress data
                            async with channel_progress_lock:
                                channel_progress.pop(channel_id, None)
                        else:
                            active_channels += 1

                if active_channels == 0:
                    logger.info("All channels are inactive. No active recordings.")

                # Wait for shutdown event or 10 seconds
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=10)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info("Recording management task was cancelled.")
        finally:
            # Cancel all active recording tasks
            for task in active_tasks.values():
                task.cancel()
            await asyncio.gather(*active_tasks.values(), return_exceptions=True)


def handle_shutdown():
    logger.info("Received shutdown signal. Shutting down...")
    shutdown_event.set()


async def display_progress():
    layout = Layout()

    # Fix the size of the upper layout to prevent it from disappearing
    layout.split(
        Layout(name="upper", size=15, ratio=1),
        Layout(name="lower", ratio=3),
    )

    log_messages = []  # List of log messages

    with Live(layout, console=console, refresh_per_second=10, screen=False):
        while not shutdown_event.is_set() or not log_queue.empty():
            # Create a list to hold individual channel panels
            channel_panels = []

            async with channel_progress_lock:
                if channel_progress:
                    for progress_data in channel_progress.values():
                        # Create a table for each channel
                        table = Table(show_header=True, header_style="bold magenta")
                        table.add_column("Channel", style="cyan", no_wrap=True)
                        table.add_column("Bitrate")
                        table.add_column("Download Speed")
                        table.add_column("Total Size")
                        table.add_column("Out Time")
                        table.add_column("Start Time")

                        table.add_row(
                            progress_data.get("channel_name", "Unknown"),
                            progress_data.get("bitrate", "N/A"),
                            progress_data.get("download_speed", "N/A"),
                            progress_data.get("total_size", "N/A"),
                            progress_data.get("out_time", "N/A"),
                            progress_data.get("recording_start_time", "N/A"),
                        )

                        # Create a panel for each channel's table
                        panel = Panel(table, title=progress_data.get("channel_name", "Unknown"))
                        channel_panels.append(panel)
                else:
                    # If no channels are recording, display a message
                    channel_panels.append(Panel("No active recordings.", title="Recording Progress"))

            # Combine all channel panels into a single renderable
            progress_display = Group(*channel_panels)

            layout["lower"].update(progress_display)

            # Read logs from the queue
            try:
                while True:
                    msg = log_queue.get_nowait()
                    log_messages.append(msg)
                    # Keep only the last 15 messages
                    log_messages = log_messages[-15:]
            except asyncio.QueueEmpty:
                pass

            # Update the log panel
            log_text = Text("\n".join(log_messages))
            layout["upper"].update(Panel(log_text, title="Logs"))

            await asyncio.sleep(0.1)


async def main() -> None:
    # Register signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    if platform.system() != "Windows":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_shutdown)
    else:
        # On Windows, signals are not supported in the event loop.
        # We'll handle KeyboardInterrupt exception instead.
        pass

    display_task = asyncio.create_task(display_progress())

    try:
        await manage_recording_tasks()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt. Shutting down...")
        handle_shutdown()
        # Wait a moment to allow tasks to clean up
        await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Main task was cancelled.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        # Wait for display_progress to process remaining logs
        shutdown_event.set()
        await display_task
        logger.info("Recorder has been shut down.")


if __name__ == "__main__":
    asyncio.run(main())
