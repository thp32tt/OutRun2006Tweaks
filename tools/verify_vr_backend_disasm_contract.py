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
            "ProjectedWorldMarker2D",
            "ProjectedScreenEffect2D",
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
            "ScopeFromDisasmPolicy(",
            "SpacePolicy::ProjectedWorldMarker2D",
            "RenderScope::ProjectedWorldMarker2D",
            "SpacePolicy::ProjectedScreenEffect2D",
            "RenderScope::ProjectedScreenEffect2D",
            "ClassifyCriticalProducer(",
            "OutRunVR::DisasmContract::ClassifyCriticalProducer(callerRva)",
            "ClassifyCriticalProducer(0x00060A21u) == RenderScope::ScreenHud",
            "ClassifyCriticalProducer(0x00060D40u) == RenderScope::ScreenHud",
            "ClassifyCriticalProducer(0x00060FBCu) == RenderScope::ScreenHud",
            "ClassifyCriticalProducer(0x000BE5CDu) == RenderScope::ScreenHud",
        ],
    )
    require(
        "src/hooks_uiscaling.cpp",
        [
            "template<std::uintptr_t CallerRva>",
            "GameSemantic::ClassifyCriticalProducer(CallerRva)",
            "scope == OutRunVR::GameSemantic::RenderScope::ScreenHud",
            "TimeRecord_AdjustPositionAndHud<0x000BE5CDu>",
            "TimeRecord_AdjustPositionAndHud<0x000BE9A3u>",
            "VR R119 TIME HUD: shared producer-map handoff",
            "DispRank_putClipSprite<0x000B9F3Au>",
            "DispRank_putClipSprite<0x000BA052u>",
            "VR R120 DIRECT CLIP: shared producer-map",
            "template<std::uintptr_t CallerRva, int HelperRva>",
            "GoalTime_TagHelper<0x000BEA5Au, 0xBE020>",
            "GoalTime_TagHelper<0x000BEA5Fu, 0xBE150>",
            "VR R121 GOAL TIME HUD: shared producer-map",
            "C2CTestSlipstream_AdjustPositionAndHud<0x000BD32Eu>",
            "VR R122 SLIPSTREAM HUD: shared producer-map handoff",
            "C2CDontLoseGF_AdjustPositionAndHud<0x000BD397u>",
            "C2CDontLoseGF_AdjustPositionAndHud<0x000BD414u>",
            "C2CDontLoseGF_AdjustPositionAndHud<0x000BD472u>",
            "VR R123 GF WARNING HUD: shared producer-map handoff",
            "DispGearPosition_AdjustPositionAndHud<0x000B9096u>",
            "DispGearPosition_AdjustPositionAndHud<0x000B90B3u>",
            "DispGearPosition_AdjustPositionAndHud<0x000B90F6u>",
            "VR R124 GEAR REV HUD: shared producer-map handoff",
            "PutGhostGapInfo_AdjustPositionAndHud<0x000BDE3Au>",
            "VR R125 GHOST GAP INFO HUD: shared producer-map handoff",
            "PutGhostGapInfo_sub_AdjustPositionAndHud<0x000BDAE8u>",
            "VR R126 GHOST GAP SUB HUD: shared producer-map handoff",
            "DispGhostGap_ForceSpacingAndHud<0x000BE045u, true>",
            "DispGhostGap_ForceSpacingAndHud<0x000BE083u, true>",
            "DispGhostGap_ForceSpacingAndHud<0x000BE0A5u, false>",
            "DispGhostGap_ForceSpacingAndHud<0x000BE067u, false>",
            "VR R127 GHOST GAP FORCE HUD: shared producer-map handoff",
            "ctrl_icon_work_AdjustPositionAndHud<0x00060D40u>",
            "ctrl_icon_work_AdjustPosition2AndHud<0x00060FBCu>",
            "ctrl_icon_work_AdjustPosition2AndHud<0x00060A21u>",
            "VR R129 CTRL ICON HUD: shared producer-map handoff",
            "DispTempHeartNum_AdjustPositionAndHud<0x000BBA89u>",
            "VR R128 TEMP HEART HUD: shared producer-map handoff",
            "C2CSpeechBubbleRank_AdjustPositionESP0AndHud<0x000FC84Eu>",
            "C2CSpeechBubbleRank_AdjustPositionESP0AndHud<0x000FC882u>",
            "C2CSpeechBubbleRank_AdjustPositionESP0AndHud<0x000FC8B4u>",
            "VR R130 SPEECH RANK HUD: shared producer-map handoff",
            "C2CSpeechBubbleGFInitial_AdjustPositionAndHud<0x000FC9EBu, 0>",
            "C2CSpeechBubbleGFInitial_AdjustPositionAndHud<0x000FCA1Eu, 0>",
            "C2CSpeechBubbleGFInitial_AdjustPositionAndHud<0x000FCA51u, 0>",
            "C2CSpeechBubbleGFInitial_AdjustPositionAndHud<0x000FCB20u, 4>",
            "VR R131 GF SPEECH INITIAL HUD: shared producer-map handoff",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096AC7u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096B14u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096B39u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096B94u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096BE1u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096C10u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096C6Au>",
            "VR R132 C2C SPEECH HUD: shared producer-map handoff",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCDC1u>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCDEAu>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCEB0u>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCED9u>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCF22u>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCF4Fu>",
            "VR R133 GF SPEECH HUD: shared producer-map handoff",
        ],
    )
    hooks_text = (ROOT / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
    if "TimeRecord_AdjustPositionAndHud);" in hooks_text:
        raise SystemExit(
            "F13 shared producer-map adoption regressed to legacy hardcoded callback"
        )
    if "DispRank_putClipSprite, Memory::HookType::Call" in hooks_text:
        raise SystemExit(
            "F13 DispRank clip ownership regressed to legacy hardcoded callback"
        )
    goal_block = re.search(
        r"template<std::uintptr_t CallerRva, int HelperRva>\s+"
        r"static void GoalTime_TagHelper\(const char\* label\)"
        r"(?P<body>.*?)"
        r"static void __cdecl GoalTime_Help020",
        hooks_text,
        re.S,
    )
    if not goal_block:
        raise SystemExit("F13 GoalTime shared producer-map helper missing")
    goal_body = goal_block.group("body")
    if "GameSemantic::ClassifyCriticalProducer(CallerRva)" not in goal_body:
        raise SystemExit("F13 GoalTime helper no longer consumes shared producer map")
    if "RegisterSpriteNodeScope(\n\t\t\t\t\tnode, producerScope)" not in goal_body:
        raise SystemExit("F13 GoalTime node ownership no longer uses shared producer scope")
    if "C2CTestSlipstream_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BD32E, put_scroll_AdjustPositionRight);" in hooks_text:
        raise SystemExit(
            "F13 C2CTestSlipstream ownership regressed to spacing-only callback"
        )
    if "put_scroll_AdjustPositionRight" in hooks_text:
        raise SystemExit(
            "F13 C2CDontLoseGF ownership regressed to legacy spacing-only callback"
        )
    if "put_scroll_AdjustPositionLeft" in hooks_text:
        raise SystemExit(
            "F13 DispGearPosition ownership regressed to legacy spacing-only callback"
        )
    if "PutGhostGapInfo_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BDE3A, PutGhostGapInfo_AdjustPosition);" in hooks_text:
        raise SystemExit(
            "F13 PutGhostGapInfo ownership regressed to spacing-only callback"
        )
    if "PutGhostGapInfo_sub_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BDAE8, PutGhostGapInfo_sub_AdjustPosition);" in hooks_text:
        raise SystemExit(
            "F13 PutGhostGapInfo_sub ownership regressed to spacing-only callback"
        )
    legacy_ghost_gap_force_hooks = [
        "DispGhostGap_ForceLeft_hk = safetyhook::create_mid((void*)0x4BE045, SpriteSpacingForceLeft);",
        "DispGhostGap_ForceLeft2_hk = safetyhook::create_mid((void*)0x4BE083, SpriteSpacingForceLeft);",
        "DispGhostGap_ForceRight_hk = safetyhook::create_mid((void*)0x4BE0A5, SpriteSpacingForceRight);",
        "DispGhostGap_ForceRight2_hk = safetyhook::create_mid((void*)0x4BE067, SpriteSpacingForceRight);",
    ]
    stale_ghost_gap_force_hooks = [
        hook for hook in legacy_ghost_gap_force_hooks if hook in hooks_text
    ]
    if stale_ghost_gap_force_hooks:
        raise SystemExit(
            "F13 DispGhostGap force ownership regressed to spacing-only callbacks: "
            f"{stale_ghost_gap_force_hooks}"
        )
    if "DispTempHeartNum_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BBA89, DispTempHeartNum_AdjustPosition);" in hooks_text:
        raise SystemExit(
            "F13 DispTempHeartNum ownership regressed to spacing-only callback"
        )
    legacy_speech_rank_hooks = [
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk8 = safetyhook::create_mid((void*)0x4FC84E, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk9 = safetyhook::create_mid((void*)0x4FC882, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk10 = safetyhook::create_mid((void*)0x4FC8B4, C2CSpeechBubble_AdjustPositionESP0);",
    ]
    stale_speech_rank_hooks = [
        hook for hook in legacy_speech_rank_hooks if hook in hooks_text
    ]
    if stale_speech_rank_hooks:
        raise SystemExit(
            "F13 C2CSpeechBubbleGF rank ownership regressed to spacing-only callbacks: "
            f"{stale_speech_rank_hooks}"
        )
    legacy_speech_initial_hooks = [
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk11 = safetyhook::create_mid((void*)0x4FC9EB, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk12 = safetyhook::create_mid((void*)0x4FCA1E, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk13 = safetyhook::create_mid((void*)0x4FCA51, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk14 = safetyhook::create_mid((void*)0x4FCB20, C2CSpeechBubble_AdjustPositionESP4);",
    ]
    stale_speech_initial_hooks = [
        hook for hook in legacy_speech_initial_hooks if hook in hooks_text
    ]
    if stale_speech_initial_hooks:
        raise SystemExit(
            "F13 C2CSpeechBubbleGF initial-position ownership regressed to spacing-only callbacks: "
            f"{stale_speech_initial_hooks}"
        )
    legacy_c2c_speech_hooks = [
        "C2CSpeechBubble_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x496AC7, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x496B14, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x496B39, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x496B94, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk5 = safetyhook::create_mid((void*)0x496BE1, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk6 = safetyhook::create_mid((void*)0x496C10, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk7 = safetyhook::create_mid((void*)0x496C6A, C2CSpeechBubble_AdjustPositionESP0);",
    ]
    stale_c2c_speech_hooks = [
        hook for hook in legacy_c2c_speech_hooks if hook in hooks_text
    ]
    if stale_c2c_speech_hooks:
        raise SystemExit(
            "F13 C2CSpeechBubble ownership regressed to spacing-only callbacks: "
            f"{stale_c2c_speech_hooks}"
        )
    legacy_gf_speech_hooks = [
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x4FCDC1, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x4FCDEA, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x4FCEB0, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x4FCED9, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk5 = safetyhook::create_mid((void*)0x4FCF22, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk6 = safetyhook::create_mid((void*)0x4FCF4F, C2CSpeechBubble_AdjustPositionESP0);",
    ]
    stale_gf_speech_hooks = [
        hook for hook in legacy_gf_speech_hooks if hook in hooks_text
    ]
    if stale_gf_speech_hooks:
        raise SystemExit(
            "F13 C2CSpeechBubbleGF ownership regressed to spacing-only callbacks: "
            f"{stale_gf_speech_hooks}"
        )
    # R134/F13 negative guard: these five legacy GF hooks are intentionally
    # NOT adopted into immediate next-draw SCREEN_HUD ownership yet. Their
    # producer ranges are canonical HUD, but exact draw adjacency/effect is
    # still unproven (0xFE8B1 is explicitly marked no-effect/uncertain and the
    # four heart hooks have not been independently traced). Keep the current
    # spacing-only bindings fail-closed until separate provenance exists.
    unproven_gf_speech_hooks = [
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk7 = safetyhook::create_mid((void*)0x4FE8B1, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x4FD60C, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x4FD591, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x4FD5CD, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x4FD652, C2CSpeechBubble_AdjustPositionESP0);",
    ]
    missing_unproven_gf_speech_hooks = [
        hook for hook in unproven_gf_speech_hooks if hook not in hooks_text
    ]
    if missing_unproven_gf_speech_hooks:
        raise SystemExit(
            "F13 unproven GF speech/heart hooks changed without exact producer evidence: "
            f"{missing_unproven_gf_speech_hooks}"
        )
    legacy_ctrl_icon_hooks = [
        "ctrl_icon_work_AdjustPosition_hk = safetyhook::create_mid((void*)0x460D40, ctrl_icon_work_AdjustPosition);",
        "ctrl_icon_work_AdjustPosition2_hk = safetyhook::create_mid((void*)0x460FBC, ctrl_icon_work_AdjustPosition2);",
        "set_icon_work_AdjustPosition_hk = safetyhook::create_mid((void*)0x460A21, ctrl_icon_work_AdjustPosition2);",
    ]
    stale_ctrl_icon_hooks = [
        hook for hook in legacy_ctrl_icon_hooks if hook in hooks_text
    ]
    if stale_ctrl_icon_hooks:
        raise SystemExit(
            "F13 ctrl_icon_work ownership regressed to spacing-only callbacks: "
            f"{stale_ctrl_icon_hooks}"
        )
    semantic_text = (ROOT / "src/vr/game/render_semantics.hpp").read_text(encoding="utf-8")
    register_block = re.search(
        r"inline void RegisterSpriteNodeScope\(.*?"
        r"inline RenderScope ConsumeSpriteNodeScope\(",
        semantic_text,
        re.S,
    )
    if not register_block:
        raise SystemExit("F16 semantic tag registration block missing")
    register_body = register_block.group(0)
    if "SpriteNodeSemanticOverflowRejected.fetch_add" not in register_body:
        raise SystemExit("F16 semantic tag overflow rejection counter missing")
    if "std::size_t oldest = 0;" in register_body or "SpriteNodeSemanticTags[oldest]" in register_body:
        raise SystemExit("F16 regression: semantic tag overflow evicts a live exact tag")
    if "SpriteNodeSemanticStaleCleared.fetch_add" in register_body:
        raise SystemExit("F16 regression: overflow is misreported as stale cleanup")

    require(
        "src/vr/hud_semantics.hpp",
        [
            "ProjectedWorldMarker2D",
            "ProjectedScreenEffect2D",
            "PROJECTED_WORLD_MARKER_2D",
            "PROJECTED_SCREEN_EFFECT_2D",
        ],
    )
    require(
        "tools/analyze_outrun_exe.py",
        [
            'GF_HOOK_PROVENANCE_RVAS = {',
            '0x0FE8B1: "C2CSpeechBubbleGF uncertain/no-effect spacing hook"',
            '0x0FD60C: "C2CSpeechBubbleGFHeart spacing hook #1"',
            '0x0FD591: "C2CSpeechBubbleGFHeart spacing hook #2"',
            '0x0FD5CD: "C2CSpeechBubbleGFHeart spacing hook #3"',
            '0x0FD652: "C2CSpeechBubbleGFHeart spacing hook #4"',
            'def collect_raw_rel32_call_candidates(',
            '"raw_rel32_call_candidates": collect_raw_rel32_call_candidates(',
            'Raw E8 rel32 candidates',
            'gf_hook_rel32=0x',
            'GF_RAW_REL32_TARGET_RVAS = {',
            '0x000653C0: "guarded GF raw rel32 target A"',
            '0x00065860: "guarded GF raw rel32 target B"',
            '0x00065970: "guarded GF raw rel32 target C"',
            'GF_RAW_REL32_TARGET_WINDOW = 96',
            'def collect_raw_inbound_rel32_candidates(',
            'def collect_guarded_gf_target_provenance(pe: PE) -> list[dict]:',
            '"guarded_gf_target_provenance": collect_guarded_gf_target_provenance(pe)',
            '"## Guarded GF rel32 target function fingerprints"',
            'guarded_gf_targets=',
            'gf_target_provenance=0x',
            'GF_TARGET_B_ENTRY_RVA = 0x00065860',
            'GF_TARGET_B_ALIGNED_CALL_RVA = 0x00065874',
            'GF_TARGET_B_ALIGNED_CALL_TARGET_RVA = 0x000285A0',
            'GF_TARGET_B_PREFIX_INSTRUCTIONS = (',
            '(0x00065874, "e8 27 2d fc ff", "call rel32")',
            'def collect_guarded_gf_target_b_alignment_proof(pe: PE) -> dict:',
            '"guarded_gf_target_b_alignment_proof": collect_guarded_gf_target_b_alignment_proof(pe)',
            '"## Guarded GF target B exact instruction-boundary proof"',
            'EXACT_PREFIX_CALL_ALIGNMENT_PROVEN',
            'gf_target_alignment=0x',
            'guarded_gf_target_b_alignment_proof=FAILED',
            'GF_TARGET_B_HELPER_RVA = 0x000285A0',
            'GF_TARGET_B_HELPER_WINDOW = 128',
            'GF_TARGET_B_HELPER_FINGERPRINT_BYTES = 96',
            'def collect_guarded_gf_target_b_helper_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_b_helper_provenance": collect_guarded_gf_target_b_helper_provenance(pe)',
            '"## Guarded GF target B helper provenance"',
            'EXACT_HELPER_PROVENANCE_CAPTURED',
            'gf_target_helper=0x',
            'guarded_gf_target_b_helper_provenance=FAILED',
            'GF_TARGET_C_ENTRY_RVA = 0x00065970',
            'GF_TARGET_C_ALIGNED_CALL_RVA = 0x00065997',
            'GF_TARGET_C_ALIGNED_CALL_TARGET_RVA = 0x00028460',
            'GF_TARGET_C_SECOND_ALIGNED_CALL_RVA = 0x000659AC',
            'GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA = 0x00028320',
            'GF_TARGET_C_THIRD_ALIGNED_CALL_RVA = 0x000659C1',
            'GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA = 0x00028800',
            'GF_TARGET_C_PREFIX_INSTRUCTIONS = (',
            '(0x00065997, "e8 c4 2a fc ff", "call rel32")',
            '(0x0006599F, "eb 13", "jmp +0x13")',
            '(0x000659AC, "e8 6f 29 fc ff", "call rel32")',
            '(0x000659B1, "83 c4 0c", "add esp, 0x0c")',
            '(0x000659C1, "e8 3a 2e fc ff", "call rel32")',
            'def collect_guarded_gf_target_c_alignment_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_alignment_proof": collect_guarded_gf_target_c_alignment_proof(pe)',
            '"second_aligned_call_rva": GF_TARGET_C_SECOND_ALIGNED_CALL_RVA',
            '"second_call_alignment_proven": second_call_alignment_proven',
            '"third_aligned_call_rva": GF_TARGET_C_THIRD_ALIGNED_CALL_RVA',
            '"third_call_alignment_proven": third_call_alignment_proven',
            '"## Guarded GF target C first/second/third CALL instruction-boundary proof"',
            'gf_target_c_alignment=0x',
            'second_call=0x',
            'second_call_proven=',
            'third_call=0x',
            'third_call_proven=',
            'guarded_gf_target_c_alignment_proof=FAILED',
            'GF_TARGET_C_HELPER_1_RVA = 0x00028460',
            'GF_TARGET_C_HELPER_PROBE_LEN = 128',
            'GF_TARGET_C_HELPER_1_RANGE_FALLBACK_RVA = 0x00028588',
            'GF_TARGET_C_HELPER_1_MISS_CLEANUP_RVA = 0x000284A6',
            'GF_TARGET_C_HELPER_1_SUCCESS_CONTINUATION_RVA = 0x000284B0',
            'GF_TARGET_C_HELPER_1_TABLE_BASE = 0x009568B8',
            'GF_TARGET_C_HELPER_1_PREFIX_INSTRUCTIONS = (',
            '(0x00028494, "8b 0c b5 b8 68 95 00", "mov ecx, [esi*4+0x9568b8]")',
            '(0x000284AF, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_provenance(pe: PE) -> dict:',
            'def collect_guarded_gf_target_c_helper_1_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_prefix_proof": collect_guarded_gf_target_c_helper_1_prefix_proof(pe)',
            '"## Guarded GF target C helper 0x28460 packed-selector lookup prefix"',
            'EXACT_PACKED_SELECTOR_LOOKUP_PREFIX_PROVEN',
            'gf_target_c_helper_1_prefix=0x',
            'guarded_gf_target_c_helper_1_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_RVA = 0x000284BC',
            'GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_TARGET_RVA = 0x000282B0',
            'GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_BRANCH_RVA = 0x000284CB',
            'GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_TARGET_RVA = 0x00028587',
            'GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_RVA = 0x000284D2',
            'GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_TARGET_RVA = 0x0008BD20',
            'GF_TARGET_C_HELPER_1_SUCCESS_PREFIX_INSTRUCTIONS = (',
            '(0x000284BC, "e8 ef fd ff ff", "call rel32")',
            '(0x000284D2, "e8 49 38 06 00", "call rel32")',
            'def collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_success_prefix_proof": collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe)',
            'EXACT_SUCCESS_CALL_CHAIN_PREFIX_PROVEN',
            'gf_target_c_helper_1_success=0x',
            'guarded_gf_target_c_helper_1_success_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_RVA = 0x000282B0',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_END_RVA = 0x0002830A',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_COUNT_TABLE = 0x00956558',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_CURSOR_TABLE = 0x00956500',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_POOL_BASE = 0x0095E028',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_INSTRUCTIONS = (',
            '(0x000282C9, "7c 05", "jl 0x282d0")',
            '(0x000282CF, "c3", "ret")',
            '(0x000282FC, "75 d3", "jne 0x282d1")',
            '(0x00028308, "89 0e", "mov [esi], ecx")',
            'def collect_guarded_gf_target_c_helper_1_first_callee_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_first_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_first_callee_prefix_proof(pe)',
            'EXACT_FIRST_CALLEE_SLOT_SCAN_PREFIX_PROVEN',
            'gf_target_c_helper_1_first_callee_prefix=0x',
            'guarded_gf_target_c_helper_1_first_callee_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_RVA = 0x0002830A',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_first_callee_continuation_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_first_callee_continuation_provenance": collect_guarded_gf_target_c_helper_1_first_callee_continuation_provenance(pe)',
            'EXACT_EXE_FIRST_CALLEE_CONTINUATION_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_first_callee_continuation=0x',
            'guarded_gf_target_c_helper_1_first_callee_continuation_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_END_RVA = 0x00028319',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_END_RVA = 0x00028320',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_RVA = 0x00028320',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_INSTRUCTIONS = (',
            '(0x0002830A, "ff 04 85 58 65 95 00", "inc dword [eax*4+0x956558]")',
            '(0x00028318, "c3", "ret")',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_BYTES = bytes.fromhex(',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_ANCHOR = bytes.fromhex("83 ec 0c")',
            'def collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof": collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe)',
            'EXACT_FIRST_CALLEE_TERMINAL_PADDING_ANCHOR_PROVEN',
            'gf_target_c_helper_1_first_callee_terminal=0x',
            'guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_RVA = 0x00028320',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_next_code_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_provenance": collect_guarded_gf_target_c_helper_1_next_code_provenance(pe)',
            'EXACT_EXE_NEXT_CODE_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_next_code=0x',
            'guarded_gf_target_c_helper_1_next_code_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_END_RVA = 0x0002837E',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_COMMON_RANGE_FAIL_RVA = 0x00028433',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_RVA = 0x00028379',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_TARGET_RVA = 0x000282B0',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_INSTRUCTIONS = (',
            '(0x0002833A, "0f 8c f3 00 00 00", "jl 0x28433")',
            '(0x00028343, "0f 8d ea 00 00 00", "jge 0x28433")',
            '(0x0002836F, "c3", "ret")',
            '(0x00028379, "e8 32 ff ff ff", "call 0x282b0")',
            'def collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe)',
            'EXACT_NEXT_CODE_PREFIX_CALL_ALIGNMENT_PROVEN',
            'gf_target_c_helper_1_next_code_prefix=0x',
            'guarded_gf_target_c_helper_1_next_code_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA = 0x0002837E',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_next_code_continuation_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_continuation_provenance": collect_guarded_gf_target_c_helper_1_next_code_continuation_provenance(pe)',
            'EXACT_EXE_NEXT_CODE_CONTINUATION_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_next_code_continuation=0x',
            'guarded_gf_target_c_helper_1_next_code_continuation_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_END_RVA = 0x000283DE',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_FAIL_RVA = 0x00028433',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA = 0x00028390',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_TARGET_RVA = 0x0008BD20',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA = 0x0002839D',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_TARGET_RVA = 0x00182194',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_INSTRUCTIONS = (',
            '(0x00028388, "0f 84 a5 00 00 00", "je 0x28433")',
            '(0x00028390, "e8 8b 39 06 00", "call 0x8bd20")',
            '(0x0002839D, "e8 f2 9d 15 00", "call 0x182194")',
            '(0x000283DB, "89 70 18", "mov [eax+0x18], esi")',
            'def collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe)',
            'EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN',
            'gf_target_c_helper_1_next_code_continuation_prefix=0x',
            'guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA = 0x000283DE',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_next_code_continuation_2_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_continuation_2_provenance": collect_guarded_gf_target_c_helper_1_next_code_continuation_2_provenance(pe)',
            'EXACT_EXE_NEXT_CODE_CONTINUATION_2_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_next_code_continuation_2=0x',
            'guarded_gf_target_c_helper_1_next_code_continuation_2_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_END_RVA = 0x0002843E',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_SHARED_EPILOGUE_RVA = 0x00028433',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_INSTRUCTIONS = (',
            '(0x000283DE, "b9 00 00 80 3f", "mov ecx, 0x3f800000")',
            '(0x00028433, "8b 44 24 0c", "mov eax, [esp+0x0c]")',
            '(0x0002843D, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof(pe)',
            'EXACT_NEXT_CODE_CONTINUATION_2_TERMINAL_PROVEN',
            'gf_target_c_helper_1_next_code_continuation_2_prefix=0x',
            'guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_ENTRY_RVA = 0x00028320',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_END_RVA = 0x0002843E',
            'def collect_guarded_gf_target_c_helper_1_next_code_function_boundary_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_function_boundary_proof": collect_guarded_gf_target_c_helper_1_next_code_function_boundary_proof(pe)',
            'EXACT_28320_FUNCTION_ENTRY_BOUNDARY_PROVEN',
            'EXACT_CALL_TARGET_PADDING_BOUNDARY_PROVEN',
            'BOUNDARY_IDENTITY_ONLY',
            'gf_target_c_helper_1_next_code_function_boundary=0x',
            'guarded_gf_target_c_helper_1_next_code_function_boundary_proof=FAILED',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_RVA = 0x0008BD20',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_second_callee_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_second_callee_provenance": collect_guarded_gf_target_c_helper_1_second_callee_provenance(pe)',
            'EXACT_EXE_8BD20_DUAL_CALL_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_second_callee=0x',
            'guarded_gf_target_c_helper_1_second_callee_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_BODY_END_RVA = 0x0008BD3C',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_END_RVA = 0x0008BD40',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_RVA = 0x0008BD40',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_BRANCH_TARGET_RVA = 0x0008BD39',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_INSTRUCTIONS = (',
            '(0x0008BD26, "74 11", "je 0x8bd39")',
            '(0x0008BD2C, "7e 0b", "jle 0x8bd39")',
            '(0x0008BD38, "c3", "ret")',
            '(0x0008BD3B, "c3", "ret")',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_BYTES = bytes.fromhex(',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_ANCHOR = bytes.fromhex(',
            'def collect_guarded_gf_target_c_helper_1_second_callee_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_second_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_second_callee_prefix_proof(pe)',
            'EXACT_8BD20_BOUNDED_ROUTINE_PADDING_PROVEN',
            'BOUNDED_CONTROL_FLOW_ONLY',
            'gf_target_c_helper_1_second_callee_prefix=0x',
            'guarded_gf_target_c_helper_1_second_callee_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_RVA = 0x00182194',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_third_callee_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_provenance": collect_guarded_gf_target_c_helper_1_third_callee_provenance(pe)',
            'EXACT_EXE_182194_CALL_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_third_callee=0x',
            'routine_call=0x',
            'function_entry={helper_1_third_callee[\'function_entry_status\']}',
            'semantic_effect={helper_1_third_callee[\'semantic_effect\']}',
            'ownership_effect={helper_1_third_callee[\'ownership_effect\']}',
            'guarded_gf_target_c_helper_1_third_callee_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_END_RVA = 0x001821F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_END_RVA = 0x001821F4',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_RVA = 0x001821F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_OPCODE = bytes.fromhex("8b")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_ZERO_RVA = 0x001821B5',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_ZERO_TARGET_RVA = 0x001821F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_SIGN_RVA = 0x001821BB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_SIGN_TARGET_RVA = 0x001821DB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_JUMP_1_RVA = 0x001821D9',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_JUMP_2_RVA = 0x001821F1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA = 0x00182207',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_INSTRUCTIONS = (',
            '(0x001821B5, "74 3c", "je 0x1821f3")',
            '(0x001821BB, "79 1e", "jns 0x1821db")',
            '(0x001821D9, "eb 2c", "jmp 0x182207")',
            '(0x001821F1, "eb 14", "jmp 0x182207")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_prefix_proof(pe)',
            'EXACT_182194_PREFIX_CONTROL_FLOW_PROVEN',
            'BOUNDED_CONTROL_FLOW_ONLY',
            'INCOMPLETE_OPCODE_AT_PROBE_END',
            'gf_target_c_helper_1_third_callee_prefix=0x',
            'guarded_gf_target_c_helper_1_third_callee_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RVA = 0x001821F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_END_RVA = 0x00182253',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_provenance(pe)',
            'EXACT_EXE_1821F3_CONTINUATION_PROVENANCE_CAPTURED',
            'UNRESOLVED_CONTINUATION_BYTES_ONLY',
            'RAW_BYTES_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation=0x',
            'common_target_in_probe={helper_1_third_cont[\'common_forward_target_within_probe\']}',
            'guarded_gf_target_c_helper_1_third_callee_continuation_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PREFIX_END_RVA = 0x00182251',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_RVA = 0x00182251',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_OPCODE = bytes.fromhex("83 e0")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_TERMINAL_RVA = 0x00182207',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RET_RVA = 0x00182208',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_POST_RET_RVA = 0x00182209',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_RVA = 0x00182240',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_TARGET_RVA = 0x00186906',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INSTRUCTIONS = (',
            '(0x001821FD, "75 b8", "jne 0x1821b7")',
            '(0x00182207, "c9", "leave")',
            '(0x00182208, "c3", "ret")',
            '(0x00182219, "0f 84 a0 00 00 00", "je 0x1822bf")',
            '(0x00182240, "e8 c1 46 00 00", "call 0x186906")',
            '(0x00182248, "eb 0a", "jmp 0x182254")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof(pe)',
            'EXACT_1821F3_CONTINUATION_CONTROL_FLOW_PROVEN',
            'EXACT_COMMON_TARGET_LEAVE_RET_PROVEN',
            'BOUNDED_CONTROL_FLOW_AND_TERMINAL_ONLY',
            'INCOMPLETE_INSTRUCTION_AT_PROBE_END',
            'gf_target_c_helper_1_third_callee_continuation_prefix=0x',
            'guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_RVA = 0x00182251',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_LEN = 128',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_END_RVA = 0x001822D1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_FORWARD_TARGET_RVAS = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance(pe)',
            'EXACT_EXE_182251_CONTINUATION_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_third_callee_continuation_2=0x',
            'forward_targets_in_probe={helper_1_third_cont_2[\'forward_targets_within_probe\']}',
            'guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PREFIX_END_RVA = 0x001822D1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_RVA = 0x0018229B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_TARGET_RVA = 0x001882CC',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_LEAVE_RVA = 0x001822D0',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_INSTRUCTIONS = (',
            '(0x00182251, "83 e0 02", "and eax, 2")',
            '(0x00182256, "74 74", "je 0x1822cc")',
            '(0x0018229B, "e8 2c 60 00 00", "call 0x1882cc")',
            '(0x001822BF, "83 fb 61", "cmp ebx, 0x61")',
            '(0x001822D0, "c9", "leave")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof(pe)',
            'EXACT_182251_CONTINUATION_CONTROL_FLOW_PROVEN',
            'LEAVE_PROVEN_RET_NOT_CAPTURED',
            'NEXT_BYTE_AFTER_LEAVE_NOT_CAPTURED',
            'gf_target_c_helper_1_third_callee_continuation_2_prefix=0x',
            'guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_RVA = 0x001822D1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_END_RVA = 0x00182331',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe)',
            'EXACT_EXE_1822D1_CONTINUATION_PROVENANCE_CAPTURED',
            'UNRESOLVED_RAW_FIRST_BYTE_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_3=0x',
            'first_byte={helper_1_third_cont_3[\'first_byte\']}',
            'guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_LEAVE_RVA = 0x001822D0',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_RET_RVA = 0x001822D1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_BYTES = bytes.fromhex("c9 c3")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA = 0x001822D2',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_BYTES = bytes.fromhex("e8 15 39 00 00")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_CALL_TARGET_RVA = 0x00185BEC',
            'def collect_guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof": collect_guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof(pe)',
            'EXACT_1822D0_LEAVE_RET_AND_1822D2_NEXT_INSTRUCTION_PROVEN',
            'EXACT_LEAVE_RET_PROVEN',
            'EXACT_NEXT_INSTRUCTION_START_PROVEN',
            'UNRESOLVED_AT_1822D2',
            'gf_target_c_helper_1_third_callee_terminal=',
            'guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PREFIX_END_RVA = 0x001822F4',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_RET_RVA = 0x001822F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_RVA = 0x001822F4',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_LEN = 12',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_NEXT_CODE_RVA = 0x00182300',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_INSTRUCTIONS = (',
            '(0x001822D2, "e8 15 39 00 00", "call 0x185bec")',
            '(0x001822E0, "74 05", "je 0x1822e7")',
            '(0x001822E2, "e8 27 48 00 00", "call 0x186b0e")',
            '(0x001822EC, "e8 18 ff ff ff", "call 0x182209")',
            '(0x001822F3, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof(pe)',
            'EXACT_1822D2_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN',
            'EXACT_RET_AT_1822F3_PROVEN',
            'EXACT_12_BYTE_INT3_PADDING_PROVEN',
            'EXACT_182300_CODE_BOUNDARY_PROVEN',
            'UNRESOLVED_AT_1822D2_AND_182300',
            'gf_target_c_helper_1_third_callee_post_terminal=',
            'guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_START_RVA = 0x00182300',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_PREFIX_END_RVA = 0x00182314',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_RET_RVA = 0x00182313',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_NEXT_INSTRUCTION_RVA = 0x00182314',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INSTRUCTIONS = (',
            '(0x00182300, "83 ec 0c", "sub esp, 0x0c")',
            '(0x00182306, "e8 3d 66 00 00", "call 0x188948")',
            '(0x0018230B, "e8 0d 00 00 00", "call 0x18231d")',
            '(0x00182313, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof(pe)',
            'EXACT_182300_SEQUENCE_RET_NEXT_BOUNDARY_PROVEN',
            'EXACT_RET_AT_182313_PROVEN',
            'EXACT_182314_INSTRUCTION_BOUNDARY_PROVEN',
            'UNRESOLVED_AT_182300_182314_AND_18231D',
            'gf_target_c_helper_1_third_callee_next_block=',
            'guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_RVA = 0x00182314',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_END_RVA = 0x00182331',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_CALL_RVA = 0x0018230B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_TARGET_RVA = 0x0018231D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_INSTRUCTIONS = (',
            '(0x00182314, "8d 54 24 04", "lea edx, [esp+4]")',
            '(0x00182318, "e8 e8 65 00 00", "call 0x188905")',
            '(0x0018231D, "52", "push edx")',
            '(0x00182322, "74 6d", "je 0x182391")',
            '(0x0018232A, "74 05", "je 0x182331")',
            '(0x0018232C, "e8 a4 65 00 00", "call 0x1888d5")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof": collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe)',
            'EXACT_182314_TO_182331_CAPTURE_END_CONTROL_FLOW_PROVEN',
            'EXACT_18231D_INCOMING_CALL_TARGET_BOUNDARY_PROVEN',
            'DECODED_ONLY_TARGET_BYTES_NOT_CAPTURED',
            'EXACT_CAPTURE_END_AT_182331_REACHED',
            'gf_target_c_helper_1_third_callee_next_continuation=',
            'guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA = 0x00182331',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_END_RVA = 0x00182391',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance(pe)',
            'EXACT_EXE_182331_TO_182391_PROVENANCE_CAPTURED',
            'UNRESOLVED_RAW_BYTES_ONLY',
            'REACHED_182391_TARGET_BYTES_NOT_CAPTURED',
            'UNRESOLVED_AT_182331_AND_182391',
            'gf_target_c_helper_1_third_callee_continuation_4=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PREFIX_END_RVA = 0x00182391',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INCOMING_BRANCH_RVA = 0x0018232A',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INSTRUCTIONS = (',
            '(0x00182331, "3d 00 00 f0 3f", "cmp eax, 0x3ff00000")',
            '(0x0018234F, "0f 85 09 66 00 00", "jne 0x18895e")',
            '(0x00182360, "e9 06 66 00 00", "jmp 0x18896b")',
            '(0x0018238A, "e8 5d 65 00 00", "call 0x1888ec")',
            '(0x0018238F, "eb 1b", "jmp 0x1823ac")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof(pe)',
            'EXACT_182331_TO_182391_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_182331_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN',
            'BOUNDED_CONTROL_FLOW_AND_CALL_TARGET_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_4_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RVA = 0x00182391',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA = 0x001823F1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_TARGET_RVAS = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance(pe)',
            'EXACT_EXE_182391_TO_1823F1_PROVENANCE_CAPTURED',
            'BYTES_CAPTURED_BOUNDARIES_UNRESOLVED',
            'UNRESOLVED_AT_182391_18239F_1823AC',
            'gf_target_c_helper_1_third_callee_continuation_5=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PREFIX_END_RVA = 0x001823CB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RET_RVA = 0x001823CA',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_RVA = 0x001823CB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_LEN = 5',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_NEXT_CODE_RVA = 0x001823D0',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_BOUNDARY_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_INSTRUCTIONS = (',
            '(0x00182391, "a9 ff ff 0f 00", "test eax, 0x000fffff")',
            '(0x0018239F, "dd d8", "fstp st(0)")',
            '(0x001823AC, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0")',
            '(0x001823C4, "e8 ae 64 00 00", "call 0x188877")',
            '(0x001823CA, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof(pe)',
            'EXACT_182391_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN',
            'EXACT_RET_AT_1823CA_PROVEN',
            'EXACT_5_BYTE_INT3_PADDING_PROVEN',
            'EXACT_1823D0_CODE_BOUNDARY_PROVEN',
            'gf_target_c_helper_1_third_callee_continuation_5_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RVA = 0x001823D0',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_PREFIX_END_RVA = 0x001823EF',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RET_RVA = 0x001823E3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_NEXT_SEQUENCE_RVA = 0x001823E4',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INNER_CALL_TARGET_RVA = 0x001823ED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_CAPTURE_RVA = 0x001823EF',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_CAPTURE_BYTES = "d9 3c"',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INSTRUCTIONS = (',
            '(0x001823D0, "83 ec 0c", "sub esp, 0x0c")',
            '(0x001823D6, "e8 6d 65 00 00", "call 0x188948")',
            '(0x001823DB, "e8 0d 00 00 00", "call 0x1823ed")',
            '(0x001823E3, "c3", "ret")',
            '(0x001823E4, "8d 54 24 04", "lea edx, [esp+4]")',
            '(0x001823E8, "e8 18 65 00 00", "call 0x188905")',
            '(0x001823ED, "52", "push edx")',
            '(0x001823EE, "9b", "fwait")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof(pe)',
            'EXACT_1823D0_TO_1823EF_PREFIX_CONTROL_FLOW_PROVEN',
            'EXACT_RET_AT_1823E3_PROVEN',
            'EXACT_1823E4_INSTRUCTION_BOUNDARY_PROVEN',
            'EXACT_1823ED_CALL_TARGET_BOUNDARY_PROVEN',
            'RAW_2_BYTE_TAIL_AT_1823EF_CAPTURE_END_NO_INSTRUCTION_CLAIM',
            'gf_target_c_helper_1_third_callee_continuation_5_tail_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_RVA = 0x001823EF',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_END_RVA = 0x0018244F',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance(pe)',
            'EXACT_EXE_1823EF_TO_18244F_PROVENANCE_CAPTURED',
            'RAW_PREDECESSOR_TAIL_BOUNDARY_UNRESOLVED',
            'UNRESOLVED_AT_1823EF_AND_DISCOVERED_TARGETS',
            'RAW_BYTES_AND_REL32_CENSUS_ONLY',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PREFIX_END_RVA = 0x0018244E',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_RVA = 0x0018244E',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_BYTES = "db"',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INSTRUCTIONS = (',
            '(0x001823EF, "d9 3c 24", "fnstcw [esp]")',
            '(0x001823FC, "e8 d4 64 00 00", "call 0x1888d5")',
            '(0x0018241D, "0f 85 3b 65 00 00", "jne 0x18895e")',
            '(0x0018242E, "e9 38 65 00 00", "jmp 0x18896b")',
            '(0x0018244C, "dd d8", "fstp st(0)")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof(pe)',
            'EXACT_1823EF_TO_18244E_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_1823EF_INSTRUCTION_BOUNDARY_PROVEN',
            'DECODED_ONLY_TARGET_BYTES_NOT_CAPTURED',
            'INCOMPLETE_OPCODE_AT_18244E_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_6_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof=FAILED',
            'gf_target_c_helper_1_third_callee_continuation_6=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_RVA = 0x0018244E',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_END_RVA = 0x001824AE',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance(pe)',
            'EXACT_EXE_18244E_TO_1824AE_PROVENANCE_CAPTURED',
            'RAW_INCOMPLETE_OPCODE_OVERLAP_UNRESOLVED',
            'UNRESOLVED_AT_18244E_AND_DISCOVERED_TARGETS',
            'gf_target_c_helper_1_third_callee_continuation_7=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PREFIX_END_RVA = 0x001824AB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_RVA = 0x001824AB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_BYTES = "e8 5e 46"',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INSTRUCTIONS = (',
            '(0x0018244E, "db 2d fa 60 73 00", "fld tbyte [0x7360fa]")',
            '(0x0018245A, "e8 8d 64 00 00", "call 0x1888ec")',
            '(0x00182494, "e8 de 63 00 00", "call 0x188877")',
            '(0x0018249A, "c3", "ret")',
            '(0x0018249B, "e8 4c 37 00 00", "call 0x185bec")',
            '(0x001824A9, "74 05", "je 0x1824b0")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof(pe)',
            'EXACT_18244E_TO_1824AB_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_18244E_INSTRUCTION_BOUNDARY_PROVEN',
            'DECODED_DESTINATIONS_ONLY_NO_SEMANTIC_PROMOTION',
            'INCOMPLETE_REL32_CALL_AT_1824AB_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_7_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RVA = 0x001824AB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_END_RVA = 0x0018250B',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance(pe)',
            'EXACT_EXE_1824AB_TO_18250B_PROVENANCE_CAPTURED',
            'RAW_INCOMPLETE_REL32_CALL_OVERLAP_UNRESOLVED',
            'UNRESOLVED_AT_1824AB_AND_DISCOVERED_TARGETS',
            'gf_target_c_helper_1_third_callee_continuation_8=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance=FAILED',
            '"semantic_effect": "UNRESOLVED"',
            '"ownership_effect": "NONE"',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PREFIX_END_RVA = 0x00182508',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_RVA = 0x00182508',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_BYTES = "8b 4c 24"',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INSTRUCTIONS = (',
            '(0x001824AB, "e8 5e 46 00 00", "call 0x186b0e")',
            '(0x001824C0, "e8 41 44 00 00", "call 0x186906")',
            '(0x001824DA, "e8 0d 37 00 00", "call 0x185bec")',
            '(0x001824EA, "e8 1f 46 00 00", "call 0x186b0e")',
            '(0x001824FC, "e8 05 44 00 00", "call 0x186906")',
            '(0x00182505, "8b 40 48", "mov eax, [eax+0x48]")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof(pe)',
            'EXACT_1824AB_TO_182508_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_1824AB_INSTRUCTION_BOUNDARY_PROVEN',
            'DECODED_DESTINATIONS_ONLY_NO_SEMANTIC_PROMOTION',
            'INCOMPLETE_MOV_ECX_ESP_DISP8_AT_182508_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_8_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA = 0x00182508',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_END_RVA = 0x00182568',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance(pe)',
            'EXACT_EXE_182508_TO_182568_PROVENANCE_CAPTURED',
            'RAW_INCOMPLETE_MOV_ECX_ESP_DISP8_OVERLAP_UNRESOLVED',
            'UNRESOLVED_AT_182508_AND_DISCOVERED_TARGETS',
            'gf_target_c_helper_1_third_callee_continuation_9=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PREFIX_END_RVA = 0x00182568',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INSTRUCTIONS = (',
            '(0x00182508, "8b 4c 24 04", "mov ecx, [esp+0x04]")',
            '(0x00182514, "e8 d3 36 00 00", "call 0x185bec")',
            '(0x00182524, "e8 e5 45 00 00", "call 0x186b0e")',
            '(0x00182536, "e8 cb 43 00 00", "call 0x186906")',
            '(0x00182557, "0f 84 b7 00 00 00", "je 0x182614")',
            '(0x00182562, "f7 c7 03 00 00 00", "test edi, 3")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe)',
            'EXACT_182508_TO_182568_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_182508_INSTRUCTION_BOUNDARY_PROVEN',
            'EXACT_PROBE_END_ON_INSTRUCTION_BOUNDARY',
            'UNRESOLVED_AT_182508_182550_AND_EXTERNAL_TARGETS',
            'gf_target_c_helper_1_third_callee_continuation_9_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA = 0x00182568',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_END_RVA = 0x001825C8',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance(pe)',
            'EXACT_EXE_182568_TO_1825C8_PROVENANCE_CAPTURED',
            'EXACT_182568_INSTRUCTION_BOUNDARY_INHERITED_FROM_R220',
            'UNRESOLVED_AT_182568_AND_DISCOVERED_TARGETS',
            'gf_target_c_helper_1_third_callee_continuation_10=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PREFIX_END_RVA = 0x001825C3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_RVA = 0x001825C3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_BYTES = "f7 c6 03 00 00"',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INSTRUCTIONS = (',
            '(0x00182568, "53", "push ebx")',
            '(0x00182569, "74 11", "je 0x18257c")',
            '(0x0018258D, "a9 00 01 01 81", "test eax, 0x81010100")',
            '(0x001825AB, "75 cf", "jne 0x18257c")',
            '(0x001825BF, "8b 74 24 14", "mov esi, [esp+0x14]")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof(pe)',
            'EXACT_182568_TO_1825C3_CONTROL_FLOW_PREFIX_PROVEN',
            'INCOMPLETE_TEST_ESI_IMM32_AT_1825C3_CAPTURE_END',
            'NO_EXTERNAL_BRANCH_TARGETS_IN_PREFIX',
            'gf_target_c_helper_1_third_callee_continuation_10_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_RVA = 0x001825C3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_END_RVA = 0x00182623',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance(pe)',
            'EXACT_EXE_1825C3_TO_182623_PROVENANCE_CAPTURED',
            'RAW_INCOMPLETE_TEST_ESI_IMM32_OVERLAP_UNRESOLVED',
            'UNRESOLVED_AT_1825C3_AND_DISCOVERED_TARGETS',
            'gf_target_c_helper_1_third_callee_continuation_11=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance=FAILED',
            'def collect_guarded_gf_hook_provenance(pe: PE, calls: list[dict]) -> list[dict]:',
            '"guarded_gf_hook_provenance": collect_guarded_gf_hook_provenance(pe, calls)',
            '"## Guarded GF hook provenance census"',
            'print(f"guarded_gf_provenance={len(provenance)}/{len(GF_HOOK_PROVENANCE_RVAS)}")',
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