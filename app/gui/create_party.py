import json
import random
import string
import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QMessageBox, QFormLayout, 
                               QScrollArea, QFileDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication

from config.loader import load_party_string, PartyFileError

def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

class CreatePartyWidget(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self._validate_live()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Back")
        self.btn_back.setFixedWidth(60)
        title = QLabel("Create Watch Party")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(self.btn_back)
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)
        
        # Scroll Area for Form (since we have many fields now)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_widget = QWidget()
        self.form_layout = QFormLayout(scroll_widget)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Friday Movie Night")
        self.form_layout.addRow("Party Name:", self.name_input)
        
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("(Optional) Bring popcorn")
        self.form_layout.addRow("Description:", self.description_input)
        
        self.created_by_input = QLineEdit()
        self.created_by_input.setPlaceholderText("(Optional) Your name")
        self.form_layout.addRow("Host Name:", self.created_by_input)
        
        self.source_value_input = QLineEdit()
        self.source_value_input.setPlaceholderText("magnet:?xt=...")
        self.form_layout.addRow("Magnet Link:", self.source_value_input)
        
        self.name_hint_input = QLineEdit()
        self.name_hint_input.setPlaceholderText("(Optional) Movie.2026.1080p.mkv")
        self.form_layout.addRow("File Name Hint:", self.name_hint_input)
        
        self.size_input = QLineEdit()
        self.size_input.setPlaceholderText("(Optional) Expected file size in bytes")
        self.form_layout.addRow("Expected Size:", self.size_input)
        
        self.hash_input = QLineEdit()
        self.hash_input.setPlaceholderText("(Optional) Expected SHA-256 hash")
        self.form_layout.addRow("Expected Hash:", self.hash_input)
        
        self.subtitle_input = QLineEdit()
        self.subtitle_input.setPlaceholderText("https://... (Optional)")
        self.form_layout.addRow("Subtitle URL:", self.subtitle_input)
        
        self.server_input = QLineEdit()
        self.server_input.setText("syncplay.pl:8997")
        self.form_layout.addRow("Syncplay Server:", self.server_input)
        
        self.room_input = QLineEdit()
        self.room_input.setText(generate_random_string())
        room_layout = QHBoxLayout()
        room_layout.addWidget(self.room_input)
        self.btn_rand_room = QPushButton("Random")
        room_layout.addWidget(self.btn_rand_room)
        self.form_layout.addRow("Room Name:", room_layout)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("(Optional)")
        pass_layout = QHBoxLayout()
        pass_layout.addWidget(self.password_input)
        self.btn_rand_pass = QPushButton("Random")
        pass_layout.addWidget(self.btn_rand_pass)
        self.form_layout.addRow("Password:", pass_layout)
        
        scroll_area.setWidget(scroll_widget)
        self.main_layout.addWidget(scroll_area)
        
        # Warnings & Errors
        self.lbl_warning = QLabel("Note: Without a password, anyone who knows the room name on this server can join.")
        self.lbl_warning.setStyleSheet("color: #d97706; font-size: 13px;")
        self.lbl_warning.setWordWrap(True)
        self.main_layout.addWidget(self.lbl_warning)
        
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #dc2626; font-weight: bold; font-size: 13px;")
        self.lbl_error.setWordWrap(True)
        self.main_layout.addWidget(self.lbl_error)
        
        # Actions
        actions_layout = QHBoxLayout()
        self.btn_export = QPushButton("Export to .oparty File")
        self.btn_copy = QPushButton("Copy to Clipboard")
        
        self.btn_export.setMinimumHeight(40)
        self.btn_copy.setMinimumHeight(40)
        
        actions_layout.addWidget(self.btn_export)
        actions_layout.addWidget(self.btn_copy)
        self.main_layout.addLayout(actions_layout)

    def _connect_signals(self):
        self.btn_back.clicked.connect(self.back_requested.emit)
        self.btn_rand_room.clicked.connect(lambda: self.room_input.setText(generate_random_string()))
        self.btn_rand_pass.clicked.connect(lambda: self.password_input.setText(generate_random_string(8)))
        
        self.name_input.textChanged.connect(self._validate_live)
        self.description_input.textChanged.connect(self._validate_live)
        self.created_by_input.textChanged.connect(self._validate_live)
        self.source_value_input.textChanged.connect(self._validate_live)
        self.name_hint_input.textChanged.connect(self._validate_live)
        self.size_input.textChanged.connect(self._validate_live)
        self.hash_input.textChanged.connect(self._validate_live)
        self.server_input.textChanged.connect(self._validate_live)
        self.room_input.textChanged.connect(self._validate_live)
        self.password_input.textChanged.connect(self._validate_live)
        self.subtitle_input.textChanged.connect(self._validate_live)
        
        self.btn_export.clicked.connect(self._on_export)
        self.btn_copy.clicked.connect(self._on_copy)

    def _generate_json(self) -> str:
        srv_text = self.server_input.text().strip()
        server = srv_text
        port = 8997
        if ":" in srv_text:
            parts = srv_text.rsplit(":", 1)
            server = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                pass
                
        subtitles = []
        if self.subtitle_input.text().strip():
            subtitles.append({"language": "Unknown", "url": self.subtitle_input.text().strip()})
            
        data = {
            "schema_version": 2,
            "party": {
                "name": self.name_input.text().strip(),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
            },
            "media": {
                "source": {
                    "type": "magnet",
                    "value": self.source_value_input.text().strip()
                },
                "subtitles": subtitles
            },
            "sync": {
                "server": server,
                "port": port,
                "room": self.room_input.text().strip(),
                "password": self.password_input.text().strip()
            }
        }
        
        desc = self.description_input.text().strip()
        if desc:
            data["party"]["description"] = desc
            
        host_name = self.created_by_input.text().strip()
        if host_name:
            data["party"]["created_by"] = host_name
        
        name_hint = self.name_hint_input.text().strip()
        size_txt = self.size_input.text().strip()
        
        if name_hint or size_txt:
            file_info = {}
            if name_hint:
                file_info["name_hint"] = name_hint
            if size_txt:
                try:
                    file_info["size"] = int(size_txt)
                except ValueError:
                    file_info["size"] = -1 # Forces a validation error natively by the loader
            data["media"]["file"] = file_info
            
        sha256 = self.hash_input.text().strip()
        if sha256:
            data["integrity"] = {"sha256": sha256}
            
        return json.dumps(data, indent=4)

    def _validate_live(self):
        if not self.password_input.text().strip():
            self.lbl_warning.show()
        else:
            self.lbl_warning.hide()
            
        raw_json = self._generate_json()
        try:
            load_party_string(raw_json)
            self.lbl_error.setText("")
            self.btn_export.setEnabled(True)
            self.btn_copy.setEnabled(True)
        except PartyFileError as e:
            self.lbl_error.setText(f"Wait: {str(e)}")
            self.btn_export.setEnabled(False)
            self.btn_copy.setEnabled(False)

    def _on_export(self):
        raw_json = self._generate_json()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Party File", "", "OpenParty Files (*.oparty)")
        if file_path:
            if not file_path.endswith(".oparty"):
                file_path += ".oparty"
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(raw_json)
                QMessageBox.information(self, "Success", f"Party file saved to:\n{file_path}\n\nYou can now share this file with your friends.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

    def _on_copy(self):
        raw_json = self._generate_json()
        cb = QGuiApplication.clipboard()
        cb.setText(raw_json)
        QMessageBox.information(self, "Copied", "Party data copied to clipboard. You can paste this directly to your friends in chat.")
