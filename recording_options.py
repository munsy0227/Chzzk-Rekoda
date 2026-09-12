"""Shared, UI-independent quality selection and H.264 settings."""

import math
import re
from copy import deepcopy

DIRECT_QUALITIES = ("144p", "360p", "480p", "720p60", "1080p60")
QUALITY_DEFAULTS = {"mode": "best", "width": 0, "height": 1080, "fps": 0.0}
H264_DEFAULTS = {
    "enable": False,
    "encoder": "libx264",
    "bitrate": "2500k",
    "max_bitrate": "10000k",
    "preset": "veryfast",
}
H264_ENCODERS = {
    "libx264",
    "h264_nvenc",
    "h264_qsv",
    "h264_amf",
    "h264_vaapi",
    "h264_videotoolbox",
}
QUALITY_NAME = re.compile(r"^(\d+)p(?:(\d+(?:\.\d+)?))?(?:_alt\d*)?$")


def normalize_quality(value):
    result = deepcopy(QUALITY_DEFAULTS)
    if not isinstance(value, dict):
        return result
    result.update(value)
    if result["mode"] not in ("best", "custom", *DIRECT_QUALITIES):
        result["mode"] = "best"
    for key, low, high in (("width", 0, 8192), ("height", 2, 4320)):
        try:
            number = int(result[key])
            result[key] = max(low, min(high, number)) // 2 * 2
        except (ValueError, TypeError, OverflowError):
            result[key] = QUALITY_DEFAULTS[key]
    try:
        fps = float(result["fps"])
        result["fps"] = max(0.0, min(120.0, fps)) if math.isfinite(fps) else 0.0
        if 0 < result["fps"] < 1:
            result["fps"] = 1.0
    except (ValueError, TypeError, OverflowError):
        result["fps"] = 0.0
    return result


def effective_split(channel, global_minutes):
    value = channel.get("recording_split_minutes")
    if value is None:
        value = global_minutes
    try:
        return max(0, min(10080, int(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def normalize_channel_options(channel):
    if channel.get("recording_split_minutes") is not None:
        channel["recording_split_minutes"] = effective_split(channel, 0)
    if channel.get("quality_settings") is not None:
        channel["quality_settings"] = normalize_quality(channel["quality_settings"])
    return channel


def quality_plan(settings, available):
    """Choose a real rendition, then filter only dimensions/FPS that differ.

    Streamlink labels contain height and (for high FPS) frame rate. Width 0
    preserves aspect ratio; known 16:9 preset widths need no rescaling.
    """
    settings = normalize_quality(settings)
    mode, target_fps = settings["mode"], settings["fps"]
    if mode == "best" and not target_fps:
        return {"stream": "best", "filters": []}
    renditions = []
    for name in available:
        match = QUALITY_NAME.fullmatch(name)
        if match:
            renditions.append((int(match[1]), float(match[2] or 30), name))
    if not renditions:
        raise ValueError("quality_unavailable")
    if mode == "best":
        height, fps, name = max(renditions)
        target_height, target_width = height, 0
    else:
        match = QUALITY_NAME.fullmatch(mode)
        target_height = int(match[1]) if match else settings["height"]
        target_width = 0 if match else settings["width"]
        if match and not target_fps and match[2]:
            target_fps = float(match[2])
        same_height = [r for r in renditions if r[0] == target_height]
        if same_height:
            height, fps, name = min(
                same_height,
                key=lambda r: (
                    abs(r[1] - target_fps) if target_fps else -r[1],
                    r[2] != mode,
                    "_alt" in r[2],
                ),
            )
        else:
            larger = [r for r in renditions if r[0] >= target_height]
            height, fps, name = (
                min(larger, key=lambda r: (r[0], -r[1])) if larger else max(renditions)
            )
    filters = []
    known_width = {144: 256, 360: 640, 480: 854, 720: 1280, 1080: 1920}.get(height)
    if height != target_height or (target_width and target_width != known_width):
        filters.append(f"scale={target_width or -2}:{target_height}:flags=lanczos")
        filters.append("setsar=1")
    if target_fps and abs(fps - target_fps) > 0.01:
        filters.append(f"fps={target_fps:g}")
    return {"stream": name, "filters": filters}


def add_video_filters(args, filters):
    """Compose CPU filters before an encoder's hardware upload filter."""
    result = list(args)
    if not filters:
        return result
    for flag in ("-vf", "-filter:v"):
        if flag in result:
            index = result.index(flag) + 1
            result[index] = ",".join([*filters, result[index]])
            return result
    return result + ["-vf", ",".join(filters)]
