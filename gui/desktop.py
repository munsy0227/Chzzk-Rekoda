"""Native desktop identity and per-user Linux icon registration."""

import os
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_ID = "CHZZK.Rekoda.GUI"


def configure_platform_identity():
    """Give Windows GUI windows their own taskbar group before showing UI."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        shell = ctypes.WinDLL("shell32", use_last_error=True)
        set_id = shell.SetCurrentProcessExplicitAppUserModelID
        set_id.argtypes = [ctypes.c_wchar_p]
        set_id.restype = ctypes.c_long
        return set_id(APP_ID) == 0
    except (AttributeError, OSError):
        return False


def write_if_changed(path, data, mode=0o644):
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def register_linux_desktop(base_dir=BASE_DIR):
    """Keep folder launchers and the app menu on the same installed icon."""
    if not sys.platform.startswith("linux"):
        return False
    configured = os.environ.get("XDG_DATA_HOME", "")
    data_home = Path(configured) if configured else Path.home() / ".local/share"
    if not data_home.is_absolute():
        data_home = Path.home() / ".local/share"
    source = base_dir / "Chzzk-Rekoda.desktop"
    try:
        icon = base_dir / "assets" / "chzzk-rekoda.png"
        theme = data_home / "icons" / "hicolor"
        changed = write_if_changed(
            theme / "512x512" / "apps" / "chzzk-rekoda.png", icon.read_bytes()
        )
        if changed:
            # Theme readers use this timestamp to invalidate their icon cache.
            theme.touch()
        # The installed copy is outside the project, so its %k must point back
        # to the original launcher. URI encoding keeps arbitrary paths out of
        # the Python command; %% preserves literal percent escapes in Exec.
        location = source.resolve().as_uri().replace("%", "%%")
        contents = (
            "\n".join(
                line.replace("%k", location) if line.startswith("Exec=") else line
                for line in source.read_text(encoding="utf-8").splitlines()
            )
            + "\n"
        )
        write_if_changed(
            data_home / "applications" / source.name, contents.encode("utf-8"), 0o755
        )
        return True
    except OSError:
        # An unwritable user icon directory must not prevent recording.
        return False
