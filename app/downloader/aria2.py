import os
import subprocess
import json
import urllib.error
import urllib.request
import urllib.parse
import socket
import time
import secrets
import base64
import ipaddress
from logger import launcher_logger
from deps import find_aria2c
from torrent_creator import BITTORRENT_PORT_RANGE, FALLBACK_TRACKERS

class Aria2Error(Exception):
    pass


def _is_safe_tracker(value: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value)
        host = (parsed.hostname or "").rstrip(".").lower()
        port = parsed.port
    except ValueError:
        return False
    try:
        address = ipaddress.ip_address(host) if host else None
    except ValueError:
        address = None
    return bool(
        len(value) <= 2048
        and parsed.scheme.lower() in {"udp", "http", "https"}
        and host
        and not parsed.username
        and not parsed.password
        and host != "localhost"
        and not host.endswith((".localhost", ".local", ".internal", ".home.arpa"))
        and (address is None or address.is_global)
        and (port is None or 1 <= port <= 65535)
    )

def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def generate_secret(length=16) -> str:
    """Generate an unpredictable RPC token for the local aria2 process."""
    return secrets.token_urlsafe(max(1, length))[:length]

class Aria2Manager:
    def __init__(self):
        self.process = None
        self.port = get_free_port()
        self.secret = generate_secret()
        self.rpc_url = f"http://127.0.0.1:{self.port}/jsonrpc"
        self._request_id = 0

    def start(self, save_dir: str):
        if self.process is not None:
            if self.process.poll() is None:
                self.stop()
            else:
                self.process = None

        exe = find_aria2c()
        if not exe:
            raise Aria2Error("aria2c not found. Please run setup.cmd.")
            
        os.makedirs(save_dir, exist_ok=True)
        
        cmd = [
            exe,
            "--no-conf=true",
            "--enable-rpc=true",
            "--rpc-listen-all=false",
            f"--rpc-listen-port={self.port}",
            f"--rpc-secret={self.secret}",
            "--daemon=false",
            f"--dir={save_dir}",
            "--bt-metadata-only=false",
            "--bt-save-metadata=true",
            "--enable-dht=true",
            "--enable-peer-exchange=true",
            "--bt-enable-lpd=true",
            "--follow-torrent=mem",
            f"--listen-port={BITTORRENT_PORT_RANGE}",
            f"--dht-listen-port={BITTORRENT_PORT_RANGE}",
            "--bt-max-peers=100",
            "--file-allocation=none",
            "--seed-ratio=0.0",
            "--summary-interval=0",
            "--console-log-level=error",
            "--bt-tracker=" + ",".join(FALLBACK_TRACKERS),
        ]
        
        # Start detached without showing a console window on Windows
        creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        self.process = subprocess.Popen(
            cmd,
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        # Wait for RPC to be available
        for _ in range(30):
            time.sleep(0.1)
            if self.process.poll() is not None:
                break
            try:
                version = self.get_version()
                if not isinstance(version, dict) or not version.get("version"):
                    continue
                launcher_logger.info(f"aria2c started on port {self.port}")
                return
            except Exception:
                pass
        
        self.stop()
        raise Aria2Error("aria2c failed to start or bind to RPC port.")

    def stop(self):
        proc = self.process
        self.process = None
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass
            launcher_logger.info("aria2c stopped.")

    def _call(self, method: str, params: list = None):
        if params is None:
            params = []
        actual_params = [f"token:{self.secret}"] + params
        
        self._request_id += 1
        req_data = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": actual_params
        }
        
        req = urllib.request.Request(self.rpc_url, data=json.dumps(req_data).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        try:
            # Never route the local RPC request through environment proxies.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                if "error" in result:
                    raise Aria2Error(result["error"].get("message", "Unknown RPC Error"))
                return result.get("result")
        except urllib.error.URLError as e:
            raise Aria2Error(f"RPC Connection Error: {e}")

    def get_version(self):
        return self._call("aria2.getVersion")

    def add_uri(self, uri: str) -> str:
        """Add a validated magnet link for download. Returns the GID."""
        clean_uri = uri.strip()
        if len(clean_uri) > 16384:
            raise Aria2Error("Magnet link is too long.")
        try:
            parsed = urllib.parse.urlsplit(clean_uri)
            query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        except ValueError as e:
            raise Aria2Error("Invalid magnet link.") from e
        if parsed.scheme.lower() != "magnet" or not any(
            key.lower() == "xt" and value.strip() for key, value in query
        ):
            raise Aria2Error("A magnet link with an xt topic is required.")

        # Keep only metadata and valid public tracker parameters. Web seeds and
        # alternative sources could make an invite fetch arbitrary HTTP URLs.
        safe_query = []
        for key, value in query:
            lowered = key.lower()
            if lowered == "xt" and value.strip():
                safe_query.append(("xt", value))
            elif lowered == "dn" and value.strip():
                safe_query.append(("dn", value[:255]))
            elif lowered == "tr" and _is_safe_tracker(value):
                safe_query.append(("tr", value))
            elif lowered == "tr" and value.strip():
                raise Aria2Error("Magnet link contains a tracker that is not a public UDP or HTTP(S) URL.")

        if not any(key == "tr" for key, _ in safe_query):
            safe_query.extend(("tr", tracker) for tracker in FALLBACK_TRACKERS)
        clean_uri = urllib.parse.urlunsplit((
            "magnet", "", "", urllib.parse.urlencode(safe_query), ""
        ))
        return self._call("aria2.addUri", [[clean_uri]])

    def add_torrent(self, torrent_path: str) -> str:
        """Add a .torrent file for download. Returns the GID."""
        with open(torrent_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return self._call("aria2.addTorrent", [b64])

    def add_torrent_bytes(self, torrent_bytes: bytes, web_seeds=None) -> str:
        """Start a verified embedded torrent with optional host web seeds.

        Callers pass bytes only after config validation has checked their info
        hash against the invite magnet. The web-seed list is deliberately not
        read from a generic magnet parameter.
        """
        if not isinstance(torrent_bytes, bytes) or not torrent_bytes:
            raise Aria2Error("The party does not contain valid torrent metadata.")
        if len(torrent_bytes) > 512 * 1024:
            raise Aria2Error("The embedded torrent metadata is too large.")
        seeds = list(web_seeds or [])
        if any(not isinstance(url, str) or len(url) > 2048 for url in seeds):
            raise Aria2Error("The party contains an invalid direct host route.")
        payload = base64.b64encode(torrent_bytes).decode("ascii")
        return self._call("aria2.addTorrent", [payload, seeds])

    def get_status(self, gid: str):
        """Returns status dictionary from aria2c."""
        status = self._call("aria2.tellStatus", [gid, [
            "gid", "status", "totalLength", "completedLength", "uploadLength",
            "downloadSpeed", "uploadSpeed", "infoHash", "numPieces", "numSeeders",
            "connections", "seeder", "errorCode", "errorMessage", "followedBy", "files",
        ]])
        if not isinstance(status, dict):
            raise Aria2Error("aria2c returned an invalid download status.")
        return status

    def get_peers(self, gid: str):
        """Return live BitTorrent peers for a download GID."""
        peers = self._call("aria2.getPeers", [gid])
        if not isinstance(peers, list):
            return []
        return [peer for peer in peers if isinstance(peer, dict)]
        
    def remove(self, gid: str):
        """Removes a download."""
        try:
            self._call("aria2.remove", [gid])
        except Exception:
            pass
