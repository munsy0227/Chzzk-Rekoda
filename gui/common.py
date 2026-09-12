from html import escape

from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QProxyStyle,
    QSizePolicy,
    QStyle,
    QToolTip,
)


def text_tooltip(text):
    """Keep user text literal, and avoid an empty rich-text tooltip box."""
    if not text or not text.strip():
        return ""
    return "<qt>" + escape(text).replace("\n", "<br>") + "</qt>"


class HelpStyle(QProxyStyle):
    def __init__(self):
        super().__init__("Fusion")

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return 700
        return super().styleHint(hint, option, widget, returnData)

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PixelMetric.PM_ToolBarExtensionExtent:
            return 32
        return super().pixelMetric(metric, option, widget)


class ElidedLabel(QLabel):
    """Keep a long preview title on one line, with the full text in help."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text_tooltip(text))
        self.refresh_text()
        self.updateGeometry()

    def refresh_text(self):
        super().setText(
            self.fontMetrics().elidedText(
                self._full_text.replace("\n", " "),
                Qt.TextElideMode.ElideRight,
                self.contentsRect().width(),
            )
        )

    def sizeHint(self):
        hint = super().sizeHint()
        return QSize(0, max(hint.height(), self.fontMetrics().height()))

    def minimumSizeHint(self):
        return self.sizeHint()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.refresh_text()
            self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_text()


class FocusHelp(QObject):
    """The same help is available to pointer and keyboard users."""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.FocusIn and watched.toolTip():
            QTimer.singleShot(700, lambda: self.show(watched))
        elif event.type() == QEvent.Type.FocusOut:
            QToolTip.hideText()
        elif event.type() == QEvent.Type.KeyPress and event.key() == 0x01000030:
            if watched.toolTip():
                QMessageBox.information(
                    watched, watched.accessibleName(), watched.toolTip()
                )
                return True
        return False

    def show(self, widget):
        try:
            if QApplication.focusWidget() is widget:
                QToolTip.showText(
                    widget.mapToGlobal(QPoint(0, widget.height())),
                    widget.toolTip(),
                    widget,
                )
        except RuntimeError:
            pass  # The dialog may have closed during the delay.


def show_error(parent, title, message):
    box = QMessageBox(QMessageBox.Icon.Warning, title, str(message), parent=parent)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.exec()
