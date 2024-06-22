import logging
import re
import time
from typing import Any, Dict, Tuple, Union, TypedDict
from dataclasses import dataclass

from streamlink.exceptions import StreamError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import (
    HLSStream,
    HLSStreamReader,
    HLSStreamWorker,
    parse_m3u8,
)

log = logging.getLogger(__name__)


class ChzzkHLSStreamWorker(HLSStreamWorker):
    """
    Custom HLS Stream Worker for Chzzk.
    """

    stream: "ChzzkHLSStream"

    def _fetch_playlist(self) -> Any:
        try:
            return super()._fetch_playlist()
        except StreamError as err:
            if err.response.status_code >= 400:
                self.stream.refresh_playlist()
                log.debug(f"Force-reloading the channel playlist on error: {err}")
            raise err


class ChzzkHLSStreamReader(HLSStreamReader):
    """
    Custom HLS Stream Reader for Chzzk.
    """

    __worker__ = ChzzkHLSStreamWorker


class ChzzkHLSStream(HLSStream):
    """
    Custom HLS Stream for Chzzk with token refresh capability.
    """

    __shortname__ = "hls-chzzk"
    __reader__ = ChzzkHLSStreamReader

    _EXPIRE = re.compile(r"exp=(\d+)")
    _REFRESH_BEFORE = 3 * 60 * 60  # 3 hours

    def __init__(self, session, url: str, channel_id: str, *args, **kwargs) -> None:
        super().__init__(session, url, *args, **kwargs)
        self._url = url
        self._channel_id = channel_id
        self._api = ChzzkAPI(session)

    def refresh_playlist(self) -> None:
        """
        Refresh the stream URL to get a new token and handle domain change.
        """
        log.debug("Refreshing the stream URL to get a new token.")
        datatype, data = self._api.get_live_detail(self._channel_id)
        if datatype == "error":
            raise StreamError(data)
        media, status, *_ = data
        if status != "OPEN" or media is None:
            raise StreamError("Error occurred while refreshing the stream URL.")
        for media_info in media:
            if media_info[1] == "HLS" and media_info[0] == "HLS":
                media_path = media_info[2]
                media_path = self._update_domain(media_path)
                res = self._fetch_variant_playlist(self.session, media_path)
                m3u8 = parse_m3u8(res)
                for playlist in m3u8.playlists:
                    if playlist.stream_info:
                        new_url = playlist.uri
                        new_url = self._update_domain(new_url)
                        self._replace_token(new_url)
                        log.debug(f"Refreshed the stream URL to {self._url}")
                        return
        raise StreamError("No valid HLS stream found in the refreshed playlist.")

    def _update_domain(self, url: str) -> str:
        """
        Update the domain of the given URL if it matches specific criteria.
        """
        if "livecloud.pstatic.net" in url:
            return url.replace("livecloud.pstatic.net", "nlive-streaming.navercdn.com")
        return url

    def _replace_token(self, new_url: str) -> None:
        """
        Replace the token in the current URL with the token from the new URL.
        """
        old_token = self._get_token(self._url)
        new_token = self._get_token(new_url)
        self._url = self._url.replace(old_token, new_token)

    def _get_token(self, url: str) -> str:
        """
        Extract the token from the given URL.
        """
        return url.split("?hdnts=")[-1]

    def _should_refresh(self) -> bool:
        return (
            self._expire is not None
            and time.time() >= self._expire - self._REFRESH_BEFORE
        )

    @property
    def _expire(self) -> Union[int, None]:
        match = self._EXPIRE.search(self._url)
        if match:
            return int(match.group(1))
        return None

    @property
    def url(self) -> str:
        if self._should_refresh():
            self.refresh_playlist()
        return self._url


class LiveDetail(TypedDict):
    status: str
    liveId: int
    liveTitle: Union[str, None]
    liveCategory: Union[str, None]
    adult: bool
    channel: str
    media: list[Dict[str, str]]


@dataclass
class ChzzkAPI:
    """
    API client for Chzzk.
    """

    session: Any
    _CHANNELS_LIVE_DETAIL_URL: str = (
        "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
    )

    def __post_init__(self):
        self.session.http.headers.update(
            {"Cookie": self.session.http.headers.get("Cookie")}
        )

    def _query_api(
        self, url: str, *schemas: validate.Schema
    ) -> Tuple[str, Union[Dict[str, Any], str]]:
        return self.session.http.get(
            url,
            acceptable_status=(200, 404),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "code": int,
                            "message": str,
                        },
                        validate.transform(lambda data: ("error", data["message"])),
                    ),
                    validate.all(
                        {
                            "code": 200,
                            "content": None,
                        },
                        validate.transform(lambda _: ("success", None)),
                    ),
                    validate.all(
                        {
                            "code": 200,
                            "content": dict,
                        },
                        validate.get("content"),
                        *schemas,
                        validate.transform(lambda data: ("success", data)),
                    ),
                ),
            ),
        )

    def get_live_detail(self, channel_id: str) -> Tuple[str, Union[LiveDetail, str]]:
        """
        Get live stream details for a given channel.
        """
        return self._query_api(
            self._CHANNELS_LIVE_DETAIL_URL.format(channel_id=channel_id),
            {
                "status": str,
                "liveId": int,
                "liveTitle": validate.any(str, None),
                "liveCategory": validate.any(str, None),
                "adult": bool,
                "channel": validate.all(
                    {"channelName": str},
                    validate.get("channelName"),
                ),
                "livePlaybackJson": validate.none_or_all(
                    str,
                    validate.parse_json(),
                    {
                        "media": [
                            validate.all(
                                {
                                    "mediaId": str,
                                    "protocol": str,
                                    "path": validate.url(),
                                },
                                validate.union_get(
                                    "mediaId",
                                    "protocol",
                                    "path",
                                ),
                            ),
                        ],
                    },
                    validate.get("media"),
                ),
            },
            validate.union_get(
                "livePlaybackJson",
                "status",
                "liveId",
                "channel",
                "liveCategory",
                "liveTitle",
                "adult",
            ),
        )


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://chzzk\.naver\.com/live/(?P<channel_id>[^/?]+)",
    ),
)
class Chzzk(Plugin):
    """
    Plugin for Chzzk live streams.
    """

    _STATUS_OPEN = "OPEN"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._api = ChzzkAPI(self.session)

    def _get_live(self, channel_id: str) -> Union[None, HLSStream]:
        datatype, data = self._api.get_live_detail(channel_id)
        if datatype == "error":
            log.error(data)
            return
        if data is None:
            return

        media, status, self.id, self.author, self.category, self.title, adult = data
        if status != self._STATUS_OPEN:
            log.error("The stream is unavailable")
            return None
        if media is None:
            log.error(f"This stream is for {'adults only' if adult else 'unavailable'}")
            return None

        for media_info in media:
            if media_info[1] == "HLS" and media_info[0] == "HLS":
                media_path = self._update_domain(media_info[2])
                return ChzzkHLSStream.parse_variant_playlist(
                    self.session,
                    media_path,
                    channel_id=channel_id,
                )

    def _update_domain(self, url: str) -> str:
        """
        Update the domain of the given URL if it matches specific criteria.
        """
        if "livecloud.pstatic.net" in url:
            return url.replace("livecloud.pstatic.net", "nlive-streaming.navercdn.com")
        return url

    def _get_streams(self) -> Union[None, HLSStream]:
        if self.matches["live"]:
            return self._get_live(self.match["channel_id"])


__plugin__ = Chzzk
