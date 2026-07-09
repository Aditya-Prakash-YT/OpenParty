# Phase 4 — Dependency Detection

## Status
✅ Complete

## What was built
- `app/deps.py`: A dependency detection module checking for `vlc`, `syncplay`, and `aria2c`.
- `app/main.py` updated to run an "Environment Check" before unlocking the main UI.
- Application displays a checklist with ✔ or ✘.
- If dependencies are missing, the UI locks and displays the specific failure message from the spec: "Required software is missing. Please run setup.cmd and restart OpenParty."
- Full technical details are logged to `launcher.log`.
- Only reports; it does not install anything itself.

## Files added / changed
- `app/deps.py` (new)
- `app/main.py` (modified)

## How to test this phase manually
1. Ensure at least one dependency is missing (e.g. Syncplay).
2. Run `python app/main.py`.
3. Verify that the UI displays a red ✘ next to the missing dependency and the exact failure message, blocking the "Create/Join Party" buttons.
4. (Optional) Install the missing dependencies (e.g. via `setup.cmd`), restart the app, and verify it unlocks correctly.

## Decisions & trade-offs made
- Used explicit path checks (`C:\Program Files\...`) alongside `shutil.which` (PATH lookups). This avoids having to run `winget list` via subprocess, which would freeze the GUI startup by a few seconds.

## Known issues / carried forward to later phases
- None.
