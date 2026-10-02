#!/usr/bin/env python3
"""Additional source-only regression cases for the DX11 conversion gate.

Covers malformed and ambiguous activation configuration states. These checks
keep static conversion evidence separate from runtime activation.
"""

from pathlib import Path

from dx11_conversion_dormant_activation_guard import validate


def test_missing_activation_marker_is_rejected(tmp_path: Path) -> None:
    candidate = tmp_path / "config.txt"
    candidate.write_text("DX11_MODE=conversion\n", encoding="utf-8")
    assert validate(candidate, False) == 0


def test_conflicting_activation_markers_fail_closed(tmp_path: Path) -> None:
    candidate = tmp_path / "config.txt"
    candidate.write_text(
        "DX11_NATIVE_DRAW_ENABLED=0\nDX11_NATIVE_DRAW_ENABLED=1\n",
        encoding="utf-8",
    )
    assert validate(candidate, False) == 1


if __name__ == "__main__":
    print("DX11 dormant activation edge regression cases defined")
