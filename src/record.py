import asyncio
import importlib
import os
import platform
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
import aiohttp

from logger import log
from utils import *
if platform.system() != "Windows":
    import uvloop

    uvloop.install()

    
# Global variables for graceful shutdown
shutdown_event = asyncio.Event()

        
async def create_instance(channel: Dict[str, Any]) -> object:
    # Get platform name from the channel dictionary
    plat_name = channel.get('platform')

    if plat_name is None:
        raise ValueError("Platform name is missing in the channel data")
    
    # Add the plugin folder to sys.path if not already included
    plugin_path = os.path.join(os.path.dirname(__file__), 'plugin')
    if plugin_path not in sys.path:
        sys.path.append(plugin_path)

    try:
        # Dynamically import the module corresponding to the platform name
        module = importlib.import_module(f"{plat_name}")

        # Get the class dynamically from the module
        class_name = f"{plat_name.capitalize()}"
        plat_class = getattr(module, class_name)

        # Create and return an instance of the class
        return plat_class(channel)
    except ModuleNotFoundError as e:
        raise ImportError(f"Module for platform '{plat_name}' not found.") from e
    except AttributeError as e:
        raise ImportError(f"Class '{class_name}' not found in module '{plat_name}'.") from e
    except Exception as e:
        raise RuntimeError(f"An error occurred while creating the instance for platform '{plat_name}': {e}")

# Constants
base_directory = Path(__file__).resolve().parent / "files"

TIME_FILE_PATH = base_directory / Path("time_sleep.txt")
THREAD_FILE_PATH = base_directory / Path("thread.txt")
CHANNELS_FILE_PATH = base_directory /Path("channels.json")
DELAYS_FILE_PATH = base_directory /Path("delays.json")
PLUGIN_DIR_PATH =  Path("plugin")
SPECIAL_CHARS_REMOVER = re.compile(r"[\\/:*?\"<>|]")
FILES = [TIME_FILE_PATH, THREAD_FILE_PATH, CHANNELS_FILE_PATH,
         DELAYS_FILE_PATH]

def colorize_log(message: str, color_code: int) -> str:
    return f"\033[{color_code}m{message}\033[0m"


async def read_stream(
    stream: asyncio.StreamReader, channel_name: str, stream_type: str
) -> None:
    summary = {}
    last_log_time = time.time()
    buffer = ""

    while True:
        try:
            chunk = await stream.read(1024)
            if not chunk:
                break
            buffer += chunk.decode()

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line_str = line.strip()

                if stream_type == "stderr" and line_str:
                    if "Invalid DTS" in line_str or "Invalid PTS" in line_str:
                        continue
                    log.debug(f"{channel_name} ffmpeg stderr: {line_str}")

                parts = line_str.split("=")
                if len(parts) == 2:
                    key, value = parts
                    summary[key.strip()] = value.strip()

                current_time = time.time()
                if "progress" in summary and (current_time - last_log_time >= 5):
                    total_size = summary.get("total_size", "0")
                    total_size_formatted = format_size(int(total_size))
                    log_message = (
                        f"Bitrate={summary.get('bitrate', 'N/A')} "
                        f"Total Size={total_size_formatted} "
                        f"Out Time={summary.get('out_time', 'N/A')} "
                        f"Speed={summary.get('speed', 'N/A')} "
                        f"Progress={summary.get('progress', 'N/A')}"
                    )
                    log.info(fr"{channel_name} {stream_type}: {log_message}")
                    last_log_time = current_time
                    summary.clear()
        except Exception as e:
            log.error(f"Error occurred while reading stream for {channel_name}: {e}")
            break


def format_size(size_bytes: int) -> str:
    if size_bytes < 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

async def output_file(channel: Dict[str, Any]) -> Tuple[Path, str, str]:
    current_time = time.strftime("%Y-%m-%d_%H_%M_%S")
    channel_name = channel.get("name", "Unknown")
    output_dir = Path(channel.get("output_dir", "./recordings"))
    output_file = shorten_filename(
        f"[{current_time}] {channel_name}.ts"
    )
    output_path = output_dir / output_file

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_path, channel_name, current_time


