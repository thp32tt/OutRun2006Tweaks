#!/usr/bin/env python3
"""Minimal regression test for DXVK continuation window validation."""

import tempfile
from pathlib import Path

from validate_dxvk_continuation_window import validate_window


def test_overlap_bytes_match():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample.bin"
        path.write_bytes(bytes.fromhex("90 66 0f 54 1d 20 91 61 90"))
        result = validate_window(path.read_bytes(), 1, "66 0f 54 1d 20 91 61")
        assert result["matches"] is True


if __name__ == "__main__":
    test_overlap_bytes_match()
    print("ok")
