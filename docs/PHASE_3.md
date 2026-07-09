# Phase 3 — The Party File Format (JSON Config)

## Status
✅ Complete

## What was built
- Full `.oparty` party file schema following the structured spec from the architecture plan (nested sections: `party`, `media`, `sync`, `playback`, `integrity`, `compatibility`, `extensions`).
- Hand-written Python loader/validator in `app/config/loader.py` — no external dependencies (no pydantic). Every field validated with human-readable error messages.
- `PartyConfig` dataclass hierarchy for clean programmatic access after loading.
- `load_party_file(path)` — loads from disk.
- `load_party_string(raw_json)` — loads from pasted JSON string.
- Both raise `PartyFileError` with a single clear sentence on failure.
- `compatibility.min_openparty_version` check implemented — produces "This party requires OpenParty X.Y.Z or newer." message.
- Example party file `app/config/example.oparty` using the Sintel open-source movie magnet link.
- Schema documentation in `docs/config-schema.md`.
- 36-test suite in `app/config/test_loader.py` — all passing.

## Files added / changed
- `app/config/__init__.py` (new)
- `app/config/loader.py` (new — loader, validator, dataclasses)
- `app/config/example.oparty` (new — real example party file)
- `app/config/test_loader.py` (new — 36 tests)
- `docs/config-schema.md` (new — full schema documentation)

## How to test this phase manually
1. Run the test suite:
   ```
   python app/config/test_loader.py
   ```
   All 36 tests should pass.
2. Open `app/config/example.oparty` in Notepad — verify it's human-readable.
3. Try loading a broken file by editing the example and re-running the loader.

## Decisions & trade-offs made
- **Hand-written validator over pydantic**: Avoids an external dependency. The validation logic is straightforward and produces cleaner, more specific error messages tailored to non-technical users.
- **Syncplay default port 8997**: Confirmed via syncplay.pl that ports 8995 and 8999 are the most congested. The site's own JavaScript randomly highlights ports 8996–8998, confirming 8997 is a reasonable default.
- **Structured schema (not flat)**: The architecture plan's Party File Specification defines nested sections (`media.source`, `sync`, etc.). Implemented the full structured version rather than the simplified flat example shown in the Phase 3 quick summary.
- **Stop at first error**: As specified — one clear message per validation attempt, not a list of all problems.

## Known issues / carried forward to later phases
- Only `magnet` source types supported (Schema v2 removed `torrent-file`). Future types (`http`, `https`, `ftp`, `local-network`) are mentioned in the spec but not validated yet.
- Subtitle download logic is a Phase 7 concern — the schema and validation support multiple subtitles, but actual downloading is not implemented yet.
