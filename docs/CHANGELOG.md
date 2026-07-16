# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **setup.cmd**: Added automated checking and silent installation of `qBittorrent 4.6.5` from SourceForge using native PowerShell.
- **setup.cmd**: Replaced all `winget` dependency with pure PowerShell (`Invoke-WebRequest` with forced TLS 1.2) for downloading and silently/interactively installing dependencies (Python, VLC, aria2c, Syncplay, qBittorrent).
- **Host UI**: Seamless qBittorrent integration. A new "Create Torrent & Seed" button automates torrent creation via the qBittorrent Web API (v5+ `torrentCreator` or v4 fallback), starts seeding, and auto-fills the magnet link.
- **Backend**: Added `torrent_creator.py` (a zero-dependency qBittorrent Web API client) and `gui/torrent_worker.py` (QThread worker for non-blocking torrent creation).


## [1.1.0] - 2026-07-09

### Added
- **setup.cmd**: Python 3.12+ check — downloads and runs the official installer if not found, prompting the user to add it to PATH.
- **setup.cmd**: Automatic `pip install -r requirements.txt` to install all Python packages after Python is confirmed.
- **setup.cmd**: Portable aria2c fallback — if winget fails or aria2c is not on PATH, downloads and extracts `aria2-1.37.0-win-64bit-build1.zip` into `setup/tools/aria2/`.
- **setup.cmd**: Syncplay direct installer fallback — downloads `Syncplay-1.7.5-Setup.exe` and prompts user to run it if winget fails.
- **setup.cmd**: Multi-location detection for aria2c and Syncplay (PATH, WinGet Links, Program Files, portable tools directory).
- **deps.py**: Added `_search_paths()` to search beyond PATH — now also checks `%LOCALAPPDATA%\Microsoft\WinGet\Links\` and extra known paths.
- **deps.py**: Added `_get_portable_paths()` for `sys.frozen`-aware portable tool discovery — correctly resolves portable tool paths both from source and from the PyInstaller `.exe`.
- **Host UI**: Added optional fields to the "Create Party" screen: Description, Host Name, File Name Hint, Expected Size (bytes), and Expected Hash (SHA-256).
- **Packaging**: `OpenParty.spec` now specifies `pathex=['app']` and full `hiddenimports` for PySide6 modules, ensuring a working single-file build.
- **Docs**: Added `docs/CHANGELOG.md`.

### Changed
- **Config Loader**: Upgraded `.oparty` party file schema to `schema_version: 2`.
- **Host UI**: Strictly enforced the use of Magnet Links — torrent file path input removed entirely.
- **DEVELOPER_GUIDE.md**: Updated build command to use `pyinstaller --clean OpenParty.spec`.
- **setup.cmd**: Syncplay detection now checks PATH, `C:\Program Files\Syncplay`, `C:\Program Files (x86)\Syncplay`, and `setup/tools/syncplay/` before attempting download.

### Removed
- **Config Loader**: Removed support for local `.torrent` files (`torrent-file` source type) — Schema v2 only accepts `magnet` links to guarantee `.oparty` files are fully portable.
- **setup.cmd**: Removed all `winget` dependency — no longer requires Windows App Installer to be present on the guest machine.

## [1.0.0] - 2026-07-09

### Added
- **Core System**: Implemented all 10 architectural phases specified in the `OpenParty_v3_Split_Architecture_Plan`.
- **Packaging**: Packaged the Python application as a standalone executable (`OpenParty.exe`) using PyInstaller.
- **Documentation**: Added comprehensive User Guide, Developer Guide, and Schema documentation.
