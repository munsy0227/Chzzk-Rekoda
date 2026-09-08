"""Versioned JSON pipe for the existing recorder; no Qt dependency."""

import asyncio
import json
import queue
import sys
import threading


def preview_segment(recorder, directory, template):
    """The new segment can still be empty while FFmpeg buffers its first data."""
    pattern = recorder.segment_template_regex(template)
    for path in reversed(recorder.segment_output_files(directory, template)):
        try:
            if path.stat().st_size >= 16384:
                return str(path), int(pattern.match(path.name).group("index"))
        except OSError:
            continue
    return "", 1


class JsonBridge:
    def __init__(self, recorder, loop):
        self.recorder = recorder
        self.loop = loop
        self.messages = queue.Queue(maxsize=256)
        self.writer = threading.Thread(target=self._write, daemon=True)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.writer.start()
        self.reader.start()

    def stop(self):
        try:
            self.loop.call_soon_threadsafe(self.recorder.handle_shutdown)
        except RuntimeError:
            pass

    def _read(self):
        while True:
            line = sys.stdin.buffer.readline(4097)
            if not line or len(line) > 4096:
                self.stop()
                return
            try:
                command = json.loads(line)
                if isinstance(command, dict) and command.get("command") == "stop":
                    self.stop()
                    return
            except (ValueError, UnicodeError):
                continue

    def _write(self):
        try:
            while True:
                event = self.messages.get()
                try:
                    if event is None:
                        return
                    sys.stdout.write(json.dumps(event, ensure_ascii=True) + "\n")
                    sys.stdout.flush()
                finally:
                    self.messages.task_done()
        except (BrokenPipeError, OSError):
            self.stop()

    def emit(self, event, **data):
        # Pipe pressure must never block the media-copy coroutine.
        if self.messages.full():
            try:
                self.messages.get_nowait()
                self.messages.task_done()
            except queue.Empty:
                pass
        self.messages.put_nowait({"version": 1, "event": event, **data})

    async def display(self, stopped):
        recorder = self.recorder
        while not stopped.is_set() or not recorder.log_queue.empty():
            async with recorder.channel_progress_lock:
                progress = {
                    key: dict(value) for key, value in recorder.channel_progress.items()
                }
            channels = []
            config = await recorder.load_config_async()
            for channel in recorder.normalize_channels(config.get("channels", [])):
                channel_id = channel["id"]
                current = progress.get(channel_id, {})
                state = "recording" if current else "waiting"
                if channel.get("active") == "off":
                    state = "inactive"
                if recorder.shutdown_event.is_set():
                    state = "stopping"
                path = current.get("output_path", "")
                template = current.get("segment_template")
                segment_index = 1
                if template:
                    try:
                        path, segment_index = await asyncio.to_thread(
                            preview_segment,
                            recorder,
                            recorder.Path(current["output_dir"]),
                            template,
                        )
                    except OSError:
                        path = ""
                out_time = current.get("out_time", "0")
                seconds = recorder.parse_time(out_time) if ":" in out_time else 0
                if current.get("split_seconds"):
                    interval = current["split_seconds"]
                    seconds = min(
                        interval, max(0, seconds - (segment_index - 1) * interval)
                    )
                channels.append(
                    {
                        "id": channel_id,
                        "state": state,
                        "out_time": current.get("out_time", ""),
                        "total_size": current.get("total_size", ""),
                        "download_speed": current.get("download_speed", ""),
                        "bitrate": current.get("bitrate", ""),
                        "title": current.get("title", ""),
                        "output_path": path,
                        # WebM clusters and the muxer's output buffer may lag
                        # encoder progress; seek into data already on disk.
                        "preview_seconds": max(0, seconds - 8),
                    }
                )
            self.emit("status", channels=channels)
            for _ in range(200):
                try:
                    message = recorder.log_queue.get_nowait()
                    recorder.log_queue.task_done()
                    self.emit("log", message=message[:4000])
                except asyncio.QueueEmpty:
                    break
            if not stopped.is_set():
                await asyncio.sleep(1)
        self.emit("stopped")
        if self.messages.full():
            try:
                self.messages.get_nowait()
                self.messages.task_done()
            except queue.Empty:
                pass
        self.messages.put_nowait(None)
        await asyncio.to_thread(self.writer.join, 2)
