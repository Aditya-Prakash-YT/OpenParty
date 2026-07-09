# Phase 1 — Project Foundations

## Status
✅ Complete

## What was built
- Two independent top-level folders: `/setup` and `/app`.
- A `requirements.txt` file in `/app` specifying PySide6.
- A basic placeholder PySide6 UI in `app/main.py` with "Create Party" and "Join Party" buttons.
- A shared logging module in `app/logger.py` configured to write to `app/logs/launcher.log` and stdout.
- A placeholder for `setup.cmd`.
- Updated `README.md` to describe the two folders and explain how to run the app in development mode.

## Files added / changed
- `app/requirements.txt`
- `app/main.py`
- `app/logger.py`
- `setup/setup.cmd` (Created, full logic implemented in Phase 2)
- `README.md` (Updated)

## How to test this phase manually
1. Verify `app/requirements.txt` contains PySide6.
2. Run `python app/main.py` and confirm the GUI launches with a title and two buttons, without errors.
3. Check `app/logs/launcher.log` to confirm the startup log was written.

## Decisions & trade-offs made
- Implemented `get_logger` to output to both console and a file in `app/logs/` folder immediately so it is scalable.
- Chose not to package as an exe yet, since that is Phase 10.

## Known issues / carried forward to later phases
- UI buttons are non-functional placeholders.
- `setup.cmd` logic is documented in Phase 2.
