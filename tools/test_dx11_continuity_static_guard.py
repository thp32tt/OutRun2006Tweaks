#!/usr/bin/env python3
"""DX11 static guard for conversion work queue continuity.

Checks repository-only evidence. It does not enable native draw routing and does
not claim Quest 3/VDXR validation.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, marker: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit(f"missing DX11 continuity marker: {path}:{marker}")


def main() -> None:
    require("docs/CONVERSION_LANE_STATE.json", '"lane": "DX11"')
    require("docs/CONVERSION_LANE_STATE.json", '"normal_success_requires"')
    require("AGENTS.md", "SUBSTANTIVE_C2_REQUIRED")
    require("CMakeLists.txt", "dx11_fixed_function_shader_semantics")

    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    if '"runtime_validation": "UNTESTED"' not in state:
        raise SystemExit("runtime evidence boundary changed unexpectedly")
    if '"NativeDrawPathActive": true' in state:
        raise SystemExit("native activation must remain gated")

    print("DX11_CONTINUITY_STATIC_GUARD=PASS")
    print("RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()
