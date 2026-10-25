"""
End-to-End Integration Test for OpenParty.
Tests the full lifecycle:
1. Host selects local video file.
2. Torrent and magnet link are created.
3. .oparty party invite file is generated and validated.
4. Joiner parses the .oparty file.
5. All metadata (hashes, trackers, file size, sync room) matches perfectly.
"""

import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.dirname(__file__))

from torrent_creator import create_local_torrent, bdecode
from config.loader import load_party_string, PartyConfig

def run_integration_test():
    print("=" * 60)
    print("OpenParty - End-to-End Host/Joiner Integration Test")
    print("=" * 60)

    # Step 1: Create dummy video file
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"SAMPLE VIDEO STREAM CONTENT FOR OPENPARTY WATCH PARTY\n" * 1500)
        video_path = f.name
    
    torrent_path = None
    try:
        file_size = os.path.getsize(video_path)
        file_name = os.path.basename(video_path)
        print(f"1. Host video file created: {file_name} ({file_size} bytes)")

        # Step 2: Create torrent & magnet
        magnet, info_hash, torrent_path = create_local_torrent(video_path)
        print(f"2. Torrent created:")
        print(f"   Info Hash: {info_hash}")
        print(f"   Magnet:    {magnet[:60]}...")
        assert magnet.startswith("magnet:?xt=urn:btih:"), "Invalid magnet scheme"
        assert f"&dn={file_name}" in magnet, "Filename missing from magnet link"
        assert os.path.isfile(torrent_path), "Torrent file not written"

        # Verify .torrent file structure
        with open(torrent_path, "rb") as tf:
            tdata = bdecode(tf.read())
        assert b"info" in tdata, "Missing info dict in torrent"
        assert tdata[b"info"][b"length"] == file_size, "Torrent length mismatch"
        print("3. Verified .torrent file binary format and integrity")

        # Step 3: Host generates .oparty file
        party_data = {
            "schema_version": 2,
            "party": {
                "name": "Friday Movie Marathon",
                "description": "Hosted with OpenParty",
                "created_by": "HostUser"
            },
            "media": {
                "source": {
                    "type": "magnet",
                    "value": magnet
                },
                "file": {
                    "name_hint": file_name,
                    "size": file_size
                }
            },
            "sync": {
                "server": "syncplay.pl",
                "port": 8997,
                "room": "friday-marathon-room",
                "password": ""
            }
        }
        oparty_json = json.dumps(party_data, indent=2)
        print("4. Host generated .oparty configuration JSON")

        # Step 4: Joiner receives and loads .oparty data
        config: PartyConfig = load_party_string(oparty_json)
        assert config.party.name == "Friday Movie Marathon"
        assert config.party.created_by == "HostUser"
        assert config.media.source.value == magnet
        assert config.media.file.name_hint == file_name
        assert config.media.file.size == file_size
        assert config.sync.room == "friday-marathon-room"
        assert config.sync.server == "syncplay.pl"
        assert config.sync.port == 8997
        print("5. Joiner successfully parsed and validated .oparty configuration")

        print("\n" + "=" * 60)
        print("INTEGRATION TEST PASSED: Full lifecycle validated!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nINTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass
        if torrent_path and os.path.exists(torrent_path):
            try:
                os.remove(torrent_path)
            except Exception:
                pass

if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)
