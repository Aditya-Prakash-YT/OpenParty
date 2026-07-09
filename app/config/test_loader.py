"""
Tests for the party file loader/validator.

Each test feeds the loader a deliberately broken input and confirms
it produces the correct specific error — never a crash.
"""

import sys
import os
import json
import traceback

# Add the app directory to the path so we can import config.loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.loader import load_party_string, load_party_file, PartyFileError


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

_passed = 0
_failed = 0


def _test(name: str, raw_json: str, expected_substring: str):
    """Run one test: feed raw_json to loader, expect PartyFileError containing expected_substring."""
    global _passed, _failed
    try:
        load_party_string(raw_json)
        print(f"  FAIL  {name}")
        print(f"        Expected error containing: '{expected_substring}'")
        print(f"        But loading succeeded (no error raised).")
        _failed += 1
    except PartyFileError as e:
        msg = str(e)
        if expected_substring.lower() in msg.lower():
            print(f"  PASS  {name}")
            _passed += 1
        else:
            print(f"  FAIL  {name}")
            print(f"        Expected error containing: '{expected_substring}'")
            print(f"        Got: '{msg}'")
            _failed += 1
    except Exception as e:
        print(f"  FAIL  {name}")
        print(f"        Expected PartyFileError, got {type(e).__name__}: {e}")
        traceback.print_exc()
        _failed += 1


def _test_success(name: str, raw_json: str):
    """Run one test: feed raw_json to loader, expect success."""
    global _passed, _failed
    try:
        config = load_party_string(raw_json)
        print(f"  PASS  {name}")
        _passed += 1
        return config
    except Exception as e:
        print(f"  FAIL  {name}")
        print(f"        Expected success, got {type(e).__name__}: {e}")
        _failed += 1
        return None


# ---------------------------------------------------------------------------
# A valid base config we can break in different ways
# ---------------------------------------------------------------------------

VALID_CONFIG = {
    "schema_version": 1,
    "party": {
        "name": "Test Party",
        "description": "Test",
        "created_at": "2026-07-09T18:00:00Z",
        "created_by": "Tester"
    },
    "media": {
        "source": {
            "type": "magnet",
            "value": "magnet:?xt=urn:btih:08ada5a7a6183aae1e09d831df6748d566095a10"
        },
        "file": {
            "name_hint": "Movie.mkv",
            "size": None
        },
        "subtitles": []
    },
    "sync": {
        "server": "syncplay.pl",
        "port": 8997,
        "room": "test-room",
        "password": ""
    },
    "playback": {
        "start_paused": True
    },
    "integrity": {
        "sha256": None
    },
    "compatibility": {
        "min_openparty_version": "1.0.0"
    },
    "extensions": {}
}


