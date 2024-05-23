import logging
import re
import time
from typing import Any, Dict, Tuple, Union

from streamlink.exceptions import StreamError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWorker, parse_m3u8

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
        Refresh the stream URL to get a new token.
        """
        log.debug("Refreshing the stream URL to get a new token.")
        datatype, data = self._api.get_live_detail(self._channel_id)
        if datatype == "error":
            raise StreamError(data)
        media, status, *_ = data
        if status != "OPEN" or media is None:
            raise StreamError("Error occurred while refreshing the stream URL.")
        for media_id, media_protocol, media_path in media:
            if media_protocol == "HLS" and media_id == "HLS":
                media_uri = self._get_media_uri(media_path)
                self._replace_token_from(media_uri)
                log.debug(f"Refreshed the stream URL to {self._url}")
                break

    def _get_media_uri(self, media_path: str) -> str:
        res = self._fetch_variant_playlist(self.session, media_path)
        m3u8 = parse_m3u8(res)
        for playlist in m3u8.playlists:
            if playlist.stream_info:
                return playlist.uri
        raise StreamError("No valid stream found in playlist")

    def _get_token_from(self, path: str) -> str:
        return path.split("/")[-2]

    def _replace_token_from(self, media_uri: str) -> None:
        prev_token = self._get_token_from(self._url)
        current_token = self._get_token_from(media_uri)
        self._url = self._url.replace(prev_token, current_token)

    def _should_refresh(self) -> bool:
        return self._expire is not None and time.time() >= self._expire - self._REFRESH_BEFORE

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


class ChzzkAPI:
    """
    API client for Chzzk.
    """
    _CHANNELS_LIVE_DETAIL_URL = "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"

    def __init__(self, session) -> None:
        self._session = session

    def _query_api(self, url: str, *schemas: validate.Schema) -> Tuple[str, Union[Dict[str, Any], str]]:
        return self._session.http.get(
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
                            "content": dict,
                        },
                        validate.get("content"),
                        *schemas,
                        validate.transform(lambda data: ("success", data)),
                    ),
                ),
            ),
        )

    def get_live_detail(self, channel_id: str) -> Tuple[str, Union[Dict[str, Any], str]]:
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
            return None

        media, status, self.id, self.author, self.category, self.title, adult = data
        if status != self._STATUS_OPEN:
            log.error("The stream is unavailable")
            return None
        if media is None:
            log.error(f"This stream is for {'adults only' if adult else 'unavailable'}")
            return None

        for media_id, media_protocol, media_path in media:
            if media_protocol == "HLS" and media_id == "HLS":
                return ChzzkHLSStream.parse_variant_playlist(
                    self.session,
                    media_path,
                    channel_id=channel_id,
                )

    def _get_streams(self) -> Union[None, HLSStream]:
        if self.matches["live"]:
            return self._get_live(self.match["channel_id"])


__plugin__ = Chzzk
