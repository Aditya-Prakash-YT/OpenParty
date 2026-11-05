"""Compact live peer transfer view shared by host and guest screens."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from peer_status import format_bytes, format_rate, peer_progress


class PeerActivityWidget(QFrame):
    """Shows only connected BitTorrent peers; protocol has no party identities."""

    def __init__(self, title="Peer transfer activity", parent=None):
        super().__init__(parent)
        self.setObjectName("peerActivityCard")
        self.setStyleSheet(
            "QFrame#peerActivityCard { background: #FFFFFF; border: 1px solid #E1E7EA; border-radius: 10px; }"
            "QLabel { background: transparent; border: none; }"
            "QTableWidget { background: #FFFFFF; border: 1px solid #E6ECEF; gridline-color: #EEF1F3; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #35434C;")
        layout.addWidget(self.title_label)

        self.connection_label = QLabel("Waiting for peer connections…")
        self.connection_label.setStyleSheet("font-size: 12px; color: #65747E;")
        self.connection_label.setWordWrap(True)
        layout.addWidget(self.connection_label)

        self.totals_label = QLabel("Uploaded 0 B  ·  Downloaded 0 B  ·  Up 0 B/s  ·  Down 0 B/s")
        self.totals_label.setStyleSheet("font-size: 11px; color: #65747E;")
        layout.addWidget(self.totals_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Peer", "Their progress", "Peer → you", "You → peer"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setMinimumHeight(88)
        self.table.setMaximumHeight(172)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.privacy_note = QLabel(
            "Shows peers connected to this device right now. BitTorrent does not provide party member names."
        )
        self.privacy_note.setStyleSheet("font-size: 10px; color: #87939A;")
        self.privacy_note.setWordWrap(True)
        layout.addWidget(self.privacy_note)

    @staticmethod
    def _item(text):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
        return item

    def update_activity(self, peers, status, *, host=False):
        peers = [peer for peer in (peers or []) if isinstance(peer, dict)]
        piece_count = status.get("numPieces", 0) if isinstance(status, dict) else 0
        upload_rate = status.get("uploadSpeed", 0) if isinstance(status, dict) else 0
        download_rate = status.get("downloadSpeed", 0) if isinstance(status, dict) else 0
        uploaded = status.get("uploadLength", 0) if isinstance(status, dict) else 0
        downloaded = status.get("completedLength", 0) if isinstance(status, dict) else 0

        if host:
            self.totals_label.setText(
                f"Sent to peers {format_bytes(uploaded)}  ·  Upload {format_rate(upload_rate)}"
            )
        else:
            self.totals_label.setText(
                f"Completed {format_bytes(downloaded)}  ·  Uploaded {format_bytes(uploaded)}"
                f"  ·  Down {format_rate(download_rate)}  ·  Up {format_rate(upload_rate)}"
            )
        if peers:
            self.connection_label.setText(
                f"{len(peers)} connected peer{'s' if len(peers) != 1 else ''}. "
                + ("The host is uploading to these peers." if host else "This device is sharing available pieces with peers.")
            )
        elif host:
            self.connection_label.setText(
                "Seeder is active; no peer is connected yet. Guests may still be blocked by the host router or network."
            )
        elif isinstance(status, dict) and str(status.get("seeder", "false")).lower() == "true":
            self.connection_label.setText(
                "Download complete. This device is ready to share when peers connect."
            )
        else:
            self.connection_label.setText(
                "No connected peers yet. Waiting for the host or another participant to become reachable."
            )

        self.table.clearSpans()
        self.table.setRowCount(len(peers))
        for row, peer in enumerate(peers):
            pct = peer_progress(peer, piece_count)
            progress = "Complete" if pct == 100 else (f"{pct}%" if pct is not None else "Unknown")
            if str(peer.get("seeder", "false")).lower() == "true":
                progress = "Seeding"
            values = (
                f"Peer {row + 1}",
                progress,
                format_rate(peer.get("downloadSpeed", 0)),
                format_rate(peer.get("uploadSpeed", 0)),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, self._item(value))
        if not peers:
            self.table.setRowCount(1)
            item = self._item("No active peer connections")
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 4)

