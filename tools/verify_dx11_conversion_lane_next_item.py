#!/usr/bin/env python3
"""Static continuation guard for the DX11 conversion lane.

This probe keeps the next source-only review target explicit when runtime
hardware evidence is unavailable. It intentionally does not activate the
native draw path; activation still requires the existing backend evidence
contracts and runtime validation.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MARKERS = {
    "AGENTS.md": [
        "DX11 Native is the primary implementation/performance lane",
        "runtime-only evidence is unavailable, continue independent GitHub-only source/static/CI work",
    ],
    "docs/CONVERSION_LANE_STATE.json": [
        '"lane": "DX11"',
        '"runtime_validation": "UNTESTED"',
    ],
}


def main() -> None:
    missing = []
    for relative, markers in REQUIRED_MARKERS.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                missing.append(f"{relative}: {marker}")
    if missing:
        raise SystemExit(
            "DX11 conversion continuation guard drift: " + ", ".join(missing)
        )
    print("DX11 conversion continuation probe: PASS")


if __name__ == "__main__":
    main()
