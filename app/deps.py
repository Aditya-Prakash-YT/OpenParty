import os
import sys
import shutil
import zipfile
from typing import Dict, Optional

# Common search locations beyond PATH
_WINGET_LINKS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")
_USER_PROGRAMS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")

def _search_paths(name: str, extra_dirs: list[str]) -> Optional[str]:
    """Prefer known install locations; use PATH only as a last resort."""
    # Prefer the app-managed tools and standard installation directories over
    # PATH, which can be modified by unrelated software or the current folder.
    for d in extra_dirs:
        if os.path.isdir(d):
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)

    # WinGet Links are a known per-user install location.
    if os.path.isdir(_WINGET_LINKS):
        candidate = os.path.join(_WINGET_LINKS, name)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    # PATH is retained for users with custom installs.
    found = shutil.which(name)
    if found:
        return os.path.abspath(found)

    return None


def _get_portable_paths(tool_name: str) -> list[str]:
    """Get potential portable tool directories whether frozen or running from source."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        base_dirs = [exe_dir, os.path.join(exe_dir, "..")]
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        repo_dir = os.path.abspath(os.path.join(app_dir, ".."))
        base_dirs = [app_dir, repo_dir]
    
    paths = [
        os.path.join(
            os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
            "OpenParty", "tools", tool_name,
        )
    ]
    for b in base_dirs:
        b_abs = os.path.abspath(b)
        paths.append(os.path.join(b_abs, "setup", "tools", tool_name))
        paths.append(os.path.join(b_abs, "tools", tool_name))
        paths.append(os.path.join(b_abs, f"{tool_name}-portable"))
        paths.append(os.path.join(b_abs, tool_name))
        paths.append(b_abs)
    return paths


def ensure_syncplay_unpacked():
    """Unpack syncplay-portable.zip if Syncplay.exe is not found but zip exists."""
    for p in _get_portable_paths("syncplay"):
        if os.path.isfile(os.path.join(p, "Syncplay.exe")):
            return
    
    app_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.abspath(os.path.join(app_dir, ".."))
    for base in [repo_dir, app_dir]:
        zip_candidate = os.path.join(base, "syncplay-portable.zip")
        if os.path.isfile(zip_candidate):
            try:
                dest = os.path.join(base, "syncplay-portable")
                os.makedirs(dest, exist_ok=True)
                with zipfile.ZipFile(zip_candidate, 'r') as zf:
                    root = os.path.realpath(dest)
                    members = zf.infolist()
                    if len(members) > 5000 or sum(item.file_size for item in members) > 512 * 1024 * 1024:
                        raise ValueError("Syncplay archive exceeds extraction limits")
                    for member in members:
                        # Reject absolute paths, parent traversal, and symlinks
                        # before writing any content from this archive.
                        target = os.path.realpath(os.path.join(root, member.filename))
                        if os.path.commonpath((root, target)) != root:
                            raise ValueError("Syncplay archive contains an unsafe path")
                        unix_mode = member.external_attr >> 16
                        if (unix_mode & 0o170000) == 0o120000:
                            raise ValueError("Syncplay archive contains a symbolic link")
                    zf.extractall(root)
                return
            except Exception:
                # Keep dependency detection non-fatal; find_syncplay will report
                # the dependency as missing and the UI can direct the user to setup.
                continue


def find_vlc() -> Optional[str]:
    """Find VLC executable path."""
    return _search_paths("vlc.exe", _get_portable_paths("vlc") + [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        os.path.join(_USER_PROGRAMS, "VideoLAN", "VLC"),
    ])


def find_syncplay() -> Optional[str]:
    """Find Syncplay executable path."""
    ensure_syncplay_unpacked()
    return _search_paths("Syncplay.exe", _get_portable_paths("syncplay") + [
        r"C:\Program Files\Syncplay",
        r"C:\Program Files (x86)\Syncplay",
        os.path.join(_USER_PROGRAMS, "Syncplay"),
        os.path.join(os.environ.get("APPDATA", ""), "Syncplay"),
    ])


def find_aria2c() -> Optional[str]:
    """Find aria2c executable path."""
    return _search_paths("aria2c.exe", _get_portable_paths("aria2") + _get_portable_paths("aria2c") + [
        r"C:\Program Files\aria2",
        r"C:\Program Files (x86)\aria2",
    ])


def find_qbittorrent() -> Optional[str]:
    """Find qBittorrent executable path."""
    return _search_paths("qbittorrent.exe", _get_portable_paths("qbittorrent") + [
        r"C:\Program Files\qBittorrent",
        r"C:\Program Files (x86)\qBittorrent",
        os.path.join(_USER_PROGRAMS, "qBittorrent"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "qBittorrent"),
    ])


def check_dependencies() -> Dict[str, bool]:
    """
    Check if required software is available.
    Returns a dictionary of dependency statuses.
    Core dependencies: vlc, syncplay, aria2c (required)
    Optional: qbittorrent (enhances seeding, not required)
    """
    return {
        "vlc": find_vlc() is not None,
        "syncplay": find_syncplay() is not None,
        "aria2c": find_aria2c() is not None,
    }


# Dependencies that are truly required to function
REQUIRED_DEPS = {"vlc", "syncplay", "aria2c"}



def run_setup_installer() -> bool:
    """Launch setup.cmd with administrative privileges."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    setup_cmd = os.path.abspath(os.path.join(app_dir, "..", "setup", "setup.cmd"))
    if not os.path.isfile(setup_cmd):
        setup_cmd = os.path.abspath(os.path.join(app_dir, "setup", "setup.cmd"))
    if not os.path.isfile(setup_cmd):
        return False
    try:
        # ShellExecute handles spaces/quotes in the path and asks Windows for
        # elevation without interpolating a filesystem path into shell code.
        os.startfile(setup_cmd, "runas")
        return True
    except Exception:
        return False
