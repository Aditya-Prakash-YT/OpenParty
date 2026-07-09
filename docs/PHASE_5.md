# Phase 5 — Create Party (Host Flow)

## Status
✅ Complete

## What was built
- `app/gui/create_party.py`: The UI for the host to generate a party file.
- **Fields:**
  - Party Name
  - Source Type (Magnet Link or Torrent File)
  - Source Value (with "Browse..." button for `.torrent` files)
  - Subtitle URL (optional)
  - Syncplay Server (defaults to `syncplay.pl:8997`)
  - Room Name (includes random generator button)
  - Password (optional, includes random generator button)
- **Live Validation:** Re-uses Phase 3's `load_party_string` to validate inputs as the user types. The Export/Copy buttons only unlock when the config is valid.
- **Warning:** Shows an orange warning if no password is set ("Note: Without a password, anyone who knows the room name on this server can join.").
- **Export / Copy:** Features an "Export to .oparty File" button and a "Copy to Clipboard" button for easy sharing via Discord/text.
- Integrated into `app/main.py` using `QStackedWidget` so the host can return to the main menu at any time.

## Files added / changed
- `app/gui/__init__.py` (new)
- `app/gui/create_party.py` (new)
- `app/main.py` (modified)

## How to test this phase manually
1. Bypass the Environment check (since VLC/Syncplay are not installed yet) by returning `True` in `deps.py` or mocking it. (Or just install Syncplay).
2. Run `python app/main.py` and click "Create Party".
3. Verify live validation blocks export if fields are empty.
4. Try generating a random room name.
5. Notice the missing password warning.
6. Once filled out, test Export and Copy to Clipboard.

## Decisions & trade-offs made
- When "Torrent File" is selected, the source value is just the local path. This works for generating the JSON locally, but a guest will not be able to use it unless they have the same `.torrent` file at the exact same path. This aligns with Phase 3 (which accepts any string for `value` as long as it's not a magnet link that misses `magnet:?`).
- Live validation directly invokes the loader. This guarantees that whatever we export is exactly what the loader understands.

## Known issues / carried forward to later phases
- None.
