"""
Party file loader and validator for OpenParty.

Loads .oparty (JSON) files, validates every field against the schema spec,
and returns a clean PartyConfig object on success or raises
PartyFileError with a single human-readable reason on failure.
"""

import base64
import binascii
import hashlib
import json
import re
import os
import ipaddress
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional

# Current application version — used for compatibility checks.
APP_VERSION = "1.0.0"

# Supported schema versions this loader can handle.
SUPPORTED_SCHEMA_VERSIONS = {1, 2}
MAX_PARTY_FILE_BYTES = 1024 * 1024


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
class P2PEndpoint:
    """A host-owned tracker/web-seed endpoint carried by a party invite."""
    scope: str
    base_url: str
    peer_host: str
    peer_port: int


@dataclass
class P2PInfo:
    """Embedded torrent metadata and deterministic bootstrap routes."""
    torrent_bytes: bytes
    endpoints: List[P2PEndpoint] = field(default_factory=list)


@dataclass
class Subtitle:
    language: str
    url: str


@dataclass
class MediaInfo:
    source: MediaSource
    file: MediaFile = field(default_factory=MediaFile)
    subtitles: List[Subtitle] = field(default_factory=list)
    p2p: Optional[P2PInfo] = None


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


def _optional_string(data: dict, key: str, default: str = "", section: str = "root") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise PartyFileError(f"'{key}' in '{section}' must be text or null.")
    return value


def _optional_int(data: dict, key: str, default: int = 0, section: str = "root") -> int:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise PartyFileError(f"'{key}' in '{section}' must be a whole number or null.")
    return value


def _optional_bool(data: dict, key: str, default: bool = False, section: str = "root") -> bool:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise PartyFileError(f"'{key}' in '{section}' must be true, false, or null.")
    return value


def _optional_section(data: dict, key: str) -> dict:
    """Read an optional object section without hiding malformed values."""
    section = data.get(key, {})
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise PartyFileError(f"'{key}' must be a section (object), not {type(section).__name__}.")
    return section


def _reject_duplicate_json_keys(pairs):
    """Reject ambiguous JSON objects instead of silently accepting the last key."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str):
    raise ValueError(f"Unsupported JSON constant: {value}")


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
        description=_optional_string(section, "description", section="party"),
        created_at=_optional_string(section, "created_at", section="party"),
        created_by=_optional_string(section, "created_by", section="party"),
    )


def _validate_media_source(source_data: dict) -> MediaSource:
    source_type = _require_string(source_data, "type", "media.source")
    value = _require_string(source_data, "value", "media.source")

    if source_type == "magnet":
        if len(value) > 16384:
            raise PartyFileError("The magnet link is too long (maximum 16 KB).")
        try:
            parsed = urllib.parse.urlsplit(value)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        except ValueError as e:
            raise PartyFileError("The media source is not a valid magnet link.") from e
        if (parsed.scheme.lower() != "magnet" or
                not query.get("xt") or
                not any(topic.strip() for topic in query["xt"])):
            raise PartyFileError(
                "The media source type is 'magnet', but the value is missing a "
                "magnet topic (xt) parameter."
            )
        for tracker in query.get("tr", []):
            try:
                tracker_url = urllib.parse.urlsplit(tracker)
                host = (tracker_url.hostname or "").rstrip(".").lower()
                port = tracker_url.port
            except ValueError as e:
                raise PartyFileError("The magnet link contains an invalid tracker URL.") from e
            try:
                ip_address = ipaddress.ip_address(host) if host else None
            except ValueError:
                ip_address = None
            if (len(tracker) > 2048 or tracker_url.scheme.lower() not in {"udp", "http", "https"}
                    or not host or tracker_url.username or tracker_url.password
                    or host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".home.arpa"))
                    or (ip_address is not None and not ip_address.is_global)
                    or (port is not None and not 1 <= port <= 65535)):
                raise PartyFileError(
                    "The magnet link contains a tracker that is not a valid public UDP or HTTP(S) URL."
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
    name_hint = _optional_string(file_data, "name_hint", section="media.file")
    size = file_data.get("size", None)
    if size is not None:
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise PartyFileError("'size' in 'media.file' must be a positive number or null.")
    return MediaFile(name_hint=name_hint, size=size)


MAX_EMBEDDED_TORRENT_BYTES = 512 * 1024


def _magnet_btih(value: str) -> Optional[str]:
    """Return a v1 info hash from a magnet, accepting hex or base32 BTIH."""
    try:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(value).query)
    except ValueError:
        return None
    for topic in query.get("xt", []):
        prefix = "urn:btih:"
        if not topic.lower().startswith(prefix):
            continue
        raw_hash = topic[len(prefix):].strip()
        if re.fullmatch(r"[0-9a-fA-F]{40}", raw_hash):
            return raw_hash.lower()
        if re.fullmatch(r"[A-Za-z2-7]{32}", raw_hash):
            try:
                return base64.b32decode(raw_hash.upper()).hex()
            except binascii.Error:
                return None
    return None


def _torrent_v1_info_hash(payload: bytes) -> str:
    """Check embedded metadata against the invite's magnet before aria2 sees it."""
    try:
        # Kept in the creator module so torrent generation and validation share
        # one canonical bencode implementation.
        from torrent_creator import bdecode, bencode

        torrent = bdecode(payload)
        info = torrent.get(b"info") if isinstance(torrent, dict) else None
        if not isinstance(info, dict):
            raise ValueError("missing info dictionary")
        return hashlib.sha1(bencode(info)).hexdigest()
    except Exception as exc:
        raise PartyFileError("The embedded torrent metadata is invalid.") from exc


