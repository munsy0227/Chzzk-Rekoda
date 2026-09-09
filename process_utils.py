"""Interpreter and console flags shared by GUI launchers and child processes."""

import os
import subprocess
import sys
from pathlib import Path


def console_python():
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        return str(executable.with_name("python.exe"))
    return str(executable)


def hidden_process_kwargs():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
