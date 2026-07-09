"""
Party file loader and validator for OpenParty.

Loads .oparty (JSON) files, validates every field against the schema spec,
and returns a clean PartyConfig object on success or raises
PartyFileError with a single human-readable reason on failure.
"""

import json
import re
import os
from dataclasses import dataclass, field
from typing import List, Optional

# Current application version — used for compatibility checks.
APP_VERSION = "1.0.0"

# Supported schema versions this loader can handle.
SUPPORTED_SCHEMA_VERSIONS = {1, 2}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class PartyFileError(Exception):
    """Raised when a party file fails validation.
    
    The message is always a single, human-readable sentence suitable
    for display to non-technical users.
    """
    pass


# ---------------------------------------------------------------------------
# Data classes — the clean objects returned on success
# ---------------------------------------------------------------------------

@dataclass
class PartyInfo:
    name: str
    description: str = ""
    created_at: str = ""
    created_by: str = ""


@dataclass
class MediaSource:
    type: str          # "magnet" (initially only supported type)
    value: str         # the magnet link / torrent URL


@dataclass
class MediaFile:
    name_hint: str = ""
    size: Optional[int] = None


@dataclass
class Subtitle:
    language: str
    url: str


@dataclass
class MediaInfo:
    source: MediaSource
    file: MediaFile = field(default_factory=MediaFile)
    subtitles: List[Subtitle] = field(default_factory=list)


@dataclass
class SyncInfo:
    server: str = "syncplay.pl"
    port: int = 8997
    room: str = ""
    password: str = ""


@dataclass
class PlaybackInfo:
    start_paused: bool = True


@dataclass
class IntegrityInfo:
    sha256: Optional[str] = None


@dataclass
class CompatibilityInfo:
    min_openparty_version: str = "1.0.0"


@dataclass
class PartyConfig:
    """Complete, validated representation of a .oparty file."""
    schema_version: int
    party: PartyInfo
    media: MediaInfo
    sync: SyncInfo
    playback: PlaybackInfo = field(default_factory=PlaybackInfo)
    integrity: IntegrityInfo = field(default_factory=IntegrityInfo)
    compatibility: CompatibilityInfo = field(default_factory=CompatibilityInfo)
    extensions: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Version comparison helper
# ---------------------------------------------------------------------------

def _parse_version(version_str: str) -> tuple:
    """Parse a semver string like '1.2.3' into a tuple (1, 2, 3)."""
    parts = version_str.strip().split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        raise PartyFileError(
            f"Invalid version string: '{version_str}'. Expected format like '1.0.0'."
        )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require_key(data: dict, key: str, section: str) -> object:
    """Return data[key] or raise with a clear message."""
    if key not in data:
        raise PartyFileError(f"'{key}' is missing from the '{section}' section.")
    return data[key]


def _require_string(data: dict, key: str, section: str, *, allow_empty: bool = False) -> str:
    value = _require_key(data, key, section)
    if not isinstance(value, str):
        raise PartyFileError(f"'{key}' in '{section}' must be text, not {type(value).__name__}.")
    if not allow_empty and not value.strip():
        raise PartyFileError(f"'{key}' in '{section}' cannot be empty.")
    return value


def _require_int(data: dict, key: str, section: str) -> int:
    value = _require_key(data, key, section)
    if not isinstance(value, int) or isinstance(value, bool):
        raise PartyFileError(f"'{key}' in '{section}' must be a whole number.")
    return value


def _optional_string(data: dict, key: str, default: str = "") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        return default
    return value


def _optional_int(data: dict, key: str, default: int = 0) -> int:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        return default
    return value


def _optional_bool(data: dict, key: str, default: bool = False) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        return default
    return value


# ---------------------------------------------------------------------------
# Section validators
# ---------------------------------------------------------------------------

def _validate_schema_version(data: dict) -> int:
    version = _require_key(data, "schema_version", "root")
    if not isinstance(version, int) or isinstance(version, bool):
        raise PartyFileError("'schema_version' must be a whole number (e.g. 1).")
    if version < 1:
        raise PartyFileError("'schema_version' must be a positive number.")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise PartyFileError(
            f"This party file uses schema version {version}, "
            f"but this version of OpenParty only supports version(s) "
            f"{', '.join(str(v) for v in sorted(SUPPORTED_SCHEMA_VERSIONS))}."
        )
    return version


def _validate_party(data: dict) -> PartyInfo:
    section = _require_key(data, "party", "root")
    if not isinstance(section, dict):
        raise PartyFileError("'party' must be a section (object), not a single value.")

    name = _require_string(section, "name", "party")
    if len(name) > 200:
        raise PartyFileError("Party name is too long (maximum 200 characters).")

    return PartyInfo(
        name=name,
        description=_optional_string(section, "description"),
        created_at=_optional_string(section, "created_at"),
        created_by=_optional_string(section, "created_by"),
    )


def _validate_media_source(source_data: dict) -> MediaSource:
    source_type = _require_string(source_data, "type", "media.source")
    value = _require_string(source_data, "value", "media.source")

    if source_type == "magnet":
        if not value.startswith("magnet:?"):
            raise PartyFileError(
                "The media source type is 'magnet', but the value doesn't look like "
                "a magnet link. It should start with 'magnet:?'."
            )
    elif source_type == "torrent-file":
        raise PartyFileError(
            "Local torrent files are no longer supported. Please use a magnet link."
        )
    else:
        raise PartyFileError(
            f"Unsupported media source type: '{source_type}'. "
            f"This version of OpenParty supports: magnet."
        )

    return MediaSource(type=source_type, value=value)


