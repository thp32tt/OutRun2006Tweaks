#pragma once
// Use the same binocular translation scale in R31 FastWorld and R30
// screen/world-effect paths.  Stereo depth is a user-controlled factor,
// not a projection-only setting.
namespace OutRunVR::Core
{
    constexpr float EffectiveStereoWorldScale(
        float worldScale, float stereoDepth) noexcept
    {
        return worldScale * stereoDepth;
    }
}