import logging
import base64
import json
import re
from http.cookies import SimpleCookie
from typing import Any, Dict, Tuple, Union, TypedDict, Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.exceptions import StreamError
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from hls_continuity import (
    ChzzkContinuityReader, ChzzkM3U8Parser, ContinuitySource, SourcePath,
    Unavailable, cdn_from_url, parse_timestamp,
)

log = logging.getLogger(__name__)


def has_auth_cookies(session: Any) -> bool:
    http = getattr(session, "http", None)
    cookie_values: Dict[str, str] = {}

    cookie_jar = getattr(http, "cookies", None)
    if cookie_jar is not None:
        get_dict = getattr(cookie_jar, "get_dict", None)
        if callable(get_dict):
            cookie_values.update(get_dict())

    headers = getattr(http, "headers", {})
    cookie_header = headers.get("Cookie", "") if headers is not None else ""
    if cookie_header:
        parsed_cookies = SimpleCookie()
        parsed_cookies.load(cookie_header)
        cookie_values.update(
            {
                name: morsel.value
                for name, morsel in parsed_cookies.items()
            }
        )

    return all(
        str(cookie_values.get(name, "")).strip()
        for name in ("NID_AUT", "NID_SES")
    )


class ChzzkHLSStream(HLSStream):
    """
    Custom HLS Stream for Chzzk with token refresh capability.
    """

    __shortname__ = "hls-chzzk"
    __reader__ = ChzzkContinuityReader
    __parser__ = ChzzkM3U8Parser

    def __init__(self, session, url: str, channel_id: str, *args,
                 live_id=0, source_paths=(), start_lookback=0, resume=None,
                 time_machine_active=None,
                 source_mode="hls", source_cdn=None,
                 **kwargs) -> None:
        super().__init__(session, url, *args, **kwargs)
        self._url = url
        self._channel_id = channel_id
        self._api = ChzzkAPI(session)
        self.continuity = ContinuitySource(
            self, self._source_snapshot, live_id, source_paths,
            lookback=start_lookback, resume=resume,
            time_machine_active=time_machine_active,
            mode=source_mode, cdn=source_cdn,
        )

    def _source_snapshot(self):
        datatype, data = self._api.get_live_detail(self._channel_id)
        if datatype == "error":
            raise Unavailable("API unavailable")
        if not data or data[1] != "OPEN":
            return None
        media, _, live_id, _, _, _, _, membership = data[:8]
        if not media:
            raise Unavailable("Media unavailable or unauthorized")
        if membership == "MEMBER_ONLY" and not has_auth_cookies(self.session):
            raise Unavailable("Authentication required")
        return live_id, source_paths(media), data[8]

    @property
    def url(self) -> str:
        # Discovery and token recovery are single-flight in ContinuitySource.
        return self._url


def source_paths(media):
    """Keep advertised sources and probe the known Akamai hostname mapping."""
    paths = []
    for item in media:
        if item.get("mediaId") not in {"HLS", "LLHLS"} or item.get("protocol") != "HLS":
            continue
        mode = "llhls" if item["mediaId"] == "LLHLS" else "hls"
        paths.append(SourcePath(item["path"], False, mode, cdn_from_url(item["path"])))
        for track in item.get("encodingTrack", []):
            p2p_path = track.get("p2pPath")
            if not isinstance(p2p_path, str):
                continue
            for encoded in parse_qs(urlparse(p2p_path).query).get("cdn_url", []):
                try:
                    url = base64.b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")
                    parsed = urlparse(url)
                    if parsed.scheme in ("http", "https") and parsed.netloc:
                        paths.append(SourcePath(url, True, "hls", cdn_from_url(url)))
                except (ValueError, UnicodeError):
                    continue
    # The user authorized testing Akamai even when the domestic API does not
    # advertise it. Keep the entire signed path/query, substitute only these
    # known CHZZK origins, and verify rendition/init/media before use.
    for path in list(paths):
        parsed = urlparse(path.url)
        if (not path.history and path.cdn == "korean" and parsed.scheme == "https"
                and parsed.hostname in {"nvelop-livecloud.pstatic.net", "livecloud.pstatic.net"}
                and parsed.username is None and parsed.port in (None, 443)):
            url = parsed._replace(netloc="livecloud.akamaized.net").geturl()
            if not any(p.url == url and p.mode == path.mode for p in paths):
                paths.append(SourcePath(url, False, path.mode, "akamai", probe=True))
    return sorted(dict.fromkeys(paths), key=lambda p: p.priority)


