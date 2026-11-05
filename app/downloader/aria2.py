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
from logger import launcher_logger
from deps import find_aria2c
from torrent_creator import FALLBACK_TRACKERS

class Aria2Error(Exception):
    pass

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
            f"--rpc-listen-port={self.port}",
            f"--rpc-secret={self.secret}",
            "--rpc-allow-origin-all",
            "--daemon=false",
            f"--dir={save_dir}",
            "--bt-metadata-only=false",
            "--bt-save-metadata=true",
            "--enable-dht=true",
            "--enable-peer-exchange=true",
            "--bt-enable-lpd=true",
            "--follow-torrent=mem",
            "--listen-port=6881-6999",
            "--dht-listen-port=6881-6999",
            "--bt-max-peers=100",
            "--file-allocation=none",
            "--seed-time=0",
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
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                if "error" in result:
                    raise Aria2Error(result["error"].get("message", "Unknown RPC Error"))
                return result.get("result")
        except urllib.error.URLError as e:
            raise Aria2Error(f"RPC Connection Error: {e}")

    def get_version(self):
        return self._call("aria2.getVersion")

    def add_uri(self, uri: str) -> str:
        """Add a URI (magnet link or HTTP URL) for download. Returns the GID."""
        clean_uri = uri.strip()
        # If it's a magnet link without trackers, append public trackers for faster peer discovery
        if clean_uri.startswith("magnet:") and "&tr=" not in clean_uri:
            for tr in FALLBACK_TRACKERS:
                clean_uri += f"&tr={urllib.parse.quote(tr)}"
        return self._call("aria2.addUri", [[clean_uri]])

    def add_torrent(self, torrent_path: str) -> str:
        """Add a .torrent file for download. Returns the GID."""
        with open(torrent_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return self._call("aria2.addTorrent", [b64])

    def get_status(self, gid: str):
        """Returns status dictionary from aria2c."""
        status = self._call("aria2.tellStatus", [gid])
        if not isinstance(status, dict):
            raise Aria2Error("aria2c returned an invalid download status.")
        return status
        
    def remove(self, gid: str):
        """Removes a download."""
        try:
            self._call("aria2.remove", [gid])
        except Exception:
            pass
