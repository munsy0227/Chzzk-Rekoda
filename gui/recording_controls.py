"""Shared global/channel recording option widgets."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.common import FocusHelp
from i18n import translate
from recording_options import DIRECT_QUALITIES, normalize_quality


class SplitEditor(QWidget):
    def __init__(self, value, language, parent=None):
        super().__init__(parent)

        def t(key):
            return translate(language, "gui." + key)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.unit = QComboBox()
        for factor, label in (
            (-1, "inherit"),
            (0, "off"),
            (1, "minutes"),
            (60, "hours"),
        ):
            self.unit.addItem(t(label), factor)
        self.number = QSpinBox()
        self.number.setRange(1, 10080)
        self.number.setValue(value or 1)
        self.factor = 1
        self.unit.setCurrentIndex(
            self.unit.findData(-1 if value is None else (1 if value else 0))
        )
        self.number.setEnabled(bool(value))
        self.help_filter = FocusHelp(self)
        for widget in (self.number, self.unit):
            widget.setToolTip(t("channel_split_help"))
            widget.installEventFilter(self.help_filter)
            layout.addWidget(widget)
        self.unit.currentIndexChanged.connect(self.changed)

    def changed(self):
        factor = self.unit.currentData()
        minutes = self.number.value() * self.factor
        self.number.setEnabled(factor > 0)
        if factor > 0:
            self.number.setMaximum(10080 // factor)
            self.number.setValue(max(1, (minutes + factor - 1) // factor))
            self.factor = factor

    def value(self):
        factor = self.unit.currentData()
        return None if factor == -1 else self.number.value() * factor


class QualityEditor(QWidget):
    def __init__(self, value, language, parent=None, allow_inherit=False):
        super().__init__(parent)
        self.language = language
        settings = normalize_quality(value)
        self.settings = settings
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.inherit = QCheckBox(self.t("inherit"))
        self.inherit.setChecked(allow_inherit and value is None)
        self.inherit.setVisible(allow_inherit)
        layout.addWidget(self.inherit)
        form = QFormLayout()
        self.form = form
        self.mode = QComboBox()
        for mode in ("best", *DIRECT_QUALITIES, "custom"):
            self.mode.addItem(
                self.t("quality_" + mode) if mode in ("best", "custom") else mode, mode
            )
        self.mode.setCurrentIndex(self.mode.findData(settings["mode"]))
        form.addRow(self.t("quality"), self.mode)
        self.width, self.height = QSpinBox(), QSpinBox()
        self.width.setRange(0, 8192)
        self.width.setSpecialValueText(self.t("aspect_auto"))
        self.height.setRange(2, 4320)
        for widget, key in ((self.width, "width"), (self.height, "height")):
            widget.setSingleStep(2)
            widget.setValue(settings[key])
            form.addRow(self.t(key), widget)
        self.fps = QDoubleSpinBox()
        self.fps.setRange(0, 120)
        self.fps.setDecimals(3)
        self.fps.setSpecialValueText(self.t("quality_original"))
        self.fps.setValue(settings["fps"])
        form.addRow(self.t("fps"), self.fps)
        layout.addLayout(form)
        help_text = QLabel(self.t("quality_help"))
        help_text.setWordWrap(True)
        help_text.setObjectName("subtle")
        layout.addWidget(help_text)
        self.help_filter = FocusHelp(self)
        for widget in (self.inherit, self.mode, self.width, self.height, self.fps):
            widget.setToolTip(self.t("quality_help"))
            widget.installEventFilter(self.help_filter)
        self.inherit.toggled.connect(self.changed)
        self.mode.currentIndexChanged.connect(self.changed)
        self.changed()

    def t(self, key):
        return translate(self.language, "gui." + key)

    def changed(self):
        enabled = not self.inherit.isChecked()
        self.mode.setEnabled(enabled)
        self.fps.setEnabled(enabled)
        for widget in (self.width, self.height):
            widget.setEnabled(enabled and self.mode.currentData() == "custom")
            self.form.setRowVisible(widget, self.mode.currentData() == "custom")

    def value(self, validate=True):
        if self.inherit.isChecked():
            return None
        result = {
            **self.settings,
            "mode": self.mode.currentData(),
            "width": self.width.value(),
            "height": self.height.value(),
            "fps": self.fps.value(),
        }
        if validate and (
            (
                result["mode"] == "custom"
                and (result["width"] % 2 or result["height"] % 2)
            )
            or 0 < result["fps"] < 1
        ):
            raise ValueError(self.t("invalid_quality"))
        return result
