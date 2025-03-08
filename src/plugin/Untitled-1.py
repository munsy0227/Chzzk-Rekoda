import subprocess

# Define the streamlink command
streamlink_command = [
    "streamlink",
    "https://live.bilibili.com/22406972",
    "best",
    "--stream-segment-threads", "10",
    "--ringbuffer-size", "256M",
    "--hls-playlist-reload-attempts", "10",
    "--hls-live-restart",
    "--hls-playlist-reload-time", "segment",
    "--stream-segment-attempts", "10",
    "--stream-segment-timeout", "240",
    "--stdout",
    "--http-header", "Referer=https://www.bilibili.com/",
    "--ffmpeg-ffmpeg", "C:/Apps/Macros/streamlink/ffmpeg/bin/ffmpeg.exe"
]

# Define the ffmpeg command
ffmpeg_command = [
    "C:/Apps/Macros/streamlink/ffmpeg/bin/ffmpeg.exe",
    "-c:v", "hevc_nvenc",
    "-preset", "slow",
    "-profile:v", "main",
    "-tier", "high",
    "-tune", "hq",
    "-pix_fmt", "yuv420p",
    "-b:v", "500k",
    "-maxrate", "1M",
    "-bufsize", "10M",
    "-rc", "vbr",
    "-g", "250",
    "-r", "25",
    "-an",
    "-progress", "pipe:1"
]

try:
    # Open a pipe to the streamlink process
    streamlink_process = subprocess.Popen(streamlink_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Open a pipe to the ffmpeg process, reading from streamlink's output
    ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=streamlink_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for the ffmpeg process to complete
    ffmpeg_stdout, ffmpeg_stderr = ffmpeg_process.communicate()

    # Wait for streamlink process to complete
    streamlink_stdout, streamlink_stderr = streamlink_process.communicate()

    # Check for errors in streamlink
    if streamlink_process.returncode != 0:
        print(f"Streamlink error: {streamlink_stderr.decode()}")
    
    # Check for errors in ffmpeg
    if ffmpeg_process.returncode != 0:
        print(f"FFmpeg error: {ffmpeg_stderr.decode()}")

except Exception as e:
    print(f"Error running the command: {e}")
