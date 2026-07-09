# Phase 9 — Making Failures Boring (Error Handling & Recovery)

## Status
✅ Complete

## What was built

### Central Error Layer: `app/errors.py`
- `format_error(problem, cause, fix)` — formats every user-visible error as:
  ```
  Problem:        <what went wrong>
  Likely cause:   <why>
  Suggested fix:  <what to do>
  ```
- `log_and_format()` — same, but also logs the full traceback to `launcher.log`.
- `open_log_folder()` — opens `%LOCALAPPDATA%/OpenParty/` in Explorer.
- Pre-built message functions for every known failure mode:
  - `err_dependency_missing(name)`
  - `err_party_file_not_found(path)`
  - `err_party_file_corrupt(detail)`
  - `err_aria2c_start_failed()`
  - `err_disk_full(required, free)`
  - `err_torrent_no_peers()`
  - `err_network_lost()`
  - `err_disk_full_mid_download()`
  - `err_media_file_missing()`
  - `err_integrity_failed()`
  - `err_syncplay_missing()`
  - `err_syncplay_crash()`
  - `err_syncplay_server_unreachable(server)`
  - `err_port_in_use(port)`
  - `err_vlc_missing()`

### Reusable Error Panel: `app/gui/error_panel.py`
- Drop-in widget showing the structured error in a styled red box.
- Three buttons: **Try Again**, **Start Over**, **View Logs**.
- `try_again` and `start_over` are Qt Signals — each screen connects them to the right action.

### Updated Screens
- **`download.py`** (fully rewritten):
  - Uses `ErrorPanel` instead of `QMessageBox.critical`.
  - Detects torrent stall (0 speed for 60 seconds) → `err_torrent_no_peers()`.
  - Detects RPC poll failures with 3 silent retries → `err_network_lost()`.
  - Classifies aria2 error codes (2/3/19 = network, 24 = disk full).
  - "Try Again" restarts the download. "Start Over" returns to menu.
- **`launch.py`** (fully rewritten):
  - Uses `ErrorPanel` with structured messages for VLC missing, Syncplay missing, SHA-256 mismatch, media file deleted.
  - "Try Again" re-runs the launch checklist. "Start Over" returns to menu.
- **`join_party.py`** (updated):
  - File-not-found and corrupt-file errors now use `errors.err_party_file_not_found()` and `errors.err_party_file_corrupt()`.
- **`main.py`** (updated):
  - Added **View Logs** button to main menu.
  - Added `sys.excepthook = global_exception_handler` — any unhandled exception anywhere in the app is caught, logged, and shown as a structured message in a dialog. The app never shows a raw traceback.

## Files added / changed
- `app/errors.py` (new — central error layer)
- `app/gui/error_panel.py` (new — reusable error widget)
- `app/gui/download.py` (rewritten)
- `app/gui/launch.py` (rewritten)
- `app/gui/join_party.py` (modified)
- `app/main.py` (modified)

## Scenarios covered

| Scenario | Trigger | Message |
|---|---|---|
| VLC missing | Uninstall VLC, launch party | `err_vlc_missing()` |
| Syncplay missing | Uninstall Syncplay, launch party | `err_syncplay_missing()` |
| Party file deleted mid-use | Delete file after selecting | `err_party_file_not_found()` |
| Party file corrupt | Paste broken JSON | `err_party_file_corrupt()` |
| Torrent stalled (0 peers) | Use dead magnet, wait 60s | `err_torrent_no_peers()` |
| Disk fills mid-download | Fill disk during download | `err_disk_full_mid_download()` |
| Disk too small before download | Total size > free space | `err_disk_full()` |
| Network drops mid-download | Disconnect WiFi | `err_network_lost()` |
| Syncplay server unreachable | Use bad server address | `err_syncplay_server_unreachable()` |
| Syncplay crashes on launch | Corrupt Syncplay install | `err_syncplay_crash()` |
| Port already in use | aria2c RPC port conflict | `err_port_in_use()` (auto-retry with random port) |
| SHA-256 mismatch | Modify downloaded file | `err_integrity_failed()` |
| Media file deleted after download | Delete file before launch | `err_media_file_missing()` |
| Unhandled exception (anything) | Any unexpected crash | `global_exception_handler` catches, logs, shows dialog |

Every scenario returns the user to a safe screen with "Try Again" or "Start Over". Nothing crashes the app.

## How to test this phase manually
1. Each row in the table above can be triggered by the method described.
2. In every case, verify the structured message appears (Problem / Likely cause / Suggested fix).
3. Verify "View Logs" opens the log folder.
4. Verify "Try Again" retries the operation.
5. Verify "Start Over" returns to the main menu.

## Decisions & trade-offs made
- Used a red-bordered panel widget rather than `QMessageBox.critical()` for errors. This keeps the user on the same screen with clear action buttons instead of modal dialogs that steal focus.
- Silent retry (3 attempts) for RPC poll failures before showing the network error. This handles transient hiccups gracefully.
- Stall detection threshold is 60 seconds of zero speed. This avoids false positives during slow torrent swarm discovery.

## Known issues / carried forward to later phases
- None.