def _validate_media_file(file_data: dict) -> MediaFile:
    name_hint = _optional_string(file_data, "name_hint")
    size = file_data.get("size", None)
    if size is not None:
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise PartyFileError("'size' in 'media.file' must be a positive number or null.")
    return MediaFile(name_hint=name_hint, size=size)


def _validate_subtitles(subs_data: list) -> List[Subtitle]:
    if not isinstance(subs_data, list):
        raise PartyFileError("'subtitles' in 'media' must be a list.")
    result = []
    for i, sub in enumerate(subs_data):
        if not isinstance(sub, dict):
            raise PartyFileError(f"Subtitle entry {i + 1} must be an object with 'language' and 'url'.")
        language = _require_string(sub, "language", f"media.subtitles[{i + 1}]")
        url = _require_string(sub, "url", f"media.subtitles[{i + 1}]")
        result.append(Subtitle(language=language, url=url))
    return result


def _validate_media(data: dict) -> MediaInfo:
    section = _require_key(data, "media", "root")
    if not isinstance(section, dict):
        raise PartyFileError("'media' must be a section (object), not a single value.")

    source_data = _require_key(section, "source", "media")
    if not isinstance(source_data, dict):
        raise PartyFileError("'source' in 'media' must be a section with 'type' and 'value'.")
    source = _validate_media_source(source_data)

    file_data = section.get("file", {})
    if not isinstance(file_data, dict):
        file_data = {}
    media_file = _validate_media_file(file_data)

    subs_data = section.get("subtitles", [])
    if subs_data is None:
        subs_data = []
    subtitles = _validate_subtitles(subs_data)

    return MediaInfo(source=source, file=media_file, subtitles=subtitles)


def _validate_sync(data: dict) -> SyncInfo:
    section = _require_key(data, "sync", "root")
    if not isinstance(section, dict):
        raise PartyFileError("'sync' must be a section (object), not a single value.")

    room = _require_string(section, "room", "sync")
    server = _optional_string(section, "server", "syncplay.pl")
    if not server.strip():
        server = "syncplay.pl"

    port = _optional_int(section, "port", 8997)
    if port < 1 or port > 65535:
        raise PartyFileError(f"Port {port} is not valid. It must be between 1 and 65535.")

    password = _optional_string(section, "password", "")

    return SyncInfo(server=server, port=port, room=room, password=password)


def _validate_playback(data: dict) -> PlaybackInfo:
    section = data.get("playback", {})
    if section is None or not isinstance(section, dict):
        return PlaybackInfo()
    return PlaybackInfo(
        start_paused=_optional_bool(section, "start_paused", True)
    )


def _validate_integrity(data: dict) -> IntegrityInfo:
    section = data.get("integrity", {})
    if section is None or not isinstance(section, dict):
        return IntegrityInfo()
    sha256 = section.get("sha256", None)
    if sha256 is not None and not isinstance(sha256, str):
        raise PartyFileError("'sha256' in 'integrity' must be text or null.")
    if sha256 is not None and sha256.strip():
        # Basic hex check
        if not re.fullmatch(r'[0-9a-fA-F]{64}', sha256.strip()):
            raise PartyFileError("'sha256' in 'integrity' doesn't look like a valid SHA-256 hash.")
    return IntegrityInfo(sha256=sha256)


def _validate_compatibility(data: dict) -> CompatibilityInfo:
    section = data.get("compatibility", {})
    if section is None or not isinstance(section, dict):
        return CompatibilityInfo()

    min_version_str = _optional_string(section, "min_openparty_version", "1.0.0")
    if not min_version_str.strip():
        min_version_str = "1.0.0"

    # Check if the running app is new enough
    required = _parse_version(min_version_str)
    current = _parse_version(APP_VERSION)
    if required > current:
        raise PartyFileError(
            f"This party requires OpenParty {min_version_str} or newer. "
            f"You are running version {APP_VERSION}. Please update OpenParty."
        )

    return CompatibilityInfo(min_openparty_version=min_version_str)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_party_file(path: str) -> PartyConfig:
    """Load and validate a .oparty file from disk.
    
    Returns a PartyConfig on success.
    Raises PartyFileError with a human-readable message on failure.
    """
    if not os.path.isfile(path):
        raise PartyFileError(f"Party file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except PermissionError:
        raise PartyFileError(f"Cannot read the party file — permission denied: {path}")
    except OSError as e:
        raise PartyFileError(f"Cannot read the party file: {e}")

    return load_party_string(raw)


def load_party_string(raw_json: str) -> PartyConfig:
    """Load and validate a party config from a raw JSON string.
    
    Returns a PartyConfig on success.
    Raises PartyFileError with a human-readable message on failure.
    """
    if not raw_json or not raw_json.strip():
        raise PartyFileError("The party file is empty.")

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise PartyFileError(
            f"The party file is not valid JSON. Check for typos or missing commas near line {e.lineno}."
        )

    if not isinstance(data, dict):
        raise PartyFileError("The party file must be a JSON object (starts with '{').")

    # Validate each section in order.
    # Stop at the first error — one clear message, not a list of problems.
    schema_version = _validate_schema_version(data)
    party = _validate_party(data)
    media = _validate_media(data)
    sync = _validate_sync(data)
    playback = _validate_playback(data)
    integrity = _validate_integrity(data)
    compatibility = _validate_compatibility(data)
    extensions = data.get("extensions", {})
    if extensions is None:
        extensions = {}

    return PartyConfig(
        schema_version=schema_version,
        party=party,
        media=media,
        sync=sync,
        playback=playback,
        integrity=integrity,
        compatibility=compatibility,
        extensions=extensions,
    )
