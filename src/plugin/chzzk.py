
from logger import log
import aiohttp
from typing import Any, Dict, List, Tuple
from pathlib import Path
from utils import load_json_async




class Chzzk:
    def __init__(self, channel: Dict[str, Any]):
        self.stream_url =  f"https://chzzk.naver.com/live/{channel['id']}"
        self.LIVE_DETAIL_API = (
            "https://api.chzzk.naver.com/service/v3/channels/{channel_id}/live-detail"
        )

        
    def get_auth_headers(self, cookies: Dict[str, str]) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (X11; Unix x86_64)",
            "Cookie": f'NID_AUT={cookies.get("NID_AUT", "")}; NID_SES={cookies.get("NID_SES", "")}',
            "Origin": "https://chzzk.naver.com",
            "DNT": "1",
            "Sec-GPC": "1",
            "Connection": "keep-alive",
            "Referer": "",
        }


    async def get_session_cookies(self) -> Dict[str, str]:
        base_directory = Path(__file__).resolve().parents[1] / "files"
        COOKIE_FILE_PATH = base_directory/  Path("cookie.json")
        return await load_json_async(COOKIE_FILE_PATH)

    async def stream_process_arguments(
        self,
        streamlink_path: Path, 
        plugin_dir: Path, 
        stream_segment_threads: int,
        ffmpeg_path: Path,
        wpipe: int,
    ):
        cookies = await self.get_session_cookies()
        args = ( 
            str(streamlink_path),
            "--stdout",
            self.stream_url,
            "best",
            "--hls-live-restart",
            # "--plugin-dirs",
            # str(plugin_dir),
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
            "--hls-segment-stream-data"
        )
        return args
    
    
    async def get_live_status(self,
        channel: Dict[str, Any], session: aiohttp.ClientSession
    ) -> str:
        # log.debug(f"Fetching live info for channel: {channel['name']}")
        headers = self.get_auth_headers(await self.get_session_cookies())

        try:
            async with session.get(
                self.LIVE_DETAIL_API.format(channel_id=channel["id"]), headers=headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                # log.debug(   
                #     f"Successfully fetched live info for channel: {channel['name']}, data: {data}"
                # )

                content = data.get("content", {})
                status = content.get("status", "")
                if status == "OPEN":
                    return status
                return "CLOSE"
        except aiohttp.ClientError as e:
            log.error(
                f"HTTP error occurred while fetching live info for {channel['name']}: {e}"
            )
        except AttributeError as e:
            pass
        except Exception as e:
            log.error(f"Failed to fetch live info for {channel['name']}: {e}")
        return "CLOSE"

