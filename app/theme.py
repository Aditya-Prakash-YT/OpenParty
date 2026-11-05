"""Shared visual theme for the OpenParty desktop interface."""

from PySide6.QtGui import QColor, QPalette


COLORS = {
    "background": "#F4F6F7",
    "surface": "#FFFFFF",
    "surface_soft": "#F8FAFB",
    "border": "#DDE4E8",
    "text": "#25323B",
    "muted": "#65747E",
    "accent": "#3E6478",
    "accent_hover": "#345668",
    "success": "#477564",
    "warning": "#8B6D43",
    "danger": "#A85D5D",
}


APP_STYLESHEET = """
QMainWindow, QDialog, QStackedWidget {
    background-color: #F4F6F7;
}
QWidget {
    color: #25323B;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}
QLabel {
    background: transparent;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    color: #25323B;
    background-color: #FFFFFF;
    border: 1px solid #DDE4E8;
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: #3E6478;
    selection-color: #FFFFFF;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover {
    border-color: #BCC9D0;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #3E6478;
}
QPushButton {
    color: #35434C;
    background-color: #FFFFFF;
    border: 1px solid #D7E0E4;
    border-radius: 8px;
    padding: 8px 14px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #F1F4F6;
    border-color: #BCC9D0;
}
QPushButton:pressed {
    background-color: #E8EEF1;
}
QPushButton:disabled {
    color: #98A4AA;
    background-color: #EEF1F2;
    border-color: #E2E7EA;
}
QPushButton:flat {
    background: transparent;
    border-color: transparent;
}
QPushButton:flat:hover {
    color: #345668;
    background-color: #E9EFF2;
}
QRadioButton {
    spacing: 8px;
    color: #35434C;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
QGroupBox {
    color: #52616A;
    font-weight: 600;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    width: 9px;
    margin: 2px;
    background: transparent;
}
QScrollBar::handle:vertical {
    min-height: 28px;
    background: #C8D2D8;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #AEBBC3;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    height: 0;
    background: transparent;
}
QProgressBar {
    color: #35434C;
    background-color: #E9EEF0;
    border: 1px solid #DDE4E8;
    border-radius: 7px;
    text-align: center;
    font-weight: 600;
}
QProgressBar::chunk {
    background-color: #587C8D;
    border-radius: 6px;
}
"""


def apply_theme(app):
    """Apply a restrained light palette and shared control styles."""
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(COLORS["background"]))
    palette.setColor(QPalette.Base, QColor(COLORS["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["surface_soft"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor(COLORS["surface"]))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLESHEET)
