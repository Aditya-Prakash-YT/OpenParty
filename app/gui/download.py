import os
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, 
                               QPushButton, QHBoxLayout, QFrame, QStyle, QFileDialog)
from PySide6.QtCore import Qt, QTimer, Signal

from config.loader import PartyConfig, usable_p2p_endpoints
from downloader.aria2 import Aria2Manager, Aria2Error
from gui.error_panel import ErrorPanel
from gui.peer_activity import PeerActivityWidget
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
        self._metadata_stall_count = 0
        self._network_retry_count = 0
        
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(32, 30, 32, 28)
        self.main_layout.setSpacing(20)
        
        # Header
        self.lbl_title = QLabel("Downloading Media")
        self.lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #25323B;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_title)
        
        # Download Card Container
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E1E7EA; border-radius: 12px; padding: 22px; }"
            "QLabel { background: transparent; border: none; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)
        
        self.lbl_movie_name = QLabel("")
        self.lbl_movie_name.setStyleSheet("font-size: 15px; font-weight: 600; color: #35434C;")
        self.lbl_movie_name.setAlignment(Qt.AlignCenter)
        self.lbl_movie_name.setWordWrap(True)
        card_layout.addWidget(self.lbl_movie_name)
        
        self.lbl_status = QLabel("Connecting to watch party peers...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 13px; color: #65747E;")
        card_layout.addWidget(self.lbl_status)
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMinimumHeight(24)
        self.progress.setStyleSheet(
            "QProgressBar { border: 1px solid #DDE4E8; border-radius: 9px; text-align: center; font-weight: bold; color: #35434C; background-color: #FFFFFF; }"
            "QProgressBar::chunk { background-color: #3E6478; border-radius: 5px; }"
        )
        card_layout.addWidget(self.progress)
        
        info_layout = QHBoxLayout()
        self.lbl_speed = QLabel("0 KB/s")
        self.lbl_speed.setStyleSheet("font-weight: 600; color: #3E6478; font-size: 13px;")
        
        self.lbl_eta = QLabel("ETA: --")
        self.lbl_eta.setStyleSheet("font-weight: 600; color: #72808A; font-size: 13px;")
        
        info_layout.addWidget(self.lbl_speed)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_eta)
        card_layout.addLayout(info_layout)

        self.peer_activity = PeerActivityWidget("Live peer activity")
        card_layout.addWidget(self.peer_activity)
        
        self.btn_select_local = QPushButton("Already have this video on your PC? Select file...")
        self.btn_select_local.setFlat(True)
        self.btn_select_local.setCursor(Qt.PointingHandCursor)
        self.btn_select_local.setStyleSheet(
            "QPushButton { color: #3E6478; font-size: 12px; font-weight: 500; border: none; background: transparent; padding: 4px; }"
            "QPushButton:hover { text-decoration: underline; color: #345668; }"
        )
        self.btn_select_local.clicked.connect(self._on_select_local_file)
        card_layout.addWidget(self.btn_select_local, alignment=Qt.AlignCenter)
        
        self.main_layout.addWidget(card)
        
        # Error panel
        self.error_panel = ErrorPanel()
        self.error_panel.try_again.connect(self._retry_download)
        self.error_panel.start_over.connect(self._start_over)
        self.main_layout.addWidget(self.error_panel)
        
        self.main_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel Download")
        self.btn_cancel.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.btn_cancel.setMinimumHeight(36)
        self.btn_cancel.setFixedWidth(150)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(
            "QPushButton { background-color: #F1F4F6; color: #35434C; font-weight: 500; border: 1px solid #DDE4E8; border-radius: 8px; }"
            "QPushButton:hover { background-color: #E6ECEF; }"
        )
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.main_layout.addWidget(self.btn_cancel, alignment=Qt.AlignCenter)

    def start_download(self, config: PartyConfig):
        self.timer.stop()
        self._cleanup()
        self.config = config
        self.checked_disk = False
        self._stall_count = 0
        self._metadata_stall_count = 0
        self._network_retry_count = 0
        self.error_panel.clear()
        self.btn_cancel.show()
        
        name_hint = self.config.media.file.name_hint or self.config.party.name
        self.lbl_movie_name.setText(name_hint)
        self.lbl_status.setText("Preparing peer download...")
        self.progress.setValue(0)
        self.lbl_speed.setText("0 KB/s")
        self.lbl_eta.setText("ETA: --")
        self.peer_activity.update_activity([], {}, host=False)

        self.lbl_status.setText("Starting download engine (aria2c)...")
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

    def _is_safe_download_path(self, path: str) -> bool:
        """Require aria2-reported media paths to resolve inside its download root."""
        try:
            root = os.path.normcase(os.path.realpath(os.path.abspath(self.save_dir)))
            resolved = os.path.normcase(os.path.realpath(os.path.abspath(path)))
            return os.path.commonpath((root, resolved)) == root
        except (OSError, ValueError, TypeError):
            return False

    def _add_download(self):
        p2p = self.config.media.p2p
        endpoints = usable_p2p_endpoints(p2p)
        if p2p and endpoints:
            web_seeds = [f"{endpoint.base_url}/media" for endpoint in endpoints]
            self.gid = self.manager.add_torrent_bytes(p2p.torrent_bytes, web_seeds)
            self.lbl_status.setText("Connecting directly to the host and available peers...")
            return

        val = self.config.media.source.value
        self.gid = self.manager.add_uri(val)
        self.lbl_status.setText("Connecting to peers & retrieving movie details...")

    def _poll_progress(self):
        if not self.manager or not self.gid:
            return
            
        try:
            status = self.manager.get_status(self.gid)
        except Aria2Error as e:
            self._network_retry_count += 1
            if self._network_retry_count <= 3:
                launcher_logger.warning(f"RPC poll failed (attempt {self._network_retry_count}): {e}")
                return
            self.timer.stop()
            msg = errors.err_network_lost()
            launcher_logger.error(f"RPC poll failed after retries: {e}")
            self._show_error(msg)
            return
        except Exception as e:
            self._network_retry_count += 1
            if self._network_retry_count <= 3:
                launcher_logger.warning(
                    f"Unexpected RPC poll failure (attempt {self._network_retry_count}): {e}"
                )
                return
            self.timer.stop()
            launcher_logger.error(f"RPC poll failed after retries: {e}")
            self._show_error(errors.err_network_lost())
            return
            
        self._network_retry_count = 0
            
        total_length = int(status.get("totalLength", 0))
        if total_length > 0 and not self.checked_disk:
            completed_for_space = int(status.get("completedLength", 0))
            remaining_length = max(0, total_length - completed_for_space)
            try:
                check_path = self.save_dir if os.path.exists(self.save_dir) else os.path.splitdrive(self.save_dir)[0] + os.sep
                free_space = shutil.disk_usage(check_path).free
            except Exception:
                free_space = 0
            if free_space > 0 and remaining_length > free_space:
                self.timer.stop()
                msg = errors.err_disk_full(remaining_length / 1024**3, free_space / 1024**3)
                self._show_error(msg, show_try_again=False)
                self._cleanup()
                return
            self.checked_disk = True
        
        # Update UI
        completed_length = int(status.get("completedLength", 0))
        speed = int(status.get("downloadSpeed", 0))
        try:
            peers = self.manager.get_peers(self.gid)
        except Exception:
            peers = []
        self.peer_activity.update_activity(peers, status, host=False)
        
        if total_length > 0:
            self._metadata_stall_count = 0
            pct = int(completed_length / total_length * 100)
            self.progress.setValue(pct)
            completed_mb = completed_length / (1024**2)
            total_mb = total_length / (1024**2)
            if total_mb >= 1024:
                self.lbl_status.setText(f"Downloading: {completed_mb/1024:.2f} GB / {total_mb/1024:.2f} GB ({pct}%)")
            else:
                self.lbl_status.setText(f"Downloading: {completed_mb:.1f} MB / {total_mb:.1f} MB ({pct}%)")
        else:
            self.progress.setValue(0)
            self._metadata_stall_count += 1
            if self._metadata_stall_count < 30:
                self.lbl_status.setText("Connecting to peers & getting movie metadata...")
            elif self._metadata_stall_count < 120:
                self.lbl_status.setText("Searching for peers... Ensure the watch party host is online and seeding.")
            else:
                self.timer.stop()
                msg = errors.err_torrent_metadata_timeout()
                self._show_error(msg)
                return
            
        if speed < 1024:
            self.lbl_speed.setText(f"{speed} B/s")
        elif speed < 1024**2:
            self.lbl_speed.setText(f"{speed/1024:.1f} KB/s")
        else:
            self.lbl_speed.setText(f"{speed/1024**2:.1f} MB/s")
        
        if speed > 0 and total_length > completed_length:
            eta_sec = (total_length - completed_length) / speed
            if eta_sec >= 60:
                mins = int(eta_sec // 60)
                secs = int(eta_sec % 60)
                self.lbl_eta.setText(f"ETA: {mins}m {secs}s")
            else:
                self.lbl_eta.setText(f"ETA: {int(eta_sec)}s")
        else:
            self.lbl_eta.setText("ETA: --")
        
        # Detect stall
        if total_length > 0 and speed == 0 and completed_length < total_length:
            self._stall_count += 1
            if self._stall_count >= 120:  # 60 seconds
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
                self.lbl_status.setText("Metadata received, starting video download...")
                self._stall_count = 0
                self._metadata_stall_count = 0
            else:
                self.timer.stop()
                self.progress.setValue(100)
                self.lbl_status.setText("Download Complete!")
                self._handle_completion(status)
                
        elif state == "error":
            self.timer.stop()
            err_code = int(status.get("errorCode", 0))
            err_msg = status.get("errorMessage", "Unknown error")
            launcher_logger.error(f"aria2 error code={err_code}: {err_msg}")
            
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
                if path and self._is_safe_download_path(path) and os.path.basename(path) == hint:
                    media_path = path
                    break
        
        # 2. Fallback to largest video file
        if not media_path:
            largest_size = -1
            for f in files:
                path = f.get("path", "")
                if not path or not self._is_safe_download_path(path):
                    continue
                size = int(f.get("length", 0))
                ext = os.path.splitext(path)[1].lower()
                if ext in [".mkv", ".mp4", ".avi", ".mov", ".wmv", ".webm", ".flv"] and size > largest_size:
                    largest_size = size
                    media_path = path
                    
        # 3. Absolute fallback to largest file overall
        if not media_path and files:
            largest_size = -1
            for f in files:
                path = f.get("path", "")
                if not path or not self._is_safe_download_path(path):
                    continue
                size = int(f.get("length", 0))
                if size > largest_size:
                    largest_size = size
                    media_path = path
                    
        if (not media_path or not self._is_safe_download_path(media_path)
                or not os.path.isfile(media_path)):
            msg = errors.err_media_file_missing()
            self._show_error(msg, show_try_again=False)
            return

        expected_size = self.config.media.file.size
        try:
            actual_size = os.path.getsize(media_path)
        except OSError:
            msg = errors.err_media_file_missing()
            self._show_error(msg, show_try_again=False)
            return
        if expected_size is not None and expected_size > 0 and actual_size != expected_size:
            msg = errors.log_and_format(
                "Downloaded media does not match the party details.",
                f"Expected {expected_size} bytes but found {actual_size} bytes.",
                "Ask the host to verify the selected media and create a new party invite."
            )
            self._show_error(msg, show_try_again=False)
            return
            
        launcher_logger.info(f"Download complete: {media_path}")
        # Keep aria2 alive after completion so this device can seed the file to
        # other participants for as long as OpenParty remains open.
        self.btn_cancel.hide()
        self.lbl_status.setText("Download complete. Sharing available pieces with peers.")
        self.download_complete.emit(media_path)

    def _show_error(self, msg: str, show_try_again: bool = True):
        self.timer.stop()
        self._cleanup()
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
        self.gid = None

    def _on_select_local_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.flv);;All Files (*.*)"
        )
        if file_path and os.path.isfile(file_path):
            self.timer.stop()
            self._cleanup()
            self.lbl_status.setText("Using selected video file.")
            self.progress.setValue(100)
            self.download_complete.emit(file_path)
