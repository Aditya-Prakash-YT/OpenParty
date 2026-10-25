"""
TorrentWorker -- Background worker that creates a torrent in pure Python,
seeds it via aria2c (primary) or qBittorrent (fallback), and yields the magnet link.
"""

import os
import subprocess
from PySide6.QtCore import QThread, Signal

from torrent_creator import (
    create_local_torrent,
    seed_with_aria2c,
    SeederManager,
    QBitClient,
    QBitError,
)
from deps import find_aria2c, find_qbittorrent
from logger import launcher_logger


class TorrentWorker(QThread):
    """Runs torrent generation and seeding on a background thread.

    Signals:
        status_update(str)  -- progress text for the UI label
        finished_ok(str, str, int, str)  -- (magnet_link, file_name, file_size, torrent_path)
        finished_err(str)   -- error message
    """

    status_update = Signal(str)
    finished_ok = Signal(str, str, int, str)   # magnet, filename, size, torrent_path
    finished_err = Signal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._seed_process = None  # aria2c Popen handle, kept alive

    def run(self):
        try:
            self.status_update.emit("Calculating hash and creating torrent...")
            file_name = os.path.basename(self.file_path)
            file_size = os.path.getsize(self.file_path)

            magnet, info_hash, torrent_path = create_local_torrent(self.file_path)
            launcher_logger.info(f"Generated torrent: {torrent_path}, hash: {info_hash}")

            seeded = False
            data_dir = os.path.dirname(os.path.abspath(self.file_path))

            # 1. Primary: seed via aria2c (already a required dependency)
            aria2c_exe = find_aria2c()
            if aria2c_exe:
                self.status_update.emit("Starting seed via aria2c...")
                proc = seed_with_aria2c(torrent_path, data_dir, aria2c_exe)
                if proc is not None:
                    self._seed_process = proc
                    SeederManager.set_seed_process(proc, torrent_path, self.file_path)
                    seeded = True
                    launcher_logger.info(f"Seeding via aria2c (pid {proc.pid})")

            # 2. Fallback: try qBittorrent Web API (if it happens to be running)
            if not seeded:
                try:
                    self.status_update.emit("Trying qBittorrent Web API...")
                    client = QBitClient()
                    client.login()
                    client.add_torrent_for_seeding(torrent_path, data_dir)
                    seeded = True
                    launcher_logger.info("Seeding via qBittorrent Web API")
                except Exception as e:
                    launcher_logger.info(f"qBittorrent Web API not available ({e})")

            # 3. Last resort: open qBittorrent GUI with the torrent file
            if not seeded:
                qbit_exe = find_qbittorrent()
                if qbit_exe:
                    try:
                        self.status_update.emit("Opening qBittorrent to seed...")
                        subprocess.Popen([qbit_exe, torrent_path])
                        seeded = True
                        launcher_logger.info("Launched qBittorrent GUI with torrent file")
                    except Exception as e:
                        launcher_logger.warning(f"Failed to launch qBittorrent: {e}")

            if seeded:
                self.status_update.emit("Torrent created and seeding.")
            else:
                self.status_update.emit(
                    "Torrent and magnet link created (not seeding -- "
                    "install aria2c via setup.cmd to enable seeding)."
                )

            self.finished_ok.emit(magnet, file_name, file_size, torrent_path)

        except Exception as e:
            launcher_logger.error(f"Torrent worker error: {e}")
            self.finished_err.emit(f"Failed to create torrent: {e}")
