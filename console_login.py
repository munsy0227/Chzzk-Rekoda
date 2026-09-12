"""Launch the CLI login flow and return its result over the GUI's private pipe."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from browser_login import LoginFailure, failure_reason
from config_store import AUTH_COOKIE_NAMES
from i18n import DEFAULT_LANGUAGE, normalize_language, translate
from process_utils import console_python

BASE_DIR = Path(__file__).resolve().parent


def read_console_line(prompt):
    # An input() daemon can hold a buffered-stdio lock during interpreter exit.
    # Raw reads allow cancellation to finish without a shutdown deadlock.
    print(prompt, end="", flush=True)
    while chunk := os.read(sys.stdin.fileno(), 1):
        if chunk == b"\n":
            return True
    return False


def terminal_command(command):
    if sys.platform == "win32":
        return command, {"creationflags": subprocess.CREATE_NEW_CONSOLE}
    if sys.platform == "darwin":
        # Pass the shell command as an AppleScript argument, never as source.
        script = 'on run argv\ntell application "Terminal"\nactivate\ndo script (item 1 of argv)\nend tell\nend run'
        return ["osascript", "-e", script, shlex.join(command)], {}
    for terminal, flags in (
        ("x-terminal-emulator", ["-e"]),
        ("gnome-terminal", ["--wait", "--"]),
        ("konsole", ["--nofork", "-e"]),
        ("xterm", ["-e"]),
    ):
        executable = shutil.which(terminal)
        if executable:
            return [executable, *flags, *command], {"start_new_session": True}
    raise LoginFailure("login_terminal_missing")


def interactive_main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser-login", choices=("chrome", "edge", "firefox"), required=True
    )
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--cancel", type=Path, required=True)
    args = parser.parse_args(argv)
    language = normalize_language(args.language)
    started = args.cancel.with_name("started.tmp")
    started.write_text(str(os.getpid()), encoding="ascii")
    started.replace(args.cancel.with_name("started"))
    if sys.platform == "win32":
        # The bridge's stdio belongs to Qt; read keys from our own new console.
        sys.stdin = open("CONIN$", encoding="utf-8")
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        sys.stderr = sys.stdout

    def confirm(prompt):
        completed = threading.Event()
        answers = []

        def read():
            try:
                if read_console_line(prompt):
                    answers.append(True)
            except (OSError, EOFError, KeyboardInterrupt):
                pass
            finally:
                completed.set()

        threading.Thread(target=read, daemon=True).start()
        while not completed.wait(0.1):
            if args.cancel.exists():
                raise LoginFailure("login_cancelled")
        if not answers or args.cancel.exists():
            raise LoginFailure("login_cancelled")
        # Return None so collect_browser_cookies reads the successful CLI tab.

    try:
        from settings import collect_cli_cookies

        print(
            translate(
                language, "settings.browser_login_notice", browser=args.browser_login
            )
        )
        cookies = collect_cli_cookies(args.browser_login, language, confirm)
        if not all(cookies.get(name) for name in AUTH_COOKIE_NAMES):
            raise LoginFailure("login_failed")
        payload = {"cookies": {name: cookies[name] for name in AUTH_COOKIE_NAMES}}
        print(translate(language, "gui.login_received"))
    except (Exception, KeyboardInterrupt) as error:
        reason = failure_reason(error)
        payload = {"error": reason}
        print(translate(language, "gui." + reason))
    temporary = args.result.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(payload, output)
    temporary.replace(args.result)
    return 1 if "error" in payload else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("browser", choices=("chrome", "edge", "firefox"))
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    args = parser.parse_args()
    cancelled = threading.Event()

    def read_cancel():
        try:
            os.read(sys.stdin.fileno(), 4096)
        finally:
            cancelled.set()

    threading.Thread(target=read_cancel, daemon=True).start()
    payload = {"error": "login_failed"}
    with tempfile.TemporaryDirectory(prefix="rekoda-login-") as directory:
        result, cancel = Path(directory) / "result.json", Path(directory) / "cancel"
        child = None
        try:
            command, options = terminal_command(
                [
                    console_python(),
                    str(BASE_DIR / "settings.py"),
                    "--browser-login",
                    args.browser,
                    "--language",
                    normalize_language(args.language),
                    "--result",
                    str(result),
                    "--cancel",
                    str(cancel),
                ]
            )
            child = subprocess.Popen(command, cwd=BASE_DIR, **options)
            launched = time.monotonic()
            deadline, cancel_deadline = launched + 600, None
            while not result.exists():
                if cancelled.is_set() or time.monotonic() > deadline:
                    if cancel_deadline is None:
                        cancel.touch()
                        cancel_deadline = time.monotonic() + 65
                    if time.monotonic() > cancel_deadline:
                        raise LoginFailure(
                            "login_cancelled" if cancelled.is_set() else "login_timeout"
                        )
                code = child.poll()
                if result.exists():
                    break
                if code is not None and (sys.platform == "win32" or code != 0):
                    raise LoginFailure("login_window_closed")
                if code == 0:
                    # Some terminal launchers exit before their window. Watch
                    # the private worker marker, not the launcher's success.
                    started = cancel.with_name("started")
                    if started.exists():
                        try:
                            os.kill(int(started.read_text(encoding="ascii")), 0)
                        except ProcessLookupError:
                            raise LoginFailure("login_window_closed") from None
                    elif time.monotonic() - launched > 10:
                        raise LoginFailure("login_window_closed")
                time.sleep(0.1)
            payload = json.loads(result.read_text(encoding="utf-8"))
            if cancelled.is_set():
                payload = {"error": "login_cancelled"}
        except (OSError, ValueError, LoginFailure) as error:
            payload = {
                "error": error.reason
                if isinstance(error, LoginFailure)
                else "login_failed"
            }
        finally:
            cancel.touch(exist_ok=True)
            if child is not None and child.poll() is None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
    print(json.dumps(payload), flush=True)
    return 1 if "error" in payload else 0


if __name__ == "__main__":
    raise SystemExit(main())
