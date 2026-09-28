#!/usr/bin/env python3
"""Verify the shared VR producer semantic catalog stays synchronized."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "src" / "vr" / "game" / "disasm_render_contract.hpp"
HUD = ROOT / "src" / "vr" / "hud_semantics.hpp"
RUNTIME_SEMANTICS = ROOT / "src" / "vr" / "game" / "render_semantics.hpp"
ANALYZER = ROOT / "tools" / "analyze_outrun_exe.py"

ENTRY_RE = re.compile(
    r'\{\s*0x([0-9A-Fa-f]+)u,\s*0x([0-9A-Fa-f]+)u,\s*'
    r'"([^"]+)",\s*"([^"]+)",\s*'
    r'SpacePolicy::(ScreenHud|WorldBillboard|ProjectedWorldMarker2D|'
    r'ProjectedScreenEffect2D)\s*\}'
)
POLICY_NAMES = {
    "ScreenHud": "SCREEN_HUD",
    "WorldBillboard": "WORLD_BILLBOARD",
    "ProjectedWorldMarker2D": "PROJECTED_WORLD_MARKER_2D",
    "ProjectedScreenEffect2D": "PROJECTED_SCREEN_EFFECT_2D",
}


def load_analyzer_ranges(source: str) -> list[tuple]:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "SEMANTIC_RANGES"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        return [tuple(item) for item in value]
    raise AssertionError("SEMANTIC_RANGES assignment not found")


def load_contract_ranges(source: str) -> list[tuple]:
    ranges = [
        (
            int(begin, 16),
            int(end, 16),
            area,
            semantic,
            POLICY_NAMES[policy],
        )
        for begin, end, area, semantic, policy in ENTRY_RE.findall(source)
    ]
    if not ranges:
        raise AssertionError("CriticalProducerRanges entries not found")
    return ranges


def main() -> int:
    contract_ranges = load_contract_ranges(CONTRACT.read_text(encoding="utf-8"))
    analyzer_ranges = load_analyzer_ranges(ANALYZER.read_text(encoding="utf-8"))

    if contract_ranges != analyzer_ranges:
        missing = [item for item in contract_ranges if item not in analyzer_ranges]
        extra = [item for item in analyzer_ranges if item not in contract_ranges]
        raise AssertionError(
            "semantic catalog drift: "
            f"contract={len(contract_ranges)} analyzer={len(analyzer_ranges)} "
            f"missing_in_analyzer={missing!r} extra_in_analyzer={extra!r}"
        )

    if len(contract_ranges) != 25:
        raise AssertionError(
            f"expected 25 reviewed producer ranges, found {len(contract_ranges)}"
        )

    hud_source = HUD.read_text(encoding="utf-8")
    if "OutRunVR::DisasmContract::CriticalProducerRanges" not in hud_source:
        raise AssertionError("runtime HUD classifier does not consume shared catalog")
    if "InRange(callRva" in hud_source:
        raise AssertionError("runtime HUD classifier still contains a duplicate range map")

    contract_source = CONTRACT.read_text(encoding="utf-8")
    runtime_source = RUNTIME_SEMANTICS.read_text(encoding="utf-8")
    for policy in ("ProjectedWorldMarker2D", "ProjectedScreenEffect2D"):
        if policy not in contract_source:
            raise AssertionError(f"F15 shared SpacePolicy missing {policy}")
        if f"SpacePolicy::{policy}" not in hud_source:
            raise AssertionError(f"F15 HUD policy naming missing {policy}")
        if (
            f"Policy::{policy}" not in runtime_source
            or f"RenderScope::{policy}" not in runtime_source
        ):
            raise AssertionError(
                f"F15 shared-to-runtime projected policy bridge missing {policy}"
            )

    expected_f14 = {
        (0x060900, 0x061100, "ctrl_icon_work", "HUD_CTRL_ICON", "SCREEN_HUD"),
        (0x0BBA00, 0x0BBC00, "DispTempHeartNum", "HUD_TEMP_HEART", "SCREEN_HUD"),
    }
    if not expected_f14.issubset(set(contract_ranges)):
        raise AssertionError("F14 ranges are missing from the shared catalog")

    print(f"VR semantic catalog contract: OK ({len(contract_ranges)} ranges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