def _validate_p2p_endpoint(data: dict, index: int) -> P2PEndpoint:
    section = f"media.p2p.endpoints[{index + 1}]"
    scope = _require_string(data, "scope", section).lower()
    base_url = _require_string(data, "base_url", section)
    peer_host = _require_string(data, "peer_host", section)
    peer_port = _require_int(data, "peer_port", section)
    if scope not in {"lan", "public"}:
        raise PartyFileError(f"'scope' in '{section}' must be 'lan' or 'public'.")
    if not 1 <= peer_port <= 65535:
        raise PartyFileError(f"'peer_port' in '{section}' is not a valid port.")
    try:
        parsed = urllib.parse.urlsplit(base_url)
        host = parsed.hostname or ""
        port = parsed.port
        endpoint_ip = ipaddress.IPv4Address(host)
        peer_ip = ipaddress.IPv4Address(peer_host)
    except (ValueError, ipaddress.AddressValueError) as exc:
        raise PartyFileError(f"'{section}' must use an IPv4 host address and port.") from exc
    if (len(base_url) > 1024 or parsed.scheme.lower() != "http" or not port
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not re.fullmatch(r"/[A-Za-z0-9_-]{32,128}", parsed.path)
            or endpoint_ip != peer_ip):
        raise PartyFileError(f"'{section}' has an invalid bootstrap URL.")
    if scope == "lan" and not endpoint_ip.is_private:
        raise PartyFileError(f"'{section}' is marked LAN but does not contain a private address.")
    if scope == "public" and not endpoint_ip.is_global:
        raise PartyFileError(f"'{section}' is marked public but does not contain a public address.")
    return P2PEndpoint(scope=scope, base_url=base_url, peer_host=str(peer_ip), peer_port=peer_port)


