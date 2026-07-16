# Phase 2 — The Setup Script

## Status
✅ Complete

## What was built
- `setup.cmd` fully rewritten to remove `winget` dependency — uses PowerShell `Invoke-WebRequest` (built into all modern Windows) for all downloads.
- Python 3.12.4: downloads and runs official installer if not found; prompts user to tick "Add to PATH".
- VLC 3.0.23: downloaded directly from VideoLAN CDN and installed silently (`/S`).
- qBittorrent 4.6.5: downloaded from SourceForge and installed silently (`/S`).
- aria2c 1.37.0: downloaded as a portable `.zip` and extracted to `setup/tools/aria2/` — no system changes.
- Syncplay 1.7.5: downloaded from GitHub releases and run interactively by the user.
- TLS 1.2 explicitly forced in all PowerShell download calls to ensure compatibility on older Windows 10 builds.

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
