#!/usr/bin/env python3
"""Static regression test for DX11 dormant activation guard behavior.

This test is intentionally source-only. It protects the conversion lane from
accidentally treating a runtime activation marker as valid evidence.
"""

from pathlib import Path

from dx11_conversion_dormant_activation_guard import validate


def test_active_marker_is_rejected(tmp_path: Path) -> None:
    candidate = tmp_path / "config.txt"
    candidate.write_text("DX11_NATIVE_DRAW_ENABLED=1\n", encoding="utf-8")
    assert validate(candidate, False) == 1


def test_inactive_configuration_is_accepted(tmp_path: Path) -> None:
    candidate = tmp_path / "config.txt"
    candidate.write_text("DX11_NATIVE_DRAW_ENABLED=0\n", encoding="utf-8")
    assert validate(candidate, False) == 0


if __name__ == "__main__":
    print("DX11 dormant activation guard regression cases defined")
