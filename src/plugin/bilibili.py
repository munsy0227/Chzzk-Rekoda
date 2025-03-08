
from pathlib import Path
from typing import Any, Dict, Tuple
import aiohttp
from logger import log

class Bilibili:
    def __init__(self, channel: Dict[str, Any]):
        self.stream_url =  f"https://live.bilibili.com/{channel['id']}"
        self.LIVE_DETAIL_API = 'https://api.live.bilibili.com/room/v1/Room/get_info'

    async def get_live_status(   
        self,
        channel: Dict[str, Any], 
        session: aiohttp.ClientSession
    ) -> str:
        log.debug(f"Fetching live info for channel: {channel['name']}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "https://www.bilibili.com/"}
            
            params = {"room_id": channel['id']}

            async with session.get(
                self.LIVE_DETAIL_API,
                params=params,
                headers=headers ) as r:

                r.raise_for_status()
                info = await r.json()  
                if info['data']['live_status']:
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
        wpipe: int,) -> Tuple:

        args = ( 
            "streamlink",
            self.stream_url, "best",
            "--plugin-dir",
            "C:\Apps\Macros\streamlink\src\plugin\reserved\bilibili.py", #teemp
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