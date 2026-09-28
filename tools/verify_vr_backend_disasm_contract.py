#!/usr/bin/env python3
"""Verify the DX11/DXVK backend contract still matches recovered OutRun EXE facts."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, needles: list[str]) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{path}: missing disassembly contract evidence: {missing}")


def verify_semantic_range_parity() -> None:
    shared_text = (ROOT / "src/vr/game/disasm_render_contract.hpp").read_text(encoding="utf-8")
    analyzer_text = (ROOT / "tools/analyze_outrun_exe.py").read_text(encoding="utf-8")
    hud_text = (ROOT / "src/vr/hud_semantics.hpp").read_text(encoding="utf-8")

    shared = {
        (int(begin, 16), int(end, 16)):
            "SCREEN_HUD" if policy == "ScreenHud" else "WORLD_BILLBOARD"
        for begin, end, policy in re.findall(
            r"\{\s*0x([0-9A-Fa-f]+)u,\s*0x([0-9A-Fa-f]+)u,\s*SpacePolicy::(ScreenHud|WorldBillboard)\s*\}",
            shared_text,
        )
    }
    analyzer = {
        (int(begin, 16), int(end, 16)): policy
        for begin, end, policy in re.findall(
            r'\(0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+),\s*"[^"]+",\s*"[^"]+",\s*"(SCREEN_HUD|WORLD_BILLBOARD)"\)',
            analyzer_text,
        )
    }
    hud_ranges = {
        (int(begin, 16), int(end, 16))
        for begin, end in re.findall(
            r"InRange\(callRva,\s*0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+)\)",
            hud_text,
        )
    }

    if shared != analyzer:
        raise SystemExit(
            "backend semantic range drift: disasm_render_contract.hpp and "
            "analyze_outrun_exe.py disagree"
        )
    if set(shared) != hud_ranges:
        missing_from_shared = sorted(hud_ranges - set(shared))
        stale_in_shared = sorted(set(shared) - hud_ranges)
        raise SystemExit(
            "backend semantic range drift vs hud_semantics.hpp: "
            f"missing_from_shared={missing_from_shared}, stale_in_shared={stale_in_shared}"
        )


def main() -> None:
    require(
        "src/vr/game/disasm_render_contract.hpp",
        [
            "ViewRva       = 0x0055D860u",
            "ProjectionRva = 0x0055D8A0u",
            "WorldViewRva  = 0x0055DB20u",
            "WvpVsRegister = 64u",
            "WvpVsRegisterCount = 4u",
            "SpriteQueueEntryRva = 0x0002D734u",
            "SpriteQueueNodeRva = 0x0002D762u",
            "SpriteQueueEpilogueRva = 0x0002DCB4u",
            "Calc3D2DRva = 0x00049940u",
            "RankMarkerRva = 0x000BAD20u",
            "0x000BB0FBu",
            "0x000BB2D0u",
            "std::array<ProducerRange, 25>",
            "0x00060900u, 0x00061100u, SpacePolicy::ScreenHud",
            "0x00081A00u, 0x00081B00u, SpacePolicy::ScreenHud",
            "0x000BBA00u, 0x000BBC00u, SpacePolicy::ScreenHud",
            "0x000BE300u, 0x000BEA40u, SpacePolicy::ScreenHud",
            "0x000FC800u, 0x000FC8A0u, SpacePolicy::ScreenHud",
            "0x0005B300u, 0x0005B700u, SpacePolicy::WorldBillboard",
        ],
    )
    require(
        "src/vr/game/outrun_renderer.cpp",
        [
            "OutRunVR::DisasmContract::WvpVsRegister",
            "OutRunVR::DisasmContract::WvpVsRegisterCount",
            "OutRunVR::DisasmContract::ViewRva",
            "OutRunVR::DisasmContract::ProjectionRva",
            "OutRunVR::DisasmContract::WorldViewRva",
        ],
    )
    require(
        "src/vr/d3d9/stereo_renderer_r7.inc",
        [
            "OutRunVR::DisasmContract::WvpVsRegister",
            "OutRunVR::DisasmContract::WvpVsRegisterCount",
            "OutRunVR::DisasmContract::ProjectionRva",
        ],
    )
    require(
        "src/vr/game/render_semantics.hpp",
        [
            "0x42D734 enters the per-priority SpriteNode walk",
            "0x42D762 begins one node",
            "0x42DCB4 is the common epilogue",
        ],
    )
    require(
        "tools/analyze_outrun_exe.py",
        [
            '0x049940: "Calc3D2D"',
            '0x0BAD20: "RankMarker_sub_4BAD20"',
            '0x0BB0FB: "RankMarker sprani #1"',
            '0x0BB2D0: "RankMarker clip #5"',
            '(0x060900, 0x061100, "ctrl_icon_work", "HUD_CTRL_ICON", "SCREEN_HUD")',
            '(0x0BAD20, 0x0BB320, "RankMarker/sub_4BAD20", "WORLD_RIVAL_MARKER", "WORLD_BILLBOARD")',
            '(0x0BBA00, 0x0BBC00, "DispTempHeartNum", "HUD_TEMP_HEART", "SCREEN_HUD")',
        ],
    )
    verify_semantic_range_parity()
    print("VR backend disassembly contract: OK")


if __name__ == "__main__":
    main()