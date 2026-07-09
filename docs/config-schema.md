# Party File Schema — `.oparty`

> **Single source of truth** for the party file format used by OpenParty.

## Overview

A party file is a portable JSON document describing everything needed to join a watch party.
It uses the `.oparty` extension but is standard UTF-8 JSON internally.

---

## Root Structure

```
Root
├── schema_version   (required, integer)
├── party            (required, object)
├── media            (required, object)
├── sync             (required, object)
├── playback         (optional, object)
├── integrity        (optional, object)
├── compatibility    (optional, object)
└── extensions       (optional, object)
```

---

## `schema_version`

| Property | Value |
|----------|-------|
| Type     | Integer |
| Required | Yes |
| Current  | `2` |

Identifies which version of this spec the file follows. Must be positive.

---

## `party`

Metadata about the watch party.

| Field        | Type   | Required | Description |
|-------------|--------|----------|-------------|
| `name`       | string | **Yes**  | Human-readable party title (max 200 chars) |
| `description`| string | No       | Host notes ("Bring popcorn", "Episode 5") |
| `created_at` | string | No       | ISO-8601 UTC timestamp |
| `created_by` | string | No       | Host display name (informational only) |

---

## `media`

Everything about the media being watched.

### `media.source`

| Field   | Type   | Required | Description |
|---------|--------|----------|-------------|
| `type`  | string | **Yes**  | Source type: `"magnet"` (Note: `"torrent-file"` was removed in v2) |
| `value` | string | **Yes**  | The magnet link URL |

**Validation:** If `type` is `"magnet"`, `value` must start with `"magnet:?"`.

### `media.file`

| Field       | Type    | Required | Description |
|------------|---------|----------|-------------|
| `name_hint` | string  | No       | Expected filename (for multi-file torrents) |
| `size`      | integer | No       | Expected file size in bytes (or `null`) |

### `media.subtitles`

A list of subtitle entries. Each entry:

| Field      | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `language` | string | **Yes**  | Language name (e.g. "English") |
| `url`      | string | **Yes**  | Direct download URL for the subtitle file |

---

## `sync`

Syncplay connection details.

| Field      | Type    | Required | Default        | Description |
|-----------|---------|----------|----------------|-------------|
| `server`   | string  | No       | `"syncplay.pl"` | Syncplay server hostname |
| `port`     | integer | No       | `8997`          | Server port (1–65535). Avoid 8995/8999 (most congested). |
| `room`     | string  | **Yes**  | —              | Shared room name |
| `password` | string  | No       | `""`            | Room password (blank = no password) |

---

## `playback`

Optional playback preferences.

| Field          | Type    | Required | Default | Description |
|---------------|---------|----------|---------|-------------|
| `start_paused` | boolean | No       | `true`  | Whether to start paused |

---

## `integrity`

Optional download verification.

| Field    | Type   | Required | Description |
|---------|--------|----------|-------------|
| `sha256` | string | No       | 64-character hex SHA-256 hash (or `null`) |

---

## `compatibility`

Application version requirements.

| Field                    | Type   | Required | Default   | Description |
|-------------------------|--------|----------|-----------|-------------|
| `min_openparty_version` | string | No       | `"1.0.0"` | Minimum OpenParty version required (semver) |

If the running app is older than `min_openparty_version`, loading fails with:

```
This party requires OpenParty X.Y.Z or newer. You are running version A.B.C. Please update OpenParty.
```

---

## `extensions`

Reserved for future plugins. Always an object. Core OpenParty ignores unknown keys here.

---

## Full Example

```json
{
    "schema_version": 2,

    "party": {
        "name": "Friday Movie Night",
        "description": "Marvel Marathon",
        "created_at": "2026-07-09T18:00:00Z",
        "created_by": "Aditya"
    },

    "media": {
        "source": {
            "type": "magnet",
            "value": "magnet:?xt=urn:btih:08ada5a7a6183aae1e09d831df6748d566095a10&dn=Sintel"
        },
        "file": {
            "name_hint": "Sintel.2010.1080p.mkv",
            "size": null
        },
        "subtitles": [
            {
                "language": "English",
                "url": "https://example.com/subtitles.srt"
            }
        ]
    },

    "sync": {
        "server": "syncplay.pl",
        "port": 8997,
        "room": "friday-movie-night",
        "password": ""
    },

    "playback": {
        "start_paused": true
    },

    "integrity": {
        "sha256": null
    },

    "compatibility": {
        "min_openparty_version": "1.0.0"
    },

    "extensions": {}
}
```

---

## Design Rules

1. **Human-readable** — Someone opening it in Notepad should understand it.
2. **No local paths** — Never store `C:\...` or `/home/...`.
3. **No app preferences** — Only party-related data.
4. **Portable** — Copying the file to another machine is enough.
5. **Forward-compatible** — `schema_version` enables safe evolution.
