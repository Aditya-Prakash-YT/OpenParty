import json
import random
import string
import datetime
import os
import urllib.parse
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QMessageBox, QFormLayout, 
                               QScrollArea, QFileDialog, QRadioButton, QButtonGroup,
                               QFrame, QGroupBox, QStyle)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication

from config.loader import load_party_string, PartyFileError
from gui.torrent_worker import TorrentWorker

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

class CreatePartyWidget(QWidget):
    back_requested = Signal()
    party_start_requested = Signal(object, str)  # (config, local_media_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._torrent_worker = None
        self._created_torrent_path = None
        self._local_file_path = None
        self._p2p_invite = None
        self._setup_ui()
        self._connect_signals()
        self._validate_live()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.setFixedWidth(80)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        
        title_box = QVBoxLayout()
        title = QLabel("Create Watch Party")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #25323B;")
        subtitle = QLabel("Configure a movie session and generate an invite for your guests.")
        subtitle.setStyleSheet("font-size: 13px; color: #65747E;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        
        header_layout.addWidget(self.btn_back)
        header_layout.addSpacing(10)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)
        
        # Scroll Area for Form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(14)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        
        # 1. Media Source Card
        source_frame = QFrame()
        source_frame.setStyleSheet(
            "QFrame { background-color: #F8FAFB; border: 1px solid #E6ECEF; border-radius: 9px; padding: 12px; }"
            "QLabel { background: transparent; border: none; }"
        )
        source_layout = QVBoxLayout(source_frame)
        source_layout.setSpacing(10)
        
        lbl_source_title = QLabel("1. Select Media")
        lbl_source_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #35434C;")
        source_layout.addWidget(lbl_source_title)
        
        # Radio toggle: File vs Magnet
        toggle_layout = QHBoxLayout()
        self.radio_file = QRadioButton("Select a local video file")
        self.radio_magnet = QRadioButton("Use an existing magnet link")
        self.radio_file.setChecked(True)
        self.radio_file.setCursor(Qt.PointingHandCursor)
        self.radio_magnet.setCursor(Qt.PointingHandCursor)
        
        self.source_btn_group = QButtonGroup(self)
        self.source_btn_group.addButton(self.radio_file)
        self.source_btn_group.addButton(self.radio_magnet)
        
        toggle_layout.addWidget(self.radio_file)
        toggle_layout.addWidget(self.radio_magnet)
        toggle_layout.addStretch()
        source_layout.addLayout(toggle_layout)
        
        # Local File picker section
        self.file_section = QWidget()
        file_sec_layout = QHBoxLayout(self.file_section)
        file_sec_layout.setContentsMargins(0, 4, 0, 4)
        
        self.btn_choose_file = QPushButton("Browse Video File...")
        self.btn_choose_file.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_choose_file.setMinimumHeight(36)
        self.btn_choose_file.setCursor(Qt.PointingHandCursor)
        self.btn_choose_file.setStyleSheet(
            "QPushButton { background-color: #3E6478; color: white; font-weight: 600; border-radius: 8px; padding: 6px 14px; border: none; }"
            "QPushButton:hover { background-color: #345668; }"
        )
        self.lbl_selected_file = QLabel("No file selected.")
        self.lbl_selected_file.setStyleSheet("color: #72808A; font-size: 13px;")
        self.lbl_selected_file.setWordWrap(True)
        
        file_sec_layout.addWidget(self.btn_choose_file)
        file_sec_layout.addWidget(self.lbl_selected_file, 1)
        source_layout.addWidget(self.file_section)
        
        # Torrent Status Label
        self.lbl_torrent_status = QLabel("")
        self.lbl_torrent_status.setStyleSheet("font-size: 12px; color: #365F50; font-weight: 500;")
        self.lbl_torrent_status.setWordWrap(True)
        self.lbl_torrent_status.hide()
        source_layout.addWidget(self.lbl_torrent_status)
        
        # Magnet link section
        self.magnet_section = QWidget()
        magnet_sec_layout = QVBoxLayout(self.magnet_section)
        magnet_sec_layout.setContentsMargins(0, 4, 0, 4)
        
        self.source_value_input = QLineEdit()
        self.source_value_input.setPlaceholderText("magnet:?xt=urn:btih:...")
        self.source_value_input.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; padding: 6px;")
        magnet_sec_layout.addWidget(self.source_value_input)
        
        source_layout.addWidget(self.magnet_section)
        self.magnet_section.hide()
        
        scroll_layout.addWidget(source_frame)
        
        # 2. Party Details Card
        details_frame = QFrame()
        details_frame.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E6ECEF; border-radius: 9px; padding: 12px; }"
            "QLabel { background: transparent; border: none; }"
        )
        details_layout = QVBoxLayout(details_frame)
        details_layout.setSpacing(10)
        
        lbl_details_sec = QLabel("2. Party Information")
        lbl_details_sec.setStyleSheet("font-size: 14px; font-weight: 600; color: #35434C;")
        details_layout.addWidget(lbl_details_sec)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Movie Night")
        self.name_input.setStyleSheet("padding: 6px;")
        form_layout.addRow("Party Name *:", self.name_input)
        
        self.created_by_input = QLineEdit()
        self.created_by_input.setPlaceholderText("(Optional) Host name")
        self.created_by_input.setStyleSheet("padding: 6px;")
        form_layout.addRow("Host Name:", self.created_by_input)
        
        details_layout.addLayout(form_layout)
        scroll_layout.addWidget(details_frame)
        
        # 3. Advanced Settings (Collapsible)
        self.adv_group = QGroupBox("Advanced Settings (Optional)")
        self.adv_group.setCheckable(True)
        self.adv_group.setChecked(False)
        self.adv_group.setStyleSheet(
            "QGroupBox { font-weight: 600; color: #65747E; border: 1px solid #DDE4E8; border-radius: 9px; margin-top: 10px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
        )
        
        adv_form = QFormLayout(self.adv_group)
        adv_form.setSpacing(8)
        
        self.server_input = QLineEdit()
        self.server_input.setText("syncplay.pl:8997")
        adv_form.addRow("Syncplay Server:", self.server_input)
        
        self.room_input = QLineEdit()
        self.room_input.setText(generate_random_string())
        room_row = QHBoxLayout()
        room_row.addWidget(self.room_input)
        self.btn_rand_room = QPushButton("Randomize")
        self.btn_rand_room.setCursor(Qt.PointingHandCursor)
        room_row.addWidget(self.btn_rand_room)
        adv_form.addRow("Room Name:", room_row)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("(Optional) Room password")
        pass_row = QHBoxLayout()
        pass_row.addWidget(self.password_input)
        self.btn_rand_pass = QPushButton("Randomize")
        self.btn_rand_pass.setCursor(Qt.PointingHandCursor)
        pass_row.addWidget(self.btn_rand_pass)
        adv_form.addRow("Password:", pass_row)
        
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("(Optional) Party description or notes")
        adv_form.addRow("Description:", self.description_input)
        
        self.subtitle_input = QLineEdit()
        self.subtitle_input.setPlaceholderText("https://... (Optional subtitle URL)")
        adv_form.addRow("Subtitle URL:", self.subtitle_input)

        self.public_host_input = QLineEdit()
        self.public_host_input.setPlaceholderText(
            "Optional public IPv4; auto-detected when blank"
        )
        self.public_host_input.setToolTip(
            "For friends outside your network, forward TCP 51413 and 51414 to this PC. "
            "Leave blank to let OpenParty detect your public IPv4."
        )
        adv_form.addRow("Remote host IP:", self.public_host_input)
        
        # Hidden metadata fields populated automatically
        self.name_hint_input = QLineEdit()
        self.size_input = QLineEdit()
        self.hash_input = QLineEdit()
        
        scroll_layout.addWidget(self.adv_group)
        
        scroll_area.setWidget(scroll_widget)
        self.main_layout.addWidget(scroll_area)
        
        # Validation / Note message
        self.lbl_note = QLabel("")
        self.lbl_note.setStyleSheet("font-size: 12px; color: #65747E;")
        self.lbl_note.setWordWrap(True)
        self.main_layout.addWidget(self.lbl_note)
        
        # Action Buttons
        actions_layout = QHBoxLayout()
        
        self.btn_start_party = QPushButton("Start Watch Party")
        self.btn_start_party.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_start_party.setMinimumHeight(40)
        self.btn_start_party.setCursor(Qt.PointingHandCursor)
        self.btn_start_party.setStyleSheet(
            "QPushButton { background-color: #3E6478; color: white; font-size: 14px; font-weight: 600; border-radius: 8px; border: none; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #345668; }"
            "QPushButton:disabled { background-color: #98A4AA; }"
        )
        
        self.btn_export = QPushButton("Save Party File (.oparty)")
        self.btn_export.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_export.setMinimumHeight(40)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #35434C; font-size: 14px; font-weight: 600; border-radius: 8px; border: 1px solid #D7E0E4; padding: 6px 14px; }"
            "QPushButton:hover { background-color: #F1F4F6; border-color: #BCC9D0; }"
            "QPushButton:disabled { background-color: #98A4AA; }"
        )
        
        self.btn_copy = QPushButton("Copy to Clipboard")
        self.btn_copy.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.btn_copy.setMinimumHeight(40)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setStyleSheet(
            "QPushButton { background-color: #F1F4F6; color: #35434C; font-size: 13px; font-weight: 500; border: 1px solid #DDE4E8; border-radius: 8px; padding: 6px 14px; }"
            "QPushButton:hover { background-color: #E6ECEF; }"
            "QPushButton:disabled { background-color: #F8FAFB; color: #98A4AA; }"
        )
        
        actions_layout.addWidget(self.btn_start_party, 2)
        actions_layout.addWidget(self.btn_export, 2)
        actions_layout.addWidget(self.btn_copy, 1)
        self.main_layout.addLayout(actions_layout)

    def _connect_signals(self):
        self.btn_back.clicked.connect(self.back_requested.emit)
        self.radio_file.toggled.connect(self._on_source_type_changed)
        self.radio_magnet.toggled.connect(self._on_source_type_changed)
        
        self.btn_choose_file.clicked.connect(self._on_choose_file)
        self.btn_rand_room.clicked.connect(lambda: self.room_input.setText(generate_random_string()))
        self.btn_rand_pass.clicked.connect(lambda: self.password_input.setText(generate_random_string(8)))
        
        self.name_input.textChanged.connect(self._validate_live)
        self.source_value_input.textChanged.connect(self._validate_live)
        self.room_input.textChanged.connect(self._validate_live)
        self.server_input.textChanged.connect(self._validate_live)
        self.password_input.textChanged.connect(self._validate_live)
        self.public_host_input.textChanged.connect(self._validate_live)
        
        self.btn_start_party.clicked.connect(self._on_start_party)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_copy.clicked.connect(self._on_copy)

    def _on_source_type_changed(self):
        if self.radio_file.isChecked():
            self.file_section.show()
            self.magnet_section.hide()
        else:
            self.file_section.hide()
            self.magnet_section.show()
        self._validate_live()

    def _on_choose_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.flv);;All Files (*.*)"
        )
        if not file_path:
            return

        self._local_file_path = file_path
        # Clear metadata from a previously selected file before starting the
        # background hash. If this selection fails, the old magnet must not
        # remain available paired with the newly selected local path.
        self.source_value_input.clear()
        self.name_hint_input.clear()
        self.size_input.clear()
        self._created_torrent_path = None
        self._p2p_invite = None
        file_name = os.path.basename(file_path)
        self.lbl_selected_file.setText(f"Selected: <b>{file_name}</b>")
        
        if not self.name_input.text().strip():
            clean_name = os.path.splitext(file_name)[0].replace(".", " ").replace("_", " ")
            self.name_input.setText(clean_name)
            
        self.btn_choose_file.setEnabled(False)
        self.btn_choose_file.setText("Preparing Torrent...")
        self.radio_file.setEnabled(False)
        self.radio_magnet.setEnabled(False)
        self.lbl_torrent_status.setStyleSheet("font-size: 12px; color: #65747E;")
        self.lbl_torrent_status.setText("Hashing file and generating torrent...")
        self.lbl_torrent_status.show()

        self._torrent_worker = TorrentWorker(
            file_path,
            public_host=self.public_host_input.text().strip(),
            parent=self,
        )
        self._torrent_worker.status_update.connect(self._on_torrent_status)
        self._torrent_worker.finished_ok.connect(self._on_torrent_ok)
        self._torrent_worker.finished_err.connect(self._on_torrent_err)
        self._torrent_worker.start()

    def _on_torrent_status(self, msg: str):
        clean_msg = msg.replace("\u2714", "").replace("\u2718", "").strip()
        self.lbl_torrent_status.setText(clean_msg)

    def _on_torrent_ok(self, magnet: str, file_name: str, file_size: int,
                       torrent_path: str = "", p2p_invite=None):
        self.source_value_input.setText(magnet)
        self.name_hint_input.setText(file_name)
        self.size_input.setText(str(file_size))
        self._created_torrent_path = torrent_path
        self._p2p_invite = p2p_invite if isinstance(p2p_invite, dict) else None

        self.btn_choose_file.setEnabled(True)
        self.btn_choose_file.setText("Change Video File...")
        self.radio_file.setEnabled(True)
        self.radio_magnet.setEnabled(True)
        seed_status = getattr(self._torrent_worker, "seed_status", "")
        if "could not be started" in seed_status:
            self.lbl_torrent_status.setStyleSheet("font-size: 12px; color: #A85D5D; font-weight: 500;")
            self.lbl_torrent_status.setText(seed_status)
        elif "not confirmed" in seed_status or "Confirm its status" in seed_status:
            self.lbl_torrent_status.setStyleSheet("font-size: 12px; color: #725839; font-weight: 500;")
            self.lbl_torrent_status.setText(seed_status)
        else:
            self.lbl_torrent_status.setStyleSheet("font-size: 12px; color: #365F50; font-weight: 500;")
            self.lbl_torrent_status.setText(seed_status or "Media prepared successfully. Ready to share.")
        self.lbl_torrent_status.show()
        self._validate_live()

    def _on_torrent_err(self, err_msg: str):
        self.btn_choose_file.setEnabled(True)
        self.btn_choose_file.setText("Browse Video File...")
        self.radio_file.setEnabled(True)
        self.radio_magnet.setEnabled(True)
        self.lbl_torrent_status.setStyleSheet("font-size: 12px; color: #A85D5D;")
        self.lbl_torrent_status.setText(f"Error: {err_msg}")
        self.lbl_torrent_status.show()
        self._validate_live()

    def _generate_json(self) -> str:
        srv_text = self.server_input.text().strip() or "syncplay.pl:8997"
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
                "name": self.name_input.text().strip() or "Watch Party",
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
                "room": self.room_input.text().strip() or generate_random_string(),
                "password": self.password_input.text().strip()
            }
        }

        if self.radio_file.isChecked() and self._p2p_invite:
            data["media"]["p2p"] = self._p2p_invite
        
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
                    file_info["size"] = -1
            data["media"]["file"] = file_info
            
        sha256 = self.hash_input.text().strip()
        if sha256:
            data["integrity"] = {"sha256": sha256}
            
        return json.dumps(data, indent=4)

    def _validate_live(self):
        source_val = self.source_value_input.text().strip()
        party_name = self.name_input.text().strip()

        if not party_name:
            self.lbl_note.setText("Please enter a party name.")
            self.lbl_note.setStyleSheet("font-size: 12px; color: #72808A;")
            self.btn_start_party.setEnabled(False)
            self.btn_export.setEnabled(False)
            self.btn_copy.setEnabled(False)
            return

        if not source_val:
            if self.radio_file.isChecked():
                self.lbl_note.setText("Please select a video file.")
            else:
                self.lbl_note.setText("Please enter a magnet link.")
            self.lbl_note.setStyleSheet("font-size: 12px; color: #72808A;")
            self.btn_start_party.setEnabled(False)
            self.btn_export.setEnabled(False)
            self.btn_copy.setEnabled(False)
            return

        raw_json = self._generate_json()
        try:
            load_party_string(raw_json)
            self.lbl_note.setText("Configuration valid. Ready to export or start party.")
            self.lbl_note.setStyleSheet("font-size: 12px; color: #365F50; font-weight: 500;")
            can_start = True
            if self.radio_file.isChecked() and self._local_file_path:
                if not self._local_seed_is_ready():
                    can_start = False
                    self.lbl_note.setText(
                        "The invite is valid, but OpenParty has not confirmed an active seeder for this file. "
                        "Guests will be unable to download it yet."
                    )
                    self.lbl_note.setStyleSheet("font-size: 12px; color: #8A6A38; font-weight: 500;")
                else:
                    self.lbl_note.setText(
                        "Seeder is active. If remote guests cannot connect, forward TCP/UDP 51413-51420 "
                        "to this PC in your router settings."
                    )
            self.btn_start_party.setEnabled(can_start)
            self.btn_export.setEnabled(True)
            self.btn_copy.setEnabled(True)
        except PartyFileError as e:
            self.lbl_note.setText(f"Validation note: {str(e)}")
            self.lbl_note.setStyleSheet("font-size: 12px; color: #A85D5D;")
            self.btn_start_party.setEnabled(False)
            self.btn_export.setEnabled(False)
            self.btn_copy.setEnabled(False)

    def _local_seed_is_ready(self, *, require_rpc: bool = False) -> bool:
        if not self._local_file_path or not os.path.isfile(self._local_file_path):
            return False
        try:
            from torrent_creator import SeederManager
            query = urllib.parse.parse_qs(
                urllib.parse.urlsplit(self.source_value_input.text().strip()).query
            )
            xt = query.get("xt", [""])[0]
            info_hash = xt.partition(":")[-1].partition(":")[-1]
            active_path = SeederManager.get_current_file(info_hash)
            ready = bool(
                active_path and os.path.normcase(os.path.realpath(active_path)) ==
                os.path.normcase(os.path.realpath(self._local_file_path))
            )
            if not ready or not require_rpc:
                return ready
            activity = SeederManager.get_status()
            status = (activity or {}).get("status", {})
            return (
                str(status.get("infoHash", "")).lower() == info_hash.lower()
                and str(status.get("seeder", "false")).lower() == "true"
                and str(status.get("status", "")).lower() == "active"
            )
        except Exception:
            return False

    def _on_start_party(self):
        raw_json = self._generate_json()
        try:
            if self.radio_file.isChecked() and self._local_file_path and not self._local_seed_is_ready(require_rpc=True):
                QMessageBox.warning(
                    self,
                    "Seeder Not Ready",
                    "OpenParty cannot confirm that this file is being seeded. "
                    "Guests will not be able to download it until a seeder is running.",
                )
                return
            config = load_party_string(raw_json)
            local_path = ""
            if self.radio_file.isChecked() and self._local_file_path and os.path.isfile(self._local_file_path):
                local_path = self._local_file_path
            self.party_start_requested.emit(config, local_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start party:\n{e}")

    def _on_export(self):
        raw_json = self._generate_json()
        default_filename = f"{self.name_input.text().strip().replace(' ', '_')}.oparty"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Party File", default_filename, "OpenParty Files (*.oparty)"
        )
        if file_path:
            if not file_path.endswith(".oparty"):
                file_path += ".oparty"
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(raw_json)
                
                QGuiApplication.clipboard().setText(raw_json)
                
                QMessageBox.information(
                    self, "Party File Saved",
                    f"Party configuration saved to:\n{file_path}\n\n"
                    "The configuration data has also been copied to your clipboard.\n"
                    "Share this file with your guests to begin."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

    def _on_copy(self):
        raw_json = self._generate_json()
        cb = QGuiApplication.clipboard()
        cb.setText(raw_json)
        QMessageBox.information(
            self, "Copied to Clipboard",
            "Party invite data copied to clipboard.\n"
            "You can paste this directly to your participants."
        )
