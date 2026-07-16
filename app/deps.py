import os
import sys
import shutil
from typing import Dict, Optional

# Common search locations beyond PATH
_WINGET_LINKS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")
_USER_PROGRAMS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")

def _search_paths(name: str, extra_dirs: list[str]) -> Optional[str]:
    """Search for an executable in PATH, WinGet Links, and extra directories."""
    # 1. Standard PATH lookup
    found = shutil.which(name)
    if found:
        return found

    # 2. WinGet Links (winget installs symlinks here)
    if os.path.isdir(_WINGET_LINKS):
        candidate = os.path.join(_WINGET_LINKS, name)
        if os.path.isfile(candidate):
            return candidate

    # 3. Extra known directories
    for d in extra_dirs:
        if os.path.isdir(d):
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate):
                return candidate

    return None


def _get_portable_paths(tool_name: str) -> list[str]:
    """Get potential portable tool directories whether frozen or not."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        base_dirs = [exe_dir, os.path.join(exe_dir, "..")]
    else:
        base_dirs = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]
    
    return [os.path.join(b, "setup", "tools", tool_name) for b in base_dirs]


def find_vlc() -> Optional[str]:
    """Find VLC executable path."""
    return _search_paths("vlc.exe", [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
    ])


def find_syncplay() -> Optional[str]:
    """Find Syncplay executable path."""
    return _search_paths("Syncplay.exe", [
        r"C:\Program Files\Syncplay",
        r"C:\Program Files (x86)\Syncplay",
        os.path.join(_USER_PROGRAMS, "Syncplay"),
        os.path.join(os.environ.get("APPDATA", ""), "Syncplay"),
    ] + _get_portable_paths("syncplay"))


def find_aria2c() -> Optional[str]:
    """Find aria2c executable path."""
    return _search_paths("aria2c.exe", _get_portable_paths("aria2"))


def find_qbittorrent() -> Optional[str]:
    """Find qBittorrent executable path."""
    return _search_paths("qbittorrent.exe", [
        r"C:\Program Files\qBittorrent",
        r"C:\Program Files (x86)\qBittorrent",
    ])


def check_dependencies() -> Dict[str, bool]:
    """
    Check if required software is available.
    Returns a dictionary of dependency statuses.
    """
    return {
        "vlc": find_vlc() is not None,
        "syncplay": find_syncplay() is not None,
        "aria2c": find_aria2c() is not None,
    }
