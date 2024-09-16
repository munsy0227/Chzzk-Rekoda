import logging
import re
import time
from typing import Any, Dict, Tuple, Union, TypedDict, Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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
        for attempt in range(2):  # Retry once before failing
            try:
                return super()._fetch_playlist()
            except StreamError as err:
                if err.response is not None and err.response.status_code >= 400:
                    self.stream.refresh_playlist()
                    log.debug(f"Force-reloading the channel playlist on error: {err}")
                else:
                    log.debug(f"Non-recoverable error occurred: {err}")
                    raise err
        raise StreamError("Failed to fetch playlist after retries")


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

    _REFRESH_BEFORE = 3 * 60 * 60  # 3 hours

    def __init__(self, session, url: str, channel_id: str, *args, **kwargs) -> None:
        super().__init__(session, url, *args, **kwargs)
        self._url = url
        self._channel_id = channel_id
        self._api = ChzzkAPI(session)
        self._expire = self._get_expire_time(url)

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
                media_path = self._update_domain(media_info[2])
                res = self._fetch_variant_playlist(self.session, media_path)
                m3u8 = parse_m3u8(res)
                for playlist in m3u8.playlists:
                    if playlist.stream_info:
                        new_url = self._update_domain(playlist.uri)
                        self._replace_token(new_url)
                        log.debug(f"Refreshed the stream URL to {self._url}")
                        self._expire = self._get_expire_time(self._url)
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
        parsed_old = urlparse(self._url)
        parsed_new = urlparse(new_url)
        qs_old = parse_qs(parsed_old.query)
        qs_new = parse_qs(parsed_new.query)
        # Replace the 'hdnts' parameter with the new token
        qs_old["hdnts"] = qs_new.get("hdnts", qs_old.get("hdnts"))
        new_query = urlencode(qs_old, doseq=True)
        self._url = urlunparse(parsed_old._replace(query=new_query))

    def _get_expire_time(self, url: str) -> Optional[int]:
        """
        Extract the expiration time from the URL's 'exp' parameter.
        """
        parsed_url = urlparse(url)
        qs = parse_qs(parsed_url.query)
        exp_values = qs.get("exp")
        if exp_values and exp_values[0].isdigit():
            return int(exp_values[0])
        return None

    def _should_refresh(self) -> bool:
        """
        Determine if the stream URL should be refreshed based on expiration time.
        """
        return (
            self._expire is not None
            and time.time() >= self._expire - self._REFRESH_BEFORE
        )

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
    media: List[Dict[str, str]]


@dataclass
class ChzzkAPI:
    """
    API client for Chzzk.
    """

    session: Any
    _CHANNELS_LIVE_DETAIL_URL: str = (
        "https://api.chzzk.naver.com/service/v3/channels/{channel_id}/live-detail"
    )

    def _query_api(
        self, url: str, *schemas: validate.Schema
    ) -> Tuple[str, Union[Dict[str, Any], str]]:
        response = self.session.http.get(
            url,
            acceptable_status=(200, 404),
            headers={"Referer": "https://chzzk.naver.com/"},
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
        return response

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
        self.author: Optional[str] = None
        self.category: Optional[str] = None
        self.title: Optional[str] = None

    def _get_live(self, channel_id: str) -> Optional[Dict[str, HLSStream]]:
        datatype, data = self._api.get_live_detail(channel_id)
        if datatype == "error":
            log.error(data)
            return None
        if data is None:
            return None

        media, status, self.id, self.author, self.category, self.title, adult = data
        if status != self._STATUS_OPEN:
            log.error("The stream is unavailable")
            return None
        if media is None:
            log.error(f"This stream is {'for adults only' if adult else 'unavailable'}")
            return None

        streams = {}
        for media_info in media:
            if media_info[1] == "HLS" and media_info[0] == "HLS":
                media_path = self._update_domain(media_info[2])
                hls_streams = ChzzkHLSStream.parse_variant_playlist(
                    self.session,
                    media_path,
                    channel_id=channel_id,
                )
                if hls_streams:
                    streams.update(hls_streams)
        if not streams:
            log.error("No valid HLS streams found.")
            return None
        return streams

    def _update_domain(self, url: str) -> str:
        """
        Update the domain of the given URL if it matches specific criteria.
        """
        if "livecloud.pstatic.net" in url:
            return url.replace("livecloud.pstatic.net", "nlive-streaming.navercdn.com")
        return url

    def _get_streams(self) -> Optional[Dict[str, HLSStream]]:
        if self.matches["live"]:
            return self._get_live(self.match["channel_id"])
        return None


__plugin__ = Chzzk
