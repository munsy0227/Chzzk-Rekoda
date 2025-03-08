from typing import Any, Dict, List, Tuple
from abc import ABC, abstractmethod, abstractproperty
from pathlib import Path
import aiohttp

class StreamingPlatforms(ABC):
    @property
    def stream_url(self):
        pass 
    @property
    def LIVE_DETAIL_API(self):
        pass
    @abstractmethod
    async def stream_process_arguments(     
        self,
        streamlink_path: Path, 
        plugin_dir: Path, 
        stream_segment_threads: int,
        ffmpeg_path: Path,
        wpipe: int,) -> Tuple:
        pass

    @abstractmethod
    async def get_live_status(   
        self,
        channel: Dict[str, Any], 
        session: aiohttp.ClientSession
    ) -> str:
        pass

