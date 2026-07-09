# Phase 8 — Verify, Launch Syncplay, Open VLC

## Status
✅ Complete

## What was built
- `app/gui/launch.py`: A `LaunchWidget` that handles the final bridge into Syncplay.
- **Verification:** Automatically validates the downloaded file against `integrity.sha256` and checks the exact byte size against `media.file.size` if those fields are provided in the party config.
- **Syncplay Launch:** Constructs the strict command-line flags required by Syncplay (`--no-store`, `--host`, `--room`, `--password`, `--player-path` pointing to the VLC detected in Phase 4). 
- **Process Monitoring:** Launches `Syncplay.exe` completely detached from the main python process, but uses a timer to verify it didn't crash instantly on launch. Logs the exact executed command and any crash output directly to `%LOCALAPPDATA%/OpenParty/syncplay.log`.
- **Live Status UI:** Provides a step-by-step checklist matching the spec:
  - ○ Verifying Download
  - ○ Launching Syncplay
  - ○ Opening VLC
  - ○ Connected to Room
  - ○ Ready
  As each stage completes, it turns into a green ✔.
- Integrated into `app/main.py` directly following the download completion flow.

## Files added / changed
- `app/gui/launch.py` (new)
- `app/main.py` (modified)

## How to test this phase manually
1. Launch `python app/main.py` (with VLC & Syncplay installed).
2. Load a valid party config and let the file finish downloading.
3. Observe the transition to the "Starting Party..." screen.
4. Watch the checklist iterate until "Ready".
5. Syncplay will launch and automatically open VLC playing the file, successfully bridged.

## Decisions & trade-offs made
- Did not supply the `--name` parameter to Syncplay. Since OpenParty (per the Phase 3 config spec) doesn't have a concept of the guest's username, letting Syncplay pop its native username dialog (or use its remembered config) is the correct path rather than forcing "OpenPartyGuest".
- Because Syncplay is a closed executable loop once launched, the final "Opening VLC", "Connected to Room" steps are optimistic UI updates. If Syncplay crashes (process dies), it immediately fails the list.

## Known issues / carried forward to later phases
- None.
