"""Optional Rust helpers with Python fallbacks."""

import asyncio
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from process_utils import hidden_process_kwargs

_INPUT_LIMIT = 64 * 1024
_OUTPUT_LIMIT = 8 * 1024 * 1024
_MAX_PENDING = 64
_TIMEOUT = 35
_HELLO_TIMEOUT = 2
_REPORT_TIMEOUT = 30
NATIVE_DIR = Path(__file__).resolve().parent / "native"


class _InputTooLarge(ValueError):
    pass


def native_executable() -> Path | None:
    """Find the repository's installed/release native helper, if present."""
    disabled = NATIVE_DIR / ".disabled"
    if disabled.exists() or disabled.is_symlink():
        return None
    suffix = ".exe" if os.name == "nt" else ""
    for path in (NATIVE_DIR / "bin" / f"chzzk-native{suffix}",
                 NATIVE_DIR / "target" / "release" / f"chzzk-native{suffix}"):
        if path.is_file():
            return path
    return None


def _json_line(value, limit):
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(data) > limit:
        raise _InputTooLarge("native protocol message too large")
    return data


class NativeLiveClient:
    """One helper process shared by concurrent live-info requests."""

    def __init__(self, executable: Path | None = None):
        self.executable = Path(executable) if executable is not None else native_executable()
        self.available = False
        self._process = None
        self._reader_task = None
        self._write_lock = asyncio.Lock()
        self._slots = asyncio.Semaphore(_MAX_PENDING)
        self._pending = {}
        self._next_id = 1
        self._disabled = False

    async def __aenter__(self):
        if self.executable is None or self._disabled:
            return self
        try:
            self._process = await asyncio.create_subprocess_exec(
                str(self.executable), "serve", stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=subprocess.DEVNULL,
                limit=_OUTPUT_LIMIT + 1, **hidden_process_kwargs(),
            )
            self._reader_task = asyncio.create_task(self._read_replies())
            reply = await self._request("hello", timeout=_HELLO_TIMEOUT)
            if (not isinstance(reply, dict) or reply.get("version") != 1
                    or type(reply.get("version")) is not int or reply.get("ok") is not True
                    or reply.get("service") != "chzzk-native"):
                await self._disable()
            else:
                self.available = True
        except asyncio.CancelledError:
            await self.close()
            raise
        except (TimeoutError, OSError, ValueError, asyncio.IncompleteReadError):
            await self._disable()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def _id(self):
        request_id = self._next_id
        self._next_id += 1
        return request_id

    async def _send(self, message):
        data = _json_line(message, _INPUT_LIMIT)
        async with self._write_lock:
            if self._process is None or self._process.returncode is not None:
                raise BrokenPipeError("native helper is unavailable")
            self._process.stdin.write(data)
            await self._process.stdin.drain()

    async def _request(self, op, *, channel_id=None, headers=None, timeout=None):
        if timeout is None:
            timeout = _TIMEOUT
        if self._disabled or self._process is None:
            return None
        request_id = self._id()
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        request = {"version": 1, "id": request_id, "op": op}
        if channel_id is not None:
            request["channel_id"] = channel_id
        if headers is not None:
            request["headers"] = headers
        try:
            await self._send(request)
            return await asyncio.wait_for(asyncio.shield(future), timeout)
        except asyncio.CancelledError:
            try:
                await asyncio.shield(self._send({
                    "version": 1, "id": request_id, "op": "cancel",
                    "channel_id": channel_id,
                }))
            except (TimeoutError, OSError, ValueError):
                await self._disable()
            raise
        except _InputTooLarge:
            return None
        except (TimeoutError, OSError, ValueError, asyncio.IncompleteReadError):
            await self._disable()
            return None
        finally:
            self._pending.pop(request_id, None)

    async def _read_replies(self):
        try:
            while self._process is not None:
                line = await self._process.stdout.readline()
                if not line:
                    raise EOFError("native helper closed stdout")
                if len(line) > _OUTPUT_LIMIT:
                    raise ValueError("native reply too large")
                reply = json.loads(line)
                if (not isinstance(reply, dict) or type(reply.get("version")) is not int
                        or reply.get("version") != 1 or type(reply.get("id")) is not int
                        or reply["id"] < 1 or type(reply.get("ok")) is not bool):
                    raise ValueError("invalid native reply")
                request_id = reply["id"]
                future = self._pending.get(request_id)
                if future is None or future.done():
                    if request_id < self._next_id:
                        continue
                    raise ValueError("unmatched native reply")
                future.set_result(reply)
        except asyncio.CancelledError:
            raise
        except (OSError, ValueError, EOFError, asyncio.IncompleteReadError,
                asyncio.LimitOverrunError, UnicodeError, json.JSONDecodeError):
            await self._disable()

    async def live(self, channel_id: str, headers: dict) -> dict | None:
        if not self.available or self._disabled:
            return None
        if (not isinstance(channel_id, str) or len(channel_id) != 32
                or any(c not in "0123456789abcdefABCDEF" for c in channel_id)
                or not isinstance(headers, dict)
                or any(not isinstance(k, str) or not isinstance(v, str)
                       for k, v in headers.items())):
            return None
        async with self._slots:
            reply = await self._request("live", channel_id=channel_id, headers=headers)
            if reply is None:
                return None
            if reply.get("ok") is False:
                category = reply.get("error")
                status = reply.get("status")
                if category == "http" and type(status) is int and 300 <= status < 400:
                    await self._disable()
                    return None
                if (isinstance(category, str)
                        and category in {"http", "network", "invalid_response"}
                        and (status is None or type(status) is int)):
                    raise NativeRequestError(category, status)
                if category == "invalid_request":
                    return None
                await self._disable()
                return None
            data = reply.get("data")
            if not isinstance(data, dict):
                await self._disable()
                return None
            return data

    async def _disable(self):
        if self._disabled:
            return
        self._disabled = True
        self.available = False
        for future in self._pending.values():
            if not future.done():
                future.set_result(None)
        await self._stop_process()

    async def _stop_process(self):
        process = self._process
        if process is None or process.returncode is not None:
            return
        try:
            process.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), 2)
        except TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                return
            try:
                await asyncio.wait_for(process.wait(), 2)
            except TimeoutError:
                pass

    async def close(self):
        self.available = False
        self._disabled = True
        for future in self._pending.values():
            if not future.done():
                future.set_result(None)
        await self._stop_process()
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None


