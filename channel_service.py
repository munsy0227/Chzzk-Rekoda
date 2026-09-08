"""CHZZK channel metadata shared by CLI and GUI."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from config_store import (
    CHZZK_API_TIMEOUT_SECONDS,
    CHZZK_CHANNEL_DETAIL_URL,
    CHZZK_CHANNEL_SEARCH_URL,
    CHZZK_SEARCH_RESULT_LIMIT,
    CONTROL_CHARS,
    INVALID_FOLDER_CHARS,
    SAFE_CHANNEL_ID,
    WINDOWS_RESERVED_NAMES,
)
from i18n import translate


def request_chzzk_api(url, language, params=None):
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Accept-Language": language,
            "Referer": "https://chzzk.naver.com/",
            "Origin": "https://chzzk.naver.com",
        },
    )
    try:
        with urlopen(request, timeout=CHZZK_API_TIMEOUT_SECONDS) as response:
            data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                return None, translate(language, "settings.api_invalid_response")
            payload = json.loads(data.decode("utf-8"))
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as error:
        message = str(error).strip().splitlines()[0] or type(error).__name__
        return None, message

    if not isinstance(payload, dict) or payload.get("code") != 200:
        message = payload.get("message") if isinstance(payload, dict) else None
        return None, str(
            message or translate(language, "settings.api_invalid_response")
        )

    content = payload.get("content")
    if not isinstance(content, dict):
        return None, translate(language, "settings.api_missing_content")
    return content, None


def search_chzzk_channels(keyword, language):
    content, error = request_chzzk_api(
        CHZZK_CHANNEL_SEARCH_URL,
        language,
        {
            "keyword": keyword,
            "offset": 0,
            "size": CHZZK_SEARCH_RESULT_LIMIT,
            "withFirstChannelContent": "false",
        },
    )
    if error:
        return [], error

    data = content.get("data")
    if not isinstance(data, list):
        return [], translate(language, "settings.api_invalid_response")

    results = []
    seen_ids = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        channel = item.get("channel")
        if not isinstance(channel, dict):
            continue
        channel_id = str(channel.get("channelId", "")).strip()
        name = CONTROL_CHARS.sub("", str(channel.get("channelName", ""))).strip()
        if (
            not SAFE_CHANNEL_ID.fullmatch(channel_id)
            or not name
            or channel_id in seen_ids
        ):
            continue
        seen_ids.add(channel_id)
        results.append(
            {
                "id": channel_id,
                "name": name,
                "image_url": channel_image_url(channel.get("channelImageUrl")),
            }
        )
    return results, None


def fetch_chzzk_channel(channel_id, language):
    if not SAFE_CHANNEL_ID.fullmatch(channel_id):
        return None, translate(language, "settings.invalid_channel_id")
    content, error = request_chzzk_api(
        CHZZK_CHANNEL_DETAIL_URL.format(channel_id=channel_id),
        language,
    )
    if error:
        return None, error

    returned_id = str(content.get("channelId", "")).strip()
    name = CONTROL_CHARS.sub("", str(content.get("channelName", ""))).strip()
    if returned_id != channel_id or not name:
        return None, translate(language, "settings.api_invalid_channel_data")
    return {
        "id": returned_id,
        "name": name,
        "image_url": channel_image_url(content.get("channelImageUrl")),
    }, None


def channel_image_url(value):
    """Only accept public HTTPS profile-image URLs supplied by CHZZK."""
    if not isinstance(value, str) or len(value) > 4096:
        return ""
    try:
        url = urlparse(value)
        host = (url.hostname or "").lower()
        if (
            url.scheme == "https"
            and not url.username
            and not url.password
            and (
                host.endswith(".pstatic.net")
                or host.endswith(".naver.net")
                or host.endswith(".naver.com")
            )
        ):
            return value
    except ValueError:
        pass
    return ""


def find_channel_by_id(channels, channel_id):
    return next(
        (channel for channel in channels if channel.get("id") == channel_id),
        None,
    )


def channels_with_name(channels, name, exclude_id=None):
    normalized_name = name.casefold()
    return [
        channel
        for channel in channels
        if channel.get("id") != exclude_id
        and str(channel.get("name", "")).casefold() == normalized_name
    ]


def safe_channel_folder_name(name, channel_id):
    folder_name = INVALID_FOLDER_CHARS.sub("_", CONTROL_CHARS.sub("", name))
    folder_name = folder_name.strip().strip(".")
    if folder_name.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        folder_name = f"_{folder_name}"
    return folder_name[:120] or channel_id
