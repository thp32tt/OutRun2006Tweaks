#!/usr/bin/env python3
"""Small GitHub-only regression probe for DX11 conversion lane invariants.

This intentionally does not require a Windows runtime or GPU.  It protects
static conversion work from accidentally enabling runtime routing while the
native draw path evidence gate is still pending.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    required = (
        '"lane": "DX11"',
        '"github_only_development": true',
        '"runtime_validation": "UNTESTED"',
    )
    missing = [item for item in required if item not in state]
    if missing:
        raise SystemExit("missing DX11 lane contract markers: " + ", ".join(missing))

    source = ROOT / "src" / "vr" / "d3d11"
    if not source.exists():
        raise SystemExit("DX11 source tree missing")

    print("DX11 conversion lane contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
