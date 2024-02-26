import json
import subprocess
import time
import re
import os
import asyncio
import importlib
import requests
import signal
from threading import Thread

# 타이틀 출력문구
print("Chzzk 자동녹화 Linux CLI")

# streamlink 상대경로
streamlink_path = os.path.join(os.path.dirname(__file__), "venv", "bin", "streamlink")

# FFmpeg 절대경로
ffmpeg_path = os.path.abspath("/usr/bin/ffmpeg")

# 현재 시스템 PATH 가져와 FFmpeg 임시등록
def add_ffmpeg_to_path(ffmpeg_directory):
    current_path = os.environ.get("PATH", "")

    # FFmpeg의 경로를 현재 PATH에 추가
    if ffmpeg_directory not in current_path:
        os.environ["PATH"] = f"{current_path};{ffmpeg_directory}"

# FFmpeg를 PATH에 추가
add_ffmpeg_to_path(os.path.dirname(ffmpeg_path))


# Chzzk API 엔드포인트
LIVE_DETAIL_API = "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"


#방송상태 감지 주기 확인
script_directory = os.path.dirname(os.path.abspath(__name__))
time_file_path = os.path.join(script_directory, 'time_sleep.txt')
with open(time_file_path, "r") as time_file:
    timeout_str = time_file.readline().strip()
    timeout = int(timeout_str)

# thread.txt에서 값 불러오기
thread_file_path = os.path.join(script_directory, 'thread.txt')
with open(thread_file_path, "r") as thread_file:
    threads_str = thread_file.readline().strip()
    stream_segment_threads = int(threads_str) if threads_str.isdigit() else 2  # 기본값은 2로 설정합니다.

# 채널 정보
channels_file_path = os.path.join(script_directory, 'channels.json')
with open(channels_file_path, "r") as channels_file:
    channels = json.load(channels_file)


# 채널별 시작 딜레이 설정(초)
delays_file_path = os.path.join(script_directory, 'delays.json')
with open(delays_file_path, "r") as delays_file:
    delays = json.load(delays_file)


def get_auth_headers(cookies):
    # 헤더에 세션 정보 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
        'Cookie': f'NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}'
    }
    return headers

def get_session_cookies():
    # cookie.json 파일에서 세션 정보 읽어오기
    cookie_file_path = os.path.join(script_directory, 'cookie.json')

    with open(cookie_file_path, 'r') as cookie_file:
        cookies = json.load(cookie_file)

    return cookies

# resolution.txt에서 값 불러오기
resolution_file_path = os.path.join(script_directory, 'resolution.txt')
with open(resolution_file_path, "r") as resolution_file:
    resolution = resolution_file.readline().strip()

# 방송정보 불러오기
def get_live_info(channel, headers):
    try:
        response = requests.get(LIVE_DETAIL_API.format(channel_id=channel["id"]), headers=headers)
        response.raise_for_status()
        return response.json().get("content", {})
    except requests.RequestException as e:
        print(f"{channel['name']} 채널의 라이브 정보를 가져오는 데 실패했습니다: {e}")
        return None

# 녹화 주요함수
def record_stream(channel, headers):
    if channel["identifier"] in delays:
        delay = delays[channel["identifier"]]
    else:
        delay = 0  # 기본값으로 0을 설정합니다.

    time.sleep(delay)  # 딜레이만큼 대기합니다.
    
    # active 필드가 "off"이면 녹화를 실행하지 않습니다.
    if channel.get("active", "on") == "off":
        print(f"{channel['name']} 채널은 비활성화되어 있습니다. 녹화를 실행하지 않습니다.")
        return

    while True:
        live_info = get_live_info(channel, headers)

        if live_info and live_info.get("status") == "OPEN":
            channel_name = live_info.get("channel", {}).get("channelName")
            live_title = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", '', live_info.get("liveTitle").rstrip())
            live_category = live_info.get("liveCategory")
            current_time = time.strftime("%Y-%m-%d_%H:%M:%S")

            output_file = f"[{current_time}] {channel_name} {live_title}.ts"

            live_playback_json = json.loads(live_info.get("livePlaybackJson") or "{}")

            stream_url = live_playback_json.get("media", [{}])[0].get("path", "")
            if stream_url:
                try:
                    # 표준 출력을 캡처하여 subprocess.PIPE를 사용합니다.
                    process = subprocess.Popen(
                        [
                            streamlink_path,
                            stream_url,
                            resolution,   # 녹화본 해상도 설정(720p, 1080p, best(설정상 최고화질)
                            "--hls-live-restart",
                            "--stream-segment-threads", str(stream_segment_threads),  # 쓰레드 수를 설정합니다.
                            "--stream-segment-timeout", "5", 
                            "--stream-segment-attempts", "5",
                            "-o",
                            os.path.join(channel['output_dir'], output_file),
                            "--ffmpeg-ffmpeg",
                            ffmpeg_path,
                            "--ffmpeg-copyts"
                        ],
                        stdout=subprocess.PIPE,  # 표준 출력을 캡처합니다.
                        universal_newlines=True  # 텍스트 모드로 출력을 처리합니다.
                    )
                    # 캡처한 출력을 한 줄씩 읽어들여 화면에 출력합니다.
                    for line in process.stdout:
                        print(line, end='')
                except subprocess.CalledProcessError as e:
                    print(f"{channel['name']} 채널에 대한 녹화 중 오류가 발생했습니다: {e}")
        else:
            print(f"{channel['name']} 채널은 현재 방송중이 아닙니다.")

        time.sleep(timeout)  # 방송상태 감지 주기(초) 30~120초 권장



def main():
    headers = get_auth_headers(get_session_cookies())
    threads = [Thread(target=record_stream, args=(channel, headers)) for channel in channels]

    try:
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("사용자에 의해 녹화가 중단되었습니다.")

if __name__ == "__main__":
    main()
