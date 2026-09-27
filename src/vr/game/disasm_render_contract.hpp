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
    inline constexpr std::array<ProducerRange, 6> CriticalProducerRanges = {{
        { 0x0005B300u, 0x0005B700u, SpacePolicy::WorldBillboard }, // attached heart
        { 0x000B9000u, 0x000B9200u, SpacePolicy::ScreenHud },      // gear/rev
        { 0x000B9E00u, 0x000BA100u, SpacePolicy::ScreenHud },      // DispRank
        { 0x000BAD20u, 0x000BB320u, SpacePolicy::WorldBillboard }, // rival rank marker
        { 0x000BE300u, 0x000BEA40u, SpacePolicy::ScreenHud },      // time attack
        { 0x000BEA40u, 0x000BEB20u, SpacePolicy::ScreenHud },      // goal time
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
}

