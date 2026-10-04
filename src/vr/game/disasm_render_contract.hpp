#pragma once

#include <array>
#include <cstdint>

namespace OutRunVR::DisasmContract
{
    // Stock OR2006C2C.EXE image base used by the existing reverse-analysis
    // tooling. Runtime hooks must remain ASLR-safe and use RVAs.
    inline constexpr std::uintptr_t StockImageBase = 0x00400000u;

    // Authoritative game camera/WVP globals recovered from the shipped EXE.
    inline constexpr std::uintptr_t ViewRva       = 0x0055D860u; // VA 0x0095D860
    inline constexpr std::uintptr_t ProjectionRva = 0x0055D8A0u; // VA 0x0095D8A0
    inline constexpr std::uintptr_t WorldViewRva  = 0x0055DB20u; // VA 0x0095DB20

    // Final OutRun programmable-world WVP upload boundary:
    // VS c64..c67 = transpose(WorldView * Projection).
    inline constexpr std::uint32_t WvpVsRegister = 64u;
    inline constexpr std::uint32_t WvpVsRegisterCount = 4u;

    // Canonical SpriteNode queue renderer boundaries. The queue entry itself is
    // deliberately not a hook target: prior runtime crashes occurred inside
    // its tiny relocated prologue. Semantic ownership starts at the node body.
    inline constexpr std::uintptr_t SpriteQueueEntryRva = 0x0002D734u;
    inline constexpr std::uintptr_t SpriteQueueNodeRva = 0x0002D762u;
    inline constexpr std::uintptr_t SpriteQueueEpilogueRva = 0x0002DCB4u;

    inline constexpr std::uintptr_t Calc3D2DRva = 0x00049940u;
    inline constexpr std::uintptr_t RankMarkerRva = 0x000BAD20u;

    inline constexpr std::array<std::uintptr_t, 9> RankMarkerCallRvas = {
        0x000BB0FBu, 0x000BB133u, 0x000BB16Cu, 0x000BB1A5u,
        0x000BB21Fu, 0x000BB241u, 0x000BB271u, 0x000BB2BCu,
        0x000BB2D0u,
    };

    enum class SpacePolicy : std::uint8_t
    {
        Unknown = 0,
        ScreenHud,
        WorldBillboard,
        // Exact world anchor that has already been projected to the game's
        // 640x480 sprite plane before the final queued 2D draw.
        ProjectedWorldMarker2D,
        // Exact world/light effect projected into screen space before its final
        // 2D draw. This is not finite-plane HUD ownership.
        ProjectedScreenEffect2D,
    };

    struct ProducerRange
    {
        std::uintptr_t begin;
        std::uintptr_t end;
        const char* area;
        const char* semantic;
        SpacePolicy policy;
    };

