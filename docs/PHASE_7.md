# Phase 7 — Downloading the Movie (aria2c)

## Status
✅ Complete

## What was built
- `app/downloader/aria2.py`: A JSON-RPC client and subprocess manager for `aria2c`.
  - Spawns `aria2c` in the background (no console window) with a dynamically chosen free port and a randomly generated RPC secret token.
  - Exposes `add_uri`, `add_torrent`, `get_status`, and `remove`.
- `app/gui/download.py`: The `DownloadWidget` that handles the download lifecycle without freezing the UI.
  - Connects to the aria2c RPC server using Python's built-in `urllib.request`.
  - Uses `QTimer` to poll progress every 500ms.
  - **Disk Space Check:** Waits until `totalLength` is retrieved (either immediately for `.torrent` files, or after metadata is fetched for magnet links), then checks against `shutil.disk_usage()`. Prompts the user and aborts if space is insufficient.
  - **Magnet Link Resolution:** Automatically detects when a magnet link's `status` returns `followedBy`, smoothly transitioning from "Fetching metadata" to tracking the actual file payload.
  - **File Selection:** When complete, checks `file_name_hint`. If it doesn't match or is missing, falls back to the largest known video file (`.mkv`, `.mp4`, `.avi`), then finally the largest file overall.

## Files added / changed
- `app/downloader/__init__.py` (new)
- `app/downloader/aria2.py` (new)
- `app/gui/download.py` (new)
- `app/main.py` (modified)

## How to test this phase manually
1. Bypass the Environment check if needed.
2. Ensure you have an `aria2c.exe` available and `app/deps.py` returns True for it.
3. Open `app/config/example.oparty` via "Join Party".
4. Click "Start Party".
5. Observe the UI: "Fetching metadata..." -> "Downloading... (progress bar & speed)" -> "Phase 8 Pending (Download finished: path/to/file.mkv)".
6. Verify no external console windows opened, and the downloaded file is correctly located in `~/Downloads/OpenParty`.

## Decisions & trade-offs made
- Used `urllib.request` for RPC calls rather than pulling in `requests`. The network calls are made to `127.0.0.1`, so they are near-instant and won't noticeably block the GUI thread, removing the need for complex `QThread` async dispatching for simple polling.
- Instead of reading stdout, strictly uses JSON-RPC. This is far more robust against version changes in aria2c console output.

## Known issues / carried forward to later phases
- **Subtitles skipped for v1**: Downloading subtitles has not been implemented (as permitted by the spec) because it involves distinct logic for external HTTP URLs or `.srt` files embedded within torrents. The schema safely carries the subtitle URL, but it is ignored for now.
