"""First-run language and channel setup; persist only on Finish."""

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from channel_service import safe_channel_folder_name
from config_store import ConfigError
from gui.common import show_error
from gui.services import BASE_DIR
from gui.settings_dialog import ChannelDialog
from i18n import SUPPORTED_LANGUAGES, translate


class ChannelPage(QWizardPage):
    def isComplete(self):
        wizard = self.wizard()
        return bool(wizard.draft["channels"]) or wizard.skip.isChecked()


class SetupWizard(QWizard):
    def __init__(self, config, store, jobs, images, parent=None):
        super().__init__(parent)
        self.draft = deepcopy(config)
        self.store, self.jobs, self.images = store, jobs, images
        self.language = config["language"]
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        for role in (
            QWizard.WizardButton.NextButton,
            QWizard.WizardButton.FinishButton,
        ):
            button = self.button(role)
            button.setObjectName("primary")
            button.style().unpolish(button)
            button.style().polish(button)
        self.resize(760, 610)
        self.pages = []
        for page in (QWizardPage(), ChannelPage(), QWizardPage()):
            page.setLayout(QVBoxLayout())
            self.addPage(page)
            self.pages.append(page)
        self.language_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.language))
        self.pages[0].layout().addWidget(self.language_combo)
        self.pages[0].layout().addStretch()
        self.language_combo.currentIndexChanged.connect(self.change_language)

        self.folder_label = QLabel()
        self.folder = QLineEdit(str(BASE_DIR))
        self.browse_button = QPushButton()
        self.browse_button.clicked.connect(self.browse)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(self.browse_button)
        layout = self.pages[1].layout()
        layout.addWidget(self.folder_label)
        layout.addLayout(folder_row)
        self.channels = QListWidget()
        self.channels.itemDoubleClicked.connect(self.edit_channel)
        layout.addWidget(self.channels, 1)
        row = QHBoxLayout()
        self.add_button, self.edit_button, self.remove_button = (
            QPushButton() for _ in range(3)
        )
        for button, callback in (
            (self.add_button, self.add_channel),
            (self.edit_button, self.edit_channel),
            (self.remove_button, self.remove_channel),
        ):
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        self.skip = QCheckBox()
        self.skip.toggled.connect(self.pages[1].completeChanged)
        layout.addWidget(self.skip)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.pages[2].layout().addWidget(self.summary)
        self.pages[2].layout().addStretch()
        self.currentIdChanged.connect(self.update_summary)
        self.retranslate()
        self.populate()

    def t(self, key, **kwargs):
        return translate(self.language, "gui." + key, **kwargs)

    def change_language(self):
        self.language = self.language_combo.currentData()
        self.draft["language"] = self.language
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(self.t("setup"))
        for page, key in zip(
            self.pages, ("setup_language", "setup_channels", "setup_ready"), strict=True
        ):
            page.setTitle(self.t(key))
            page.setSubTitle(self.t(key + "_help"))
        for button, key in (
            (QWizard.WizardButton.BackButton, "back"),
            (QWizard.WizardButton.NextButton, "next"),
            (QWizard.WizardButton.FinishButton, "finish"),
            (QWizard.WizardButton.CancelButton, "cancel"),
        ):
            self.setButtonText(button, self.t(key))
        self.folder_label.setText(self.t("setup_folder"))
        for widget, key in (
            (self.browse_button, "browse"),
            (self.add_button, "add"),
            (self.edit_button, "edit"),
            (self.remove_button, "remove"),
            (self.skip, "setup_skip"),
        ):
            widget.setText(self.t(key))
        self.folder.setToolTip(self.t("setup_folder_help"))
        self.update_summary()

    def update_summary(self):
        self.summary.setText(
            self.t(
                "setup_summary",
                language=SUPPORTED_LANGUAGES[self.language],
                count=len(self.draft["channels"]),
            )
        )

    def populate(self):
        self.channels.clear()
        for channel in self.draft["channels"]:
            item = QListWidgetItem(channel["name"] + "\n" + channel["output_dir"])
            item.setData(Qt.ItemDataRole.UserRole, channel["id"])
            self.channels.addItem(item)
        self.pages[1].completeChanged.emit()
        self.update_summary()

    def browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, self.t("browse"), self.folder.text()
        )
        if folder:
            self.folder.setText(folder)

    def add_channel(self):
        from gui.window import SearchDialog

        if not self.folder.text().strip():
            show_error(self, self.t("error"), self.t("required"))
            return
        search = SearchDialog(
            self.language,
            self.jobs,
            self.images,
            {c["id"] for c in self.draft["channels"]},
            self,
        )
        if search.exec() != QDialog.DialogCode.Accepted:
            return
        channel = dict(search.selected)
        number = 1
        used = {c["identifier"] for c in self.draft["channels"]}
        while f"ch{number}" in used:
            number += 1
        channel.update(
            identifier=f"ch{number}",
            active="on",
            output_dir=str(
                Path(self.folder.text()).expanduser()
                / safe_channel_folder_name(channel["name"], channel["id"])
            ),
        )
        editor = ChannelDialog(channel, 0, self.language, self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.draft["channels"].append(editor.channel)
            self.draft["delays"][channel["identifier"]] = editor.delay_value
            self.populate()

    def current_channel(self):
        item = self.channels.currentItem()
        return next(
            (
                c
                for c in self.draft["channels"]
                if item and c["id"] == item.data(Qt.ItemDataRole.UserRole)
            ),
            None,
        )

    def edit_channel(self):
        channel = self.current_channel()
        if channel is None:
            return
        editor = ChannelDialog(
            channel,
            self.draft["delays"].get(channel["identifier"], 0),
            self.language,
            self,
        )
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.draft["channels"] = [
                editor.channel if c["id"] == channel["id"] else c
                for c in self.draft["channels"]
            ]
            self.draft["delays"][channel["identifier"]] = editor.delay_value
            self.populate()

    def remove_channel(self):
        channel = self.current_channel()
        if channel:
            self.draft["channels"].remove(channel)
            self.draft["delays"].pop(channel["identifier"], None)
            self.populate()

    def accept(self):
        if not self.pages[1].isComplete():
            return
        candidate = deepcopy(self.draft)
        candidate["gui_settings"]["onboarding_completed"] = True
        try:
            self.store.save(candidate)
        except (ConfigError, OSError) as error:
            show_error(self, self.t("error"), error)
            return
        self.draft = candidate
        super().accept()
