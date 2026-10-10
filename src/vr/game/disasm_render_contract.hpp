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
        // F15: exact world anchor already projected to the game's 640x480
        // sprite plane before its final queued 2D draw.
        ProjectedWorldMarker2D,
        // F15: exact world/light effect already projected into screen space.
        // This remains distinct from finite-plane HUD ownership.
        ProjectedScreenEffect2D,
    };

    struct ProducerRange
    {
        std::uintptr_t begin;
        std::uintptr_t end;
        SpacePolicy policy;
    };

    // High-value producer ranges already recovered by analyze_outrun_exe.py.
    // Keep this deliberately small: backend code must not invent primitive,
    // alpha, depth or cull heuristics when exact game provenance exists.
    inline constexpr std::array<ProducerRange, 25> CriticalProducerRanges = {{
        { 0x0005B300u, 0x0005B700u, SpacePolicy::WorldBillboard }, // HeartDisp_car_heart
        { 0x00060900u, 0x00061100u, SpacePolicy::ScreenHud },      // ctrl_icon_work
        { 0x00081A00u, 0x00081B00u, SpacePolicy::ScreenHud },      // C2C_Fruit
        { 0x00081B00u, 0x00081C00u, SpacePolicy::ScreenHud },      // C2C_Heart
        { 0x00096A80u, 0x00096D00u, SpacePolicy::ScreenHud },      // C2CSpeechBubble
        { 0x000B9000u, 0x000B9200u, SpacePolicy::ScreenHud },      // DispGearPosition
        { 0x000B9E00u, 0x000BA100u, SpacePolicy::ScreenHud },      // DispRank
        { 0x000BAD20u, 0x000BB320u, SpacePolicy::WorldBillboard }, // RankMarker/sub_4BAD20
        { 0x000BBA00u, 0x000BBC00u, SpacePolicy::ScreenHud },      // DispTempHeartNum
        { 0x000BD2E0u, 0x000BD360u, SpacePolicy::ScreenHud },      // C2CTestSlipstream
        { 0x000BD360u, 0x000BD500u, SpacePolicy::ScreenHud },      // C2CDontLoseGF
        { 0x000BD900u, 0x000BE100u, SpacePolicy::ScreenHud },      // GhostGap
        { 0x000BE300u, 0x000BEA40u, SpacePolicy::ScreenHud },      // DispTimeAttack2D
        { 0x000BEA40u, 0x000BEB20u, SpacePolicy::ScreenHud },      // TimeAttackGoal
        { 0x000BEB60u, 0x000BEBC0u, SpacePolicy::ScreenHud },      // NaviPub_Disp_Rival
        { 0x000BEBC0u, 0x000BEC50u, SpacePolicy::ScreenHud },      // NaviPub_Disp_Heart
        { 0x000BEC50u, 0x000BECA0u, SpacePolicy::ScreenHud },      // NaviPub_Disp_Rival
        { 0x000BECA0u, 0x000BED20u, SpacePolicy::ScreenHud },      // NaviPub_Disp_Heart
        { 0x000BED20u, 0x000BEE80u, SpacePolicy::ScreenHud },      // NaviPub_Disp
        { 0x000FC800u, 0x000FC8A0u, SpacePolicy::ScreenHud },      // RankEmoji
        { 0x000FC8A0u, 0x000FC900u, SpacePolicy::ScreenHud },      // RankText
        { 0x000FC900u, 0x000FCC00u, SpacePolicy::ScreenHud },      // SpeechBubbleGF
        { 0x000FCD80u, 0x000FD080u, SpacePolicy::ScreenHud },      // SpeechBubbleGF
        { 0x000FD560u, 0x000FD680u, SpacePolicy::ScreenHud },      // SpeechBubbleGF
        { 0x000FE860u, 0x000FE900u, SpacePolicy::ScreenHud },      // SpeechBubbleGF
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
    static_assert(ClassifyCriticalProducer(0x000B9E00u) == SpacePolicy::ScreenHud);
    static_assert(ClassifyCriticalProducer(0x000BAD20u) == SpacePolicy::WorldBillboard);
    static_assert(IsRankMarkerCall(0x000BB0FBu));
    static_assert(IsScreenHudProducer(0x00060900u));
    static_assert(IsScreenHudProducer(0x000BBA00u));
    static_assert(IsScreenHudProducer(0x000BE300u));
    static_assert(IsWorldBillboardProducer(0x0005B300u));
}
