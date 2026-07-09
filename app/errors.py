"""
Central error-handling layer for OpenParty.

Every user-visible error should go through `format_error()` to produce
a structured, non-scary message:

    Problem:        <what went wrong, one sentence>
    Likely cause:   <the probable reason, one sentence>
    Suggested fix:  <what to do, one sentence>

Technical details go to the log only.
"""

import os
import traceback
from logger import launcher_logger

LOG_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "OpenParty")


def format_error(problem: str, cause: str, fix: str) -> str:
    """Return a structured, human-friendly error string."""
    return (
        f"Problem:  {problem}\n"
        f"Likely cause:  {cause}\n"
        f"Suggested fix:  {fix}"
    )


def log_and_format(problem: str, cause: str, fix: str, exc: Exception = None) -> str:
    """Log technical details, return the user-facing message."""
    msg = format_error(problem, cause, fix)
    launcher_logger.error(msg)
    if exc:
        launcher_logger.error(traceback.format_exc())
    return msg


def open_log_folder():
    """Open the log folder in Explorer."""
    os.makedirs(LOG_DIR, exist_ok=True)
    os.startfile(LOG_DIR)


# ─────────────────────────────────────────────────────────────────
# Pre-built messages for known failure modes
# ─────────────────────────────────────────────────────────────────

def err_dependency_missing(name: str) -> str:
    return format_error(
        f"{name} is not installed or could not be found.",
        f"{name} was either never installed or was uninstalled since you last ran setup.cmd.",
        "Run setup.cmd again and restart OpenParty."
    )

def err_party_file_not_found(path: str) -> str:
    return format_error(
        f"Party file not found: {os.path.basename(path)}",
        "The file was deleted or moved after you selected it.",
        "Ask the host to re-send the party file."
    )

def err_party_file_corrupt(detail: str) -> str:
    return format_error(
        "Party file is invalid.",
        detail,
        "Ask the host to re-export the party file, or check for copy-paste errors."
    )

def err_aria2c_start_failed() -> str:
    return format_error(
        "Could not start the download engine (aria2c).",
        "aria2c may have been uninstalled or is blocked by antivirus.",
        "Run setup.cmd again, or temporarily disable your antivirus and retry."
    )

def err_disk_full(required_gb: float, free_gb: float) -> str:
    return format_error(
        f"Not enough disk space ({free_gb:.1f} GB free, {required_gb:.1f} GB needed).",
        "The download drive is full.",
        "Free up disk space and try again."
    )

def err_torrent_no_peers() -> str:
    return format_error(
        "Download stalled — no peers found.",
        "Nobody is seeding this torrent right now, or the magnet link may be invalid.",
        "Ask the host to confirm the magnet link is correct, or try again later."
    )

def err_network_lost() -> str:
    return format_error(
        "Network connection lost during download.",
        "Your internet connection dropped.",
        "Check your connection and click Try Again. The download will resume where it left off."
    )

def err_disk_full_mid_download() -> str:
    return format_error(
        "Disk ran out of space during download.",
        "Another program may have used disk space, or the file is larger than estimated.",
        "Free up disk space and click Try Again."
    )

def err_media_file_missing() -> str:
    return format_error(
        "Downloaded media file is missing.",
        "The file was deleted or moved between downloading and launching.",
        "Try downloading again by clicking Start Over."
    )

def err_integrity_failed() -> str:
    return format_error(
        "File integrity check failed (SHA-256 mismatch).",
        "The downloaded file does not match the expected hash. It may be corrupt or the wrong file.",
        "Delete the file and try downloading again."
    )

def err_syncplay_missing() -> str:
    return format_error(
        "Syncplay is not installed or could not be found.",
        "Syncplay was uninstalled or moved since the last check.",
        "Run setup.cmd again and restart OpenParty."
    )

def err_syncplay_crash() -> str:
    return format_error(
        "Syncplay exited unexpectedly.",
        "Syncplay may be misconfigured, or the server may be unreachable.",
        "Check your internet connection. If the problem persists, try reinstalling via setup.cmd. Check View Logs for details."
    )

def err_syncplay_server_unreachable(server: str) -> str:
    return format_error(
        f"Cannot reach Syncplay server: {server}",
        "The server may be down, or your firewall is blocking the connection.",
        "Try a different Syncplay server, or check your firewall settings."
    )

def err_port_in_use(port: int) -> str:
    return format_error(
        f"Port {port} is already in use.",
        "Another program is using this port.",
        "Close the other program, or the app will try a different port automatically."
    )

def err_vlc_missing() -> str:
    return format_error(
        "VLC media player is not installed or could not be found.",
        "VLC was uninstalled or moved since the last check.",
        "Run setup.cmd again and restart OpenParty."
    )
