#pragma once
// Scheduled-review baseline marker: UIScaling-derived VR HUD semantics.

#include <array>
#include <cstdint>

#include "game/disasm_render_contract.hpp"

namespace OutRunVRHudSemantics
{
    using SpacePolicy = OutRunVR::DisasmContract::SpacePolicy;

    struct SemanticInfo
    {
        const char* area;
        const char* semantic;
        SpacePolicy space;
    };

    struct SemanticAnchor
    {
        std::uint32_t rva;
        const char* semantic;
        SpacePolicy space;
        const char* note;
    };

    constexpr const char* SpacePolicyName(SpacePolicy policy) noexcept
    {
        switch (policy)
        {
        case SpacePolicy::ScreenHud: return "SCREEN_HUD";
        case SpacePolicy::WorldBillboard: return "WORLD_BILLBOARD";
        case SpacePolicy::ProjectedWorldMarker2D:
            return "PROJECTED_WORLD_MARKER_2D";
        case SpacePolicy::ProjectedScreenEffect2D:
            return "PROJECTED_SCREEN_EFFECT_2D";
        default: return "UNKNOWN";
        }
    }

    constexpr SemanticInfo UnknownInfo() noexcept
    {
        return { "", "UNKNOWN", SpacePolicy::Unknown };
    }

    // Runtime classification delegates to the backend-neutral disassembly
    // contract. The exact EXE identity gate remains in hud_inspector.cpp, so
    // this centralization does not broaden which callers are trusted at runtime.
    constexpr SemanticInfo ClassifyCaller(std::uint32_t callRva) noexcept
    {
        for (const auto& range :
             OutRunVR::DisasmContract::CriticalProducerRanges)
        {
            if (callRva >= range.begin && callRva < range.end)
                return {
                    range.area,
                    range.semantic,
                    static_cast<SpacePolicy>(range.policy)
                };
        }
        return UnknownInfo();
    }

