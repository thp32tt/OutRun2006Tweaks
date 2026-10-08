#!/usr/bin/env python3
"""Static guard for DXVK conversion frontier metadata.

This guard intentionally avoids runtime assumptions. It verifies that the
branch-local conversion state keeps the canonical disassembly frontier
explicit and does not silently drop runtime-validation boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "docs" / "CONVERSION_LANE_STATE.json"


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))

    assert state["branch"] == "vr-dxvk-r71-disasm"
    assert state["lane"] == "DXVK"
    assert state["runtime_validation"] == "UNTESTED" if "runtime_validation" in state else True

    frontier = state["follow_on_frontier"]
    assert frontier["provenance_status"].startswith("EXACT_EXE_")
    assert frontier["predecessor_exact"] is True
    assert frontier["runtime_validation"] == "UNTESTED"

    assert state["latest_static_evidence"]["runtime_validation"] == "UNTESTED"
    assert state["controller_pipeline"]["normal_release_requires"]

    print("DXVK conversion frontier guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
