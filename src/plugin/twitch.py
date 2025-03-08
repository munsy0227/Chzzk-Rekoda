

from logger import log
import aiohttp
from typing import Any, Dict, List, Tuple
from pathlib import Path
from utils import load_json_async
import requests
from dotenv import load_dotenv
import os


class Twitch:
    def __init__(self, channel: Dict[str, Any]):
        load_dotenv()

        self.stream_url =  f"https://www.twitch.tv/{channel["name"]}"
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.token_url = "https://id.twitch.tv/oauth2/token?client_id=" + self.client_id + "&client_secret=" \
                         + self.client_secret + "&grant_type=client_credentials"
        self.url = "https://api.twitch.tv/helix/streams"
        self.access_token = self.fetch_access_token()

        self.headers = {"Client-ID": self.client_id, "Authorization": "Bearer " + self.access_token}

    def fetch_access_token(self):
        token_response = requests.post(self.token_url, timeout=15)
        token_response.raise_for_status()
        token = token_response.json()
        return token["access_token"]
    
    
    async def get_live_status(
            self,
        channel: Dict[str, Any], session: aiohttp.ClientSession
    ) -> str:
        log.debug(f"Fetching live info for channel: {channel['name']}")
        try:
            async with session.get(
               self.url + "?user_login=" + channel['name'], headers=self.headers
            ) as r:
                r.raise_for_status()
                info = await r.json()
                if info["data"]:
                    if info["data"][0]['game_name'] == 'Art':
                        return "OPEN"
            return "CLOSE"
        except aiohttp.ClientError as e:
            log.error(
                f"HTTP error occurred while fetching live info for {channel['name']}: {e}"
            )
        except Exception as e:
            log.error(f"Failed to fetch live info for {channel['name']}: {e}")
        return "CLOSE"
    
    async def stream_process_arguments(
        self,
        streamlink_path: Path, 
        plugin_dir: Path, 
        stream_segment_threads: int,
        ffmpeg_path: Path,
        wpipe: int,
    ):
        args = ( 
            "streamlink", "-l", "trace", "--logfile", "./logging.log",
            "--twitch-disable-ads", 
            self.stream_url, "best",
            "--stream-segment-threads", "10", 
            "--ringbuffer-size", "256M", 
            "--hls-playlist-reload-attempts", "10",
            "--hls-live-restart" ,
            "--hls-playlist-reload-time", "segment",
            "--stream-segment-attempts", "10",
            "--stream-segment-timeout", "240",
            "--stdout",
            "--http-header",
            "Referer=",
            "--ffmpeg-ffmpeg",
            str(ffmpeg_path)

        )
        return args

