"""Small, UI-independent helpers for describing aria2 BitTorrent peers."""


def format_rate(value) -> str:
    try:
        rate = max(0, int(value or 0))
    except (TypeError, ValueError):
        rate = 0
    if rate >= 1024 * 1024:
        return f"{rate / (1024 * 1024):.1f} MiB/s"
    if rate >= 1024:
        return f"{rate / 1024:.1f} KiB/s"
    return f"{rate} B/s"


def format_bytes(value) -> str:
    try:
        amount = max(0, int(value or 0))
    except (TypeError, ValueError):
        amount = 0
    if amount >= 1024 ** 3:
        return f"{amount / (1024 ** 3):.2f} GiB"
    if amount >= 1024 ** 2:
        return f"{amount / (1024 ** 2):.1f} MiB"
    if amount >= 1024:
        return f"{amount / 1024:.1f} KiB"
    return f"{amount} B"


def peer_progress(peer: dict, piece_count: int):
    """Convert aria2's bitfield to a percentage when piece count is known."""
    if str(peer.get("seeder", "false")).lower() == "true":
        return 100
    try:
        piece_count = int(piece_count)
        bits = bytes.fromhex(str(peer.get("bitfield", "")))
    except (TypeError, ValueError):
        return None
    if piece_count <= 0:
        return None
    available = sum(byte.bit_count() for byte in bits)
    return min(100, round(available * 100 / piece_count))

