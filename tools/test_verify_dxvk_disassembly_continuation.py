#!/usr/bin/env python3
"""Regression coverage for DXVK continuation overlap verification.

Keeps the byte-boundary contract fail-closed without assigning runtime meaning
or promoting incomplete disassembly into implementation claims.
"""

from __future__ import annotations

import unittest

from verify_dxvk_disassembly_continuation import verify_overlap


class ContinuationOverlapTests(unittest.TestCase):
    def test_accepts_exact_boundary_overlap(self) -> None:
        verify_overlap(
            "90 66 0f 54 1d 20 91 61",
            "66 0f 54 1d 20 91 61",
            "66 0f 54 1d 20 91 61 c3",
        )

    def test_rejects_missing_capture_overlap(self) -> None:
        with self.assertRaises(ValueError):
            verify_overlap(
                "90 66 0f 54 1d 20 91",
                "66 0f 54 1d 20 91 61",
                "66 0f 54 1d 20 91 61 c3",
            )

    def test_rejects_changed_continuation_prefix(self) -> None:
        with self.assertRaises(ValueError):
            verify_overlap(
                "90 66 0f 54 1d 20 91 61",
                "66 0f 54 1d 20 91 61",
                "66 0f 54 1d 20 91 62 c3",
            )


if __name__ == "__main__":
    unittest.main()
