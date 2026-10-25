"""
Unit tests for torrent creation, magnet link generation, and dependency checking.
"""

import sys
import os
import tempfile
import hashlib

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from torrent_creator import (
    build_magnet_link,
    create_local_torrent,
    bencode,
    bdecode,
    FALLBACK_TRACKERS,
    PUBLIC_TRACKERS,
    get_optimal_piece_length,
    SeederManager,
    seed_with_aria2c,
)
from deps import check_dependencies, REQUIRED_DEPS, find_aria2c
from downloader.aria2 import Aria2Manager
import time
import shutil

_passed = 0
_failed = 0

def assert_true(cond, name, detail=""):
    global _passed, _failed
    if cond:
        print(f"  PASS  {name}")
        _passed += 1
    else:
        print(f"  FAIL  {name} {detail}")
        _failed += 1

def run_torrent_tests():
    global _passed, _failed
    print("=" * 60)
    print("OpenParty - Torrent & Dependencies Tests")
    print("=" * 60)

    # 1. Test build_magnet_link
    print("\n--- Magnet Link Generation ---")
    dummy_hash = "0123456789abcdef0123456789abcdef01234567"
    mag = build_magnet_link(dummy_hash, "test movie.mp4")
    assert_true(mag.startswith("magnet:?xt=urn:btih:" + dummy_hash), "Magnet prefix and hash")
    assert_true("&dn=test+movie.mp4" in mag or "&dn=test%20movie.mp4" in mag, "Magnet display name encoded")
    assert_true("&tr=" in mag, "Magnet contains trackers")

    custom_trackers = ["udp://tracker.custom.org:1337/announce"]
    mag_custom = build_magnet_link(dummy_hash, "custom.mkv", custom_trackers)
    assert_true("tracker.custom.org" in mag_custom, "Magnet uses custom trackers")

    # 2. Test bencode and bdecode roundtrip
    print("\n--- Bencode / Bdecode Roundtrip ---")
    test_dict = {
        b"announce": b"udp://tracker.example.com:80/announce",
        b"info": {
            b"length": 1048576,
            b"name": b"sample.mp4",
            b"piece length": 262144,
            b"pieces": b"x" * 80
        }
    }
    encoded = bencode(test_dict)
    assert_true(isinstance(encoded, bytes) and len(encoded) > 0, "Bencode produces non-empty bytes")
    decoded = bdecode(encoded)
    assert_true(decoded[b"announce"] == test_dict[b"announce"], "Bdecode preserves announce")
    assert_true(decoded[b"info"][b"length"] == 1048576, "Bdecode preserves piece length")

    # 3. Test create_local_torrent with temporary file
    print("\n--- Local Torrent Creation ---")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        # Write 300 KB of dummy data
        data = b"OpenParty test video chunk content\n" * 9000
        f.write(data)
        temp_file_path = f.name

    try:
        file_size = os.path.getsize(temp_file_path)
        magnet, info_hash, torrent_path = create_local_torrent(temp_file_path)

        assert_true(len(info_hash) == 40, f"Info hash length is 40 hex chars (got {len(info_hash)})")
        assert_true(magnet.startswith("magnet:?xt=urn:btih:"), "Magnet starts with correct URI scheme")
        assert_true(os.path.isfile(torrent_path), f"Torrent file created at {torrent_path}")
        assert_true(torrent_path.endswith(".torrent"), "Torrent file has .torrent extension")

        # Verify contents of generated .torrent file
        with open(torrent_path, "rb") as tf:
            tf_data = tf.read()
        parsed = bdecode(tf_data)
        assert_true(b"info" in parsed, "Torrent file has 'info' dictionary")
        assert_true(parsed[b"info"][b"name"].decode("utf-8") == os.path.basename(temp_file_path), "Torrent info name matches")
        assert_true(parsed[b"info"][b"length"] == file_size, "Torrent info length matches")

        # Clean up torrent file
        try:
            if os.path.exists(torrent_path):
                os.remove(torrent_path)
        except Exception:
            pass

    finally:
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception:
            pass

    # 4. Test dependencies contract
    print("\n--- Dependencies Specification ---")
    assert_true("vlc" in REQUIRED_DEPS, "VLC is in REQUIRED_DEPS")
    assert_true("syncplay" in REQUIRED_DEPS, "Syncplay is in REQUIRED_DEPS")
    assert_true("aria2c" in REQUIRED_DEPS, "aria2c is in REQUIRED_DEPS")
    assert_true("qbittorrent" not in REQUIRED_DEPS, "qbittorrent is NOT in REQUIRED_DEPS (optional fallback)")

    deps_status = check_dependencies()
    assert_true(isinstance(deps_status, dict), "check_dependencies returns a dict")
    assert_true(all(k in deps_status for k in REQUIRED_DEPS), "All required deps checked")

    # 5. Test optimal piece length
    print("\n--- Optimal Piece Length ---")
    assert_true(get_optimal_piece_length(10 * 1024 * 1024) == 64 * 1024, "Tiny file piece length is 64KB")
    assert_true(get_optimal_piece_length(200 * 1024 * 1024) == 256 * 1024, "Medium file piece length is 256KB")
    assert_true(get_optimal_piece_length(1500 * 1024 * 1024) == 1024 * 1024, "1.5GB file piece length is 1MB")
    assert_true(get_optimal_piece_length(4 * 1024**3) == 2 * 1024 * 1024, "4GB file piece length is 2MB")

    # 6. Test trackers list
    print("\n--- Trackers Configuration ---")
    assert_true(len(PUBLIC_TRACKERS) >= 8, f"Sufficient public trackers configured (got {len(PUBLIC_TRACKERS)})")
    assert_true(any(t.startswith("http://") for t in PUBLIC_TRACKERS), "HTTP tracker fallback present")
    assert_true(any(t.startswith("udp://") for t in PUBLIC_TRACKERS), "UDP trackers present")

    # 7. Test SeederManager lifecycle
    print("\n--- SeederManager Lifecycle ---")
    assert_true(not SeederManager.is_seeding(), "SeederManager initial state is not seeding")
    SeederManager.stop_seeding()
    assert_true(SeederManager.get_current_file() is None, "Current file is None after stop_seeding")

    # 8. Loopback aria2c Transfer Test
    aria_exe = find_aria2c()
    if aria_exe:
        print("\n--- Loopback aria2c Seeder & Downloader Transfer ---")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            tf.write(b"OpenParty integration loopback data payload\n" * 5000)
            loop_video = tf.name
        
        loop_mag, loop_h, loop_tor = create_local_torrent(loop_video)
        loop_proc = seed_with_aria2c(loop_tor, os.path.dirname(loop_video), aria_exe)
        assert_true(loop_proc is not None, "seed_with_aria2c started seeder process")

        if loop_proc:
            SeederManager.set_seed_process(loop_proc, loop_tor, loop_video)
            assert_true(SeederManager.is_seeding(), "SeederManager reports is_seeding() == True")
            assert_true(SeederManager.get_current_file() == loop_video, "SeederManager tracks current file")

            dl_dir = tempfile.mkdtemp()
            mgr = Aria2Manager()
            try:
                mgr.start(dl_dir)
                gid = mgr.add_uri(loop_mag)
                assert_true(bool(gid), f"Downloader accepted magnet link (GID: {gid})")

                # Poll up to 15 seconds for metadata and download completion
                transferred = False
                cur_gid = gid
                for _ in range(30):
                    time.sleep(0.5)
                    st = mgr.get_status(cur_gid)
                    state = st.get("status")
                    fol = st.get("followedBy")
                    if fol and state == "complete":
                        cur_gid = fol[0]
                        continue
                    if state == "complete" and not fol:
                        transferred = True
                        break

                assert_true(transferred, "Downloader completed file transfer via Local Peer Discovery (LPD)")
            finally:
                mgr.stop()
                SeederManager.stop_seeding()
                shutil.rmtree(dl_dir, ignore_errors=True)
                try:
                    os.remove(loop_video)
                    os.remove(loop_tor)
                except Exception:
                    pass

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
    success = run_torrent_tests()
    sys.exit(0 if success else 1)
