#!/usr/bin/env python3
"""Regression tests for DXVK disassembly continuation-window overlap rules.

This is a repository-only static guard. It intentionally does not infer runtime
semantics from bytes; it only verifies that continuation windows preserve the
validated overlap contract required by the DXVK evidence pipeline.
"""

import unittest


EXPECTED_OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


def validate_continuation_window(previous_tail: bytes, next_window_prefix: bytes) -> bool:
    """Require the next window to begin with the exact captured overlap bytes."""
    return previous_tail == EXPECTED_OVERLAP and next_window_prefix.startswith(EXPECTED_OVERLAP)


class ContinuationWindowOverlapTests(unittest.TestCase):
    def test_validated_overlap_is_required(self):
        self.assertTrue(validate_continuation_window(
            EXPECTED_OVERLAP,
            EXPECTED_OVERLAP + b"\x90\x90",
        ))

    def test_truncated_overlap_is_rejected(self):
        self.assertFalse(validate_continuation_window(
            EXPECTED_OVERLAP[:-1],
            EXPECTED_OVERLAP + b"\x90",
        ))

    def test_modified_prefix_is_rejected(self):
        modified = bytes.fromhex("66 0f 54 1d 20 91 60")
        self.assertFalse(validate_continuation_window(modified, modified))


if __name__ == "__main__":
    unittest.main()
