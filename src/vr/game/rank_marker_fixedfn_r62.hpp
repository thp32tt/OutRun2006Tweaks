#pragma once
// Exact R62 D3DXSprite car-rank candidate, plus all four R84 physical Draw families.
// FVF alone is never HUD/world-marker ownership. The live device shader must be null.
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
    // A complete FVF142 producer is either an anchored vehicle marker, an
    // independently tagged native gameplay ScreenHud, or the exact queued
    // ESC menu shell. A missing anchor must never borrow HUD permission.
    constexpr bool ExactR84FixedFnSpriteOwner(
        bool projected, bool markerValid, bool screenHud, bool queuedPause,
        bool shaderNull, std::uint32_t fvf, bool triangleList,
        bool gameBackbuffer) noexcept
    {
        return shaderNull && fvf == 0x00000142u && triangleList &&
            gameBackbuffer &&
            ((projected && markerValid) ||
             (!projected && (screenHud || queuedPause)));
    }
    static_assert(ExactR84FixedFnSpriteOwner(true,true,false,false,true,0x142u,true,true));
    static_assert(ExactR84FixedFnSpriteOwner(false,false,true,false,true,0x142u,true,true));
    static_assert(ExactR84FixedFnSpriteOwner(false,false,false,true,true,0x142u,true,true));
    static_assert(!ExactR84FixedFnSpriteOwner(true,false,true,false,true,0x142u,true,true));
    static_assert(!ExactR84FixedFnSpriteOwner(false,false,false,false,true,0x142u,true,true));
    static_assert(!ExactR84FixedFnSpriteOwner(false,false,true,false,false,0x142u,true,true));
}
