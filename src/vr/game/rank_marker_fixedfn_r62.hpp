#pragma once
// Exact R62 indexed D3DXSprite car-rank candidate. Consumed in R84 R30 TU.
// Do not infer screen ownership from alpha, HUD, FVF alone or prior WVP.
#include <cstdint>
namespace OutRunVR::RankMarker
{
    constexpr bool ExactR62FixedFnRankRoute(
        bool projectedOwner, bool markerValid, bool shaderNull,
        std::uint32_t fvf, bool triangleList, bool gameBackbuffer) noexcept
    {
        return projectedOwner && markerValid && shaderNull &&
            fvf == 0x00000142u && triangleList && gameBackbuffer;
    }
    static_assert(ExactR62FixedFnRankRoute(
        true, true, true, 0x142u, true, true));
    static_assert(!ExactR62FixedFnRankRoute(
        true, true, true, 0x144u, true, true)); // no RHW/shader HUD
    static_assert(!ExactR62FixedFnRankRoute(
        false, true, true, 0x142u, true, true)); // world/F11
}
