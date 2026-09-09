"""Application font and a window/tray icon at multiple resolutions."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap

from gui.services import BASE_DIR


def apply_application_font(app):
    directory = BASE_DIR / "font" / "02_NotoSansCJK-TTF-VF"
    candidates = [directory / "Variable" / "TTF" / "Subset" / "NotoSansKR-VF.ttf"]
    for path in candidates:
        if not path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            continue
        font = QFont(families[0], 10)
        font.setWeight(QFont.Weight.Normal)
        # Qt identifies this variable font's default instance as Thin. Select
        # its regular axis explicitly so Korean text stays readable.
        font.setVariableAxis(QFont.Tag.fromString("wght"), 400)
        app.setFont(font)
        return True
    return False


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
