import logging
import re
import time
from typing import Any, Dict, Tuple, Union, TypedDict, Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs, urlunparse

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


def stream_error_status_code(err: StreamError) -> Optional[int]:
    response = getattr(err, "response", None)
    if response is None:
        response = getattr(getattr(err, "err", None), "response", None)
    return getattr(response, "status_code", None)


class ChzzkHLSStreamWorker(HLSStreamWorker):
    """
    Custom HLS Stream Worker for Chzzk.
    """

    stream: "ChzzkHLSStream"

    def _fetch_playlist(self) -> Any:
        last_error: Optional[StreamError] = None
        for attempt in range(2):  # Retry once before failing
            try:
                return super()._fetch_playlist()
            except StreamError as err:
                last_error = err
                status_code = stream_error_status_code(err)
                if status_code is not None and status_code < 400:
                    log.debug(f"Non-recoverable error occurred: {err}")
                    raise
                if attempt == 1:
                    break
                self.stream.refresh_playlist()
                log.debug(f"Force-reloading the channel playlist on error: {err}")
        raise last_error or StreamError("Failed to fetch playlist after retries")


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
        if not data or len(data) < 2:
            raise StreamError("Error occurred while refreshing the stream URL.")
        media, status, *_ = data
        if status != "OPEN" or media is None:
            raise StreamError("Error occurred while refreshing the stream URL.")
        current_quality = self._playlist_quality(self._url)
        for media_info in media:
            if (
                len(media_info) >= 3
                and media_info[1] == "HLS"
                and media_info[0] == "HLS"
            ):
                media_path = self._update_domain(media_info[2])
                request_args = dict(self.args)
                request_args.pop("url", None)
                res = type(self)._fetch_playlist(self.session, media_path, **request_args)
                m3u8 = parse_m3u8(res, parser=type(self).__parser__)
                playlists = [playlist for playlist in m3u8.playlists if playlist.stream_info]
                if not playlists:
                    continue

                playlist = self._select_refreshed_playlist(playlists, current_quality)
                new_url = self._update_domain(playlist.uri)
                self._url = new_url
                self.args["url"] = new_url
                log.debug("Refreshed the stream URL.")
                self._expire = self._get_expire_time(self._url)
                return
        raise StreamError("No valid HLS stream found in the refreshed playlist.")

    def _playlist_quality(self, url: str) -> Optional[str]:
        for part in urlparse(url).path.split("/"):
            if re.fullmatch(r"\d+p(?:\d+)?", part):
                return part
        return None

    def _select_refreshed_playlist(
        self, playlists: List[Any], quality: Optional[str]
    ) -> Any:
        if quality is not None:
            for playlist in playlists:
                if self._playlist_quality(playlist.uri) == quality:
                    return playlist
        return playlists[-1]

    def _update_domain(self, url: str) -> str:
        """
        Update the domain of the given URL if it matches specific criteria.
        """
        parsed = urlparse(url)
        if parsed.hostname == "livecloud.pstatic.net":
            return urlunparse(parsed._replace(netloc="nlive-streaming.navercdn.com"))
        return url

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
        r"https?://chzzk\.naver\.com/live/(?P<channel_id>[A-Za-z0-9_-]{1,128})",
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

        if len(data) < 7:
            log.error("Incomplete data received from API.")
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
            if (
                len(media_info) >= 3
                and media_info[1] == "HLS"
                and media_info[0] == "HLS"
            ):
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
        parsed = urlparse(url)
        if parsed.hostname == "livecloud.pstatic.net":
            return urlunparse(parsed._replace(netloc="nlive-streaming.navercdn.com"))
        return url

    def _get_streams(self) -> Optional[Dict[str, HLSStream]]:
        if self.matches["live"]:
            return self._get_live(self.match["channel_id"])
        return None


__plugin__ = Chzzk