def _validate_p2p(data: object, magnet: str) -> Optional[P2PInfo]:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise PartyFileError("'p2p' in 'media' must be an object or null.")
    version = _require_int(data, "version", "media.p2p")
    if version != 1:
        raise PartyFileError("This party uses an unsupported P2P bootstrap version.")
    torrent_text = _require_string(data, "torrent", "media.p2p")
    if len(torrent_text) > 720000:
        raise PartyFileError("The embedded torrent metadata is too large.")
    try:
        torrent_bytes = base64.b64decode(torrent_text, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise PartyFileError("The embedded torrent metadata is not valid base64.") from exc
    if not torrent_bytes or len(torrent_bytes) > MAX_EMBEDDED_TORRENT_BYTES:
        raise PartyFileError("The embedded torrent metadata is too large or empty.")
    expected_hash = _magnet_btih(magnet)
    actual_hash = _torrent_v1_info_hash(torrent_bytes)
    if not expected_hash or actual_hash != expected_hash:
        raise PartyFileError("The embedded torrent does not match the media magnet link.")

    endpoint_data = _require_key(data, "endpoints", "media.p2p")
    if not isinstance(endpoint_data, list) or not endpoint_data or len(endpoint_data) > 8:
        raise PartyFileError("'endpoints' in 'media.p2p' must contain between 1 and 8 routes.")
    endpoints = []
    seen = set()
    for index, endpoint in enumerate(endpoint_data):
        if not isinstance(endpoint, dict):
            raise PartyFileError(f"Endpoint {index + 1} in 'media.p2p' must be an object.")
        parsed = _validate_p2p_endpoint(endpoint, index)
        if parsed.base_url in seen:
            raise PartyFileError("The P2P bootstrap endpoints contain a duplicate route.")
        seen.add(parsed.base_url)
        endpoints.append(parsed)
    return P2PInfo(torrent_bytes=torrent_bytes, endpoints=endpoints)


def usable_p2p_endpoints(p2p: Optional[P2PInfo]) -> List[P2PEndpoint]:
    """Select local LAN routes first and public routes for Internet guests.

    A private endpoint from an untrusted invite is never contacted unless it is
    on this device's own LAN. This retains direct LAN setup while avoiding
    arbitrary private-network requests from a party file.
    """
    if not p2p:
        return []
    try:
        from p2p_bootstrap import is_same_lan_address
    except Exception:
        return [endpoint for endpoint in p2p.endpoints if endpoint.scope == "public"]
    local = [endpoint for endpoint in p2p.endpoints
             if endpoint.scope == "lan" and is_same_lan_address(endpoint.peer_host)]
    public = [endpoint for endpoint in p2p.endpoints if endpoint.scope == "public"]
    return local if local else public


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
    if file_data is None:
        file_data = {}
    if not isinstance(file_data, dict):
        raise PartyFileError("'file' in 'media' must be a section (object).")
    media_file = _validate_media_file(file_data)

    subs_data = section.get("subtitles", [])
    if subs_data is None:
        subs_data = []
    subtitles = _validate_subtitles(subs_data)

    p2p = _validate_p2p(section.get("p2p"), source.value)

    return MediaInfo(source=source, file=media_file, subtitles=subtitles, p2p=p2p)


def _validate_sync(data: dict) -> SyncInfo:
    section = _require_key(data, "sync", "root")
    if not isinstance(section, dict):
        raise PartyFileError("'sync' must be a section (object), not a single value.")

    room = _require_string(section, "room", "sync")
    server = _optional_string(section, "server", "syncplay.pl", "sync")
    if not server.strip():
        server = "syncplay.pl"

    port = _optional_int(section, "port", 8997, "sync")
    if port < 1 or port > 65535:
        raise PartyFileError(f"Port {port} is not valid. It must be between 1 and 65535.")

    password = _optional_string(section, "password", "", "sync")

    return SyncInfo(server=server, port=port, room=room, password=password)


def _validate_playback(data: dict) -> PlaybackInfo:
    section = _optional_section(data, "playback")
    return PlaybackInfo(
        start_paused=_optional_bool(section, "start_paused", True, "playback")
    )


def _validate_integrity(data: dict) -> IntegrityInfo:
    section = _optional_section(data, "integrity")
    sha256 = section.get("sha256", None)
    if sha256 is not None and not isinstance(sha256, str):
        raise PartyFileError("'sha256' in 'integrity' must be text or null.")
    if sha256 is not None and sha256.strip():
        # Basic hex check
        if not re.fullmatch(r'[0-9a-fA-F]{64}', sha256.strip()):
            raise PartyFileError("'sha256' in 'integrity' doesn't look like a valid SHA-256 hash.")
    return IntegrityInfo(sha256=sha256)


def _validate_compatibility(data: dict) -> CompatibilityInfo:
    section = _optional_section(data, "compatibility")

    min_version_str = _optional_string(
        section, "min_openparty_version", "1.0.0", "compatibility"
    )
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
        with open(path, "rb") as f:
            raw_bytes = f.read(MAX_PARTY_FILE_BYTES + 1)
        if len(raw_bytes) > MAX_PARTY_FILE_BYTES:
            raise PartyFileError("The party file is too large (maximum 1 MB).")
        raw = raw_bytes.decode("utf-8")
    except PermissionError:
        raise PartyFileError(f"Cannot read the party file — permission denied: {path}")
    except UnicodeDecodeError:
        raise PartyFileError("The party file is not valid UTF-8 text.")
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
    if len(raw_json) > MAX_PARTY_FILE_BYTES or len(raw_json.encode("utf-8")) > MAX_PARTY_FILE_BYTES:
        raise PartyFileError("The party file is too large (maximum 1 MB).")

    try:
        data = json.loads(
            raw_json,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as e:
        raise PartyFileError(
            f"The party file is not valid JSON. Check for typos or missing commas near line {e.lineno}."
        )
    except ValueError as e:
        raise PartyFileError(f"The party file contains invalid JSON values: {e}") from e

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
    if not isinstance(extensions, dict):
        raise PartyFileError("'extensions' must be an object or null.")

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
