"""
Reusable error display widget.

Shows structured error messages with Try Again / Start Over / View Logs buttons.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QStyle)
from PySide6.QtCore import Qt, Signal
from errors import open_log_folder


class ErrorPanel(QWidget):
    """
    Drop-in error panel. Shows structured error messages and action buttons.
    
    Signals:
        try_again  — user wants to retry the same step
        start_over — user wants to go back to the main menu
    """
    try_again = Signal()
    start_over = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(
            "background-color: #FAF1F1; border: 1px solid #E8C9C9; "
            "border-radius: 8px; padding: 14px; font-size: 13px; "
            "color: #884949; font-family: 'Segoe UI', sans-serif;"
        )
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setTextFormat(Qt.PlainText)
        layout.addWidget(self.lbl_error)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.btn_try_again = QPushButton("Try Again")
        self.btn_try_again.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_try_again.setMinimumHeight(34)
        self.btn_try_again.setCursor(Qt.PointingHandCursor)
        self.btn_try_again.clicked.connect(self.try_again.emit)
        btn_layout.addWidget(self.btn_try_again)
        
        self.btn_start_over = QPushButton("Start Over")
        self.btn_start_over.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_start_over.setMinimumHeight(34)
        self.btn_start_over.setCursor(Qt.PointingHandCursor)
        self.btn_start_over.clicked.connect(self.start_over.emit)
        btn_layout.addWidget(self.btn_start_over)
        
        self.btn_view_logs = QPushButton("View Logs")
        self.btn_view_logs.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_view_logs.setMinimumHeight(34)
        self.btn_view_logs.setCursor(Qt.PointingHandCursor)
        self.btn_view_logs.clicked.connect(open_log_folder)
        btn_layout.addWidget(self.btn_view_logs)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def show_error(self, message: str, show_try_again: bool = True):
        """Display the error. Optionally hide Try Again if retry makes no sense."""
        self.lbl_error.setText(message)
        self.btn_try_again.setVisible(show_try_again)
        self.show()

    def clear(self):
        self.lbl_error.setText("")
        self.hide()
