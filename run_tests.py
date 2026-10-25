"""
Test runner for OpenParty.
Executes all test suites (loader tests, torrent tests, dependency tests).
"""

import sys
import os
import subprocess

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    test_scripts = [
        os.path.join(root, "app", "config", "test_loader.py"),
        os.path.join(root, "app", "test_torrent.py"),
        os.path.join(root, "app", "test_integration.py"),
    ]

    print("=" * 60)
    print("OpenParty Automated Test Suite")
    print("=" * 60)

    all_passed = True
    for script in test_scripts:
        rel = os.path.relpath(script, root)
        print(f"\n>>> Running: {rel}")
        ret = subprocess.call([sys.executable, script])
        if ret != 0:
            all_passed = False
            print(f">>> FAILED: {rel}")
        else:
            print(f">>> PASSED: {rel}")

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TEST SUITES PASSED SUCCESSFULLY")
        print("=" * 60)
        sys.exit(0)
    else:
        print("ERROR: ONE OR MORE TEST SUITES FAILED")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
