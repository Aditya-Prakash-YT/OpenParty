import os
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, 
                               QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt, QTimer, Signal

from config.loader import PartyConfig
from downloader.aria2 import Aria2Manager, Aria2Error
from gui.error_panel import ErrorPanel
from logger import launcher_logger
import errors

class DownloadWidget(QWidget):
    download_complete = Signal(str) # Emits the path to the media file
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = None
        self.manager = None
        self.gid = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll_progress)
        self.save_dir = os.path.join(os.path.expanduser("~"), "Downloads", "OpenParty")
        self.checked_disk = False
        self._stall_count = 0
        self._network_retry_count = 0
        
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        
        self.lbl_title = QLabel("Downloading Media")
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_title)
        
        self.lbl_status = QLabel("Starting...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_status)
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.main_layout.addWidget(self.progress)
        
        info_layout = QHBoxLayout()
        self.lbl_speed = QLabel("0 KB/s")
        self.lbl_eta = QLabel("ETA: --")
        info_layout.addWidget(self.lbl_speed)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_eta)
        self.main_layout.addLayout(info_layout)
        
        # Error panel
        self.error_panel = ErrorPanel()
        self.error_panel.try_again.connect(self._retry_download)
        self.error_panel.start_over.connect(self._start_over)
        self.main_layout.addWidget(self.error_panel)
        
        self.main_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.main_layout.addWidget(self.btn_cancel, alignment=Qt.AlignCenter)

    def start_download(self, config: PartyConfig):
        self.config = config
        self.checked_disk = False
        self._stall_count = 0
        self._network_retry_count = 0
        self.error_panel.clear()
        self.btn_cancel.show()
        self.lbl_status.setText("Starting aria2c...")
        self.progress.setValue(0)
        self.lbl_speed.setText("0 KB/s")
        self.lbl_eta.setText("ETA: --")
        
        try:
            self.manager = Aria2Manager()
            self.manager.start(self.save_dir)
            self._add_download()
            self.timer.start(500)
        except Aria2Error as e:
            msg = errors.err_aria2c_start_failed()
            errors.log_and_format("aria2c start failed", str(e), "reinstall", exc=e)
            self._show_error(msg)
        except Exception as e:
            msg = errors.log_and_format(
                "Unexpected error starting download.",
                str(e),
                "Try again or check View Logs for details.",
                exc=e
            )
            self._show_error(msg)

    def _add_download(self):
        source_type = self.config.media.source.type
        val = self.config.media.source.value
        
        if source_type == "magnet":
            self.gid = self.manager.add_uri(val)
            self.lbl_status.setText("Fetching metadata...")
        elif source_type == "torrent-file":
            if os.path.exists(val):
                self.gid = self.manager.add_torrent(val)
            else:
                self.gid = self.manager.add_uri(val)
            self.lbl_status.setText("Starting download...")

    def _poll_progress(self):
        if not self.manager or not self.gid:
            return
            
        try:
            status = self.manager.get_status(self.gid)
        except Aria2Error as e:
            # Network drop or aria2c crash during poll
            self._network_retry_count += 1
            if self._network_retry_count <= 3:
                launcher_logger.warning(f"RPC poll failed (attempt {self._network_retry_count}): {e}")
                return  # silent retry on next tick
            self.timer.stop()
            msg = errors.err_network_lost()
            launcher_logger.error(f"RPC poll failed after retries: {e}")
            self._show_error(msg)
            return
        except Exception as e:
            launcher_logger.error(f"Unexpected poll error: {e}")
            return
            
        self._network_retry_count = 0  # reset on success
            
        # Check for disk space once we know total length
        total_length = int(status.get("totalLength", 0))
        if total_length > 0 and not self.checked_disk:
            try:
                free_space = shutil.disk_usage(self.save_dir).free
            except Exception:
                free_space = 0
            if total_length > free_space:
                self.timer.stop()
                msg = errors.err_disk_full(total_length / 1024**3, free_space / 1024**3)
                self._show_error(msg, show_try_again=False)
                self._cleanup()
                return
            self.checked_disk = True
        
        # Update UI
        completed_length = int(status.get("completedLength", 0))
        speed = int(status.get("downloadSpeed", 0))
        
        if total_length > 0:
            pct = int(completed_length / total_length * 100)
            self.progress.setValue(pct)
            self.lbl_status.setText(f"Downloading... ({completed_length/1024**2:.1f} MB / {total_length/1024**2:.1f} MB)")
        else:
            self.progress.setValue(0)
            
        self.lbl_speed.setText(f"{speed/1024:.1f} KB/s" if speed < 1024**2 else f"{speed/1024**2:.1f} MB/s")
        
        if speed > 0 and total_length > completed_length:
            eta_sec = (total_length - completed_length) / speed
            self.lbl_eta.setText(f"ETA: {int(eta_sec)}s")
        else:
            self.lbl_eta.setText("ETA: --")
        
        # Detect stall (no peers)
        if total_length > 0 and speed == 0 and completed_length < total_length:
            self._stall_count += 1
            if self._stall_count >= 120:  # 60 seconds at 500ms poll
                self.timer.stop()
                msg = errors.err_torrent_no_peers()
                self._show_error(msg)
                return
        else:
            self._stall_count = 0
            
        state = status.get("status")
        if state == "complete":
            followed_by = status.get("followedBy")
            if followed_by:
                self.gid = followed_by[0]
                self.lbl_status.setText("Metadata fetched, starting payload download...")
                self._stall_count = 0
            else:
                self.timer.stop()
                self.lbl_status.setText("Complete!")
                self._handle_completion(status)
                
        elif state == "error":
            self.timer.stop()
            err_code = int(status.get("errorCode", 0))
            err_msg = status.get("errorMessage", "Unknown error")
            launcher_logger.error(f"aria2 error code={err_code}: {err_msg}")
            
            # Classify error
            if err_code in (2, 3, 19):
                msg = errors.err_network_lost()
            elif err_code == 24:
                msg = errors.err_disk_full_mid_download()
            else:
                msg = errors.log_and_format(
                    "Download failed.",
                    err_msg,
                    "Click Try Again or check View Logs for details."
                )
            self._show_error(msg)

    def _handle_completion(self, status):
        files = status.get("files", [])
        media_path = None
        
        # 1. Try file_name_hint
        hint = self.config.media.file.name_hint
        if hint:
            for f in files:
                path = f.get("path", "")
                if os.path.basename(path) == hint:
                    media_path = path
                    break
        
        # 2. Fallback to largest video file
        if not media_path:
            largest_size = -1
            for f in files:
                path = f.get("path", "")
                size = int(f.get("length", 0))
                ext = os.path.splitext(path)[1].lower()
                if ext in [".mkv", ".mp4", ".avi", ".mov"] and size > largest_size:
                    largest_size = size
                    media_path = path
                    
        # 3. Absolute fallback to largest file overall
        if not media_path and files:
            largest_size = -1
            for f in files:
                path = f.get("path", "")
                size = int(f.get("length", 0))
                if size > largest_size:
                    largest_size = size
                    media_path = path
                    
        if not media_path or not os.path.exists(media_path):
            msg = errors.err_media_file_missing()
            self._show_error(msg, show_try_again=False)
            return
            
        launcher_logger.info(f"Download complete: {media_path}")
        self._cleanup()
        self.download_complete.emit(media_path)

    def _show_error(self, msg: str, show_try_again: bool = True):
        self.timer.stop()
        self.btn_cancel.hide()
        self.error_panel.show_error(msg, show_try_again=show_try_again)
        
    def _retry_download(self):
        self.error_panel.clear()
        self.btn_cancel.show()
        self._cleanup()
        self.start_download(self.config)
        
    def _start_over(self):
        self._cleanup()
        self.error_panel.clear()
        self.cancel_requested.emit()

    def _on_cancel(self):
        self.timer.stop()
        if self.manager and self.gid:
            try:
                self.manager.remove(self.gid)
            except Exception:
                pass
        self._cleanup()
        self.cancel_requested.emit()

    def _cleanup(self):
        if self.manager:
            self.manager.stop()
            self.manager = None
