import json
import sys
from copy import deepcopy
from urllib.parse import urlparse

from PySide6.QtCore import QProcess, QProcessEnvironment
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config_store import (
    ALLOWED_AV1_ENCODERS,
    ALLOWED_ENCODERS,
    AUTH_COOKIE_NAMES,
    BROWSER_LOGIN_OPTIONS,
    DEFAULT_DOH_URL,
    ENCODER_DEFAULT_PRESETS,
    ENCODER_PRESETS,
    SAFE_BITRATE,
    ConfigError,
)
from gui.common import FocusHelp, show_error
from gui.services import BASE_DIR
from i18n import SUPPORTED_LANGUAGES, translate


class SettingsDialog(QDialog):
    def __init__(self, config, store, parent=None, category="basic"):
        super().__init__(parent)
        self.config = deepcopy(config)
        self.store = store
        self.language = config["language"]
        self.controls = {}
        self.login_process = None
        self.closing = False
        self.help_filter = FocusHelp(self)
        self.setWindowTitle(self.t("settings"))
        self.resize(920, 640)
        layout = QVBoxLayout(self)
        content = QHBoxLayout()
        layout.addLayout(content, 1)
        self.categories = QListWidget()
        self.categories.setMaximumWidth(190)
        self.pages = QStackedWidget()
        content.addWidget(self.categories)
        content.addWidget(self.pages, 1)
        for key in ("basic", "hevc", "av1", "auth", "network", "app"):
            self.categories.addItem(self.t(key))
            page = QWidget()
            page.setObjectName("settingsPage")
            page_layout = QVBoxLayout(page)
            form = QFormLayout()
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            form.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
            )
            form.setVerticalSpacing(16)
            page_layout.addLayout(form)
            page_layout.addStretch()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.pages.addWidget(scroll)
            if key in ("hevc", "av1"):
                self.codec(form, key)
            else:
                getattr(self, "build_" + key)(form)
        self.categories.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.categories.setCurrentRow(
            ("basic", "hevc", "av1", "auth", "network", "app").index(category)
        )
        hint = QLabel(self.t("apply_hint"))
        hint.setWordWrap(True)
        hint.setObjectName("subtle")
        layout.addWidget(hint)
        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton(self.t("cancel"))
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton(self.t("save"))
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self.save)
        actions.addWidget(cancel)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)
        for codec in ("hevc", "av1"):
            self.controls[codec + "_settings.enable"].toggled.connect(
                lambda checked, codec=codec: self.exclusive(codec, checked)
            )

    def t(self, key, **kwargs):
        return translate(self.language, "gui." + key, **kwargs)

    def get(self, path):
        value = self.config
        for key in path.split("."):
            value = value[key]
        return value

    def field(self, form, path, widget, label, help_key):
        self.controls[path] = widget
        widget.setObjectName(path)
        widget.setAccessibleName(self.t(label))
        widget.setToolTip(self.t(help_key))
        widget.installEventFilter(self.help_filter)
        row = QHBoxLayout()
        row.addWidget(widget, 1)
        help_button = QToolButton()
        help_button.setText("?")
        help_button.setAccessibleName(self.t(label) + " · " + self.t("help"))
        help_button.setToolTip(self.t(help_key))
        help_button.clicked.connect(
            lambda: QMessageBox.information(self, self.t(label), self.t(help_key))
        )
        row.addWidget(help_button)
        form.addRow(self.t(label), row)
        return widget

    def combo(self, values, current):
        box = QComboBox()
        box.setMinimumContentsLength(12)
        box.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        for value, label in values:
            box.addItem(label, value)
        box.setCurrentIndex(max(0, box.findData(current)))
        return box

    def check(self, value):
        box = QCheckBox()
        box.setChecked(bool(value))
        return box

    def spin(self, value, low, high):
        box = QSpinBox()
        box.setRange(low, high)
        box.setValue(value)
        return box

    def build_basic(self, form):
        self.field(
            form,
            "output_format",
            self.combo(
                [(v, v.upper()) for v in ("ts", "mkv", "webm")],
                self.get("output_format"),
            ),
            "format",
            "format_help",
        )
        split = self.get("recording_split_minutes")
        self.split_unit = self.combo(
            [(0, self.t("off")), (1, self.t("minutes")), (60, self.t("hours"))],
            0 if split == 0 else 1,
        )
        self.split_number = self.spin(split, 1, 10080)
        self.split_number.setEnabled(bool(split))
        self.split_number.setToolTip(self.t("split_help"))
        self.split_unit.setToolTip(self.t("split_help"))
        self.split_number.installEventFilter(self.help_filter)
        self.split_unit.installEventFilter(self.help_filter)
        self.split_factor = 1
        split_row = QHBoxLayout()
        split_row.addWidget(self.split_number)
        split_row.addWidget(self.split_unit)
        form.addRow(self.t("split"), split_row)
        self.split_unit.currentIndexChanged.connect(self.change_split_unit)
        self.field(
            form,
            "timeout",
            self.spin(self.get("timeout"), 1, 3600),
            "timeout",
            "timeout_help",
        )
        self.field(
            form,
            "stream_segment_threads",
            self.spin(self.get("stream_segment_threads"), 1, 16),
            "threads",
            "threads_help",
        )

    def change_split_unit(self):
        factor = self.split_unit.currentData()
        minutes = self.split_number.value() * self.split_factor
        self.split_number.setEnabled(bool(factor))
        if factor:
            self.split_number.setMaximum(10080 // factor)
            self.split_number.setValue(max(1, (minutes + factor - 1) // factor))
            self.split_factor = factor

    def codec(self, form, codec):
        prefix = codec + "_settings."
        self.field(
            form,
            prefix + "enable",
            self.check(self.get(prefix + "enable")),
            "enabled",
            "enabled_help",
        )
        encoders = ALLOWED_ENCODERS if codec == "hevc" else ALLOWED_AV1_ENCODERS
        encoder = self.field(
            form,
            prefix + "encoder",
            self.combo(
                [(v, v) for v in sorted(encoders)], self.get(prefix + "encoder")
            ),
            "encoder",
            "encoder_help",
        )
        preset = self.field(
            form, prefix + "preset", QComboBox(), "preset", "preset_help"
        )
        self.update_presets(codec, self.get(prefix + "preset"))
        encoder.currentIndexChanged.connect(
            lambda: self.update_presets(codec, preset.currentData())
        )
        self.field(
            form,
            prefix + "bitrate",
            QLineEdit(self.get(prefix + "bitrate")),
            "bitrate",
            "bitrate_help",
        )
        self.field(
            form,
            prefix + "max_bitrate",
            QLineEdit(self.get(prefix + "max_bitrate")),
            "max_bitrate",
            "bitrate_help",
        )

    def update_presets(self, codec, previous):
        prefix = codec + "_settings."
        encoder = self.controls[prefix + "encoder"].currentData()
        preset = self.controls[prefix + "preset"]
        values = ENCODER_PRESETS.get(encoder)
        preset.clear()
        if values:
            ordered = sorted(
                values, key=lambda v: (0, int(v)) if v.lstrip("-").isdigit() else (1, v)
            )
            for value in ordered:
                preset.addItem(value, value)
            current = (
                previous if previous in values else ENCODER_DEFAULT_PRESETS[encoder]
            )
        else:
            preset.addItem(self.t("auto"), "auto")
            current = "auto"
        preset.setCurrentIndex(preset.findData(current))
        preset.setEnabled(bool(values))

    def exclusive(self, codec, checked):
        if checked:
            other = "av1" if codec == "hevc" else "hevc"
            self.controls[other + "_settings.enable"].setChecked(False)

    def build_auth(self, form):
        self.browser = self.combo(
            [(code, label) for code, label in BROWSER_LOGIN_OPTIONS.values()], "chrome"
        )
        form.addRow(self.t("browser"), self.browser)
        self.login_button = QPushButton(self.t("login"))
        self.login_button.clicked.connect(self.login)
        form.addRow(self.login_button)
        self.login_notice = QLabel()
        self.login_notice.setWordWrap(True)
        form.addRow(self.login_notice)
        for name in AUTH_COOKIE_NAMES:
            line = QLineEdit(self.get("cookies." + name))
            line.setEchoMode(QLineEdit.EchoMode.Password)
            self.controls["cookies." + name] = line
            line.setObjectName("cookies." + name)
            line.setAccessibleName(name)
            line.setToolTip(self.t("cookie_help"))
            line.installEventFilter(self.help_filter)
            form.addRow(name, line)
        show = QCheckBox(self.t("show_cookies"))
        show.toggled.connect(
            lambda value: [
                self.controls["cookies." + name].setEchoMode(
                    QLineEdit.EchoMode.Normal if value else QLineEdit.EchoMode.Password
                )
                for name in AUTH_COOKIE_NAMES
            ]
        )
        form.addRow(show)
        clear = QPushButton(self.t("clear_cookies"))
        clear.clicked.connect(
            lambda: [
                self.controls["cookies." + name].clear() for name in AUTH_COOKIE_NAMES
            ]
        )
        form.addRow(clear)

    def build_network(self, form):
        self.field(
            form,
            "dns_settings.enable",
            self.check(self.get("dns_settings.enable")),
            "doh_enabled",
            "dns_help",
        )
        self.field(
            form,
            "dns_settings.doh_url",
            QLineEdit(self.get("dns_settings.doh_url")),
            "doh_url",
            "dns_help",
        )
        restore = QPushButton(self.t("restore"))
        restore.clicked.connect(
            lambda: self.controls["dns_settings.doh_url"].setText(DEFAULT_DOH_URL)
        )
        form.addRow(restore)

    def build_app(self, form):
        self.field(
            form,
            "language",
            self.combo(SUPPORTED_LANGUAGES.items(), self.language),
            "language",
            "language_help",
        )
        self.field(
            form,
            "log_enabled",
            self.check(self.get("log_enabled")),
            "log_enabled",
            "log_help",
        )

    def collect(self, validate=True):
        result = deepcopy(self.config)
        for path, widget in self.controls.items():
            if isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QComboBox):
                value = widget.currentData()
            elif isinstance(widget, QSpinBox):
                value = widget.value()
            else:
                value = widget.text()
            parts = path.split(".")
            target = result
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = value
        result["recording_split_minutes"] = (
            self.split_number.value() * self.split_unit.currentData()
        )
        if validate:
            for codec in ("hevc_settings", "av1_settings"):
                for key in ("bitrate", "max_bitrate"):
                    if not SAFE_BITRATE.fullmatch(result[codec][key].strip()):
                        raise ValueError(self.t("invalid_bitrate"))
            try:
                url = urlparse(result["dns_settings"]["doh_url"].strip())
                if url.scheme != "https" or not url.hostname:
                    raise ValueError()
            except ValueError:
                raise ValueError(self.t("invalid_doh")) from None
        return result

    def save(self):
        try:
            candidate = self.collect()
            self.store.save(candidate)
        except (ConfigError, OSError, ValueError) as error:
            show_error(self, self.t("error"), error)
            return
        self.config = candidate
        self.accept()

    def login(self):
        if (
            self.login_process
            and self.login_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.login_process.write(b"cancel\n")
            self.login_button.setEnabled(False)
            return
        process = QProcess(self)
        self.login_process = process
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUTF8", "1")
        env.insert("SE_TIMEOUT", "30")
        process.setProcessEnvironment(env)
        process.setWorkingDirectory(str(BASE_DIR))
        self.cookie_data = bytearray()
        process.readyReadStandardOutput.connect(self.read_login)
        process.readyReadStandardError.connect(process.readAllStandardError)
        process.finished.connect(self.login_done)
        process.errorOccurred.connect(
            lambda error: (
                self.login_done(1, None)
                if error == QProcess.ProcessError.FailedToStart
                else None
            )
        )
        self.login_notice.setText(self.t("login_wait"))
        self.login_button.setText(self.t("login_cancel"))
        self.save_button.setEnabled(False)
        process.start(
            sys.executable,
            ["-u", str(BASE_DIR / "browser_login.py"), self.browser.currentData()],
        )

    def read_login(self):
        self.cookie_data.extend(bytes(self.login_process.readAllStandardOutput()))
        if len(self.cookie_data) > 65536:
            self.cookie_data.clear()
            self.login_process.write(b"cancel\n")

    def login_done(self, code, status):
        self.read_login()
        try:
            data = json.loads(self.cookie_data)
            cookies = data["cookies"]
            if code or not all(
                isinstance(cookies.get(name), str) and cookies[name]
                for name in AUTH_COOKIE_NAMES
            ):
                raise ValueError()
            for name in AUTH_COOKIE_NAMES:
                self.controls["cookies." + name].setText(cookies[name])
            self.login_notice.setText(self.t("login_received"))
        except (ValueError, KeyError, TypeError):
            self.login_notice.setText(self.t("login_failed"))
        self.cookie_data.clear()
        self.login_button.setEnabled(True)
        self.login_button.setText(self.t("login"))
        self.save_button.setEnabled(True)
        if self.closing:
            super().reject()

    def reject(self):
        if self.collect(False) != self.config:
            box = QMessageBox(
                QMessageBox.Icon.Question,
                self.t("settings"),
                self.t("unsaved"),
                parent=self,
            )
            discard = box.addButton(
                self.t("discard"), QMessageBox.ButtonRole.DestructiveRole
            )
            box.addButton(self.t("cancel"), QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is not discard:
                return
        if (
            self.login_process
            and self.login_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.closing = True
            self.login_process.write(b"cancel\n")
            self.setEnabled(False)
            return
        super().reject()


class ChannelDialog(QDialog):
    def __init__(self, channel, delay, language, parent=None):
        super().__init__(parent)
        self.channel = deepcopy(channel)
        self.language = language
        self.delay_value = delay
        self.setWindowTitle(self.t("edit"))
        self.resize(580, 330)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(channel["name"])
        self.path = QLineEdit(channel["output_dir"])
        self.delay = QSpinBox()
        self.delay.setRange(0, 3600)
        self.delay.setValue(delay)
        self.active = QCheckBox(self.t("active"))
        self.active.setChecked(channel.get("active") != "off")
        channel_id = QLineEdit(channel["id"])
        channel_id.setReadOnly(True)
        form.addRow(self.t("id"), channel_id)
        form.addRow(self.t("name"), self.name)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path, 1)
        browse = QPushButton(self.t("browse"))
        browse.clicked.connect(self.browse)
        path_row.addWidget(browse)
        form.addRow(self.t("path"), path_row)
        form.addRow(self.t("delay"), self.delay)
        form.addRow(self.active)
        self.help_filter = FocusHelp(self)
        for widget in (self.name, self.path, self.delay, self.active):
            widget.setToolTip(self.t("channel_help"))
            widget.installEventFilter(self.help_filter)
        layout.addLayout(form)
        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton(self.t("cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(self.t("save"))
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(actions)

    def t(self, key):
        return translate(self.language, "gui." + key)

    def browse(self):
        path = QFileDialog.getExistingDirectory(
            self, self.t("browse"), self.path.text()
        )
        if path:
            self.path.setText(path)

    def save(self):
        if not self.name.text().strip() or not self.path.text().strip():
            show_error(self, self.t("error"), self.t("required"))
            return
        self.channel.update(
            name=self.name.text().strip(),
            output_dir=self.path.text().strip(),
            active="on" if self.active.isChecked() else "off",
        )
        self.delay_value = self.delay.value()
        self.accept()
