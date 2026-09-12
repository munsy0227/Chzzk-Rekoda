"""Select the interface after dependency/FFmpeg installation."""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config_store import ConfigError, ConfigStore
from i18n import DEFAULT_LANGUAGE, translate
from process_utils import console_python


def main():
    language = DEFAULT_LANGUAGE
    try:
        store = ConfigStore()
        config = store.load()
        language = config["language"]
        while True:
            print(translate(language, "gui.install_mode"))
            choice = (
                input(translate(language, "gui.install_mode_prompt")).strip() or "1"
            )
            if choice in {"1", "2"}:
                break
            print(translate(language, "settings.try_again"))
        if choice == "2":
            return subprocess.call(
                [console_python(), str(BASE_DIR / "settings.py")], cwd=BASE_DIR
            )
        subprocess.run(["uv", "sync", "--extra", "gui"], cwd=BASE_DIR, check=True)
        print(translate(language, "gui.install_gui_ready"), flush=True)
        if os.name == "nt":
            subprocess.Popen(
                ["wscript.exe", "//nologo", str(BASE_DIR / "chzzk_gui.vbs")],
                cwd=BASE_DIR,
            )
        else:
            subprocess.Popen(
                [console_python(), str(BASE_DIR / "chzzk_gui.py")],
                cwd=BASE_DIR,
                start_new_session=True,
            )
        return 0
    except (ConfigError, OSError, subprocess.SubprocessError) as error:
        print(translate(language, "gui.install_failed", error=error), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
