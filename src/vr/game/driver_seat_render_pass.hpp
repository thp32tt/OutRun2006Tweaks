#pragma once
#include <cstdint>

namespace OutRunVR::DriverSeatRenderPass
{
    // Quest's native renderer keeps cockpit geometry/motion state separate
    // from 2D effects. On the original Windows game the SceneEffect callback
    // temporarily reconstructs a different near-plane camera; it must not
    // borrow the seat-position offset from the world/cockpit render pass.
    inline thread_local std::uint32_t SceneEffectDepth = 0;

    class ScopedSceneEffect final
    {
    public:
        ScopedSceneEffect() noexcept { ++SceneEffectDepth; }
        ~ScopedSceneEffect() noexcept { --SceneEffectDepth; }
        ScopedSceneEffect(const ScopedSceneEffect&) = delete;
        ScopedSceneEffect& operator=(const ScopedSceneEffect&) = delete;
    };

    inline bool IsWorldOrCockpitPass() noexcept
    {
        return SceneEffectDepth == 0;
    }

    inline bool UseCockpitForCamera(bool verifiedNativeCamera) noexcept
    {
        return verifiedNativeCamera && IsWorldOrCockpitPass();
    }
}
