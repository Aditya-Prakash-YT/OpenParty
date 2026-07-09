import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QFileDialog, QFrame,
                               QFormLayout, QMessageBox)
from PySide6.QtCore import Qt, Signal
from config.loader import load_party_file, load_party_string, PartyFileError, PartyConfig
import errors

class JoinPartyWidget(QWidget):
    back_requested = Signal()
    party_loaded = Signal(object) # Emit config when Start Party clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loaded_config = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Back")
        self.btn_back.setFixedWidth(60)
        title = QLabel("Join Watch Party")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(self.btn_back)
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)
        
        # Input Section
        self.input_frame = QFrame()
        input_layout = QVBoxLayout(self.input_frame)
        input_layout.setContentsMargins(0, 10, 0, 10)
        
        self.btn_open_file = QPushButton("Open .oparty File")
        self.btn_open_file.setMinimumHeight(40)
        input_layout.addWidget(self.btn_open_file)
        
        lbl_or = QLabel("— OR Paste Party Data below —")
        lbl_or.setAlignment(Qt.AlignCenter)
        lbl_or.setStyleSheet("color: #6b7280; margin: 10px 0;")
        input_layout.addWidget(lbl_or)
        
        self.text_paste = QTextEdit()
        self.text_paste.setPlaceholderText("Paste JSON here...")
        self.text_paste.setMaximumHeight(150)
        input_layout.addWidget(self.text_paste)
        
        self.btn_load_text = QPushButton("Load from Text")
        input_layout.addWidget(self.btn_load_text)
        
        self.main_layout.addWidget(self.input_frame)
        
        # Error Label
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #dc2626; font-weight: bold; font-size: 13px;")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        self.main_layout.addWidget(self.lbl_error)
        
        # Details Panel
        self.details_frame = QFrame()
        # Light gray background just to separate it visually
        self.details_frame.setStyleSheet("QFrame { background-color: #f3f4f6; border-radius: 8px; } QLabel { background-color: transparent; }")
        details_layout = QVBoxLayout(self.details_frame)
        
        self.lbl_details_title = QLabel("Party Details")
        self.lbl_details_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        details_layout.addWidget(self.lbl_details_title)
        
        self.form_details = QFormLayout()
        
        self.val_name = QLabel("")
        self.val_room = QLabel("")
        self.val_server = QLabel("")
        self.val_source = QLabel("")
        
        # Make values selectable
        for lbl in (self.val_name, self.val_room, self.val_server, self.val_source):
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl.setStyleSheet("font-weight: 500;")
        
        self.form_details.addRow("Party Name:", self.val_name)
        self.form_details.addRow("Room:", self.val_room)
        self.form_details.addRow("Server:", self.val_server)
        self.form_details.addRow("Media Source:", self.val_source)
        
        details_layout.addLayout(self.form_details)
        
        self.btn_start = QPushButton("Start Party")
        self.btn_start.setMinimumHeight(50)
        # We can't style background-color without breaking native styling sometimes, 
        # but let's give it a bold look.
        self.btn_start.setStyleSheet("font-size: 16px; font-weight: bold;")
        details_layout.addWidget(self.btn_start)
        
        self.details_frame.hide()
        self.main_layout.addWidget(self.details_frame)
        
        self.main_layout.addStretch()

    def _connect_signals(self):
        self.btn_back.clicked.connect(self._on_back)
        self.btn_open_file.clicked.connect(self._on_open_file)
        self.btn_load_text.clicked.connect(self._on_load_text)
        self.btn_start.clicked.connect(self._on_start)
        
    def _on_back(self):
        # Reset view when going back
        self.details_frame.hide()
        self.lbl_error.hide()
        self.text_paste.clear()
        self.loaded_config = None
        self.back_requested.emit()
        
    def _on_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Party File", "", "OpenParty Files (*.oparty);;All Files (*.*)")
        if file_path:
            if not os.path.exists(file_path):
                self._show_error(errors.err_party_file_not_found(file_path))
                return
            try:
                config = load_party_file(file_path)
                self._show_details(config)
            except PartyFileError as e:
                self._show_error(errors.err_party_file_corrupt(str(e)))
                
    def _on_load_text(self):
        text = self.text_paste.toPlainText().strip()
        if not text:
            self._show_error(errors.format_error(
                "No data to load.",
                "The text box is empty.",
                "Paste the party data (JSON) into the text box first."
            ))
            return
            
        try:
            config = load_party_string(text)
            self._show_details(config)
        except PartyFileError as e:
            self._show_error(errors.err_party_file_corrupt(str(e)))
            
    def _show_error(self, msg: str):
        self.details_frame.hide()
        self.lbl_error.setText(f"Error: {msg}")
        self.lbl_error.show()
        
    def _show_details(self, config: PartyConfig):
        self.loaded_config = config
        self.lbl_error.hide()
        
        self.val_name.setText(config.party.name)
        self.val_room.setText(config.sync.room)
        self.val_server.setText(f"{config.sync.server}:{config.sync.port}")
        
        source_val = config.media.source.value
        if len(source_val) > 50:
            source_val = source_val[:47] + "..."
        self.val_source.setText(f"[{config.media.source.type}] {source_val}")
        
        self.details_frame.show()
        
    def _on_start(self):
        if self.loaded_config:
            self.party_loaded.emit(self.loaded_config)
