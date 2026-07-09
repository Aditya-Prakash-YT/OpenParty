# Phase 6 — Join Party (Guest Flow)

## Status
✅ Complete

## What was built
- `app/gui/join_party.py`: The UI for the guest to load and validate a party config.
- **Two ways to load:**
  1. File Picker for `.oparty` files.
  2. Text box to paste raw JSON (for when hosts just copy-paste the config into a chat).
- **Validation & Details:**
  - Uses the Phase 3 validator strictly.
  - On failure, shows the exact error message in red.
  - On success, reveals a "Party Details" panel showing the Room, Server, Party Name, and Media Source.
- **Start Party:** A prominent button that currently shows a placeholder dialog indicating readiness for Phase 7 (Downloading).
- Integrated into `app/main.py` using the `QStackedWidget` system.

## Files added / changed
- `app/gui/join_party.py` (new)
- `app/main.py` (modified)

## How to test this phase manually
1. Launch the app (bypassing the Environment check if needed).
2. Click "Join Party".
3. Try loading `app/config/example.oparty`.
4. The Details Panel should appear with "Friday Movie Night".
5. Click "Start Party" — a placeholder popup for Phase 7 should appear.
6. Alternatively, try pasting broken JSON into the text box and verify the red error label works.

## Decisions & trade-offs made
- Added a "Details" panel to parse and display exactly what the guest is about to join before they commit to downloading anything. This ensures transparency (e.g. they can see the magnet link and the syncplay server).

## Known issues / carried forward to later phases
- Clicking "Start Party" just shows a popup. Actual downloading is Phase 7.