def resume_option(value):
    data = json.loads(value)
    if (not isinstance(data, dict) or type(data.get("live_id")) is not int
            or not isinstance(data.get("rendition"), str)
            or not isinstance(data.get("from"), str)
            or type(data.get("after_gap", False)) is not bool):
        raise ValueError("Invalid resume position")
    parse_timestamp(data["from"])
    return data


class LiveDetail(TypedDict):
    status: str
    liveId: int
    liveTitle: Union[str, None]
    liveCategory: Union[str, None]
    adult: bool
    membershipBenefitType: Optional[str]
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
            timeout=(5, 5),
            retries=0,
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
                validate.optional("timeMachineActive"): validate.any(bool, None),
                validate.optional("membershipBenefitType"): validate.any(str, None),
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
                                    validate.optional("encodingTrack"): [dict],
                                },
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
                "membershipBenefitType",
                "timeMachineActive",
            ),
        )


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://chzzk\.naver\.com/live/"
        r"(?P<channel_id>[A-Za-z0-9_-]{1,128})(?=$|[/?#])",
    ),
)
@pluginargument("start-lookback", type=int, choices=[0, 3600], default=0)
@pluginargument("resume", type=resume_option, default=None)
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

        if len(data) < 8:
            log.error("Incomplete data received from API.")
            return None

        (
            media,
            status,
            self.id,
            self.author,
            self.category,
            self.title,
            adult,
            membership_benefit_type,
        ) = data[:8]
        if status != self._STATUS_OPEN:
            log.error("The stream is unavailable")
            return None
        if (
            membership_benefit_type == "MEMBER_ONLY"
            and not has_auth_cookies(self.session)
        ):
            log.error(
                "This stream can be recorded with a Naver Plus Membership or "
                "Cheat Key subscription. Set both NID_AUT and NID_SES cookie "
                "values."
            )
            return None
        if media is None:
            if membership_benefit_type == "MEMBER_ONLY":
                log.error(
                    "This stream requires a Naver Plus Membership or Cheat Key "
                    "subscription. Check that NID_AUT and NID_SES are valid for "
                    "the subscribed account."
                )
                return None
            log.error(f"This stream is {'for adults only' if adult else 'unavailable'}")
            return None

        streams = {}
        paths = source_paths(media)
        # Resolve the preferred CDN first. A standby query must not delay a
        # usable domestic stream or replace its rendition with the last result.
        for path in paths:
            if not path.history:
                media_path = path.url
                try:
                    hls_streams = ChzzkHLSStream.parse_variant_playlist(
                        self.session,
                        media_path,
                        channel_id=channel_id,
                        live_id=self.id,
                        source_paths=paths,
                        source_mode=path.mode,
                        source_cdn=path.cdn,
                        start_lookback=self.get_option("start-lookback"),
                        resume=self.get_option("resume"),
                        time_machine_active=data[8],
                    )
                except (StreamError, ValueError):
                    # Signed URLs can occur in the original request exception.
                    continue
                if hls_streams:
                    for name, stream in hls_streams.items():
                        streams.setdefault(name, stream)
                    break
        if not streams:
            log.error("No valid HLS streams found.")
            return None
        return streams

    def _get_streams(self) -> Optional[Dict[str, HLSStream]]:
        if self.matches["live"]:
            return self._get_live(self.match["channel_id"])
        return None


__plugin__ = Chzzk