async def record_stream(
    channel: Dict[str, Any],
    session: aiohttp.ClientSession,
    delay: int,
    timeout: int,
    streamlink_path: Path,
    ffmpeg_path: Path,
    stream_segment_threads: int,
) -> None:
    log.info(f"Attempting to record stream for channel: {channel['name']}")
    await asyncio.sleep(delay)

    if channel.get("active", "on") == "off":
        log.info(f"{channel['name']} channel is inactive. Skipping recording.")
        return

    recording_started = False
    stream_process = None
    ffmpeg_process = None
    try:
        while True:

            platform = await create_instance(channel)
            stream_url = platform.stream_url
            if stream_url:
                log.debug(f"Found stream URL for channel: {channel['name']}")
                try:
                    while True:

                        status = await platform.get_live_status(
                            channel, session
                        )
                        if status != "CLOSE":
                            break

                        await asyncio.sleep(timeout)

                    output_path,channel_name, current_time  = await output_file(channel)

                    if not recording_started:
                        log.info(
                            f"Recording started for {channel_name} at {current_time}."
                        )
                        recording_started = True

                    if stream_process and stream_process.returncode is None:
                        stream_process.kill()
                        await stream_process.wait()
                        log.info("Existing stream process killed successfully.")

                    if ffmpeg_process and ffmpeg_process.returncode is None:
                        ffmpeg_process.kill()
                        await ffmpeg_process.wait()
                        log.info("Existing ffmpeg process killed successfully.")


                    rpipe, wpipe = os.pipe()

                    streamlink_command =  await platform.stream_process_arguments(
                        streamlink_path,
                        PLUGIN_DIR_PATH,
                        stream_segment_threads,
                        ffmpeg_path,
                        wpipe,
                        )


                    # Start streamlink subprocess
                    stream_process = await asyncio.create_subprocess_exec(
                        *streamlink_command,
                        stdout=wpipe
                    )
                    os.close(wpipe)

                    # Start ffmpeg subprocess
                    ffmpeg_command = [
                        str(ffmpeg_path), 
                        # "-hide_banner",
                        "-v", 
                        "info", 
                        "-i", "-", 
                    ]
                    # ffmpeg_command += ["-c:v", "libx265", 
                    #     "-crf", "23",
                    #     "-b:v", "0",
                    # ]
                    ffmpeg_command += [
                        "-c:v", "hevc_nvenc", 
                        "-preset", "slow",            # Slow preset for higher quality encoding
                        # "-cq", "30",                  # Constant quantizer value for quality control (lower is better)
                        "-profile:v", "main",       # Use 8-bit color profile 
                        "-tier", "high",              # Use high tier for better quality
                        "-tune", "hq",                # Tune for high-quality output
                        "-pix_fmt", "yuv420p",         # Set pixel format to 8-bit 
                        "-b:v", "500k",               # Set target bitrate
                        "-maxrate", "1M",           # Set maximum allowed bitrate
                        "-bufsize", "10M",           # Set buffer size (controls bitrate fluctuations)
                        "-rc", "vbr",             # Use constant quantizer rate control for consistent quality
                        "-g", "250"                   # Set GOP size to 250 frames
                    ]

                    ffmpeg_command += [
                        "-r", "25", 
                        "-an",
                          output_path
                        ,"-progress",
                        "pipe:1"
                     ]
                    ffmpeg_process = await asyncio.create_subprocess_exec(
                        *ffmpeg_command,
                        stdin=rpipe,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    os.close(rpipe)
                    stdout_task = asyncio.create_task(
                        read_stream(ffmpeg_process.stdout, channel_name, "stdout")
                    )
                    stderr_task = asyncio.create_task(
                        read_stream(ffmpeg_process.stderr, channel_name, "stderr")
                    )
                    # log.info(ffmpeg_process.returncode)
                    await asyncio.gather(
                        stdout_task, stderr_task, 
                        ffmpeg_process.wait()
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

                    if recording_started:
                        log.info(f"Recording stopped for {channel_name}.")
                        recording_started = False

                except Exception as e:
                    log.exception(
                        f"Error occurred while recording {channel_name}: {e}"
                    )
                    if recording_started:
                        log.info(f"Recording stopped for {channel_name}.")
                        recording_started = False
            else:
                log.error(f"No stream URL available for {channel['name']}")
                if recording_started:
                    log.info(f"Recording stopped for {channel_name}.")
                    recording_started = False

            await asyncio.sleep(timeout)

    finally:
        if stream_process and stream_process.returncode is None:
            stream_process.kill()
            await stream_process.wait()
        if ffmpeg_process and ffmpeg_process.returncode is None:
            ffmpeg_process.kill()
            await ffmpeg_process.wait()

  # Function to read and log output
async def read_ffmpeg_output(stream, log_method):
    while True:
        line = await stream.readline()
        if not line:
            break
        log_method(line.decode().strip())

async def manage_recording_tasks():
    active_tasks: Dict[str, asyncio.Task] = {}
    timeout, stream_segment_threads, channels, delays = await load_settings(FILES)
    streamlink_path, ffmpeg_path = await setup_paths()

    async with aiohttp.ClientSession() as session:
        while not shutdown_event.is_set():
            new_timeout, new_stream_segment_threads, new_channels, new_delays = (
                await load_settings(FILES)
            )
            active_channels = 0

            current_channel_ids = {channel.get("id") for channel in new_channels}

            for channel_id in list(active_tasks.keys()):
                if channel_id not in current_channel_ids:
                    task = active_tasks.pop(channel_id)
                    task.cancel()
                    log.info(
                        f"Cancelled recording task for removed channel: {channel['name']}"
                    )

            for channel in new_channels:
                channel_id = channel.get("id")
                if channel_id not in active_tasks:
                    if channel.get("active", "on") == "on" :
                        task = asyncio.create_task(
                            record_stream(
                                channel,
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
                        log.info(
                            f"Started recording task for new active channel: {channel['name']}"
                        )
                else:
                    if channel.get("active", "on") == "off":
                        task = active_tasks.pop(channel_id)
                        task.cancel()
                        log.info(
                            f"Cancelled recording task for deactivated channel: {channel['name']}"
                        )
                    else:
                        active_channels += 1

            if active_channels == 0:
                log.info("All channels are inactive. No active recordings.")

            await asyncio.sleep(10)

def handle_shutdown():
    log.info("Received shutdown signal. Shutting down...")
    shutdown_event.set()

async def main() -> None:
    try:
        await manage_recording_tasks()
    except KeyboardInterrupt:
        log.info("Received KeyboardInterrupt. Shutting down...")
        handle_shutdown()
        # Wait a moment to allow tasks to clean up
        await asyncio.sleep(0.1)    
    except Exception as e:
        log.exception(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
