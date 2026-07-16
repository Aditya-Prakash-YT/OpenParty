"""
QBitClient — Lightweight qBittorrent Web API client.

Uses only stdlib (urllib, json, http.cookiejar) so there are zero
extra pip dependencies.  Supports:
  • Auth login/logout
  • Creating a torrent from a local file (v5+ torrentCreator API)
  • Falling back to adding an externally-created .torrent file (v4+)
  • Fetching torrent info to extract the info hash → magnet link
"""

import json
import os
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from typing import Optional, Tuple

# ---------- public tracker list for magnet links ----------
PUBLIC_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://explodie.org:6969/announce",
    "udp://p4p.arenabg.com:1337/announce",
]


class QBitError(Exception):
    """Raised when the Web API returns an unexpected error."""


class QBitClient:
    """Minimal, zero-dependency qBittorrent Web API client."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080,
                 username: str = "admin", password: str = "adminadmin"):
        self.base = f"http://{host}:{port}"
        self.username = username
        self.password = password

        self._cj = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cj)
        )
        self._logged_in = False

    # ── helpers ──────────────────────────────────────────────

    def _post(self, path: str, data: Optional[dict] = None,
              raw_body: Optional[bytes] = None,
              content_type: Optional[str] = None) -> bytes:
        """POST to the API and return the response body."""
        url = f"{self.base}{path}"
        if raw_body is not None:
            body = raw_body
        elif data is not None:
            body = urllib.parse.urlencode(data).encode()
            content_type = content_type or "application/x-www-form-urlencoded"
        else:
            body = b""

        req = urllib.request.Request(url, data=body, method="POST")
        if content_type:
            req.add_header("Content-Type", content_type)
        req.add_header("Referer", self.base)

        try:
            with self._opener.open(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise QBitError(f"HTTP {e.code} from {path}: {e.read().decode(errors='replace')}") from e

    def _get(self, path: str, params: Optional[dict] = None) -> bytes:
        """GET from the API and return the response body."""
        url = f"{self.base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url)
        req.add_header("Referer", self.base)
        try:
            with self._opener.open(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise QBitError(f"HTTP {e.code} from {path}: {e.read().decode(errors='replace')}") from e

    # ── auth ─────────────────────────────────────────────────

    def login(self) -> None:
        """Authenticate with qBittorrent.  Raises QBitError on failure."""
        body = self._post("/api/v2/auth/login", {
            "username": self.username,
            "password": self.password,
        })
        text = body.decode()
        if text.strip().upper() != "OK.":
            raise QBitError(f"Login failed: {text}")
        self._logged_in = True

    def ensure_login(self) -> None:
        if not self._logged_in:
            self.login()

    # ── version detection ────────────────────────────────────

    def get_version(self) -> str:
        """Return qBittorrent app version string, e.g. 'v5.1.0'."""
        self.ensure_login()
        return self._get("/api/v2/app/version").decode().strip()

    def supports_torrent_creator(self) -> bool:
        """True if the qBittorrent version has the torrentCreator API (v5.0+)."""
        ver = self.get_version()               # e.g. "v5.1.0"
        try:
            major = int(ver.lstrip("v").split(".")[0])
            return major >= 5
        except (ValueError, IndexError):
            return False

    # ── torrent creation (v5+ API) ───────────────────────────

    def create_torrent_v5(self, source_path: str,
                          trackers: Optional[list] = None) -> str:
        """Use the v5 torrentCreator API.  Returns the task id."""
        self.ensure_login()
        if trackers is None:
            trackers = PUBLIC_TRACKERS

        data = {
            "sourcePath": source_path,
            "torrentFilePath": "",   # empty = auto
            "format": "hybrid",
            "startSeeding": "true",
            "optimizeAlignment": "true",
            "pieceSize": "0",        # auto
            "padFileSize": "-1",
            "trackers": "\n".join(trackers),
            "urlSeeds": "",
            "comment": "Created by OpenParty",
            "isPrivate": "false",
        }
        body = self._post("/api/v2/torrentCreator/addTask", data)
        return body.decode().strip()

    def poll_torrent_creator(self, task_id: str,
                             timeout: int = 300,
                             poll_interval: float = 1.0) -> str:
        """Poll until the torrentCreator task finishes.
        Returns the info hash of the created torrent.
        """
        self.ensure_login()
        deadline = time.time() + timeout
        while time.time() < deadline:
            body = self._get("/api/v2/torrentCreator/status",
                             {"id": task_id})
            status = json.loads(body)
            if isinstance(status, list) and len(status) > 0:
                status = status[0]
            state = status.get("status", "").lower()
            if state == "finished":
                return status.get("infoHash", status.get("torrentHash", ""))
            if state in ("failed", "error"):
                raise QBitError(f"Torrent creation failed: {status}")
            time.sleep(poll_interval)
        raise QBitError("Torrent creation timed out")

    # ── fallback: create .torrent manually + add via API ────

    def create_torrent_v4(self, file_path: str,
                          trackers: Optional[list] = None) -> str:
        """Create .torrent in pure Python, add to qBittorrent, return info hash."""
        self.ensure_login()
        if trackers is None:
            trackers = PUBLIC_TRACKERS

        torrent_bytes, info_hash = _create_torrent_bytes(file_path, trackers)

        # multipart/form-data upload
        boundary = "----OpenPartyBoundary"
        body = b""

        # 1. torrent file
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="torrents"; filename="party.torrent"\r\n'
        body += b"Content-Type: application/x-bittorrent\r\n\r\n"
        body += torrent_bytes
        body += b"\r\n"

        # 2. savepath = directory containing the file
        save_dir = os.path.dirname(os.path.abspath(file_path))
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="savepath"\r\n\r\n'
        body += save_dir.encode() + b"\r\n"

        # 3. paused = false  (start seeding immediately)
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="paused"\r\n\r\n'
        body += b"false\r\n"

        body += f"--{boundary}--\r\n".encode()

        ct = f"multipart/form-data; boundary={boundary}"
        self._post("/api/v2/torrents/add", raw_body=body, content_type=ct)

        return info_hash

    # ── torrent list / magnet ────────────────────────────────

    def get_magnet_link(self, info_hash: str, name: str = "",
                        trackers: Optional[list] = None) -> str:
        """Build a magnet URI from an info hash."""
        if trackers is None:
            trackers = PUBLIC_TRACKERS
        parts = [f"magnet:?xt=urn:btih:{info_hash}"]
        if name:
            parts.append(f"&dn={urllib.parse.quote(name)}")
        for tr in trackers:
            parts.append(f"&tr={urllib.parse.quote(tr)}")
        return "".join(parts)

    # ── convenience: full flow ───────────────────────────────

    def create_and_seed(self, file_path: str) -> Tuple[str, str]:
        """Create a torrent, start seeding, return (magnet_link, info_hash)."""
        self.ensure_login()
        name = os.path.basename(file_path)

        if self.supports_torrent_creator():
            task_id = self.create_torrent_v5(file_path)
            info_hash = self.poll_torrent_creator(task_id)
        else:
            info_hash = self.create_torrent_v4(file_path)

        magnet = self.get_magnet_link(info_hash, name)
        return magnet, info_hash


# ═══════════════════════════════════════════════════════════
# Pure-Python .torrent creator (no external dependencies)
# ═══════════════════════════════════════════════════════════

def _bencode(obj) -> bytes:
    """Bencode a Python object."""
    if isinstance(obj, int):
        return f"i{obj}e".encode()
    if isinstance(obj, bytes):
        return f"{len(obj)}:".encode() + obj
    if isinstance(obj, str):
        encoded = obj.encode("utf-8")
        return f"{len(encoded)}:".encode() + encoded
    if isinstance(obj, list):
        return b"l" + b"".join(_bencode(i) for i in obj) + b"e"
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: kv[0].encode() if isinstance(kv[0], str) else kv[0])
        result = b"d"
        for k, v in items:
            result += _bencode(k) + _bencode(v)
        result += b"e"
        return result
    raise TypeError(f"Cannot bencode {type(obj)}")


def _create_torrent_bytes(file_path: str,
                          trackers: list,
                          piece_length: int = 256 * 1024
                          ) -> Tuple[bytes, str]:
    """Create a .torrent file in memory.  Returns (torrent_bytes, info_hash_hex)."""
    file_path = os.path.abspath(file_path)
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    # Hash pieces
    pieces = b""
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(piece_length)
            if not chunk:
                break
            pieces += hashlib.sha1(chunk).digest()

    info = {
        "length": file_size,
        "name": file_name,
        "piece length": piece_length,
        "pieces": pieces,
    }

    info_bencoded = _bencode(info)
    info_hash = hashlib.sha1(info_bencoded).hexdigest()

    torrent = {
        "announce": trackers[0] if trackers else "",
        "announce-list": [[t] for t in trackers],
        "comment": "Created by OpenParty",
        "created by": "OpenParty",
        "creation date": int(time.time()),
        "info": info,
    }

    return _bencode(torrent), info_hash
