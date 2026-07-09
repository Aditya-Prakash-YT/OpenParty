import os
import shutil
from typing import Dict, Optional

def find_vlc() -> Optional[str]:
    """Find VLC executable path."""
    paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
    ]
    for p in paths:
        if os.path.isfile(p):
            return p
    return shutil.which("vlc")

def find_syncplay() -> Optional[str]:
    """Find Syncplay executable path."""
    paths = [
        r"C:\Program Files\Syncplay\Syncplay.exe",
        r"C:\Program Files (x86)\Syncplay\Syncplay.exe"
    ]
    for p in paths:
        if os.path.isfile(p):
            return p
    return shutil.which("syncplay")

def find_aria2c() -> Optional[str]:
    """Find aria2c executable path."""
    # Winget adds aria2c to the system PATH.
    return shutil.which("aria2c")

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
