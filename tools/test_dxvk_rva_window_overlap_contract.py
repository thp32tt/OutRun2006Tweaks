"""Static regression tests for DXVK disassembly window overlap contracts.

This test is intentionally offline: it validates evidence-window rules used by
DXVK conversion analysis without promoting bytes into runtime semantics.
"""


def validate_overlap(prefix_hex: str, continuation_hex: str) -> bool:
    prefix = bytes.fromhex(prefix_hex)
    continuation = bytes.fromhex(continuation_hex)
    if not prefix or not continuation:
        return False
    if len(continuation) > len(prefix):
        return False
    return prefix[-len(continuation):] == continuation


def test_known_182f7e_overlap_frontier():
    assert validate_overlap(
        "66 0f 54 1d 20 91 61",
        "66 0f 54 1d 20 91 61",
    )


def test_shorter_continuation_frontier_is_accepted():
    assert validate_overlap(
        "90 66 0f 54 1d",
        "66 0f 54 1d",
    )


def test_longer_continuation_than_window_is_rejected():
    assert not validate_overlap(
        "66 0f 54",
        "66 0f 54 1d",
    )


def test_empty_overlap_is_rejected():
    assert not validate_overlap("", "66 0f")


def test_non_matching_frontier_is_rejected():
    assert not validate_overlap(
        "90 90 90 90",
        "66 0f 54 1d",
    )
