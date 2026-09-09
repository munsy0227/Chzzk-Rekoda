"""Optional Qt entry point. The existing CLI remains available without Qt."""

import argparse
import sys

from config_store import ConfigError, config_file_path
from i18n import DEFAULT_LANGUAGE, translate


def main():
    parser = argparse.ArgumentParser(
        description=translate(DEFAULT_LANGUAGE, "gui.title")
    )
    parser.add_argument(
        "--config",
        default=config_file_path,
        help=translate(DEFAULT_LANGUAGE, "gui.config_path"),
    )
    args = parser.parse_args()
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        from gui.appearance import application_icon, apply_application_font
        from gui.common import HelpStyle, show_error
        from gui.window import MainWindow
    except ImportError:
        print(translate(DEFAULT_LANGUAGE, "gui.missing_qt"), file=sys.stderr)
        return 1
    app = QApplication(sys.argv[:1])
    app.setApplicationName("CHZZK Rekoda")
    app.setStyle(HelpStyle())
    apply_application_font(app)
    app.setWindowIcon(application_icon())
    try:
        window = MainWindow(args.config)
    except (ConfigError, OSError) as error:
        show_error(None, translate(DEFAULT_LANGUAGE, "gui.error"), error)
        return 1
    window.show()
    if not window.config["gui_settings"]["onboarding_completed"]:
        QTimer.singleShot(0, window.setup)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
