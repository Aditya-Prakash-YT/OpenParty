import os
import sys
import subprocess
import hashlib
import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QHBoxLayout, QFrame, QStyle)
from PySide6.QtCore import Qt, QTimer, QThread, Signal as QSignal

from config.loader import PartyConfig
from deps import find_vlc, find_syncplay
from gui.error_panel import ErrorPanel
from logger import launcher_logger
import errors

class _HashWorker(QThread):
    """Compute SHA-256 off the main thread so the UI stays responsive."""
    finished = QSignal(str)   # hex digest
    error    = QSignal(str)   # error message

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            sha256 = hashlib.sha256()
            with open(self.path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            self.finished.emit(sha256.hexdigest())
        except Exception as e:
            self.error.emit(str(e))


class LaunchWidget(QWidget):
    back_requested = QSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = None
        self.media_path = None
        self.process = None
        self.log_file = None
        self._hash_worker = None
        
        self.step_timer = QTimer()
        self.step_timer.timeout.connect(self._next_step)
        self.current_step = 0
        
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(32, 30, 32, 28)
        self.main_layout.setSpacing(20)
        
        self.lbl_title = QLabel("Starting Watch Party...")
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: 600; color: #25323B;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_title)
        
        # Checklist Card
        self.card = QFrame()
        self.card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E1E7EA; border-radius: 12px; padding: 22px; }"
            "QLabel { background: transparent; border: none; }"
        )
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setSpacing(12)
        
        self.check_layout = QVBoxLayout()
        self.check_layout.setSpacing(8)
        self.card_layout.addLayout(self.check_layout)
        
        # Status completion message
        self.lbl_success = QLabel("VLC and Syncplay are synchronized with your party.\nYou may minimize OpenParty or return to the main menu.")
        self.lbl_success.setStyleSheet("font-size: 13px; font-weight: 500; color: #365F50; padding-top: 6px;")
        self.lbl_success.setAlignment(Qt.AlignCenter)
        self.lbl_success.setWordWrap(True)
        self.lbl_success.hide()
        self.card_layout.addWidget(self.lbl_success)
        
        self.main_layout.addWidget(self.card)
        
        # Error panel
        self.error_panel = ErrorPanel()
        self.error_panel.try_again.connect(self._retry)
        self.error_panel.start_over.connect(self._start_over)
        self.main_layout.addWidget(self.error_panel)
        
        self.main_layout.addStretch()
        
        # Action buttons
        self.btn_layout = QHBoxLayout()
        self.btn_minimize = QPushButton("Minimize to Taskbar")
        self.btn_minimize.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))
        self.btn_minimize.setMinimumHeight(38)
        self.btn_minimize.setCursor(Qt.PointingHandCursor)
        self.btn_minimize.setStyleSheet(
            "QPushButton { background-color: #3E6478; color: white; font-weight: 600; border-radius: 8px; padding: 6px 16px; border: none; }"
            "QPushButton:hover { background-color: #345668; }"
        )
        self.btn_minimize.clicked.connect(self._on_minimize)
        self.btn_minimize.hide()
        
        self.btn_back = QPushButton("Return to Main Menu")
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.setMinimumHeight(38)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setStyleSheet(
            "QPushButton { background-color: #F1F4F6; color: #35434C; font-weight: 500; border: 1px solid #DDE4E8; border-radius: 8px; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #E6ECEF; }"
        )
        self.btn_back.clicked.connect(self._on_back)
        self.btn_back.hide()
        
        self.btn_layout.addWidget(self.btn_minimize)
        self.btn_layout.addWidget(self.btn_back)
        self.main_layout.addLayout(self.btn_layout)

    def _on_minimize(self):
        if self.window():
            self.window().showMinimized()

    def start_launch(self, config: PartyConfig, media_path: str):
        self.config = config
        self.media_path = media_path
        self.current_step = 0
        self.btn_back.hide()
        self.btn_minimize.hide()
        self.lbl_success.hide()
        self.lbl_title.setText("Starting Watch Party...")
        self.error_panel.clear()
        
        # Clear checklist
        for i in reversed(range(self.check_layout.count())): 
            widget = self.check_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                
        self.steps = [
            ("Verifying downloaded media", self._step_verify),
            ("Starting Syncplay engine", self._step_launch),
            ("Opening VLC media player", self._step_wait),
            ("Connecting to room", self._step_wait),
            ("Playback ready", self._step_ready)
        ]
        
        self.step_labels = []
        for text, _ in self.steps:
            lbl = QLabel(f"[  ] {text}")
            lbl.setStyleSheet("font-size: 13px; color: #72808A; font-family: Consolas, monospace;")
            self.check_layout.addWidget(lbl)
            self.step_labels.append(lbl)
            
        self.step_timer.start(800)
        
    def _next_step(self):
        if self.current_step > 0:
            prev_lbl = self.step_labels[self.current_step - 1]
            prev_text = self.steps[self.current_step - 1][0]
            prev_lbl.setText(f"[OK] {prev_text}")
            prev_lbl.setStyleSheet("font-size: 13px; color: #365F50; font-weight: 600; font-family: Consolas, monospace;")
            
        if self.current_step < len(self.steps):
            curr_lbl = self.step_labels[self.current_step]
            curr_text = self.steps[self.current_step][0]
            curr_lbl.setText(f"[..] {curr_text}...")
            curr_lbl.setStyleSheet("font-size: 13px; color: #25323B; font-weight: 600; font-family: Consolas, monospace;")
            
            func = self.steps[self.current_step][1]
            result = func()

            if result == "async":
                self.step_timer.stop()
                return

            if not result:
                self.step_timer.stop()
                curr_lbl.setText(f"[Failed] {curr_text}")
                curr_lbl.setStyleSheet("font-size: 13px; color: #A85D5D; font-weight: 600; font-family: Consolas, monospace;")
                return
                
            self.current_step += 1
        else:
            self.step_timer.stop()
            self.lbl_title.setText("Watch Party Started")
            self.lbl_success.show()
            self.btn_minimize.show()
            self.btn_back.show()

    def _resume_after_async(self, success: bool):
        if not success:
            curr_lbl = self.step_labels[self.current_step]
            curr_text = self.steps[self.current_step][0]
            curr_lbl.setText(f"[Failed] {curr_text}")
            curr_lbl.setStyleSheet("font-size: 13px; color: #A85D5D; font-weight: 600; font-family: Consolas, monospace;")
            return
        self.current_step += 1
        self.step_timer.start(800)

    def _step_verify(self):
        if not os.path.exists(self.media_path):
            msg = errors.err_media_file_missing()
            self.error_panel.show_error(msg, show_try_again=False)
            return False
            
        expected_size = self.config.media.file.size
        if expected_size is not None and expected_size > 0:
            try:
                actual_size = os.path.getsize(self.media_path)
            except OSError as e:
                msg = errors.log_and_format(
                    "Could not inspect the selected media file.",
                    str(e),
                    "Check that the file is accessible, then select it again.",
                    exc=e
                )
                self.error_panel.show_error(msg, show_try_again=False)
                return False
            if actual_size != expected_size:
                launcher_logger.error(
                    f"Media size mismatch: expected {expected_size}, got {actual_size}"
                )
                msg = errors.log_and_format(
                    "The selected media does not match the party details.",
                    f"Expected {expected_size} bytes but found {actual_size} bytes.",
                    "Select the original media file and create a new party invite."
                )
                self.error_panel.show_error(msg, show_try_again=False)
                return False
                
        expected_hash = self.config.integrity.sha256
        if expected_hash and expected_hash.strip():
            self._hash_worker = _HashWorker(self.media_path, parent=self)
            self._expected_hash = expected_hash.strip()
            self._hash_worker.finished.connect(self._on_hash_done)
            self._hash_worker.error.connect(self._on_hash_error)
            self._hash_worker.start()
            return "async"
                
        return True

    def _on_hash_done(self, digest: str):
        if digest.lower() != self._expected_hash.lower():
            msg = errors.err_integrity_failed()
            self.error_panel.show_error(msg, show_try_again=False)
            self._resume_after_async(False)
        else:
            self._resume_after_async(True)

    def _on_hash_error(self, err_msg: str):
        launcher_logger.error(f"Hash computation failed: {err_msg}")
        msg = errors.log_and_format(
            "Could not verify media integrity.",
            err_msg,
            "Check that the file is readable, then select it again."
        )
        self.error_panel.show_error(msg, show_try_again=False)
        self._resume_after_async(False)

    def _step_launch(self) -> bool:
        vlc_exe = find_vlc()
        syncplay_exe = find_syncplay()
        
        if not syncplay_exe:
            msg = errors.err_syncplay_missing()
            self.error_panel.show_error(msg, show_try_again=False)
            return False
            
        if not vlc_exe:
            msg = errors.err_vlc_missing()
            self.error_panel.show_error(msg, show_try_again=False)
            return False
            
        cmd = [
            syncplay_exe,
            "--no-store",
            "--host", f"{self.config.sync.server}:{self.config.sync.port}",
            "--room", self.config.sync.room,
            "--player-path", vlc_exe,
        ]
        
        if self.config.sync.password:
            cmd.extend(["--password", self.config.sync.password])
            
        cmd.append(self.media_path)
        
        try:
            from logger import LOG_DIR
            log_dir = LOG_DIR
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "syncplay.log")
            
            self.log_file = open(log_path, "a", encoding="utf-8")
            safe_cmd = list(cmd)
            if "--password" in safe_cmd:
                password_index = safe_cmd.index("--password") + 1
                if password_index < len(safe_cmd):
                    safe_cmd[password_index] = "<redacted>"
            self.log_file.write(
                f"\n--- Launching Syncplay ({time.ctime()}) ---\nCmd: {safe_cmd}\n"
            )
            self.log_file.flush()
            
            CREATE_NO_WINDOW = 0x08000000
            self.process = subprocess.Popen(
                cmd, 
                stdout=self.log_file, 
                stderr=subprocess.STDOUT
            )
            
            QTimer.singleShot(500, self._check_syncplay_early_exit)
            return True
        except Exception as e:
            launcher_logger.error(f"Syncplay launch failed: {e}")
            msg = errors.err_syncplay_crash()
            self.error_panel.show_error(msg)
            return False

    def _check_syncplay_early_exit(self):
        """Called 500ms after Syncplay launch — check if it died immediately."""
        if self.process and self.process.poll() is not None:
            if self.log_file:
                self.log_file.write(f"Process exited early with code {self.process.returncode}\n")
            launcher_logger.error(f"Syncplay exited early with code {self.process.returncode}")
            msg = errors.err_syncplay_crash()
            self.error_panel.show_error(msg)
            if self.current_step < len(self.step_labels):
                curr_lbl = self.step_labels[self.current_step]
                curr_text = self.steps[self.current_step][0]
                curr_lbl.setText(f"[Failed] {curr_text}")
                curr_lbl.setStyleSheet("font-size: 13px; color: #A85D5D; font-weight: 600; font-family: Consolas, monospace;")
            self.step_timer.stop()

    def _step_wait(self) -> bool:
        if self.process and self.process.poll() is not None:
            if self.process.returncode != 0:
                msg = errors.err_syncplay_crash()
                self.error_panel.show_error(msg)
                return False
        return True
        
    def _step_ready(self) -> bool:
        return self._step_wait()

    def _retry(self):
        self.error_panel.clear()
        self.start_launch(self.config, self.media_path)
        
    def _start_over(self):
        self.error_panel.clear()
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.back_requested.emit()
        
    def _on_back(self):
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.back_requested.emit()
