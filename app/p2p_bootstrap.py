"""Authenticated, per-party LAN/bootstrap service for deterministic first contact.

The service is intentionally small: it exposes a private tracker and an HTTP
web seed for one file.  Both routes contain an unguessable party token and are
stopped with the active host seeder.  The torrent itself remains the transfer
format; the HTTP source prevents a fresh guest from being stranded while DHT
and public trackers find the swarm.
"""

from __future__ import annotations

import base64
import hmac
import ipaddress
import os
import secrets
import socket
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Iterable, List, Optional, Tuple


BITTORRENT_PORT = 51413
BOOTSTRAP_PORT = 51414
MAX_TRACKER_PEERS = 80


def _bencode(value) -> bytes:
    if isinstance(value, int):
        return f"i{value}e".encode("ascii")
    if isinstance(value, bytes):
        return str(len(value)).encode("ascii") + b":" + value
    if isinstance(value, str):
        return _bencode(value.encode("utf-8"))
    if isinstance(value, list):
        return b"l" + b"".join(_bencode(item) for item in value) + b"e"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: item[0] if isinstance(item[0], bytes) else str(item[0]).encode("utf-8"))
        return b"d" + b"".join(_bencode(key) + _bencode(item) for key, item in items) + b"e"
    raise TypeError(f"Unsupported bencode value: {type(value)!r}")


def _is_usable_ipv4(value: str) -> bool:
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        return False
    return not (address.is_loopback or address.is_unspecified or address.is_link_local or address.is_multicast)


def local_ipv4_addresses() -> List[str]:
    """Return likely LAN addresses, with the active route first when known."""
    found: List[str] = []

    def add(value: str) -> None:
        if _is_usable_ipv4(value) and value not in found:
            found.append(value)

    # UDP connect chooses the interface without sending any packet.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("1.1.1.1", 80))
            add(probe.getsockname()[0])
    except OSError:
        pass

    try:
        _, _, addresses = socket.gethostbyname_ex(socket.gethostname())
        for address in addresses:
            add(address)
    except OSError:
        pass

    # Prefer RFC1918 interfaces. A host with a public address still receives a
    # usable direct endpoint if no LAN interface was found.
    found.sort(key=lambda value: (not ipaddress.IPv4Address(value).is_private, value))
    return found[:6]


def is_same_lan_address(host: str) -> bool:
    """Accept RFC1918 bootstrap routes only when they share a /24 with us."""
    try:
        target = ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        return False
    if not target.is_private:
        return False
    for local in local_ipv4_addresses():
        try:
            if target in ipaddress.IPv4Network(f"{local}/24", strict=False):
                return True
        except ipaddress.AddressValueError:
            continue
    return False


def normalize_public_ipv4(value: str) -> Optional[str]:
    try:
        address = ipaddress.IPv4Address(value.strip())
    except ipaddress.AddressValueError:
        return None
    return str(address) if address.is_global else None


def discover_public_ipv4(timeout: float = 2.5) -> Optional[str]:
    """Best-effort public address lookup. It is optional and never required for LAN."""
    try:
        import urllib.request

        request = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "OpenParty/1.0"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:
            return normalize_public_ipv4(response.read(64).decode("ascii", "strict"))
    except Exception:
        return None


