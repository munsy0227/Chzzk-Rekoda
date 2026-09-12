"""Asynchronous metadata, image, recording-process and frame-preview adapters."""

import json
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QObject,
    QProcess,
    QProcessEnvironment,
    QRunnable,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from channel_service import channel_image_url
from process_utils import console_python

BASE_DIR = Path(__file__).resolve().parent.parent


def ffmpeg_executable():
    bundled = BASE_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
    return (
        str(bundled)
        if sys.platform == "win32" and bundled.is_file()
        else shutil.which("ffmpeg")
    )


class JobSignals(QObject):
    done = Signal(int, object, str)


class Job(QRunnable):
    def __init__(self, number, function):
        super().__init__()
        self.number, self.function = number, function
        self.signals = JobSignals()

    def run(self):
        try:
            self.signals.done.emit(self.number, self.function(), "")
        except Exception as error:
            self.signals.done.emit(self.number, None, type(error).__name__)


class Jobs(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(3)
        self.callbacks = {}
        self.number = 0

    def submit(self, function, callback):
        self.number += 1
        job = Job(self.number, function)
        self.callbacks[self.number] = callback
        job.signals.done.connect(self.completed)
        self.pool.start(job)

    @Slot(int, object, str)
    def completed(self, number, result, error):
        callback = self.callbacks.pop(number, None)
        if callback:
            callback(result, error)

    def cancel_pending(self):
        self.callbacks.clear()
        self.pool.clear()


def image_from_bytes(data, max_side=640):
    if not data or len(data) > 2 * 1024 * 1024:
        return QPixmap()
    buffer = QBuffer()
    buffer.setData(QByteArray(data))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    if bytes(reader.format()).lower() not in {b"png", b"jpg", b"jpeg", b"webp"}:
        return QPixmap()
    size = reader.size()
    if (
        size.width() <= 0
        or size.height() <= 0
        or size.width() * size.height() > 16_000_000
    ):
        return QPixmap()
    if max(size.width(), size.height()) > max_side:
        from PySide6.QtCore import Qt

        size.scale(max_side, max_side, Qt.AspectRatioMode.KeepAspectRatio)
        reader.setScaledSize(size)
    return QPixmap.fromImage(reader.read())


class Images(QObject):
    ready = Signal(str, QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        self.cache = {}
        self.pending = set()

    def request(self, url):
        url = channel_image_url(url)
        if not url:
            return
        if url in self.cache:
            self.ready.emit(url, self.cache[url])
            return
        if url in self.pending:
            return
        self.pending.add(url)
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(8000)
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.ManualRedirectPolicy,
        )
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0")
        reply = self.network.get(request)
        data = bytearray()

        def read():
            data.extend(bytes(reply.readAll()))
            if len(data) > 2 * 1024 * 1024:
                reply.abort()

        def finish():
            read()
            self.pending.discard(url)
            if reply.error() == QNetworkReply.NetworkError.NoError:
                pixmap = image_from_bytes(data, 96)
                if not pixmap.isNull():
                    if len(self.cache) >= 256:
                        self.cache.pop(next(iter(self.cache)))
                    self.cache[url] = pixmap
                    self.ready.emit(url, pixmap)
            reply.deleteLater()

        reply.readyRead.connect(read)
        reply.finished.connect(finish)


class Recorder(QObject):
    snapshot = Signal(list)
    log = Signal(str)
    error = Signal(str)
    changed = Signal(str)
    finished = Signal()

    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(BASE_DIR))
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUTF8", "1")
        # -u affects the JSON recorder only. Do not force raw stdout on its
        # Streamlink children; use the same binary buffering as the CLI.
        env.remove("PYTHONUNBUFFERED")
        self.process.setProcessEnvironment(env)
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.readyReadStandardError.connect(self.read_errors)
        self.process.started.connect(self.started)
        self.process.finished.connect(self.done)
        self.process.errorOccurred.connect(self.failed)
        self.buffer = bytearray()
        self.stopping = False
        self.stop_reason = "user"

    @property
    def running(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def start(self):
        if self.running:
            return
        self.buffer.clear()
        self.stopping = False
        self.stop_reason = "user"
        self.changed.emit("starting")
        self.process.start(
            console_python(),
            [
                "-u",
                str(BASE_DIR / "chzzk_record.py"),
                "--gui-events",
                "--config",
                str(self.config_path),
            ],
        )

    def stop(self):
        self.request_stop("user")

    def request_stop(self, reason):
        if self.running and not self.stopping:
            self.stopping = True
            self.stop_reason = reason
            if self.process.state() == QProcess.ProcessState.Running:
                self.send_stop()
            self.changed.emit("stopping")

    def send_stop(self):
        command = {"command": "stop", "reason": self.stop_reason}
        self.process.write((json.dumps(command) + "\n").encode("ascii"))

    def started(self):
        if self.stopping:
            self.send_stop()
        else:
            self.changed.emit("running")

    def read(self):
        self.buffer.extend(bytes(self.process.readAllStandardOutput()))
        while b"\n" in self.buffer:
            raw, _, remainder = self.buffer.partition(b"\n")
            self.buffer = bytearray(remainder)
            if len(raw) > 2 * 1024 * 1024:
                self.protocol_failed()
                return
            try:
                event = json.loads(raw)
                if not isinstance(event, dict) or event.get("version") != 1:
                    continue
                kind = event.get("event")
                if kind == "status" and isinstance(event.get("channels"), list):
                    self.snapshot.emit(event["channels"])
                elif kind == "log":
                    self.log.emit(str(event.get("message", ""))[:4000])
                elif kind == "error":
                    self.error.emit(str(event.get("message", ""))[:4000])
            except (ValueError, UnicodeError):
                self.error.emit("protocol_error")
        if len(self.buffer) > 2 * 1024 * 1024:
            self.protocol_failed()

    def protocol_failed(self):
        self.buffer.clear()
        self.request_stop("protocol_error")
        self.error.emit("protocol_error")

    def read_errors(self):
        text = bytes(self.process.readAllStandardError()).decode("utf-8", "replace")
        if text.strip():
            self.log.emit(text[-4000:])

    def failed(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.error.emit("start_failed")
            self.changed.emit("idle")
            self.finished.emit()

    def done(self, code, status):
        self.read()
        self.read_errors()
        if code or status == QProcess.ExitStatus.CrashExit:
            self.error.emit("recorder_failed")
        self.changed.emit("idle")
        self.finished.emit()


class Preview(QObject):
    frame = Signal(QPixmap)
    unavailable = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.readyReadStandardError.connect(self.process.readAllStandardError)
        self.process.finished.connect(self.done)
        self.process.errorOccurred.connect(lambda _: self.unavailable.emit("failed"))
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.process.kill)
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.target = None
        self.generation = 0
        self.active_generation = -1
        self.data = bytearray()

    def set_target(self, target):
        old = self.target or {}
        new = target or {}
        if (old.get("output_path"), old.get("id")) != (
            new.get("output_path"),
            new.get("id"),
        ):
            self.generation += 1
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.kill()
            self.unavailable.emit("waiting")
        self.target = target
        if target and self.active_generation != self.generation:
            self.refresh()

    def refresh(self):
        if not self.target or self.process.state() != QProcess.ProcessState.NotRunning:
            return
        path = Path(self.target.get("output_path", ""))
        executable = ffmpeg_executable()
        try:
            if not executable or not path.is_file() or path.stat().st_size < 16384:
                self.unavailable.emit("waiting")
                return
        except OSError:
            self.unavailable.emit("failed")
            return
        self.data.clear()
        self.active_generation = self.generation
        seconds = max(0, float(self.target.get("preview_seconds", 0)))
        self.process.start(
            executable,
            [
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-threads",
                "1",
                "-ss",
                f"{seconds:.3f}",
                "-i",
                str(path),
                "-map",
                "0:v:0",
                "-frames:v",
                "1",
                "-an",
                "-sn",
                "-threads",
                "1",
                "-vf",
                "scale=640:360:force_original_aspect_ratio=decrease",
                "-c:v",
                "mjpeg",
                "-f",
                "image2pipe",
                "pipe:1",
            ],
        )
        self.timeout.start(7000)

    def read(self):
        self.data.extend(bytes(self.process.readAllStandardOutput()))
        if len(self.data) > 2 * 1024 * 1024:
            self.process.kill()

    def done(self, code, status):
        self.timeout.stop()
        self.read()
        if self.active_generation != self.generation:
            return
        pixmap = image_from_bytes(self.data)
        if code == 0 and not pixmap.isNull():
            self.frame.emit(pixmap)
        else:
            self.unavailable.emit("failed")

    def close(self):
        self.target = None
        self.generation += 1
        self.timer.stop()
        self.timeout.stop()
        self.process.kill()
        self.process.waitForFinished(1000)