def _make(overrides: dict = None, remove_keys: list = None) -> str:
    """Create a modified copy of VALID_CONFIG and return as JSON string."""
    import copy
    cfg = copy.deepcopy(VALID_CONFIG)
    if overrides:
        for dotted_key, value in overrides.items():
            keys = dotted_key.split(".")
            target = cfg
            for k in keys[:-1]:
                target = target[k]
            target[keys[-1]] = value
    if remove_keys:
        for dotted_key in remove_keys:
            keys = dotted_key.split(".")
            target = cfg
            for k in keys[:-1]:
                target = target[k]
            del target[keys[-1]]
    return json.dumps(cfg, indent=2)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests():
    global _passed, _failed

    print("=" * 60)
    print("OpenParty — Party File Loader Tests")
    print("=" * 60)

    # --- Valid file ---
    print("\n--- Valid Files ---")
    _test_success("Valid config loads cleanly", _make())
    _test_success("Valid config minimal (no optional sections)",
        json.dumps({
            "schema_version": 1,
            "party": {"name": "Minimal Party"},
            "media": {
                "source": {"type": "magnet", "value": "magnet:?xt=urn:btih:abc123"}
            },
            "sync": {"room": "test-room"}
        })
    )

    # --- Load from example file ---
    print("\n--- Example File ---")
    example_path = os.path.join(os.path.dirname(__file__), "example.oparty")
    try:
        config = load_party_file(example_path)
        print(f"  PASS  example.oparty loads cleanly")
        print(f"        Party: {config.party.name}")
        print(f"        Room:  {config.sync.room}")
        _passed += 1
    except Exception as e:
        print(f"  FAIL  example.oparty: {e}")
        _failed += 1

    # --- Empty / malformed ---
    print("\n--- Empty / Malformed ---")
    _test("Empty string", "", "empty")
    _test("Whitespace only", "   \n  ", "empty")
    _test("Not JSON", "this is not json", "not valid JSON")
    _test("JSON array instead of object", "[1, 2, 3]", "JSON object")

    # --- schema_version ---
    print("\n--- schema_version ---")
    _test("Missing schema_version", _make(remove_keys=["schema_version"]), "schema_version")
    _test("schema_version is string", _make({"schema_version": "1"}), "whole number")
    _test("schema_version is boolean", _make({"schema_version": True}), "whole number")
    _test("schema_version is 0", _make({"schema_version": 0}), "positive")
    _test("schema_version is -1", _make({"schema_version": -1}), "positive")
    _test("schema_version is 99 (unsupported)", _make({"schema_version": 99}), "only supports")

    # --- party ---
    print("\n--- party ---")
    _test("Missing party section", _make(remove_keys=["party"]), "missing")
    _test("party is a string", _make({"party": "not an object"}), "section")
    _test("Missing party name", json.dumps({
        "schema_version": 1,
        "party": {"description": "No name"},
        "media": {"source": {"type": "magnet", "value": "magnet:?xt=urn:btih:abc"}},
        "sync": {"room": "r"}
    }), "name")
    _test("Empty party name", _make({"party.name": ""}), "cannot be empty")
    _test("Party name too long", _make({"party.name": "x" * 201}), "too long")

    # --- media ---
    print("\n--- media ---")
    _test("Missing media section", _make(remove_keys=["media"]), "missing")
    _test("Missing media.source", json.dumps({
        "schema_version": 1,
        "party": {"name": "T"},
        "media": {"file": {}},
        "sync": {"room": "r"}
    }), "source")
    _test("media.source missing type", json.dumps({
        "schema_version": 1,
        "party": {"name": "T"},
        "media": {"source": {"value": "magnet:?xt=urn:btih:abc"}},
        "sync": {"room": "r"}
    }), "type")
    _test("Magnet link doesn't start with magnet:?",
        _make({"media.source.value": "not-a-magnet"}), "magnet")
    _test("Unsupported source type",
        _make({"media.source.type": "ftp", "media.source.value": "ftp://example.com"}), "Unsupported")
    _test("Local torrent file",
        _make({"media.source.type": "torrent-file", "media.source.value": "C:/movie.torrent"}), "no longer supported")

    # --- media.file ---
    _test("File size is negative",
        _make({"media.file.size": -100}), "positive")

    # --- subtitles ---
    _test("Subtitles is a string",
        _make({"media.subtitles": "not a list"}), "list")
    _test("Subtitle entry missing language", json.dumps({
        "schema_version": 1,
        "party": {"name": "T"},
        "media": {
            "source": {"type": "magnet", "value": "magnet:?xt=urn:btih:abc"},
            "subtitles": [{"url": "https://example.com/sub.srt"}]
        },
        "sync": {"room": "r"}
    }), "language")

    # --- sync ---
    print("\n--- sync ---")
    _test("Missing sync section", _make(remove_keys=["sync"]), "missing")
    _test("Missing room", json.dumps({
        "schema_version": 1,
        "party": {"name": "T"},
        "media": {"source": {"type": "magnet", "value": "magnet:?xt=urn:btih:abc"}},
        "sync": {"server": "syncplay.pl"}
    }), "room")
    _test("Port out of range (99999)",
        _make({"sync.port": 99999}), "not valid")
    _test("Port zero",
        _make({"sync.port": 0}), "not valid")

    # --- integrity ---
    print("\n--- integrity ---")
    _test("Invalid SHA-256",
        _make({"integrity.sha256": "not-a-hash"}), "SHA-256")

    # --- compatibility / version check ---
    print("\n--- compatibility ---")
    _test("Requires newer OpenParty (99.0.0)",
        _make({"compatibility.min_openparty_version": "99.0.0"}), "requires OpenParty 99.0.0")
    _test("Requires newer OpenParty (2.0.0)",
        _make({"compatibility.min_openparty_version": "2.0.0"}), "requires OpenParty 2.0.0")
    _test_success("Requires exactly current version (1.0.0)",
        _make({"compatibility.min_openparty_version": "1.0.0"}))
    _test_success("Requires older version (0.5.0)",
        _make({"compatibility.min_openparty_version": "0.5.0"}))

    # --- File not found ---
    print("\n--- File loading ---")
    try:
        load_party_file("nonexistent_file.oparty")
        print("  FAIL  File not found — expected error")
        _failed += 1
    except PartyFileError as e:
        if "not found" in str(e).lower():
            print("  PASS  File not found gives clear error")
            _passed += 1
        else:
            print(f"  FAIL  File not found — wrong message: {e}")
            _failed += 1

    # --- Summary ---
    print("\n" + "=" * 60)
    total = _passed + _failed
    print(f"Results: {_passed}/{total} passed, {_failed}/{total} failed")
    if _failed == 0:
        print("All tests passed!")
    else:
        print(f"{_failed} test(s) failed.")
    print("=" * 60)

    return _failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
