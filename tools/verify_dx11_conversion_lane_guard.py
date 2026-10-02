#!/usr/bin/env python3
"""Static guard helper for DX11 conversion lane invariants."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_file_token(relative_path: str, token: str) -> None:
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    if token not in text:
        raise SystemExit(
            f"DX11 conversion guard failed: {relative_path} missing {token}"
        )


def main() -> None:
    # Keep activation disabled until exact-build/runtime evidence exists.
    require_file_token(
        "docs/CONVERSION_LANE_STATE.json",
        "NativeDrawPathActive disabled",
    )
    require_file_token(
        "docs/CONVERSION_LANE_STATE.json",
        "runtime_validation",
    )


if __name__ == "__main__":
    main()
