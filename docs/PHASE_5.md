# Phase 5 — Create Party (Host Flow)

## Status
✅ Complete

## What was built
- `app/gui/create_party.py`: The UI for the host to generate a party file.
- **Fields:**
  - Party Name
  - Source Value (Magnet Link only)
  - Subtitle URL (optional)
  - Description, Host Name, File Name Hint, Expected Size, Expected Hash (added in Phase 10 Schema v2 update)
  - Syncplay Server (defaults to `syncplay.pl:8997`)
  - Room Name (includes random generator button)
  - Password (optional, includes random generator button)
- **Live Validation:** Re-uses Phase 3's `load_party_string` to validate inputs as the user types. The Export/Copy buttons only unlock when the config is valid.
- **Warning:** Shows an orange warning if no password is set ("Note: Without a password, anyone who knows the room name on this server can join.").
- **Export / Copy:** Features an "Export to .oparty File" button and a "Copy to Clipboard" button for easy sharing via Discord/text.
- **Seamless qBittorrent Integration:** 
  - Hosts can pick a video file and the app will communicate with the qBittorrent Web API (via a background `QThread`). 
  - It automatically creates the torrent, starts seeding it, and pulls the magnet link back into the form.

## Files added / changed
- `app/gui/__init__.py` (new)
- `app/gui/create_party.py` (new/updated)
- `app/main.py` (modified)
- `app/torrent_creator.py` (new)
- `app/gui/torrent_worker.py` (new)

## How to test this phase manually
1. Bypass the Environment check (since VLC/Syncplay are not installed yet) by returning `True` in `deps.py` or mocking it. (Or just install Syncplay).
2. Run `python app/main.py` and click "Create Party".
3. Verify live validation blocks export if fields are empty.
4. Try generating a random room name.
5. Notice the missing password warning.
6. Once filled out, test Export and Copy to Clipboard.

## Decisions & trade-offs made
- Replaced `torrent-file` support with Magnet Links only in Phase 10, to guarantee that party files are universally shareable across the internet.
- Live validation directly invokes the loader. This guarantees that whatever we export is exactly what the loader understands.

## Known issues / carried forward to later phases
- None.
