from copy import deepcopy
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from channel_service import (
    fetch_chzzk_channel,
    safe_channel_folder_name,
    search_chzzk_channels,
)
from config_store import ConfigError, ConfigStore
from gui.appearance import application_icon
from gui.common import show_error
from gui.services import BASE_DIR, Images, Jobs, Preview, Recorder, ffmpeg_executable
from gui.settings_dialog import ChannelDialog, SettingsDialog
from i18n import translate


def fallback_icon(name):
    pixmap = QPixmap(72, 72)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#dceee7"))
    painter.drawRoundedRect(0, 0, 72, 72, 20, 20)
    painter.setPen(QColor("#245647"))
    font = painter.font()
    font.setPixelSize(28)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, name[:1] or "?")
    painter.end()
    return QIcon(pixmap)


class SearchDialog(QDialog):
    def __init__(self, language, jobs, images, registered, parent):
        super().__init__(parent)
        self.language, self.jobs, self.images = language, jobs, images
        self.registered = registered
        self.selected = None
        self.results = []
        self.serial = 0
        self.setWindowTitle(self.t("add"))
        self.resize(640, 500)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItem(self.t("by_name"), "name")
        self.mode.addItem(self.t("by_id"), "id")
        self.query = QLineEdit()
        self.query.setAccessibleName(self.t("query"))
        self.query.setPlaceholderText(self.t("query"))
        self.search_button = QPushButton(self.t("search"))
        self.search_button.clicked.connect(self.search)
        self.query.returnPressed.connect(self.search)
        row.addWidget(self.mode)
        row.addWidget(self.query, 1)
        row.addWidget(self.search_button)
        layout.addLayout(row)
        self.notice = QLabel(self.t("icons_hint"))
        self.notice.setWordWrap(True)
        self.notice.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.notice)
        self.list = QListWidget()
        self.list.setIconSize(QSize(44, 44))
        self.list.itemDoubleClicked.connect(self.choose)
        layout.addWidget(self.list, 1)
        self.images.ready.connect(self.image_ready)
        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton(self.t("cancel"))
        close.clicked.connect(self.reject)
        add = QPushButton(self.t("add"))
        add.setObjectName("primary")
        add.clicked.connect(self.choose)
        buttons.addWidget(close)
        buttons.addWidget(add)
        layout.addLayout(buttons)

    def t(self, key):
        return translate(self.language, "gui." + key)

    def search(self):
        if not self.search_button.isEnabled():
            return
        query = self.query.text().strip()
        if not query:
            return
        self.serial += 1
        serial = self.serial
        self.search_button.setEnabled(False)
        self.list.clear()
        self.results = []
        self.notice.setText(self.t("fetching"))
        by_id = self.mode.currentData() == "id"

        def work():
            if by_id:
                channel, error = fetch_chzzk_channel(query, self.language)
                return ([channel] if channel else []), error
            return search_chzzk_channels(query, self.language)

        def result(value, error):
            if not self.isVisible() or serial != self.serial:
                return
            self.search_button.setEnabled(True)
            channels, message = value if value is not None else ([], error)
            if message:
                self.notice.setText(
                    translate(
                        self.language, "settings.channel_search_failed", error=message
                    )
                )
                return
            self.results = channels
            self.notice.setText(
                self.t("icons_hint")
                if channels
                else translate(self.language, "settings.no_search_results")
            )
            for channel in channels:
                text = channel["name"] + "\n" + channel["id"]
                item = QListWidgetItem(fallback_icon(channel["name"]), text)
                item.setData(Qt.ItemDataRole.UserRole, channel)
                item.setSizeHint(QSize(0, 66))
                if channel["id"] in self.registered:
                    item.setText(
                        text
                        + " · "
                        + translate(self.language, "settings.already_registered_marker")
                    )
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.list.addItem(item)
                self.images.request(channel.get("image_url", ""))

        self.jobs.submit(work, result)

    def image_ready(self, url, pixmap):
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.data(Qt.ItemDataRole.UserRole).get("image_url") == url:
                item.setIcon(QIcon(pixmap))

    def choose(self, *args):
        item = self.list.currentItem()
        if item and item.data(Qt.ItemDataRole.UserRole)["id"] not in self.registered:
            self.selected = item.data(Qt.ItemDataRole.UserRole)
            self.accept()


