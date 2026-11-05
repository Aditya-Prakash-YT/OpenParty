import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QFileDialog, QFrame,
                               QFormLayout, QMessageBox, QGroupBox, QStyle)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QDragEnterEvent, QDropEvent
from config.loader import load_party_file, load_party_string, PartyFileError, PartyConfig
import errors

class JoinPartyWidget(QWidget):
    back_requested = Signal()
    party_loaded = Signal(object) # Emit config when Start Party clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.loaded_config = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(18)
        
        # Header
        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.setFixedWidth(80)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        
        title_box = QVBoxLayout()
        title = QLabel("Join Watch Party")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #25323B;")
        subtitle = QLabel("Open a party configuration file or paste invite data from a host.")
        subtitle.setStyleSheet("font-size: 13px; color: #65747E;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        
        header_layout.addWidget(self.btn_back)
        header_layout.addSpacing(10)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)
        
        # Input Section (Drag & Drop Zone + Buttons)
        self.input_frame = QFrame()
        self.input_frame.setStyleSheet(
            "QFrame { border: 1px dashed #C8D2D8; border-radius: 10px; background-color: #F8FAFB; padding: 20px; }"
        )
        input_layout = QVBoxLayout(self.input_frame)
        input_layout.setSpacing(12)
        
        lbl_drag = QLabel("Drag and drop an .oparty file here, or choose an option below:")
        lbl_drag.setAlignment(Qt.AlignCenter)
        lbl_drag.setStyleSheet("font-size: 13px; font-weight: 500; color: #65747E; border: none; background: transparent;")
        input_layout.addWidget(lbl_drag)
        
        btn_row = QHBoxLayout()
        self.btn_open_file = QPushButton("Browse File...")
        self.btn_open_file.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_open_file.setMinimumHeight(36)
        self.btn_open_file.setCursor(Qt.PointingHandCursor)
        self.btn_open_file.setStyleSheet(
            "QPushButton { background-color: #3E6478; color: white; font-weight: 600; border-radius: 8px; padding: 6px 16px; border: none; }"
            "QPushButton:hover { background-color: #345668; }"
        )
        
        self.btn_paste_clipboard = QPushButton("Paste from Clipboard")
        self.btn_paste_clipboard.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.btn_paste_clipboard.setMinimumHeight(36)
        self.btn_paste_clipboard.setCursor(Qt.PointingHandCursor)
        self.btn_paste_clipboard.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #35434C; font-weight: 500; border: 1px solid #DDE4E8; border-radius: 8px; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #F1F4F6; }"
        )
        btn_row.addWidget(self.btn_open_file)
        btn_row.addWidget(self.btn_paste_clipboard)
        input_layout.addLayout(btn_row)
        
        # Expandable manual paste box
        self.btn_toggle_text = QPushButton("Enter party data manually...")
        self.btn_toggle_text.setFlat(True)
        self.btn_toggle_text.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_text.setStyleSheet("color: #72808A; font-size: 12px; border: none; background: transparent;")
        input_layout.addWidget(self.btn_toggle_text, alignment=Qt.AlignCenter)
        
        self.text_paste = QTextEdit()
        self.text_paste.setPlaceholderText("Paste party JSON or invite code here...")
        self.text_paste.setMaximumHeight(90)
        self.text_paste.setStyleSheet("border: 1px solid #DDE4E8; border-radius: 8px; background-color: white; font-family: Consolas, monospace;")
        self.text_paste.hide()
        input_layout.addWidget(self.text_paste)
        
        self.btn_load_text = QPushButton("Load Pasted Text")
        self.btn_load_text.setMinimumHeight(32)
        self.btn_load_text.hide()
        input_layout.addWidget(self.btn_load_text)
        
        self.main_layout.addWidget(self.input_frame)
        
        # Error Label
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(
            "color: #884949; background-color: #FAF1F1; border: 1px solid #E8C9C9; border-radius: 8px; padding: 10px; font-size: 13px;"
        )
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        self.main_layout.addWidget(self.lbl_error)
        
        # Details Panel (Party Summary Card)
        self.details_frame = QFrame()
        self.details_frame.setStyleSheet(
            "QFrame { background-color: #F8FAFB; border: 1px solid #DDE4E8; border-radius: 9px; padding: 14px; }"
            "QLabel { background-color: transparent; border: none; }"
        )
        details_layout = QVBoxLayout(self.details_frame)
        details_layout.setSpacing(10)
        
        card_header = QHBoxLayout()
        self.lbl_details_title = QLabel("Party Details")
        self.lbl_details_title.setStyleSheet("font-weight: 600; font-size: 15px; color: #25323B;")
        card_header.addWidget(self.lbl_details_title)
        card_header.addStretch()
        details_layout.addLayout(card_header)
        
        self.form_details = QFormLayout()
        self.form_details.setSpacing(6)
        
        self.val_name = QLabel("")
        self.val_host = QLabel("")
        self.val_media = QLabel("")
        self.val_room = QLabel("")
        self.val_server = QLabel("")
        
        for lbl in (self.val_name, self.val_host, self.val_media, self.val_room, self.val_server):
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl.setStyleSheet("font-weight: 500; color: #35434C; font-size: 13px;")
        
        self.form_details.addRow("Party Name:", self.val_name)
        self.form_details.addRow("Host:", self.val_host)
        self.form_details.addRow("Media:", self.val_media)
        self.form_details.addRow("Sync Room:", self.val_room)
        self.form_details.addRow("Server:", self.val_server)
        
        details_layout.addLayout(self.form_details)
        
        self.btn_start = QPushButton("Start Watching")
        self.btn_start.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_start.setMinimumHeight(42)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #3E6478; color: white; font-size: 14px; font-weight: 600; border-radius: 8px; border: none; }"
            "QPushButton:hover { background-color: #345668; }"
        )
        details_layout.addWidget(self.btn_start)
        
        self.details_frame.hide()
        self.main_layout.addWidget(self.details_frame)
        self.main_layout.addStretch()

    def _connect_signals(self):
        self.btn_back.clicked.connect(self._on_back)
        self.btn_open_file.clicked.connect(self._on_open_file)
        self.btn_paste_clipboard.clicked.connect(self._on_paste_clipboard)
        self.btn_toggle_text.clicked.connect(self._toggle_text_box)
        self.btn_load_text.clicked.connect(self._on_load_text)
        self.btn_start.clicked.connect(self._on_start)

    def _toggle_text_box(self):
        if self.text_paste.isVisible():
            self.text_paste.hide()
            self.btn_load_text.hide()
            self.btn_toggle_text.setText("Enter party data manually...")
        else:
            self.text_paste.show()
            self.btn_load_text.show()
            self.btn_toggle_text.setText("Hide manual input...")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                self.load_file(file_path)

    def load_file(self, file_path: str):
        """Public method to load a party file directly (e.g. from CLI)."""
        if not os.path.exists(file_path):
            self._show_error(errors.err_party_file_not_found(file_path))
            return False
        try:
            config = load_party_file(file_path)
            self._show_details(config)
            return True
        except PartyFileError as e:
            self._show_error(errors.err_party_file_corrupt(str(e)))
            return False

    def _on_back(self):
        self.details_frame.hide()
        self.lbl_error.hide()
        self.text_paste.clear()
        self.loaded_config = None
        self.back_requested.emit()

    def _on_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Party File", "", "OpenParty Files (*.oparty);;All Files (*.*)"
        )
        if file_path:
            self.load_file(file_path)

    def _on_paste_clipboard(self):
        cb = QGuiApplication.clipboard()
        text = cb.text().strip()
        if not text:
            self._show_error(errors.format_error(
                "Clipboard is empty.",
                "No text was found on the clipboard.",
                "Copy the party invite or file content from your message app first."
            ))
            return
        
        self.load_text_data(text)

    def _on_load_text(self):
        text = self.text_paste.toPlainText().strip()
        if not text:
            self._show_error(errors.format_error(
                "No data to load.",
                "The text box is empty.",
                "Paste the party data into the text box first."
            ))
            return
        self.load_text_data(text)

    def load_text_data(self, text: str):
        try:
            config = load_party_string(text)
            self._show_details(config)
        except PartyFileError as e:
            self._show_error(errors.err_party_file_corrupt(str(e)))

    def _show_error(self, msg: str):
        self.details_frame.hide()
        self.lbl_error.setText(msg)
        self.lbl_error.show()

    def _show_details(self, config: PartyConfig):
        self.loaded_config = config
        self.lbl_error.hide()

        self.val_name.setText(config.party.name)
        host = getattr(config.party, 'created_by', '') or "Host"
        self.val_host.setText(host)

        media_name = config.media.file.name_hint or "Movie file"
        size_bytes = config.media.file.size
        if size_bytes and size_bytes > 0:
            if size_bytes >= 1024**3:
                size_str = f" ({size_bytes / 1024**3:.2f} GB)"
            else:
                size_str = f" ({size_bytes / 1024**2:.1f} MB)"
            media_name += size_str
        self.val_media.setText(media_name)

        self.val_room.setText(config.sync.room)
        self.val_server.setText(f"{config.sync.server}:{config.sync.port}")

        self.details_frame.show()

    def _on_start(self):
        if self.loaded_config:
            self.party_loaded.emit(self.loaded_config)
