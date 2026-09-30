#!/usr/bin/env python3
"""Verify the DX11/DXVK backend contract still matches recovered OutRun EXE facts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, needles: list[str]) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{path}: missing disassembly contract evidence: {missing}")


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
            '0x00060900u, 0x00061100u, "ctrl_icon_work", "HUD_CTRL_ICON", SpacePolicy::ScreenHud',
            '0x000BBA00u, 0x000BBC00u, "DispTempHeartNum", "HUD_TEMP_HEART", SpacePolicy::ScreenHud',
            '0x00081A00u, 0x00081B00u, "C2C_Fruit", "HUD_FRUIT", SpacePolicy::ScreenHud',
            '0x000BE300u, 0x000BEA40u, "DispTimeAttack2D", "HUD_TIME_ATTACK", SpacePolicy::ScreenHud',
            '0x000FC800u, 0x000FC8A0u, "C2CSpeechBubbleGF_RankEmoji", "HUD_RANK_EMOJI", SpacePolicy::ScreenHud',
            '0x0005B300u, 0x0005B700u, "HeartDisp_car_heart", "WORLD_HEART", SpacePolicy::WorldBillboard',
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
            "RenderScopeFromSpacePolicy(",
            "ClassifyCriticalProducer(",
            "OutRunVR::DisasmContract::ClassifyCriticalProducer(callerRva)",
            "ClassifyCriticalProducer(0x000BE5CDu) == RenderScope::ScreenHud",
            "ClassifyCriticalProducer(0x000BB0FBu) == RenderScope::WorldBillboard",
        ],
    )
    require(
        "src/hooks_uiscaling.cpp",
        [
            "template<std::uintptr_t CallerRva>",
            "GameSemantic::ClassifyCriticalProducer(CallerRva)",
            "scope == OutRunVR::GameSemantic::RenderScope::ScreenHud",
            "TimeRecord_AdjustPositionAndHud<0x000BE5CDu>",
            "TimeRecord_AdjustPositionAndHud<0x000BE603u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE633u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE66Du>",
            "TimeRecord_AdjustPositionAndHud<0x000BE690u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE6B5u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE6D5u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE8D8u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE915u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE94Au>",
            "TimeRecord_AdjustPositionAndHud<0x000BE97Au>",
            "TimeRecord_AdjustPositionAndHud<0x000BE9A3u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE7E8u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE802u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE81Cu>",
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
            "DispTempHeartNum_AdjustPositionAndHud<0x000BBA89u>",
            "VR R128 TEMP HEART HUD: shared producer-map handoff",
            "CtrlIcon_AdjustPositionAndHud<0x00060D40u, false>",
            "CtrlIcon_AdjustPositionAndHud<0x00060FBCu, true>",
            "CtrlIcon_AdjustPositionAndHud<0x00060A21u, true>",
            "VR R129 CTRL ICON HUD: shared producer-map handoff",
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
    goal_start = hooks_text.find(
        "template<std::uintptr_t CallerRva, int HelperRva>\n"
        "\tstatic void GoalTime_TagHelper(const char* label)"
    )
    goal_end = hooks_text.find(
        "static void __cdecl GoalTime_Help020", goal_start
    )
    if goal_start < 0 or goal_end < 0:
        raise SystemExit("F13 GoalTime shared producer-map helper missing")
    goal_body = hooks_text[goal_start:goal_end]
    if "GameSemantic::ClassifyCriticalProducer(CallerRva)" not in goal_body:
        raise SystemExit("F13 GoalTime helper no longer consumes shared producer map")
    if "node, producerScope" not in goal_body:
        raise SystemExit("F13 GoalTime node ownership no longer uses shared producer scope")
    if 'GoalTime_TagHelper(0xBE020, "BE020")' in hooks_text or \
       'GoalTime_TagHelper(0xBE150, "BE150")' in hooks_text:
        raise SystemExit("F13 GoalTime ownership regressed to legacy unclassified helper")
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
            "F13 ctrl_icon_work ownership regressed to legacy spacing-only callbacks: "
            f"{stale_ctrl_icon_hooks}"
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
    require(
        "tools/analyze_outrun_exe.py",
        [
            '0x049940: "Calc3D2D"',
            '0x0BAD20: "RankMarker_sub_4BAD20"',
            '0x0BB0FB: "RankMarker sprani #1"',
            '0x0BB2D0: "RankMarker clip #5"',
            '(0x0BAD20, 0x0BB320, "RankMarker/sub_4BAD20", "WORLD_RIVAL_MARKER", "WORLD_BILLBOARD")',
        ],
    )
    print("VR backend disassembly contract: OK")


if __name__ == "__main__":
    main()