"""Create the party torrent and verify the local aria2 seeder is ready."""

import os
from PySide6.QtCore import QThread, Signal

from torrent_creator import (
    create_local_torrent,
    seed_with_aria2c,
    SeederManager,
    BITTORRENT_PORT_RANGE,
    PUBLIC_TRACKERS,
)
from deps import find_aria2c
from logger import launcher_logger
from p2p_bootstrap import PartyBootstrapManager


class TorrentWorker(QThread):
    """Runs torrent generation and seeding on a background thread.

    Signals:
        status_update(str)  -- progress text for the UI label
        finished_ok(str, str, int, str, object) -- torrent details and bootstrap invite data
        finished_err(str)   -- error message
    """

    status_update = Signal(str)
    finished_ok = Signal(str, str, int, str, object)
    finished_err = Signal(str)

    def __init__(self, file_path: str, public_host: str = "", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.public_host = public_host.strip()
        self._seed_process = None  # aria2c Popen handle, kept alive
        self.seed_status = ""
        self.bootstrap_invite = None

    def run(self):
        try:
            self.status_update.emit("Calculating hash and creating torrent...")
            # This process manages a single host seed. Stop any prior seed so
            # a newly generated invite cannot leave the old media being served.
            SeederManager.stop_seeding()
            file_name = os.path.basename(self.file_path)
            file_size = os.path.getsize(self.file_path)

            bootstrap = None
            tracker_urls = None
            try:
                self.status_update.emit("Starting a direct host route for guests...")
                bootstrap = PartyBootstrapManager.start(self.file_path, self.public_host)
                tracker_urls = bootstrap.tracker_urls()
                if not tracker_urls:
                    raise RuntimeError("No LAN or public IPv4 address is available for the host route.")
            except Exception as exc:
                PartyBootstrapManager.stop()
                bootstrap = None
                launcher_logger.warning("Direct host route unavailable: %s", exc)
                self.status_update.emit(
                    "Direct host route could not start; falling back to public torrent discovery."
                )

            magnet, info_hash, torrent_path = create_local_torrent(
                self.file_path,
                trackers=(tracker_urls + PUBLIC_TRACKERS) if tracker_urls else None,
                magnet_trackers=PUBLIC_TRACKERS if tracker_urls else None,
            )
            launcher_logger.info(f"Generated torrent: {torrent_path}, hash: {info_hash}")

            if bootstrap:
                try:
                    bootstrap.configure(torrent_path, info_hash)
                    self.bootstrap_invite = bootstrap.invite_payload()
                    self.status_update.emit(
                        "Direct host route ready. Guests on the same network can connect immediately."
                    )
                except Exception as exc:
                    launcher_logger.warning("Could not configure direct host route: %s", exc)
                    PartyBootstrapManager.stop()
                    bootstrap = None
                    self.bootstrap_invite = None

            seeded = False
            data_dir = os.path.dirname(os.path.abspath(self.file_path))

            # 1. Primary: seed via aria2c (already a required dependency)
            aria2c_exe = find_aria2c()
            if aria2c_exe:
                self.status_update.emit("Starting seed via aria2c...")
                proc = seed_with_aria2c(
                    torrent_path, data_dir, aria2c_exe, self.status_update.emit
                )
                if proc is not None:
                    self._seed_process = proc
                    SeederManager.set_seed_process(
                        proc, torrent_path, self.file_path, info_hash
                    )
                    seeded = True
                    self.seed_status = (
                        f"Seeder is running on TCP/UDP ports {BITTORRENT_PORT_RANGE}. "
                        "Waiting for peers; internet reachability is not confirmed yet."
                    )
                    launcher_logger.info(f"Seeding via aria2c (pid {proc.pid})")

            if seeded:
                self.status_update.emit(self.seed_status)
            else:
                PartyBootstrapManager.stop()
                self.seed_status = (
                    "Torrent and magnet link created, but seeding could not be started. "
                    "Guests will not be able to download until a seeder is online."
                )
                self.status_update.emit(self.seed_status)

            self.finished_ok.emit(
                magnet, file_name, file_size, torrent_path, self.bootstrap_invite
            )

        except Exception as e:
            PartyBootstrapManager.stop()
            launcher_logger.error(f"Torrent worker error: {e}")
            self.finished_err.emit(f"Failed to create torrent: {e}")
