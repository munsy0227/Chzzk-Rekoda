"""Compact light/dark surfaces shared by the ribbon and its dialogs."""

from pathlib import Path


def stylesheet(dark=False):
    icons = Path(__file__).resolve().parent.parent / "assets" / "controls"
    up, down = (
        (icons / f"chevron-{direction}.svg").as_posix().replace('"', r"\"")
        for direction in ("up", "down")
    )
    if dark:
        canvas, surface, alternate = "#151b20", "#20282e", "#242e34"
        text, muted, border = "#e6eeec", "#a6b8b1", "#35434a"
        accent, accent_hover, on_accent = "#8bdfc3", "#a5ead3", "#102e25"
        selected, hover, danger = "#244d42", "#2c393f", "#ffb4ab"
    else:
        canvas, surface, alternate = "#f3f6f7", "#ffffff", "#f8fafb"
        text, muted, border = "#20312d", "#62756e", "#dde5e3"
        accent, accent_hover, on_accent = "#087e65", "#066a55", "#ffffff"
        selected, hover, danger = "#dff4eb", "#edf3f1", "#b63732"
    return f"""
        QMainWindow, QDialog {{ background: {canvas}; color: {text}; }}
        QLabel, QCheckBox, QRadioButton, QToolButton, QPushButton {{ color: {text}; }}
        QLabel#brand {{ font-size: 12pt; font-weight: 600; }}
        QLabel#sectionTitle, QLabel#previewTitle {{ font-weight: 600; }}
        QLabel#subtle {{ color: {muted}; }}
        QLabel#engineState {{ background: {surface}; color: {muted};
            border: 1px solid {border}; border-radius: 12px; padding: 4px 12px; }}
        QLabel#engineState[state="running"] {{ background: {selected}; color: {accent}; }}
        QLabel#engineState[state="starting"], QLabel#engineState[state="stopping"] {{
            color: {accent}; border-color: {accent}; }}
        QWidget#previewPanel {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; }}
        QTabWidget::pane {{ background: {surface}; border: 1px solid {border}; border-radius: 8px; }}
        QTabBar::tab {{ color: {muted}; padding: 6px 16px; border: 0;
            border-bottom: 2px solid transparent; background: transparent; }}
        QTabBar::tab:selected {{ color: {accent}; border-bottom-color: {accent}; font-weight: 600; }}
        QTabBar::tab:hover {{ background: {hover}; }}
        QToolBar#ribbonCommands {{ background: transparent; border: 0; spacing: 4px; padding: 2px; }}
        QToolBar::separator {{ width: 1px; background: {border}; margin: 6px 6px; }}
        QToolButton {{ padding: 6px 8px; border: 1px solid transparent; border-radius: 6px; }}
        QToolButton#qt_toolbar_ext_button {{ padding: 0; border: 0; background: {hover}; }}
        QPushButton {{ padding: 5px 12px; min-height: 20px; background: {surface};
            border: 1px solid {border}; border-radius: 6px; }}
        QToolButton:hover, QPushButton:hover {{ background: {hover}; }}
        QToolButton:pressed, QPushButton:pressed {{ background: {selected}; }}
        QToolButton#primary, QPushButton#primary {{ background: {accent}; color: {on_accent}; border-color: {accent}; }}
        QToolButton#primary:hover, QPushButton#primary:hover {{ background: {accent_hover}; }}
        QToolButton:disabled, QPushButton:disabled {{ color: {muted}; background: {alternate}; border-color: {border}; }}
        QToolButton#primary:disabled, QPushButton#primary:disabled {{ background: {alternate}; color: {muted}; border-color: {border}; }}
        QToolButton:focus, QPushButton:focus {{ border: 1px solid {accent}; }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ padding: 4px 8px; min-height: 20px;
            color: {text}; background: {surface}; border: 1px solid {border}; border-radius: 6px;
            selection-background-color: {selected}; selection-color: {text}; }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {accent}; }}
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{ color: {muted}; background: {alternate}; }}
        QComboBox QAbstractItemView {{ color: {text}; background: {surface};
            selection-background-color: {selected}; selection-color: {text}; }}
        QComboBox::drop-down {{ border: 0; width: 24px; }}
        QComboBox::down-arrow {{ image: url("{down}"); width: 12px; height: 12px; }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ border: 0; width: 18px; }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{up}"); width: 10px; height: 10px; }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{down}"); width: 10px; height: 10px; }}
        QScrollArea {{ border: 0; background: {surface}; }}
        QWidget#settingsPage {{ background: {surface}; }}
        QTableWidget, QListWidget, QPlainTextEdit {{ color: {text}; background: {surface};
            alternate-background-color: {alternate}; border: 1px solid {border}; border-radius: 8px;
            selection-background-color: {selected}; selection-color: {text}; }}
        QListWidget::item {{ padding: 8px; border-radius: 5px; }}
        QListWidget#settingsCategories {{ background: {canvas}; border: 0; }}
        QListWidget#settingsCategories::item:selected {{ color: {accent}; font-weight: 600; }}
        QHeaderView {{ background: {surface}; }}
        QHeaderView::section {{ color: {muted}; padding: 7px 10px; border: 0;
            border-bottom: 1px solid {border}; background: {surface}; font-weight: 500; }}
        QTableWidget::item {{ padding: 4px 8px; border: 0; }}
        QTableWidget::item:selected, QListWidget::item:selected {{ background: {selected}; color: {text}; }}
        QTableWidget::item:hover, QListWidget::item:hover {{ background: {hover}; }}
        QTableWidget::item:selected:hover, QListWidget::item:selected:hover {{ background: {selected}; }}
        QLabel#video {{ background: #111e1a; color: #c6ddd4; border-radius: 8px; padding: 8px; }}
        QLabel#error {{ color: {danger}; }}
        QMenu {{ color: {text}; background: {surface}; border: 1px solid {border}; padding: 4px; }}
        QMenu::item {{ padding: 6px 24px; border-radius: 4px; }}
        QMenu::item:selected {{ background: {selected}; }}
        QMenu::item:disabled {{ color: {muted}; }}
        QMenu::separator {{ height: 1px; background: {border}; margin: 4px 6px; }}
        QToolTip {{ color: {text}; background: {surface}; border: 1px solid {border}; padding: 6px; }}
        QSplitter::handle {{ background: {canvas}; }}
        QSplitter::handle:hover {{ background: {border}; }}
        QStatusBar {{ color: {muted}; background: {canvas}; }}
    """
