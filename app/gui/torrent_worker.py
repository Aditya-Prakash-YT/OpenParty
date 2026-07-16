"""
TorrentWorker — QThread that creates a torrent and seeds it via
qBittorrent in the background so the UI stays responsive.
"""

import os
from PySide6.QtCore import QThread, Signal
from torrent_creator import QBitClient, QBitError


class TorrentWorker(QThread):
    """Runs create_and_seed() on a background thread.

    Signals:
        status_update(str)  — progress text for the UI label
        finished_ok(str, str, int)  — (magnet_link, file_name, file_size)
        finished_err(str)   — error message
    """

    status_update = Signal(str)
    finished_ok = Signal(str, str, int)   # magnet, filename, size
    finished_err = Signal(str)

    def __init__(self, file_path: str,
                 host: str = "127.0.0.1", port: int = 8080,
                 username: str = "admin", password: str = "adminadmin",
                 parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def run(self):
        try:
            client = QBitClient(self.host, self.port,
                                self.username, self.password)

            self.status_update.emit("Connecting to qBittorrent…")
            client.login()

            self.status_update.emit("Creating torrent & starting seed…")
            magnet, info_hash = client.create_and_seed(self.file_path)

            file_name = os.path.basename(self.file_path)
            file_size = os.path.getsize(self.file_path)

            self.status_update.emit("Seeding ✔")
            self.finished_ok.emit(magnet, file_name, file_size)

        except QBitError as e:
            self.finished_err.emit(str(e))
        except ConnectionRefusedError:
            self.finished_err.emit(
                "Could not connect to qBittorrent Web API.\n\n"
                "Make sure qBittorrent is running and the Web UI is enabled:\n"
                "  Tools → Options → Web UI → ☑ Enable the Web User Interface\n"
                "  (Default address: localhost, port: 8080)"
            )
        except Exception as e:
            self.finished_err.emit(f"Unexpected error: {e}")
