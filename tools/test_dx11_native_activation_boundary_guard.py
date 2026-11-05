#!/usr/bin/env python3
"""DX11 native activation boundary guard.

Repository-only static guard. This intentionally verifies the conversion lane
still keeps the native draw path behind evidence gates. It does not validate
Quest 3/VDXR runtime behaviour.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, marker: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit(f"missing DX11 activation boundary marker: {path}:{marker}")


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    require("docs/CONVERSION_LANE_STATE.json", '"lane": "DX11"')
    require("docs/CONVERSION_LANE_STATE.json", '"native_draw_path_activation_changed": false')
    require("AGENTS.md", "Do not activate or promote semantics without the branch-specific evidence gate.")

    if '"runtime_validation": "PASS"' in state:
        raise SystemExit("runtime claim must not be synthesized by static guard")

    print("DX11_NATIVE_ACTIVATION_BOUNDARY_GUARD=PASS")
    print("RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()