    // Canonical producer catalog recovered from the shipped EXE/UI-scaling
    // reverse engineering. Runtime HUD classification and static analysis must
    // consume this exact catalog instead of maintaining independent range lists.
    inline constexpr std::array<ProducerRange, 25> CriticalProducerRanges = {{
        { 0x0005B300u, 0x0005B700u, "HeartDisp_car_heart", "WORLD_HEART", SpacePolicy::WorldBillboard },
        { 0x00060900u, 0x00061100u, "ctrl_icon_work", "HUD_CTRL_ICON", SpacePolicy::ScreenHud },
        { 0x00081A00u, 0x00081B00u, "C2C_Fruit", "HUD_FRUIT", SpacePolicy::ScreenHud },
        { 0x00081B00u, 0x00081C00u, "C2C_Heart", "HUD_HEART_TOTAL", SpacePolicy::ScreenHud },
        { 0x00096A80u, 0x00096D00u, "C2CSpeechBubble", "HUD_GF_SPEECH", SpacePolicy::ScreenHud },
        { 0x000B9000u, 0x000B9200u, "DispGearPosition", "HUD_GEAR_REV", SpacePolicy::ScreenHud },
        { 0x000B9E00u, 0x000BA100u, "DispRank", "HUD_RANK", SpacePolicy::ScreenHud },
        { 0x000BAD20u, 0x000BB320u, "RankMarker/sub_4BAD20", "WORLD_RIVAL_MARKER", SpacePolicy::WorldBillboard },
        { 0x000BBA00u, 0x000BBC00u, "DispTempHeartNum", "HUD_TEMP_HEART", SpacePolicy::ScreenHud },
        { 0x000BD2E0u, 0x000BD360u, "C2CTestSlipstream", "HUD_SLIPSTREAM", SpacePolicy::ScreenHud },
        { 0x000BD360u, 0x000BD500u, "C2CDontLoseGF", "HUD_GF_WARNING", SpacePolicy::ScreenHud },
        { 0x000BD900u, 0x000BE100u, "GhostGap", "HUD_GHOST", SpacePolicy::ScreenHud },
        { 0x000BE300u, 0x000BEA40u, "DispTimeAttack2D", "HUD_TIME_ATTACK", SpacePolicy::ScreenHud },
        { 0x000BEA40u, 0x000BEB20u, "NaviPub_DispTimeAttackGoal", "HUD_GOAL_TIME", SpacePolicy::ScreenHud },
        { 0x000BEB60u, 0x000BEBC0u, "NaviPub_Disp_Rival", "HUD_RIVAL", SpacePolicy::ScreenHud },
        { 0x000BEBC0u, 0x000BEC50u, "NaviPub_Disp_Heart", "HUD_HEART_TOTAL", SpacePolicy::ScreenHud },
        { 0x000BEC50u, 0x000BECA0u, "NaviPub_Disp_Rival", "HUD_RIVAL", SpacePolicy::ScreenHud },
        { 0x000BECA0u, 0x000BED20u, "NaviPub_Disp_Heart", "HUD_HEART_TOTAL", SpacePolicy::ScreenHud },
        { 0x000BED20u, 0x000BEE80u, "NaviPub_Disp", "HUD_NAV_GENERIC", SpacePolicy::ScreenHud },
        { 0x000FC800u, 0x000FC8A0u, "C2CSpeechBubbleGF_RankEmoji", "HUD_RANK_EMOJI", SpacePolicy::ScreenHud },
        { 0x000FC8A0u, 0x000FC900u, "C2CSpeechBubbleGF_RankText", "HUD_RANK_TEXT", SpacePolicy::ScreenHud },
        { 0x000FC900u, 0x000FCC00u, "C2CSpeechBubbleGF", "HUD_GF_SPEECH", SpacePolicy::ScreenHud },
        { 0x000FCD80u, 0x000FD080u, "C2CSpeechBubbleGF", "HUD_GF_SPEECH", SpacePolicy::ScreenHud },
        { 0x000FD560u, 0x000FD680u, "C2CSpeechBubbleGF", "HUD_GF_SPEECH", SpacePolicy::ScreenHud },
        { 0x000FE860u, 0x000FE900u, "C2CSpeechBubbleGF", "HUD_GF_SPEECH", SpacePolicy::ScreenHud },
    }};

    [[nodiscard]] constexpr SpacePolicy ClassifyCriticalProducer(
        std::uintptr_t callerRva) noexcept
    {
        for (const auto& range : CriticalProducerRanges)
        {
            if (callerRva >= range.begin && callerRva < range.end)
                return range.policy;
        }
        return SpacePolicy::Unknown;
    }

    [[nodiscard]] constexpr bool IsScreenHudProducer(
        std::uintptr_t callerRva) noexcept
    {
        return ClassifyCriticalProducer(callerRva) == SpacePolicy::ScreenHud;
    }

    [[nodiscard]] constexpr bool IsWorldBillboardProducer(
        std::uintptr_t callerRva) noexcept
    {
        return ClassifyCriticalProducer(callerRva) == SpacePolicy::WorldBillboard;
    }

    [[nodiscard]] constexpr bool IsRankMarkerCall(
        std::uintptr_t callRva) noexcept
    {
        for (const auto known : RankMarkerCallRvas)
        {
            if (known == callRva)
                return true;
        }
        return false;
    }

    static_assert(WvpVsRegister == 64u && WvpVsRegisterCount == 4u);
    static_assert(ClassifyCriticalProducer(0x00060D40u) == SpacePolicy::ScreenHud);
    static_assert(ClassifyCriticalProducer(0x000B9E00u) == SpacePolicy::ScreenHud);
    static_assert(ClassifyCriticalProducer(0x000BAD20u) == SpacePolicy::WorldBillboard);
    static_assert(ClassifyCriticalProducer(0x000BBA89u) == SpacePolicy::ScreenHud);
    static_assert(IsRankMarkerCall(0x000BB0FBu));
    static_assert(IsScreenHudProducer(0x000BE300u));
    static_assert(IsWorldBillboardProducer(0x0005B300u));
}
