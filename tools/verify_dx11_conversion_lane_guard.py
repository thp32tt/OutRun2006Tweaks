#!/usr/bin/env python3
"""Static guard helper for DX11 conversion lane invariants.

This is a repository-only check. It does not claim runtime validation.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


REQUIRED_STATE_TOKENS = (
    "NativeDrawPathActive disabled",
    '"runtime_validation": "UNTESTED"',
)


def require_file_token(relative_path: str, token: str) -> None:
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    if token not in text:
        raise SystemExit(
            f"DX11 conversion guard failed: {relative_path} missing {token}"
        )


def main() -> int:
    state_file = "docs/CONVERSION_LANE_STATE.json"
    for token in REQUIRED_STATE_TOKENS:
        require_file_token(state_file, token)

    print("DX11_CONVERSION_LANE_GUARD=PASS")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
