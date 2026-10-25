"""
Torrent creator and seeder for OpenParty.

Pure-Python .torrent file generation and magnet link building.
Seeding is handled via aria2c (the same download engine already required
by OpenParty), so no extra dependencies are needed.

QBitClient is retained as a secondary fallback if qBittorrent happens
to be running with its Web API enabled.
"""

import json
import os
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import subprocess
import socket
import random
import string
from typing import Optional, Tuple

import atexit

# ---------- public tracker list for magnet links ----------
PUBLIC_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://explodie.org:6969/announce",
    "udp://p4p.arenabg.com:1337/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://opentracker.i2p.rocks:6969/announce",
    "udp://open.demonii.com:1337/announce",
    "http://tracker.openbittorrent.com:80/announce",
]
FALLBACK_TRACKERS = PUBLIC_TRACKERS

def get_optimal_piece_length(file_size: int) -> int:
    """Calculate an optimal BitTorrent piece size based on file size."""
    if file_size < 50 * 1024 * 1024:
        return 64 * 1024            # 64 KB
    elif file_size < 512 * 1024 * 1024:
        return 256 * 1024           # 256 KB
    elif file_size < 2 * 1024**3:
        return 1024 * 1024          # 1 MB
    elif file_size < 8 * 1024**3:
        return 2 * 1024 * 1024      # 2 MB
    else:
        return 4 * 1024 * 1024      # 4 MB


# ═══════════════════════════════════════════════════════════
# Pure-Python .torrent creator and bencode/bdecode
# ═══════════════════════════════════════════════════════════

def bencode(obj) -> bytes:
    """Bencode a Python object."""
    if isinstance(obj, int):
        return f"i{obj}e".encode()
    if isinstance(obj, bytes):
        return f"{len(obj)}:".encode() + obj
    if isinstance(obj, str):
        encoded = obj.encode("utf-8")
        return f"{len(encoded)}:".encode() + encoded
    if isinstance(obj, list):
        return b"l" + b"".join(bencode(i) for i in obj) + b"e"
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: kv[0].encode() if isinstance(kv[0], str) else kv[0])
        result = b"d"
        for k, v in items:
            result += bencode(k) + bencode(v)
        result += b"e"
        return result
    raise TypeError(f"Cannot bencode {type(obj)}")


_bencode = bencode


def bdecode(data: bytes):
    """Decode bencoded bytes into Python objects."""
    def _decode_item(idx: int):
        b = data[idx:idx+1]
        if b == b"i":
            end = data.index(b"e", idx + 1)
            return int(data[idx+1:end]), end + 1
        elif b == b"l":
            items = []
            curr = idx + 1
            while data[curr:curr+1] != b"e":
                item, curr = _decode_item(curr)
                items.append(item)
            return items, curr + 1
        elif b == b"d":
            d = {}
            curr = idx + 1
            while data[curr:curr+1] != b"e":
                key, curr = _decode_item(curr)
                val, curr = _decode_item(curr)
                d[key] = val
            return d, curr + 1
        elif b.isdigit():
            colon = data.index(b":", idx)
            length = int(data[idx:colon])
            start = colon + 1
            return data[start:start+length], start + length
        raise ValueError(f"Invalid bencode byte at index {idx}: {b}")

    res, _ = _decode_item(0)
    return res


def _create_torrent_bytes(file_path: str,
                          trackers: list,
                          piece_length: Optional[int] = None
                          ) -> Tuple[bytes, str]:
    """Create a .torrent file in memory.  Returns (torrent_bytes, info_hash_hex)."""
    file_path = os.path.abspath(file_path)
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    if piece_length is None:
        piece_length = get_optimal_piece_length(file_size)

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


def build_magnet_link(info_hash: str, name: str = "",
                      trackers: Optional[list] = None) -> str:
    """Build a magnet URI from an info hash. Pure string operation, no network."""
    if trackers is None:
        trackers = PUBLIC_TRACKERS
    parts = [f"magnet:?xt=urn:btih:{info_hash}"]
    if name:
        parts.append(f"&dn={urllib.parse.quote(name)}")
    for tr in trackers:
        parts.append(f"&tr={urllib.parse.quote(tr)}")
    return "".join(parts)


