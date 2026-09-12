"""Small, consistent line icons rendered by Qt at native display sizes."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_VIDEO = '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3z"/>'
_PATHS = {
    "start": '<path d="m8 5 11 7-11 7z"/>',
    "stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    "add": '<circle cx="9" cy="7" r="3"/><path d="M3 20v-3a6 6 0 0 1 12 0v3m4-11v6m-3-3h6"/>',
    "folder": '<path d="M3 8V5h7l2 3h9v3M3 8h8l2 3h9l-3 9H5z"/>',
    "edit": '<path d="m5 15 11-11 4 4L9 19l-5 1zm8-8 4 4"/>',
    "remove": '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>',
    "refresh": '<path d="M20 8a8 8 0 1 0 0 8M20 3v5h-5"/>',
    "basic": '<path d="M4 6h8m4 0h4M4 12h3m4 0h9M4 18h10m4 0h2M12 3v6M7 9v6m7 0v6"/>',
    "quality": '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4M7 8h3m4 5h3"/>',
    "h264": _VIDEO,
    "hevc": _VIDEO,
    "av1": _VIDEO,
    "auth": '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 4v3"/>',
    "network": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    "app": '<path d="M4 5h16M4 12h16M4 19h16"/><circle cx="9" cy="5" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="19" r="2"/>',
    "background": '<path d="M4 15v5h16v-5M12 3v12m-5-5 5 5 5-5"/>',
    "quit_app": '<path d="M10 4H4v16h6m5-13 5 5-5 5m-6-5h11"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 5 2c-2 1-2 2-2 3m0 3h.01"/>',
    "logs": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8m-8 4h8m-8 4h5"/>',
    "setup": '<path d="m4 20 12-12 4 4L8 24m6-14 4 4M6 3v6M3 6h6m9-4v4m-2-2h4" transform="translate(0 -2)"/>',
}


def command_icon(name, color):
    drawing = _PATHS[name]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round">{drawing}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    icon = QIcon()
    for size in (18, 24, 36, 48, 72):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon
