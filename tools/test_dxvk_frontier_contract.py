#!/usr/bin/env python3
"""Static regression checks for DXVK conversion frontier evidence contracts."""

from __future__ import annotations

import json
from pathlib import Path


FRONTIER_START = "0x00182F7E"
FRONTIER_END = "0x00182FBE"
OVERLAP = "66 0f 54 1d 20 91 61"


def load_state() -> dict:
    state = Path(__file__).parents[1] / "docs" / "CONVERSION_LANE_STATE.json"
    return json.loads(state.read_text(encoding="utf-8"))


def test_frontier_contract_constants() -> None:
    state = load_state()
    frontier = state["follow_on_frontier"]

    assert frontier["provenance_start_rva"] == FRONTIER_START
    assert frontier["probe_end_rva"] == FRONTIER_END
    assert frontier["overlap_bytes"] == OVERLAP
    assert frontier["runtime_validation"] == "UNTESTED"


def test_no_semantic_promotion_from_static_frontier() -> None:
    state = load_state()
    assert state["runtime_blocker"]
    assert state["follow_on_frontier"]["provenance_status"].startswith("EXACT_")


if __name__ == "__main__":
    test_frontier_contract_constants()
    test_no_semantic_promotion_from_static_frontier()
    print("DXVK frontier contract: PASS")
