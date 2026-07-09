import os
import subprocess
import json
import urllib.request
import socket
import time
import random
import string
import base64
from logger import launcher_logger
from deps import find_aria2c

class Aria2Error(Exception):
    pass

def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def generate_secret(length=16) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class Aria2Manager:
    def __init__(self):
        self.process = None
        self.port = get_free_port()
        self.secret = generate_secret()
        self.rpc_url = f"http://127.0.0.1:{self.port}/jsonrpc"
        self._request_id = 0

    def start(self, save_dir: str):
        exe = find_aria2c()
        if not exe:
            raise Aria2Error("aria2c not found. Please run setup.cmd.")
            
        os.makedirs(save_dir, exist_ok=True)
        
        cmd = [
            exe,
            "--enable-rpc=true",
            f"--rpc-listen-port={self.port}",
            f"--rpc-secret={self.secret}",
            "--rpc-allow-origin-all",
            "--daemon=false",
            f"--dir={save_dir}",
            "--bt-metadata-only=false",
            "--bt-save-metadata=true",
            "--seed-time=0",
            "--summary-interval=0",
            "--console-log-level=error"
        ]
        
        # Start detached without showing a console window on Windows
        CREATE_NO_WINDOW = 0x08000000
        self.process = subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for RPC to be available
        for _ in range(20):
            time.sleep(0.1)
            try:
                self.get_version()
                launcher_logger.info(f"aria2c started on port {self.port}")
                return
            except Exception:
                pass
        
        self.stop()
        raise Aria2Error("aria2c failed to start or bind to RPC port.")

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                self.process.kill()
            self.process = None
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
            with urllib.request.urlopen(req, timeout=2) as response:
                result = json.loads(response.read().decode('utf-8'))
                if "error" in result:
                    raise Aria2Error(result["error"].get("message", "Unknown RPC Error"))
                return result.get("result")
        except urllib.error.URLError as e:
            raise Aria2Error(f"RPC Connection Error: {e}")

    def get_version(self):
        return self._call("aria2.getVersion")

    def add_uri(self, uri: str) -> str:
        """Returns the GID of the new download."""
        return self._call("aria2.addUri", [[uri]])

    def add_torrent(self, torrent_path: str) -> str:
        """Returns the GID of the new download."""
        with open(torrent_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return self._call("aria2.addTorrent", [b64])

    def get_status(self, gid: str):
        """Returns status dictionary from aria2c."""
        return self._call("aria2.tellStatus", [gid])
        
    def remove(self, gid: str):
        """Removes a download."""
        try:
            self._call("aria2.remove", [gid])
        except Exception:
            pass