def create_local_torrent(file_path: str,
                         output_torrent_path: Optional[str] = None,
                         trackers: Optional[list] = None) -> Tuple[str, str, str]:
    """Pure-Python torrent generator without external dependencies.
    Returns (magnet_link, info_hash, torrent_file_path).
    """
    if trackers is None:
        trackers = PUBLIC_TRACKERS
    torrent_bytes, info_hash = _create_torrent_bytes(file_path, trackers)

    if not output_torrent_path:
        base_dir = os.path.dirname(os.path.abspath(file_path))
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_torrent_path = os.path.join(base_dir, f"{base_name}.torrent")

    with open(output_torrent_path, "wb") as f:
        f.write(torrent_bytes)

    magnet = build_magnet_link(info_hash, os.path.basename(file_path), trackers)
    return magnet, info_hash, output_torrent_path


# ═══════════════════════════════════════════════════════════
# aria2c-based seeder (uses the same tool the joiner uses)
# ═══════════════════════════════════════════════════════════

def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def seed_with_aria2c(torrent_path: str, data_dir: str,
                     aria2c_exe: Optional[str] = None) -> Optional[subprocess.Popen]:
    """Start aria2c in seed-only mode for an already-complete torrent.

    Args:
        torrent_path: Path to the .torrent file.
        data_dir: Directory containing the actual media file.
        aria2c_exe: Path to aria2c executable (auto-detected if None).

    Returns:
        The Popen process handle, or None on failure.
    """
    if not aria2c_exe:
        from deps import find_aria2c
        aria2c_exe = find_aria2c()
    if not aria2c_exe:
        return None

    rpc_port = _get_free_port()
    secret = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    cmd = [
        aria2c_exe,
        "--enable-rpc=true",
        f"--rpc-listen-port={rpc_port}",
        f"--rpc-secret={secret}",
        "--rpc-allow-origin-all",
        "--daemon=false",
        f"--dir={data_dir}",
        "--bt-metadata-only=false",
        "--bt-save-metadata=false",
        "--enable-dht=true",
        "--enable-peer-exchange=true",
        "--bt-enable-lpd=true",
        "--bt-seed-unverified=true",
        "--seed-ratio=0.0",        # seed indefinitely (no ratio limit)
        "--listen-port=6881-6999",
        "--dht-listen-port=6881-6999",
        "--bt-max-peers=100",
        "--file-allocation=none",
        "--summary-interval=0",
        "--console-log-level=error",
        "--bt-tracker=" + ",".join(PUBLIC_TRACKERS),
        torrent_path,
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Give it a moment to start
        time.sleep(0.5)
        if proc.poll() is not None:
            return None
        return proc
    except Exception:
        return None


class SeederManager:
    """Manages active aria2c seeding processes across the application."""
    _active_seed_process: Optional[subprocess.Popen] = None
    _active_torrent_path: Optional[str] = None
    _active_file_path: Optional[str] = None

    @classmethod
    def set_seed_process(cls, proc: subprocess.Popen, torrent_path: str, file_path: str):
        cls.stop_seeding()
        cls._active_seed_process = proc
        cls._active_torrent_path = torrent_path
        cls._active_file_path = file_path

    @classmethod
    def stop_seeding(cls):
        if cls._active_seed_process:
            try:
                cls._active_seed_process.terminate()
                cls._active_seed_process.wait(timeout=2)
            except Exception:
                try:
                    cls._active_seed_process.kill()
                except Exception:
                    pass
            cls._active_seed_process = None
            cls._active_torrent_path = None
            cls._active_file_path = None

    @classmethod
    def is_seeding(cls) -> bool:
        return cls._active_seed_process is not None and cls._active_seed_process.poll() is None

    @classmethod
    def get_current_file(cls) -> Optional[str]:
        return cls._active_file_path


atexit.register(SeederManager.stop_seeding)


# ═══════════════════════════════════════════════════════════
# QBitClient — secondary fallback for seeding via qBittorrent
# ═══════════════════════════════════════════════════════════

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

    # -- helpers --

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
            with self._opener.open(req, timeout=10) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise QBitError(f"HTTP {e.code} from {path}: {e.read().decode(errors='replace')}") from e

    # -- auth --

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

    # -- add torrent to seed --

    def add_torrent_for_seeding(self, torrent_path: str, save_dir: str) -> None:
        """Upload a .torrent file to qBittorrent and start seeding."""
        self.ensure_login()

        with open(torrent_path, "rb") as f:
            torrent_bytes = f.read()

        boundary = "----OpenPartyBoundary"
        body = b""

        # 1. torrent file
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="torrents"; filename="party.torrent"\r\n'
        body += b"Content-Type: application/x-bittorrent\r\n\r\n"
        body += torrent_bytes
        body += b"\r\n"

        # 2. savepath = directory containing the file
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