    // Exact reverse-engineered anchor inventory from hooks_uiscaling.cpp.
    // This is a review/test source-of-truth, even where the anchor itself is
    // not a direct sprite call and therefore may not appear in hudtrace.csv.
    inline constexpr std::array<SemanticAnchor, 55> Anchors{{
        {0x05B43A, "WORLD_HEART", SpacePolicy::WorldBillboard, "HeartDisp_car_heart pulse angle"},
        {0x060A21, "HUD_CTRL_ICON", SpacePolicy::ScreenHud, "set_icon_work girlfriend/control icon"},
        {0x060D40, "HUD_CTRL_ICON", SpacePolicy::ScreenHud, "ctrl_icon_work adjustment #1"},
        {0x060FBC, "HUD_CTRL_ICON", SpacePolicy::ScreenHud, "ctrl_icon_work adjustment #2"},
        {0x081A86, "HUD_FRUIT", SpacePolicy::ScreenHud, "C2C fruit scaling disable"},
        {0x081A8B, "HUD_FRUIT", SpacePolicy::ScreenHud, "C2C fruit scaling enable"},
        {0x081B76, "HUD_HEART_TOTAL", SpacePolicy::ScreenHud, "C2C heart scaling disable"},

        {0x0B9096, "HUD_GEAR_REV", SpacePolicy::ScreenHud, "REV left adjustment #1"},
        {0x0B90B3, "HUD_GEAR_REV", SpacePolicy::ScreenHud, "REV left adjustment #2"},
        {0x0B90F6, "HUD_GEAR_REV", SpacePolicy::ScreenHud, "REV left adjustment #3"},

        {0x0B9F3A, "HUD_RANK", SpacePolicy::ScreenHud, "DispRank adjustment #1"},
        {0x0B9F5E, "HUD_RANK", SpacePolicy::ScreenHud, "DispRank adjustment #2"},
        {0x0B9F81, "HUD_RANK", SpacePolicy::ScreenHud, "DispRank adjustment #3"},
        {0x0B9FD0, "HUD_RANK", SpacePolicy::ScreenHud, "DispRank adjustment #4"},
        {0x0B9FFC, "HUD_RANK", SpacePolicy::ScreenHud, "DispRank adjustment #5"},
        {0x0BA01E, "HUD_RANK", SpacePolicy::ScreenHud, "DispRank adjustment #6"},
        {0x0BA035, "HUD_RANK", SpacePolicy::ScreenHud, "DispRank adjustment #7"},
        {0x0BA052, "HUD_RANK", SpacePolicy::ScreenHud, "DispRank adjustment #8"},

        {0x0BA0E0, "HUD_RANK", SpacePolicy::ScreenHud, "dispMarkerCheck scaling gate shared by rival marker functions"},

        {0x0BB0FB, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker sprani #1"},
        {0x0BB133, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker sprani #2"},
        {0x0BB16C, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker sprani #3"},
        {0x0BB1A5, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker sprani #4"},
        {0x0BB21F, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker clip #1"},
        {0x0BB241, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker clip #2"},
        {0x0BB271, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker clip #3"},
        {0x0BB2BC, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker clip #4"},
        {0x0BB2D0, "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard, "rank marker clip #5"},

        {0x0BBA89, "HUD_TEMP_HEART", SpacePolicy::ScreenHud, "negative temporary heart score '-' text"},
        {0x0BD32E, "HUD_SLIPSTREAM", SpacePolicy::ScreenHud, "test your slipstream"},
        {0x0BD397, "HUD_GF_WARNING", SpacePolicy::ScreenHud, "don't lose girlfriend #1"},
        {0x0BD414, "HUD_GF_WARNING", SpacePolicy::ScreenHud, "don't lose girlfriend #2"},
        {0x0BD472, "HUD_GF_WARNING", SpacePolicy::ScreenHud, "don't lose girlfriend #3"},
        {0x0BDAE8, "HUD_GHOST", SpacePolicy::ScreenHud, "Ghost/You/Diff sub adjustment"},
        {0x0BDE3A, "HUD_GHOST", SpacePolicy::ScreenHud, "Ghost/You/Diff adjustment"},

        {0x0BE4BC, "HUD_TIME_ATTACK", SpacePolicy::ScreenHud, "TimeAttack force right"},
        {0x0BE4E7, "HUD_TIME_ATTACK", SpacePolicy::ScreenHud, "TimeAttack force left"},
        {0x0BE5CD, "HUD_TIME_ATTACK", SpacePolicy::ScreenHud, "TimeAttack scroll #1"},
        {0x0BE8D8, "HUD_TIME_ATTACK", SpacePolicy::ScreenHud, "TimeAttack scroll later group"},
        {0x0BEA64, "HUD_GOAL_TIME", SpacePolicy::ScreenHud, "TimeAttack goal"},
        {0x0BEB8E, "HUD_RIVAL", SpacePolicy::ScreenHud, "Rival scaling disable"},
        {0x0BEBAF, "HUD_RIVAL", SpacePolicy::ScreenHud, "Rival scaling enable"},
        {0x0BEBE1, "HUD_HEART_TOTAL", SpacePolicy::ScreenHud, "Heart total disable"},
        {0x0BEBE6, "HUD_HEART_TOTAL", SpacePolicy::ScreenHud, "Heart total enable"},
        {0x0BEC83, "HUD_RIVAL", SpacePolicy::ScreenHud, "Rival online disable"},
        {0x0BEC88, "HUD_RIVAL", SpacePolicy::ScreenHud, "Rival online enable"},
        {0x0BECBA, "HUD_HEART_TOTAL", SpacePolicy::ScreenHud, "C2C heart enable"},
        {0x0BECE0, "HUD_HEART_TOTAL", SpacePolicy::ScreenHud, "C2C heart enable #2"},

        {0x0FC84E, "HUD_RANK_EMOJI", SpacePolicy::ScreenHud, "ranking emoji #1"},
        {0x0FC882, "HUD_RANK_EMOJI", SpacePolicy::ScreenHud, "ranking emoji #2"},
        {0x0FC8B4, "HUD_RANK_TEXT", SpacePolicy::ScreenHud, "rank: aaa text"},
        {0x0FC9EB, "HUD_GF_SPEECH", SpacePolicy::ScreenHud, "speech initial position #1"},
        {0x0FCA1E, "HUD_GF_SPEECH", SpacePolicy::ScreenHud, "speech initial position #2"},
        {0x0FCA51, "HUD_GF_SPEECH", SpacePolicy::ScreenHud, "speech initial position #3"},
        {0x0FCB20, "HUD_GF_SPEECH", SpacePolicy::ScreenHud, "speech initial position #4"},
    }};

    static_assert(ClassifyCaller(0x060D40).space == SpacePolicy::ScreenHud);
    static_assert(ClassifyCaller(0x0BBA89).space == SpacePolicy::ScreenHud);
    static_assert(ClassifyCaller(0x0B9F3A).space == SpacePolicy::ScreenHud);
    static_assert(ClassifyCaller(0x0BB0FB).space == SpacePolicy::WorldBillboard);
    static_assert(ClassifyCaller(0x0BE5CD).space == SpacePolicy::ScreenHud);
    static_assert(ClassifyCaller(0x0FC84E).space == SpacePolicy::ScreenHud);
}