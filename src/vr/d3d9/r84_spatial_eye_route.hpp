#pragma once
#include <cmath>

// R84 differentiates shader HUD's flat tangent-ray eye affine from the
// original game's C993 centre and exact car-shadow spatial WVP routes.
// Spatial world producers retain their own source-backed head inverse,
// asymmetric XR eye projection and physical LEFT/RIGHT GPU draw fences.
// This predicate never grants world ownership: the caller must still prove
// exact call/shader/c64/pose and validate both eye matrices.
namespace OutRunVR::SpatialEyeRoute
{
    constexpr bool NeedsFlatHudAffine(
        bool exactWorldLensCentre, bool exactWorldCarShadow) noexcept
    {
        return !exactWorldLensCentre && !exactWorldCarShadow;
    }

    inline bool PositiveWorldScale(float worldScale) noexcept
    {
        return std::isfinite(worldScale) && worldScale > 0.0f;
    }

    // Native compile-time negative/positive routing checks, included by
    // the R84 main DLL, without recreating its actual source admission.
    static_assert(NeedsFlatHudAffine(false, false),
        "HUD, GOAL, rank and flat projected effects retain HUD affine");
    static_assert(!NeedsFlatHudAffine(true, false),
        "the source-owned central world sun must not require a HUD affine");
    static_assert(!NeedsFlatHudAffine(false, true),
        "the original car shadow must not require a HUD affine");
    static_assert(!NeedsFlatHudAffine(true, true),
        "even a malformed combined spatial flag must not gain HUD affine");
}