def _valid_summary(value):
    counts = ("gap_count", "unresolved_count", "checkpoint_count", "duplicate_count", "error_count")
    if (not isinstance(value, dict) or type(value.get("version")) is not int
            or value["version"] != 1 or type(value.get("passed")) is not bool
            or any(type(value.get(key)) is not int or value[key] < 0 for key in counts)
            or type(value.get("gap_seconds")) not in (int, float)
            or not math.isfinite(value["gap_seconds"]) or value["gap_seconds"] < 0
            or not isinstance(value.get("gaps"), list)):
        return False
    if (value["gap_count"] != len(value["gaps"])
            or (value["checkpoint_count"] == 0 and value["error_count"] == 0)):
        return False
    for gap in value["gaps"]:
        if (not isinstance(gap, dict) or not isinstance(gap.get("channel_id"), str)
                or len(gap["channel_id"]) > 128
                or type(gap.get("live_id")) is not int
                or not isinstance(gap.get("rendition"), str) or len(gap["rendition"]) > 32
                or any(type(gap.get(key)) not in (int, float) or not math.isfinite(gap[key])
                       for key in ("start", "end")) or gap["end"] < gap["start"]):
            return False
    gap_seconds = round(sum(gap["end"] - gap["start"] for gap in value["gaps"]), 6)
    if value["gap_seconds"] != gap_seconds:
        return False
    expected = not any((value["gap_count"], value["unresolved_count"],
                        value["duplicate_count"], value["error_count"]))
    return value["passed"] is expected


class NativeRequestError(Exception):
    """A helper-side per-request failure safe for callers to log."""

    def __init__(self, category: str, status: int | None = None):
        self.category = category
        self.status = status
        super().__init__(category)


def native_report_summary(path) -> dict | None:
    """Summarize a sufficiently large report with the optional native helper."""
    executable = native_executable()
    if executable is None:
        return None
    path = Path(path)
    try:
        if path.stat().st_size < 256 * 1024:
            return None
        with tempfile.TemporaryFile() as stdout:
            process = subprocess.Popen(
                [str(executable), "report", str(path)], stdout=stdout,
                stderr=subprocess.DEVNULL, **hidden_process_kwargs(),
            )
            try:
                if process.wait(timeout=_REPORT_TIMEOUT) != 0:
                    return None
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                return None
            if stdout.tell() > _OUTPUT_LIMIT:
                return None
            stdout.seek(0)
            output = stdout.read(_OUTPUT_LIMIT + 1)
        result = json.loads(output.decode("utf-8"))
        if (not isinstance(result, dict) or type(result.get("version")) is not int
                or result["version"] != 1 or result.get("ok") is not True):
            return None
        summary = result.get("summary")
        return summary if _valid_summary(summary) else None
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired,
            json.JSONDecodeError):
        return None