class _BootstrapHttpServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class _BootstrapHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "OpenPartyBootstrap/1.0"

    def log_message(self, fmt, *args):
        # Request details include the bearer token in the URL. Never write it
        # to standard output or application logs.
        return

    @property
    def party(self) -> "PartyBootstrap":
        return self.server.party  # type: ignore[attr-defined]

    def do_HEAD(self):
        self._dispatch(send_body=False)

    def do_GET(self):
        self._dispatch(send_body=True)

    def _dispatch(self, *, send_body: bool) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        segments = [segment for segment in parsed.path.split("/") if segment]
        if len(segments) != 2 or not hmac.compare_digest(segments[0], self.party.token):
            self.send_error(404)
            return
        route = segments[1]
        if route == "announce":
            self._announce(parsed.query, send_body)
        elif route == "media":
            self._media(send_body)
        elif route == "torrent":
            self._torrent(send_body)
        else:
            self.send_error(404)

    def _announce(self, query: str, send_body: bool) -> None:
        try:
            info_hash, port = self.party.parse_announce(query)
            if info_hash != self.party.info_hash_bytes:
                raise ValueError("wrong torrent")
            remote_ip = self.client_address[0]
            self.party.note_peer(remote_ip, port)
            peers = self.party.compact_peers_for(remote_ip, port)
            body = _bencode({b"interval": 20, b"min interval": 10, b"peers": peers})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if send_body:
                self.wfile.write(body)
        except Exception:
            # Return a bencoded tracker failure rather than HTML so aria2 can
            # keep using other discovery mechanisms.
            body = _bencode({b"failure reason": b"OpenParty bootstrap request was invalid"})
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)

    def _torrent(self, send_body: bool) -> None:
        payload = self.party.torrent_bytes
        if not payload:
            self.send_error(503)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/x-bittorrent")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def _media(self, send_body: bool) -> None:
        try:
            size = os.path.getsize(self.party.file_path)
            start, end = self._parse_range(size)
        except (OSError, ValueError):
            self.send_error(416)
            return

        length = end - start + 1
        partial = start != 0 or end != size - 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not send_body:
            return
        sent = 0
        try:
            with open(self.party.file_path, "rb") as stream:
                stream.seek(start)
                remaining = length
                while remaining:
                    chunk = stream.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    sent += len(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            if sent:
                self.party.note_webseed_transfer(self.client_address[0], sent)

    def _parse_range(self, size: int) -> Tuple[int, int]:
        if size <= 0:
            raise ValueError("empty media")
        value = self.headers.get("Range", "").strip()
        if not value:
            return 0, size - 1
        if not value.startswith("bytes=") or "," in value:
            raise ValueError("unsupported range")
        begin, _, end = value[6:].partition("-")
        if not begin:
            suffix = int(end)
            if suffix <= 0:
                raise ValueError("invalid suffix")
            return max(0, size - suffix), size - 1
        start = int(begin)
        finish = int(end) if end else size - 1
        if start < 0 or start >= size or finish < start:
            raise ValueError("invalid range")
        return start, min(finish, size - 1)


class PartyBootstrap:
    """One authenticated tracker/web-seed endpoint attached to a host party."""

    def __init__(self, file_path: str, public_host: str = ""):
        self.file_path = os.path.abspath(file_path)
        self.token = secrets.token_urlsafe(32)
        self.peer_port = BITTORRENT_PORT
        self.local_addresses = local_ipv4_addresses()
        self.public_host = normalize_public_ipv4(public_host) or discover_public_ipv4()
        self.info_hash_bytes = b""
        self.torrent_bytes = b""
        self._lock = threading.RLock()
        self._peers: Dict[Tuple[str, int], float] = {}
        self._webseed_transfers: Dict[str, Tuple[int, float]] = {}
        self._closed = False

        self._server = _BootstrapHttpServer(("0.0.0.0", BOOTSTRAP_PORT), _BootstrapHandler)
        self._server.party = self  # type: ignore[attr-defined]
        self.port = int(self._server.server_address[1])
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="OpenParty bootstrap",
            daemon=True,
        )
        self._thread.start()

    def configure(self, torrent_path: str, info_hash_hex: str) -> None:
        with open(torrent_path, "rb") as stream:
            torrent = stream.read()
        if not torrent or len(torrent) > 768 * 1024:
            raise ValueError("The torrent metadata is too large to include in a party invite.")
        try:
            info_hash = bytes.fromhex(info_hash_hex)
        except ValueError as exc:
            raise ValueError("The torrent info hash is invalid.") from exc
        if len(info_hash) != 20:
            raise ValueError("The torrent info hash is invalid.")
        with self._lock:
            self.torrent_bytes = torrent
            self.info_hash_bytes = info_hash

    def base_urls(self) -> List[Tuple[str, str, str]]:
        """Return (scope, advertised-host, base-url) tuples."""
        endpoints: List[Tuple[str, str, str]] = []
        for address in self.local_addresses:
            endpoints.append(("lan", address, f"http://{address}:{self.port}/{self.token}"))
        if self.public_host and self.public_host not in self.local_addresses:
            endpoints.append(("public", self.public_host, f"http://{self.public_host}:{self.port}/{self.token}"))
        return endpoints

    def tracker_urls(self) -> List[str]:
        return [f"{base}/announce" for _, _, base in self.base_urls()]

    def invite_payload(self) -> dict:
        if not self.torrent_bytes or len(self.info_hash_bytes) != 20:
            raise RuntimeError("Bootstrap service is not configured for a torrent.")
        endpoints = []
        for scope, address, base in self.base_urls():
            endpoints.append({
                "scope": scope,
                "base_url": base,
                "peer_host": address,
                "peer_port": self.peer_port,
            })
        if not endpoints:
            raise RuntimeError("No usable network address was found for the host.")
        return {
            "version": 1,
            "torrent": base64.b64encode(self.torrent_bytes).decode("ascii"),
            "endpoints": endpoints,
        }

    def parse_announce(self, raw_query: str) -> Tuple[bytes, int]:
        info_hash = None
        port = None
        for part in raw_query.split("&"):
            key, separator, value = part.partition("=")
            if not separator:
                continue
            if key == "info_hash":
                info_hash = urllib.parse.unquote_to_bytes(value)
            elif key == "port":
                try:
                    port = int(value)
                except ValueError:
                    pass
        if info_hash is None or len(info_hash) != 20 or port is None or not 1 <= port <= 65535:
            raise ValueError("missing announce data")
        return info_hash, port

    def _is_lan_client(self, address: str) -> bool:
        try:
            target = ipaddress.IPv4Address(address)
        except ipaddress.AddressValueError:
            return False
        for local in self.local_addresses:
            if target in ipaddress.IPv4Network(f"{local}/24", strict=False):
                return True
        return False

    def note_peer(self, address: str, port: int) -> None:
        if not _is_usable_ipv4(address) or not 1 <= port <= 65535:
            return
        with self._lock:
            self._peers[(address, port)] = time.monotonic()
            self._prune_locked()

    def compact_peers_for(self, request_ip: str, request_port: int) -> bytes:
        now = time.monotonic()
        with self._lock:
            self._prune_locked(now)
            peers: List[Tuple[str, int]] = []
            # A LAN guest gets an immediate direct route to the host. A remote
            # guest receives it only when the invite has an advertised public IP.
            if self._is_lan_client(request_ip):
                request_address = ipaddress.IPv4Address(request_ip)
                matching = next((address for address in self.local_addresses
                                 if request_address in ipaddress.IPv4Network(f"{address}/24", strict=False)), None)
                if matching:
                    peers.append((matching, self.peer_port))
            elif self.public_host:
                peers.append((self.public_host, self.peer_port))
            for peer, seen_at in self._peers.items():
                if now - seen_at <= 90 and peer != (request_ip, request_port):
                    peers.append(peer)

        result = bytearray()
        seen = set()
        for address, port in peers:
            if (address, port) in seen or not _is_usable_ipv4(address):
                continue
            seen.add((address, port))
            result.extend(socket.inet_aton(address))
            result.extend(port.to_bytes(2, "big"))
            if len(seen) >= MAX_TRACKER_PEERS:
                break
        return bytes(result)

    def note_webseed_transfer(self, address: str, amount: int) -> None:
        if not _is_usable_ipv4(address) or amount <= 0:
            return
        with self._lock:
            previous, _ = self._webseed_transfers.get(address, (0, 0.0))
            self._webseed_transfers[address] = (previous + amount, time.monotonic())

    def status(self) -> dict:
        with self._lock:
            self._prune_locked()
            return {
                "port": self.port,
                "lan_addresses": list(self.local_addresses),
                "public_host": self.public_host or "",
                "tracker_peers": len(self._peers),
                "webseed_clients": len(self._webseed_transfers),
                "webseed_bytes": sum(item[0] for item in self._webseed_transfers.values()),
            }

    def _prune_locked(self, now: Optional[float] = None) -> None:
        now = now if now is not None else time.monotonic()
        self._peers = {peer: seen for peer, seen in self._peers.items() if now - seen <= 90}
        self._webseed_transfers = {
            address: item for address, item in self._webseed_transfers.items()
            if now - item[1] <= 120
        }

    def stop(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class PartyBootstrapManager:
    """Owns the single active party bootstrap endpoint."""

    _active: Optional[PartyBootstrap] = None
    _lock = threading.RLock()

    @classmethod
    def start(cls, file_path: str, public_host: str = "") -> PartyBootstrap:
        cls.stop()
        session = PartyBootstrap(file_path, public_host)
        with cls._lock:
            cls._active = session
        return session

    @classmethod
    def current(cls) -> Optional[PartyBootstrap]:
        with cls._lock:
            return cls._active

    @classmethod
    def status(cls) -> Optional[dict]:
        session = cls.current()
        return session.status() if session else None

    @classmethod
    def stop(cls) -> None:
        with cls._lock:
            session = cls._active
            cls._active = None
        if session:
            session.stop()

