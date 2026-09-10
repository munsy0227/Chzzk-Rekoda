"""Interpreter and console flags shared by GUI launchers and child processes."""

import errno
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path


def console_python():
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        return str(executable.with_name("python.exe"))
    return str(executable)


def hidden_process_kwargs():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def read_pipe(fd, size):
    """Read a GUI pipe without CRT buffering or buffered-stdin shutdown locks."""
    if sys.platform != "win32":
        return os.read(fd, size)

    import _winapi
    import ctypes
    import msvcrt

    # QProcess opens the child's named-pipe handles with FILE_FLAG_OVERLAPPED.
    # A synchronous CRT read can report completion before data has arrived.
    try:
        operation, _ = _winapi.ReadFile(msvcrt.get_osfhandle(fd), size, overlapped=True)
        _, error = operation.GetOverlappedResult(True)
        if error not in (0, _winapi.ERROR_MORE_DATA):
            raise ctypes.WinError(error)
        return operation.getbuffer()
    except OSError as error:
        if getattr(error, "winerror", None) in (
            _winapi.ERROR_BROKEN_PIPE,
            _winapi.ERROR_NO_DATA,
        ):
            return b""
        raise


def write_pipe(fd, data):
    """Write a complete binary message, including partial or pending writes."""
    data = memoryview(data)
    while data:
        if sys.platform == "win32":
            import _winapi
            import ctypes
            import msvcrt

            operation, _ = _winapi.WriteFile(
                msvcrt.get_osfhandle(fd), data, overlapped=True
            )
            written, error = operation.GetOverlappedResult(True)
            if error:
                raise ctypes.WinError(error)
        else:
            written = os.write(fd, data)
        if not written:
            raise BrokenPipeError(errno.EPIPE, "pipe write returned zero bytes")
        data = data[written:]


@contextmanager
def terminal_display_mode():
    """Use Windows VT redraws instead of clearing each legacy-console line."""
    restore = None
    enabled = False
    if sys.platform == "win32" and sys.stdout and sys.stdout.isatty():
        try:
            import ctypes
            import msvcrt
            from ctypes import wintypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetConsoleMode.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.DWORD),
            ]
            kernel.GetConsoleMode.restype = wintypes.BOOL
            kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.SetConsoleMode.restype = wintypes.BOOL
            handle = msvcrt.get_osfhandle(sys.stdout.fileno())
            mode = wintypes.DWORD()
            if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
                enabled = bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
                if enabled:
                    restore = lambda: kernel.SetConsoleMode(handle, mode.value)
        except (AttributeError, OSError, ValueError):
            pass
    try:
        yield enabled
    finally:
        if restore:
            restore()
