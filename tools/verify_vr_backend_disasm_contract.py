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
            '"semantic_effect": "UNRESOLVED"',
            '"ownership_effect": "NONE"',
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