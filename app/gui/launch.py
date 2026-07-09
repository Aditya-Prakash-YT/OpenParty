import os
import sys
import subprocess
import hashlib
import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt, QTimer, Signal

from config.loader import PartyConfig
from deps import find_vlc, find_syncplay
from gui.error_panel import ErrorPanel
from logger import launcher_logger
import errors

class LaunchWidget(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = None
        self.media_path = None
        self.process = None
        self.log_file = None
        
        self.step_timer = QTimer()
        self.step_timer.timeout.connect(self._next_step)
        self.current_step = 0
        
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        
        self.lbl_title = QLabel("Starting Party...")
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_title)
        
        # Checklist
        self.check_layout = QVBoxLayout()
        self.main_layout.addLayout(self.check_layout)
        
        # Error panel
        self.error_panel = ErrorPanel()
        self.error_panel.try_again.connect(self._retry)
        self.error_panel.start_over.connect(self._start_over)
        self.main_layout.addWidget(self.error_panel)
        
        self.main_layout.addStretch()
        
        self.btn_back = QPushButton("← Back to Menu")
        self.btn_back.setMinimumHeight(40)
        self.btn_back.clicked.connect(self._on_back)
        self.btn_back.hide()
        self.main_layout.addWidget(self.btn_back, alignment=Qt.AlignCenter)

    def start_launch(self, config: PartyConfig, media_path: str):
        self.config = config
        self.media_path = media_path
        self.current_step = 0
        self.btn_back.hide()
        self.error_panel.clear()
        
        # Clear checklist
        for i in reversed(range(self.check_layout.count())): 
            widget = self.check_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                
        self.steps = [
            ("Verifying Download", self._step_verify),
            ("Launching Syncplay", self._step_launch),
            ("Opening VLC", self._step_wait),
            ("Connected to Room", self._step_wait),
            ("Ready", self._step_ready)
        ]
        
        self.step_labels = []
        for text, _ in self.steps:
            lbl = QLabel(f"○ {text}")
            lbl.setStyleSheet("font-size: 16px; color: gray;")
            self.check_layout.addWidget(lbl)
            self.step_labels.append(lbl)
            
        self.step_timer.start(800)
        
    def _next_step(self):
        if self.current_step > 0:
            prev_lbl = self.step_labels[self.current_step - 1]
            prev_text = self.steps[self.current_step - 1][0]
            prev_lbl.setText(f"✔ {prev_text}")
            prev_lbl.setStyleSheet("font-size: 16px; color: green; font-weight: bold;")
            
        if self.current_step < len(self.steps):
            curr_lbl = self.step_labels[self.current_step]
            curr_text = self.steps[self.current_step][0]
            curr_lbl.setText(f"↻ {curr_text}...")
            curr_lbl.setStyleSheet("font-size: 16px; color: black; font-weight: bold;")
            
            func = self.steps[self.current_step][1]
            success = func()
            if not success:
                self.step_timer.stop()
                curr_lbl.setText(f"✘ {curr_text} — Failed")
                curr_lbl.setStyleSheet("font-size: 16px; color: red; font-weight: bold;")
                return
                
            self.current_step += 1
        else:
            self.step_timer.stop()
            self.btn_back.setText("Return to Main Menu")
            self.btn_back.show()

    def _step_verify(self) -> bool:
        if not os.path.exists(self.media_path):
            msg = errors.err_media_file_missing()
            self.error_panel.show_error(msg, show_try_again=False)
            return False
            
        expected_size = self.config.media.file.size
        if expected_size:
            actual_size = os.path.getsize(self.media_path)
            if actual_size != expected_size:
                launcher_logger.warning(f"Size mismatch: expected {expected_size}, got {actual_size}")
                
        expected_hash = self.config.integrity.sha256
        if expected_hash:
            sha256 = hashlib.sha256()
            with open(self.media_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            if sha256.hexdigest() != expected_hash:
                msg = errors.err_integrity_failed()
                self.error_panel.show_error(msg, show_try_again=False)
                return False
                
        return True

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
            log_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "OpenParty")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "syncplay.log")
            
            self.log_file = open(log_path, "a", encoding="utf-8")
            self.log_file.write(f"\n--- Launching Syncplay ({time.ctime()}) ---\nCmd: {cmd}\n")
            self.log_file.flush()
            
            self.process = subprocess.Popen(
                cmd, 
                stdout=self.log_file, 
                stderr=subprocess.STDOUT
            )
            
            time.sleep(0.5)
            if self.process.poll() is not None:
                self.log_file.write(f"Process exited early with code {self.process.returncode}\n")
                msg = errors.err_syncplay_crash()
                self.error_panel.show_error(msg)
                return False
                
            return True
        except Exception as e:
            launcher_logger.error(f"Syncplay launch failed: {e}")
            msg = errors.err_syncplay_crash()
            self.error_panel.show_error(msg)
            return False

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
