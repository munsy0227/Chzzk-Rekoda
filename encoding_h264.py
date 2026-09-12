"""H.264 encoder arguments and a bounded real FFmpeg availability probe."""

import subprocess

from process_utils import hidden_process_kwargs

PROBE_CACHE = {}


def build_h264_encoding_args(settings, recording_format):
    encoder = settings["encoder"]
    preset = settings["preset"]
    args = ["-c:v", encoder]
    if encoder in {"libx264", "h264_nvenc", "h264_qsv"}:
        args += ["-preset", preset]
    elif encoder == "h264_amf":
        args += ["-quality", preset, "-rc", "vbr_peak"]
    elif encoder == "h264_vaapi":
        args += ["-vf", "format=nv12,hwupload"]
    elif encoder == "h264_videotoolbox":
        args += ["-allow_sw", "1"]
    if encoder == "libx264":
        args += ["-pix_fmt", "yuv420p", "-tune", "zerolatency"]
    rate = settings["max_bitrate"]
    suffix = rate[-1] if rate[-1].lower() in ("k", "m") else ""
    number = int(rate[:-1] if suffix else rate)
    args += [
        "-b:v",
        settings["bitrate"],
        "-maxrate",
        rate,
        "-bufsize",
        f"{number * 2}{suffix}",
        "-c:a",
        "copy",
    ]
    if recording_format == "ts":
        args += ["-bsf:v", "h264_mp4toannexb"]
    return args


def probe_h264_encoder(ffmpeg_path, settings):
    key = (
        str(ffmpeg_path),
        *(settings[k] for k in ("encoder", "preset", "bitrate", "max_bitrate")),
    )
    if key in PROBE_CACHE:
        return PROBE_CACHE[key]
    args = [str(ffmpeg_path), "-hide_banner", "-loglevel", "error", "-nostdin"]
    if settings["encoder"] == "h264_vaapi":
        args += [
            "-init_hw_device",
            "vaapi=vaapi0:/dev/dri/renderD128",
            "-filter_hw_device",
            "vaapi0",
        ]
    args += ["-f", "lavfi", "-i", "testsrc2=size=640x480:rate=1", "-frames:v", "1"]
    video_args = build_h264_encoding_args(settings, "mkv")
    index = video_args.index("-c:a")
    del video_args[index : index + 2]
    try:
        result = subprocess.run(
            args + video_args + ["-an", "-f", "null", "-"],
            capture_output=True,
            timeout=15,
            check=False,
            **hidden_process_kwargs(),
        )
        works = result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        works = False
    PROBE_CACHE[key] = works
    return works
