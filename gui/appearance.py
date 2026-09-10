"""Application font and a window/tray icon at multiple resolutions."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap

from gui.services import BASE_DIR


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
    if families is None:
        font_id = QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        app._rekoda_font_families = families
    if not families:
        return False
    region = {"ko": "KR", "ja": "JP", "zh-CN": "SC", "zh-TW": "TC"}.get(language, "JP")
    preferred = "Noto Sans CJK " + region
    ordered = [preferred, *(family for family in families if family != preferred)]
    font = QFont(ordered, 10)
    font.setWeight(QFont.Weight.Normal)
    font.setVariableAxis(QFont.Tag.fromString("wght"), 400)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    return True


def application_icon():
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#28715b"))
        painter.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(
            int(size * 0.17),
            int(size * 0.24),
            int(size * 0.66),
            int(size * 0.52),
            size * 0.09,
            size * 0.09,
        )
        painter.setBrush(QColor("#d84343"))
        painter.drawEllipse(
            int(size * 0.36), int(size * 0.36), int(size * 0.28), int(size * 0.28)
        )
        painter.end()
        icon.addPixmap(pixmap)
    return icon
