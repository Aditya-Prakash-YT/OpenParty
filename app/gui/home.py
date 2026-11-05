"""Home screen and required dependency status for OpenParty."""

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QCommandLinkButton,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from deps import check_dependencies
from logger import launcher_logger


class HomeWidget(QWidget):
    """Home screen UI; emits user intent for the application window to handle."""

    create_requested = Signal()
    join_requested = Signal()
    setup_requested = Signal()
    help_requested = Signal()
    logs_requested = Signal()

    _TOOL_LABELS = {
        "vlc": "VLC Media Player (media playback)",
        "syncplay": "Syncplay (playback synchronization)",
        "aria2c": "aria2c (download engine)",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh_dependencies()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 36, 48, 30)
        layout.setSpacing(22)

        header = QVBoxLayout()
        header.setSpacing(6)
        eyebrow = QLabel("WATCH TOGETHER, SIMPLY")
        eyebrow.setStyleSheet(
            "font-size: 10px; font-weight: 700; letter-spacing: 1.4px; color: #72808A;"
        )
        eyebrow.setAlignment(Qt.AlignCenter)
        header.addWidget(eyebrow)

        title = QLabel("OpenParty")
        title.setStyleSheet("font-size: 30px; font-weight: 700; color: #25323B;")
        title.setAlignment(Qt.AlignCenter)
        header.addWidget(title)

        subtitle = QLabel("Synchronized movie playback for watch parties.")
        subtitle.setStyleSheet("font-size: 13px; color: #65747E;")
        subtitle.setAlignment(Qt.AlignCenter)
        header.addWidget(subtitle)
        layout.addLayout(header)

        self.dependency_layout = QVBoxLayout()
        self.dependency_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.dependency_layout)

        actions = QVBoxLayout()
        actions.setContentsMargins(0, 10, 0, 10)
        actions.setSpacing(12)
        self.btn_join = self._make_action(
            "Join a Watch Party",
            "Open a party invite file (.oparty) or paste invite data from a friend.",
            QStyle.SP_MediaPlay,
        )
        self.btn_join.clicked.connect(self.join_requested.emit)
        actions.addWidget(self.btn_join)

        self.btn_create = self._make_action(
            "Host a Watch Party",
            "Select a local video file or enter a magnet link to invite friends.",
            QStyle.SP_FileDialogStart,
        )
        self.btn_create.clicked.connect(self.create_requested.emit)
        actions.addWidget(self.btn_create)
        layout.addLayout(actions)
        layout.addStretch()

        footer = QHBoxLayout()
        self.btn_help = self._make_footer_button(
            "How It Works", QStyle.SP_MessageBoxInformation, self.help_requested
        )
        footer.addWidget(self.btn_help)
        footer.addStretch()
        self.btn_logs = self._make_footer_button(
            "View Logs", QStyle.SP_FileDialogDetailedView, self.logs_requested
        )
        footer.addWidget(self.btn_logs)
        layout.addLayout(footer)

    def _make_action(self, title: str, description: str, icon):
        button = QCommandLinkButton(title, description)
        button.setIcon(self.style().standardIcon(icon))
        button.setIconSize(QSize(24, 24))
        button.setMinimumHeight(84)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(
            "QCommandLinkButton { padding: 14px 18px; border: 1px solid #DDE4E8; "
            "border-radius: 12px; background-color: #FFFFFF; }"
            "QCommandLinkButton:hover { background-color: #F8FAFB; border-color: #BCC9D0; }"
            "QCommandLinkButton:disabled { color: #98A3AA; background-color: #F5F7F8; }"
        )
        return button

    def _make_footer_button(self, title, icon, signal):
        button = QPushButton(title)
        button.setIcon(self.style().standardIcon(icon))
        button.setFlat(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet("color: #65747E; font-size: 12px; font-weight: 500;")
        button.clicked.connect(signal.emit)
        return button

    def refresh_dependencies(self):
        """Refresh the status banner and gate workflows on required tools."""
        dependencies = check_dependencies()
        all_found = all(dependencies.values())
        self.btn_join.setEnabled(all_found)
        self.btn_create.setEnabled(all_found)
        self._clear_dependency_status()

        if all_found:
            launcher_logger.info("All dependencies found.")
            self.dependency_layout.addWidget(self._success_banner())
        else:
            missing = [name for name, found in dependencies.items() if not found]
            launcher_logger.warning("Missing dependencies: %s", dependencies)
            self.dependency_layout.addWidget(self._missing_banner(dependencies, missing))

    def _clear_dependency_status(self):
        while self.dependency_layout.count():
            item = self.dependency_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _success_banner(self):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #F8FAFB; border: 1px solid #E6ECEF; "
            "border-radius: 9px; padding: 4px 10px; }"
            "QLabel { color: #3F4E57; font-size: 12px; font-weight: 500; "
            "border: none; background: transparent; }"
        )
        row = QHBoxLayout(frame)
        row.setContentsMargins(6, 4, 6, 4)
        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(QStyle.SP_DialogApplyButton).pixmap(14, 14))
        row.addWidget(icon)
        row.addWidget(QLabel("System check passed: VLC, Syncplay, and aria2c are ready."))
        row.addStretch()
        return frame

    def _missing_banner(self, dependencies, missing):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #FAF7F0; border: 1px solid #E8DDBB; "
            "border-radius: 9px; padding: 12px; }"
            "QLabel { border: none; background: transparent; }"
        )
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxWarning).pixmap(18, 18))
        title_row.addWidget(icon)
        title = QLabel("Required software components are missing:")
        title.setStyleSheet("font-weight: 600; color: #6F5738; font-size: 13px;")
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        for name, found in dependencies.items():
            row = QHBoxLayout()
            status = QStyle.SP_DialogApplyButton if found else QStyle.SP_DialogCancelButton
            icon = QLabel()
            icon.setPixmap(self.style().standardIcon(status).pixmap(14, 14))
            row.addWidget(icon)
            description = QLabel(self._TOOL_LABELS.get(name, name.capitalize()))
            description.setStyleSheet("font-size: 12px; color: #35434C;")
            row.addWidget(description)
            row.addStretch()
            layout.addLayout(row)

        buttons = QHBoxLayout()
        setup = QPushButton("Run Setup")
        setup.setIcon(self.style().standardIcon(QStyle.SP_DesktopIcon))
        setup.setCursor(Qt.PointingHandCursor)
        setup.setStyleSheet(
            "QPushButton { background-color: #8B6D43; color: white; font-weight: 600; "
            "padding: 6px 14px; border-radius: 8px; border: none; }"
            "QPushButton:hover { background-color: #725839; }"
        )
        setup.clicked.connect(self.setup_requested.emit)
        recheck = QPushButton("Check Again")
        recheck.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        recheck.setCursor(Qt.PointingHandCursor)
        recheck.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #35434C; font-weight: 500; "
            "padding: 6px 14px; border: 1px solid #D4DDE2; border-radius: 8px; }"
            "QPushButton:hover { background-color: #F1F4F6; }"
        )
        recheck.clicked.connect(self.refresh_dependencies)
        buttons.addWidget(setup)
        buttons.addWidget(recheck)
        buttons.addStretch()
        layout.addLayout(buttons)
        return frame
