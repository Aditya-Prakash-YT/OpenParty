# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Dependencies**: Added Python 3.12+ installation checks and automatic installer download to `setup.cmd`.
- **Dependencies**: Added automatic installation of missing `pip` packages (from `requirements.txt`) in `setup.cmd`.
- **Host UI**: Added new optional fields to the "Create Party" screen: Description, Host Name, File Name Hint, Expected Size, and Expected Hash (SHA-256).

### Changed
- **Config Loader**: Upgraded `.oparty` party file schema to `schema_version: 2`.
- **Host UI**: Strictly enforced the use of Magnet Links for creating watch parties.

### Removed
- **Config Loader**: Removed support for local `.torrent` files to guarantee that generated `.oparty` files are fully portable and cross-platform for guests.

## [1.0.0] - 2026-07-09

### Added
- **Core System**: Implemented all 10 architectural phases specified in the `OpenParty_v3_Split_Architecture_Plan`.
- **Packaging**: Packaged the Python application as a standalone executable (`OpenParty.exe`) using PyInstaller.
- **Documentation**: Added comprehensive User Guide, Developer Guide, and Schema documentation.
