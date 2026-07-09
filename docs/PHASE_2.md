# Phase 2 — The Setup Script

## Status
✅ Complete

## What was built
- `setup.cmd` script that checks for Python 3.12+, installing the official installer if missing, and running pip to install dependencies.
- Installs VLC via `winget`.
- Checks for `aria2c` on PATH, then in portable tools, falling back to winget and finally downloading/extracting a portable version to `setup/tools/aria2/`.
- Checks for `Syncplay` on PATH, Program Files, or portable tools, falling back to downloading and running the `Syncplay-1.7.5-Setup.exe` installer.
- Added self-elevation check to ensure the script runs with Administrator privileges.
- Registered `.oparty` file extension to open with `python app/main.py`.
- Full output logged to `setup/install.log`.

## Files added / changed
- `setup/setup.cmd`

## How to test this phase manually
1. Double click `setup\setup.cmd` on a Windows machine.
2. Allow UAC elevation if prompted.
3. Observe installation progress and completion messages.
4. Verify VLC, Syncplay, and aria2 are installed.
5. Check `setup/install.log` for correct logging output.
6. Verify `.oparty` extension is associated with OpenParty.

## Decisions & trade-offs made
- Pinned specific versions found via `winget search` to ensure reproducibility.
- Syncplay direct download link hardcoded to 1.7.5 to match the pinned winget version for fallback.
- File association points to `python` since there is no `.exe` yet. This is sufficient for development and will be adjusted in Phase 10.

## Known issues / carried forward to later phases
- Windows SmartScreen may flag `setup.cmd`. Users need to click "More info -> Run anyway" (To be documented in User Guide, Phase 10).
