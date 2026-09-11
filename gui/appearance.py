"""Application font and a window/tray icon at multiple resolutions."""

import sys

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QFont, QFontDatabase, QIcon, QRawFont
from PySide6.QtWidgets import QWidget

from gui.services import BASE_DIR


class VariableFontWeights(QObject):
    """Keep the bundled TTC's weight axis in sync with each QSS font weight."""

    def __init__(self, app):
        super().__init__(app)
        self.families = set()
        self.updating = False

    def eventFilter(self, watched, event):
        if (
            not self.updating
            and isinstance(watched, QWidget)
            and event.type() in (QEvent.Type.FontChange, QEvent.Type.Polish)
        ):
            font = watched.font()
            axis = QFont.Tag.fromString("wght")
            if self.families.intersection(font.families()) and (
                not font.isVariableAxisSet(axis)
                or font.variableAxisValue(axis) != int(font.weight())
                or font.hintingPreference() != QFont.HintingPreference.PreferFullHinting
                or font.styleStrategy() != QFont.StyleStrategy.PreferAntialias
            ):
                self.updating = True
                try:
                    font.setVariableAxis(axis, int(font.weight()))
                    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
                    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
                    watched.setFont(font)
                finally:
                    self.updating = False
        return False


def qt_application_args():
    args = sys.argv[:1]
    if sys.platform == "win32":
        # Variable CJK fonts need DirectWrite; render at each monitor's DPI.
        args += ["-platform", "windows:fontengine=directwrite:dpiawareness=2"]
    return args


def apply_application_font(app, language="ko"):
    directory = BASE_DIR / "font" / "02_NotoSansCJK-TTF-VF"
    path = directory / "Variable" / "OTC" / "NotoSansCJK-VF.ttf.ttc"
    families = getattr(app, "_rekoda_font_families", None)
    if not families:
        font_id = QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app._rekoda_font_families = families
            # Linux may also have static Noto families installed. Qualify the
            # bundled font's foundry when Qt exposes otherwise identical names.
            raw = QRawFont(str(path), 13)
            vendor = (
                bytes(raw.fontTable("OS/2"))[58:62].decode("ascii", "ignore").strip()
            )
            available = set(QFontDatabase.families())
            app._rekoda_font_names = {
                family: (
                    f"{family} [{vendor}]"
                    if vendor and f"{family} [{vendor}]" in available
                    else family
                )
                for family in families
            }
    if not families:
        return False
    region = {"ko": "KR", "ja": "JP", "zh-CN": "SC", "zh-TW": "TC"}.get(language, "JP")
    preferred = "Noto Sans CJK " + region
    ordered = [preferred, *(family for family in families if family != preferred)]
    ordered = [app._rekoda_font_names.get(family, family) for family in ordered]
    # Set fonts through QSS, just like the window's styles. Mixing setFont()
    # with those styles can restore KDE's per-widget system fonts on polish.
    # The TTC exposes its Thin face on some FreeType builds, so apply each
    # widget's final weight to the variable axis after QSS has resolved it.
    weights = getattr(app, "_rekoda_font_weights", None)
    if weights is None:
        weights = VariableFontWeights(app)
        app._rekoda_font_weights = weights
        app.installEventFilter(weights)
    weights.families = set(ordered)
    family_list = ", ".join('"' + family + '"' for family in ordered)
    font_style = (
        "QWidget { font-family: "
        + family_list
        + "; font-size: 10pt; font-weight: 500; }"
    )
    if app.styleSheet() != font_style:
        app.setStyleSheet(font_style)
    return True


def application_icon():
    directory = BASE_DIR / "assets"
    icon = QIcon(str(directory / "chzzk-rekoda.ico"))
    icon.addFile(str(directory / "chzzk-rekoda.png"))
    return icon