class MainWindow(QMainWindow):
    def __init__(self, config_path=None):
        super().__init__()
        self.store = ConfigStore(config_path)
        self.config = self.store.load()
        self.language = self.config["language"]
        self.recorder = Recorder(self.store.path, self)
        self.jobs = Jobs(self)
        self.images = Images(self)
        self.preview = Preview(self)
        self.metadata = {}
        self.metadata_pending = set()
        self.snapshots = {}
        self.engine_state = "idle"
        self.closing = False
        self.tray = QSystemTrayIcon(application_icon(), self)
        self.setWindowIcon(application_icon())
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        self.last_frame = QPixmap()
        self.recorder.snapshot.connect(self.receive_status)
        self.recorder.changed.connect(self.engine_changed)
        self.recorder.log.connect(self.append_log)
        self.recorder.error.connect(self.recorder_error)
        self.recorder.finished.connect(self.recorder_finished)
        self.preview.frame.connect(self.show_frame)
        self.preview.unavailable.connect(self.preview_unavailable)
        self.images.ready.connect(self.image_ready)
        self.resize(1180, 820)
        self.setMinimumSize(760, 600)
        self.build_ui()
        QTimer.singleShot(0, self.refresh_metadata)

    def t(self, key, **kwargs):
        return translate(self.language, "gui." + key, **kwargs)

    def build_ui(self):
        previous_logs = self.logs.toPlainText() if hasattr(self, "logs") else ""
        preview_enabled = (
            self.preview_check.isChecked() if hasattr(self, "preview_check") else True
        )
        old = self.takeCentralWidget()
        if old:
            old.deleteLater()
        self.setWindowTitle(self.t("title"))
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 12, 16, 12)
        header = QHBoxLayout()
        title = QLabel(self.t("title"))
        title.setObjectName("brand")
        header.addWidget(title)
        header.addStretch()
        self.state_label = QLabel(self.t(self.engine_state))
        header.addWidget(self.state_label)
        outer.addLayout(header)
        ribbon = QTabWidget()
        ribbon.setObjectName("ribbon")
        ribbon.setMaximumHeight(152)
        self.start_buttons, self.stop_buttons = [], []
        groups = [
            (
                "home",
                [
                    (
                        "basic",
                        [
                            ("start", self.start, QStyle.StandardPixmap.SP_MediaPlay),
                            (
                                "stop",
                                self.recorder.stop,
                                QStyle.StandardPixmap.SP_MediaStop,
                            ),
                        ],
                    ),
                    (
                        "channels",
                        [
                            (
                                "add",
                                self.add_channel,
                                QStyle.StandardPixmap.SP_FileDialogNewFolder,
                            ),
                            (
                                "folder",
                                self.open_folder,
                                QStyle.StandardPixmap.SP_DirOpenIcon,
                            ),
                        ],
                    ),
                ],
            ),
            (
                "channels",
                [
                    (
                        "channels",
                        [
                            (
                                "add",
                                self.add_channel,
                                QStyle.StandardPixmap.SP_FileDialogNewFolder,
                            ),
                            (
                                "edit",
                                self.edit_channel,
                                QStyle.StandardPixmap.SP_FileDialogDetailedView,
                            ),
                            (
                                "remove",
                                self.remove_channel,
                                QStyle.StandardPixmap.SP_TrashIcon,
                            ),
                        ],
                    ),
                    (
                        "refresh",
                        [
                            (
                                "refresh",
                                self.reload_channels,
                                QStyle.StandardPixmap.SP_BrowserReload,
                            )
                        ],
                    ),
                ],
            ),
            (
                "settings",
                [
                    (
                        "basic",
                        [
                            (
                                "basic",
                                lambda: self.settings("basic"),
                                QStyle.StandardPixmap.SP_FileDialogContentsView,
                            ),
                            (
                                "quality",
                                lambda: self.settings("quality"),
                                QStyle.StandardPixmap.SP_DesktopIcon,
                            ),
                        ],
                    ),
                    (
                        "encoder",
                        [
                            (
                                "h264",
                                lambda: self.settings("h264"),
                                QStyle.StandardPixmap.SP_ComputerIcon,
                            ),
                            (
                                "hevc",
                                lambda: self.settings("hevc"),
                                QStyle.StandardPixmap.SP_ComputerIcon,
                            ),
                            (
                                "av1",
                                lambda: self.settings("av1"),
                                QStyle.StandardPixmap.SP_ComputerIcon,
                            ),
                        ],
                    ),
                    (
                        "network",
                        [
                            (
                                "auth",
                                lambda: self.settings("auth"),
                                QStyle.StandardPixmap.SP_DialogApplyButton,
                            ),
                            (
                                "network",
                                lambda: self.settings("network"),
                                QStyle.StandardPixmap.SP_DriveNetIcon,
                            ),
                        ],
                    ),
                    (
                        "app",
                        [
                            (
                                "app",
                                lambda: self.settings("app"),
                                QStyle.StandardPixmap.SP_FileDialogInfoView,
                            ),
                            (
                                "background",
                                self.hide_to_tray,
                                QStyle.StandardPixmap.SP_TitleBarMinButton,
                            ),
                        ],
                    ),
                ],
            ),
            (
                "help",
                [
                    (
                        "help",
                        [
                            (
                                "help",
                                self.help,
                                QStyle.StandardPixmap.SP_DialogHelpButton,
                            ),
                            (
                                "logs",
                                self.toggle_logs,
                                QStyle.StandardPixmap.SP_FileDialogDetailedView,
                            ),
                        ],
                    ),
                ],
            ),
        ]
        for name, sections in groups:
            page = QWidget()
            row = QHBoxLayout(page)
            row.setContentsMargins(4, 4, 4, 4)
            for section, commands in sections:
                group = QGroupBox(self.t(section))
                group_row = QHBoxLayout(group)
                group_row.setContentsMargins(8, 8, 8, 4)
                for key, callback, icon in commands:
                    button = QToolButton()
                    button.setText(self.t(key))
                    button.setIcon(self.style().standardIcon(icon))
                    button.setIconSize(QSize(24, 24))
                    button.setToolButtonStyle(
                        Qt.ToolButtonStyle.ToolButtonTextUnderIcon
                    )
                    button.setToolTip(
                        self.t("quick_help")
                        if key in ("start", "stop")
                        else self.t(key)
                    )
                    button.clicked.connect(callback)
                    group_row.addWidget(button)
                    if key == "start":
                        self.start_buttons.append(button)
                    if key == "stop":
                        self.stop_buttons.append(button)
                row.addWidget(group)
            row.addStretch()
            ribbon.addTab(page, self.t(name))
        outer.addWidget(ribbon)
        self.empty = QLabel(self.t("empty"))
        self.empty.setWordWrap(True)
        outer.addWidget(self.empty)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [
                self.t(k)
                for k in ("channels", "broadcast_title", "status", "duration", "size")
            ]
        )
        self.table.setIconSize(QSize(44, 44))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.table.setColumnWidth(0, 165)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for index in range(2, 5):
            self.table.horizontalHeader().setSectionResizeMode(
                index, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.itemSelectionChanged.connect(self.select_channel)
        self.table.itemDoubleClicked.connect(self.edit_channel)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.channel_menu)
        splitter.addWidget(self.table)
        preview_panel = QWidget()
        right = QVBoxLayout(preview_panel)
        right.setContentsMargins(16, 4, 0, 4)
        label = QLabel(self.t("preview"))
        label.setObjectName("sectionTitle")
        right.addWidget(label)
        self.video = QLabel(self.t("preview_select"))
        self.video.setObjectName("video")
        self.video.setTextFormat(Qt.TextFormat.PlainText)
        self.video.setWordWrap(True)
        self.video.setMinimumSize(280, 185)
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        right.addWidget(self.video, 1)
        self.preview_title = QLabel()
        self.preview_title.setTextFormat(Qt.TextFormat.PlainText)
        self.preview_title.setWordWrap(True)
        right.addWidget(self.preview_title)
        self.preview_note = QLabel(self.t("preview_hint"))
        self.preview_note.setWordWrap(True)
        self.preview_note.setObjectName("subtle")
        right.addWidget(self.preview_note)
        self.preview_time = QLabel()
        self.preview_time.setObjectName("subtle")
        right.addWidget(self.preview_time)
        self.preview_check = QCheckBox(self.t("preview_enabled"))
        self.preview_check.setChecked(preview_enabled)
        self.preview_check.setToolTip(self.t("preview_hint"))
        self.preview_check.toggled.connect(self.select_channel)
        right.addWidget(self.preview_check)
        splitter.addWidget(preview_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([650, 450])
        outer.addWidget(splitter, 1)
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        self.error_label.hide()
        outer.addWidget(self.error_label)
        log_actions = QHBoxLayout()
        log_toggle = QPushButton(self.t("logs"))
        log_toggle.clicked.connect(self.toggle_logs)
        log_actions.addWidget(log_toggle)
        log_actions.addStretch()
        copy = QPushButton(self.t("copy"))
        copy.clicked.connect(
            lambda: QApplication.clipboard().setText(self.logs.toPlainText())
        )
        clear = QPushButton(self.t("clear"))
        clear.clicked.connect(lambda: self.logs.clear())
        log_actions.addWidget(copy)
        log_actions.addWidget(clear)
        outer.addLayout(log_actions)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(1000)
        self.logs.setMaximumHeight(165)
        self.logs.setPlainText(previous_logs)
        outer.addWidget(self.logs)
        self.setCentralWidget(root)
        self.populate()
        self.build_tray_menu()
        self.engine_changed(self.engine_state)
        self.apply_style()

    def apply_style(self):
        dark = QApplication.palette().window().color().lightness() < 128
        surface, field, text, border, accent, muted = (
            ("#252b30", "#20252a", "#e6ecea", "#414a4e", "#91c6b2", "#bac6c1")
            if dark
            else ("#f4f7f6", "#ffffff", "#263b33", "#dce4e0", "#28715b", "#60756b")
        )
        self.setStyleSheet(f"""
            QMainWindow, QDialog {{ background: {surface}; color: {text}; }}
            QWidget {{ font-size: 13px; }}
            QLabel {{ color: {text}; }}
            QLabel#brand {{ font-size: 19px; font-weight: 600; padding: 4px; }}
            QLabel#sectionTitle {{ font-size: 16px; font-weight: 600; }}
            QLabel#subtle {{ color: {muted}; }}
            QGroupBox {{ border: 0; border-right: 1px solid {border}; margin-top: 15px; }}
            QGroupBox::title {{ subcontrol-origin: margin; color: {muted}; }}
            QTabWidget::pane {{ border: 1px solid {border}; background: {field}; border-radius: 7px; }}
            QTabBar::tab {{ padding: 8px 17px; background: transparent; border: 0; }}
            QTabBar::tab:selected {{ color: {accent}; border-bottom: 2px solid {accent}; }}
            QToolButton {{ padding: 6px 9px; border: 0; border-radius: 5px; }}
            QToolButton:hover {{ background: {border}; }}
            QPushButton {{ padding: 7px 12px; border: 1px solid {border}; border-radius: 5px; }}
            QPushButton#primary {{ background: {accent}; color: {field}; }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ padding: 6px; min-height: 22px; background: {field}; color: {text}; border: 1px solid {border}; border-radius: 5px; }}
            QScrollArea {{ border: 0; background: {field}; }}
            QWidget#settingsPage {{ background: {field}; }}
            QListWidget::item {{ padding: 10px 6px; }}
            QTableWidget, QListWidget, QPlainTextEdit {{ background: {field}; border: 1px solid {border}; border-radius: 7px; }}
            QHeaderView::section {{ padding: 9px; border: 0; background: {surface}; }}
            QTableWidget::item {{ padding: 6px; }}
            QTableWidget::item:selected, QListWidget::item:selected {{ background: {accent}; color: {field}; }}
            QLabel#video {{ background: #18211e; color: #dce8e2; border-radius: 9px; padding: 8px; }}
            QLabel#error {{ color: {"#ffb4a9" if dark else "#a72d23"}; }}
        """)

    def current_channel(self):
        row = self.table.currentRow()
        if row < 0 or self.table.item(row, 0) is None:
            return None
        channel_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((c for c in self.config["channels"] if c["id"] == channel_id), None)

    def populate(self):
        selected = self.current_channel() if self.table.rowCount() else None
        selected_id = selected["id"] if selected else None
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for channel in self.config["channels"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 64)
            name = QTableWidgetItem(fallback_icon(channel["name"]), channel["name"])
            name.setData(Qt.ItemDataRole.UserRole, channel["id"])
            name.setToolTip(channel["id"] + "\n" + self.t("icons_hint"))
            self.table.setItem(row, 0, name)
            for column in range(1, 5):
                self.table.setItem(row, column, QTableWidgetItem())
            metadata = self.metadata.get(channel["id"], channel)
            self.images.request(metadata.get("image_url", ""))
            if channel["id"] == selected_id:
                self.table.selectRow(row)
        self.empty.setVisible(not bool(self.config["channels"]))
        if not self.current_channel() and self.table.rowCount():
            self.table.selectRow(0)
        self.table.blockSignals(False)
        self.update_rows()

    def update_rows(self):
        for row, channel in enumerate(self.config["channels"]):
            state = self.snapshots.get(channel["id"], {})
            status = state.get("state", "waiting" if self.recorder.running else "idle")
            if channel["active"] == "off" and not state:
                status = "inactive"
            if status not in ("recording", "waiting", "inactive", "stopping", "idle"):
                status = "waiting"
            title = state.get("title", "")
            self.table.item(row, 1).setText(title or "—")
            self.table.item(row, 1).setToolTip(
                "<qt>" + escape(title).replace("\n", "<br>") + "</qt>"
            )
            self.table.item(row, 2).setText(self.t(status))
            self.table.item(row, 3).setText(state.get("out_time", "") or "—")
            self.table.item(row, 4).setText(state.get("total_size", "") or "—")
        self.select_channel()

    def refresh_metadata(self):
        for channel in self.config["channels"]:
            channel_id = channel["id"]
            if channel_id in self.metadata_pending:
                continue
            self.metadata_pending.add(channel_id)
            self.jobs.submit(
                lambda channel_id=channel_id: fetch_chzzk_channel(
                    channel_id, self.language
                ),
                lambda value, error, channel_id=channel_id: self.metadata_result(
                    channel_id, value, error
                ),
            )

    def metadata_result(self, channel_id, value, error):
        self.metadata_pending.discard(channel_id)
        metadata, message = value if value is not None else (None, error)
        if metadata:
            self.metadata[channel_id] = metadata
            self.images.request(metadata.get("image_url", ""))
        elif message:
            self.statusBar().showMessage(self.t("icon_unavailable"), 10000)

    def image_ready(self, url, pixmap):
        for row, channel in enumerate(self.config["channels"]):
            metadata = self.metadata.get(channel["id"], channel)
            if metadata.get("image_url") == url and self.table.item(row, 0):
                self.table.item(row, 0).setIcon(QIcon(pixmap))

    def reload_channels(self):
        try:
            self.config = self.store.load()
        except (ConfigError, OSError) as error:
            show_error(self, self.t("error"), error)
            return
        if self.language != self.config["language"]:
            self.language = self.config["language"]
            self.build_ui()
        else:
            self.populate()
        self.refresh_metadata()

    def settings(self, category="basic"):
        try:
            config = self.store.load()
        except (ConfigError, OSError) as error:
            show_error(self, self.t("error"), error)
            return
        dialog = SettingsDialog(config, self.store, self, category)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        # Loading advances the store revision even when the dialog is cancelled.
        # Keep the window's data paired with that revision to avoid stale writes.
        self.config = dialog.config if accepted else config
        self.language = self.config["language"]
        self.build_ui()
        if accepted:
            self.statusBar().showMessage(self.t("saved"), 7000)

    def save_channels(self, candidate):
        try:
            self.store.save(candidate)
        except (ConfigError, OSError) as error:
            show_error(self, self.t("error"), error)
            return False
        self.config = candidate
        self.populate()
        self.statusBar().showMessage(self.t("saved"), 5000)
        return True

    def add_channel(self):
        dialog = SearchDialog(
            self.language,
            self.jobs,
            self.images,
            {c["id"] for c in self.config["channels"]},
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        channel = dict(dialog.selected)
        number = 1
        used = {c["identifier"] for c in self.config["channels"]}
        while f"ch{number}" in used:
            number += 1
        channel.update(
            identifier=f"ch{number}",
            active="on",
            output_dir=str(
                BASE_DIR / safe_channel_folder_name(channel["name"], channel["id"])
            ),
        )
        editor = ChannelDialog(channel, 0, self.language, self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            candidate = deepcopy(self.config)
            candidate["channels"].append(editor.channel)
            candidate["delays"][channel["identifier"]] = editor.delay_value
            self.save_channels(candidate)

    def edit_channel(self, *args):
        channel = self.current_channel()
        if not channel:
            return
        dialog = ChannelDialog(
            channel,
            self.config["delays"].get(channel["identifier"], 0),
            self.language,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            candidate = deepcopy(self.config)
            candidate["channels"] = [
                dialog.channel if c["id"] == channel["id"] else c
                for c in candidate["channels"]
            ]
            candidate["delays"][channel["identifier"]] = dialog.delay_value
            self.save_channels(candidate)

    def remove_channel(self):
        channel = self.current_channel()
        if not channel:
            return
        box = QMessageBox(
            QMessageBox.Icon.Question,
            self.t("remove"),
            self.t("remove_confirm", name=channel["name"]),
            parent=self,
        )
        box.setTextFormat(Qt.TextFormat.PlainText)
        remove = box.addButton(self.t("remove"), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(self.t("cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is remove:
            candidate = deepcopy(self.config)
            candidate["channels"] = [
                c for c in candidate["channels"] if c["id"] != channel["id"]
            ]
            candidate["delays"].pop(channel["identifier"], None)
            self.save_channels(candidate)

    def open_folder(self):
        channel = self.current_channel()
        if channel:
            path = Path(channel["output_dir"]).expanduser()
            if not path.is_absolute():
                path = BASE_DIR / path
            try:
                path.mkdir(parents=True, exist_ok=True)
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            except OSError as error:
                show_error(self, self.t("error"), error)

    def channel_menu(self, position):
        item = self.table.itemAt(position)
        if item is None:
            return
        self.table.selectRow(item.row())
        channel = self.current_channel()
        if not channel:
            return
        menu = QMenu(self)
        menu.addAction(self.t("edit"), self.edit_channel)
        menu.addAction(self.t("open_folder"), self.open_folder)
        active = menu.addAction(self.t("active"))
        active.setCheckable(True)
        active.setChecked(channel["active"] == "on")
        active.triggered.connect(self.toggle_channel_active)
        menu.addSeparator()
        menu.addAction(self.t("remove"), self.remove_channel)
        menu.exec(self.table.viewport().mapToGlobal(position))
        menu.deleteLater()

    def toggle_channel_active(self, checked):
        channel = self.current_channel()
        if not channel:
            return
        candidate = deepcopy(self.config)
        for current in candidate["channels"]:
            if current["id"] == channel["id"]:
                current["active"] = "on" if checked else "off"
        self.save_channels(candidate)

    def build_tray_menu(self):
        old = self.tray.contextMenu()
        menu = QMenu(self)
        menu.addAction(self.t("show_window"), self.restore_window)
        self.tray_start = menu.addAction(self.t("start"), self.start)
        self.tray_stop = menu.addAction(self.t("stop"), self.recorder.stop)
        menu.addSeparator()
        menu.addAction(self.t("quit"), self.quit_application)
        self.tray.setContextMenu(menu)
        if old:
            old.deleteLater()

    def tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_window()

    def restore_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.information(
                self, self.t("background"), self.t("tray_unavailable")
            )
            return
        self.tray.show()
        self.hide()

    def quit_application(self):
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, (SettingsDialog, ChannelDialog)):
            dialog.reject()
            if dialog.isVisible():
                if getattr(dialog, "closing", False):
                    dialog.finished.connect(
                        self.quit_application, Qt.ConnectionType.SingleShotConnection
                    )
                return
        elif dialog is not None:
            self.restore_window()
            return
        self.closing = True
        self.close()

    def start(self):
        try:
            self.config = self.store.load()
        except (ConfigError, OSError) as error:
            show_error(self, self.t("error"), error)
            return
        if self.language != self.config["language"]:
            self.language = self.config["language"]
            self.build_ui()
        else:
            self.populate()
        if not ffmpeg_executable():
            self.recorder_error(
                translate(self.language, "record.ffmpeg_not_found_path")
            )
            return
        if not any(c["active"] == "on" for c in self.config["channels"]):
            self.statusBar().showMessage(self.t("empty"), 10000)
            return
        self.error_label.hide()
        self.recorder.start()

    def engine_changed(self, state):
        self.engine_state = state
        self.state_label.setText(self.t(state))
        self.tray.setToolTip(self.t("title") + " · " + self.t(state))
        self.tray_start.setEnabled(state == "idle")
        self.tray_stop.setEnabled(state in ("starting", "running"))
        for button in self.start_buttons:
            button.setEnabled(state == "idle")
        for button in self.stop_buttons:
            button.setEnabled(state in ("starting", "running"))
        if state == "idle":
            self.snapshots.clear()
        self.update_rows()

    def receive_status(self, channels):
        self.snapshots = {
            c["id"]: c
            for c in channels
            if isinstance(c, dict) and isinstance(c.get("id"), str)
        }
        self.update_rows()

    def select_channel(self, *args):
        channel = self.current_channel()
        state = self.snapshots.get(channel["id"], {}) if channel else {}
        target = (
            state
            if self.preview_check.isChecked()
            and state.get("state") == "recording"
            and state.get("output_path")
            else None
        )
        self.preview.set_target(target)
        self.preview_title.setText(
            state.get("title", "") or (channel["name"] if channel else "")
        )
        if not target:
            self.last_frame = QPixmap()
            self.video.clear()
            self.video.setText(
                self.t("preview_select")
                if self.preview_check.isChecked()
                else self.t("off")
            )
            self.preview_time.clear()

    def show_frame(self, pixmap):
        self.last_frame = pixmap
        self.scale_frame()
        self.preview_time.setText(
            self.t("preview_updated", time=datetime.now().strftime("%H:%M:%S"))
        )

    def scale_frame(self):
        if not self.last_frame.isNull():
            self.video.setPixmap(
                self.last_frame.scaled(
                    self.video.size() - QSize(16, 16),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def preview_unavailable(self, reason="waiting"):
        self.last_frame = QPixmap()
        if hasattr(self, "video"):
            self.video.clear()
            self.video.setText(
                self.t("preview_failed" if reason == "failed" else "preview_wait")
            )
            self.preview_time.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "video"):
            self.scale_frame()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ApplicationPaletteChange and hasattr(
            self, "table"
        ):
            self.apply_style()

    def append_log(self, text):
        self.logs.appendPlainText(text)

    def recorder_error(self, message):
        if message in ("protocol_error", "start_failed", "recorder_failed"):
            message = self.t(message)
        self.error_label.setText(message)
        self.error_label.show()
        self.append_log(message)

    def help(self):
        QMessageBox.information(self, self.t("help"), self.t("quick_help"))

    def toggle_logs(self):
        self.logs.setVisible(not self.logs.isVisible())

    def recorder_finished(self):
        if self.closing:
            self.close()

    def closeEvent(self, event):
        if (
            not self.closing
            and self.config["gui_settings"]["close_to_tray"]
            and QSystemTrayIcon.isSystemTrayAvailable()
        ):
            self.hide_to_tray()
            event.ignore()
            return
        self.closing = True
        self.preview.close()
        self.jobs.cancel_pending()
        if self.recorder.running:
            self.recorder.stop()
            event.ignore()
            return
        event.accept()
        self.tray.hide()
        QTimer.singleShot(0, QApplication.instance().quit)
