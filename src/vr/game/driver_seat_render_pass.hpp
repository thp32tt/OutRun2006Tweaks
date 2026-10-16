#pragma once
#include <cstdint>
#include <utility>

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

    // The game's Clr_SceneEffect callback rebuilds the native near-plane
    // camera for its particles. Restore the world/cockpit camera only AFTER
    // the temporary scene-effect guard has expired. Nested callbacks retain
    // the outer guard, so they cannot re-enable a seat inside another effect.
    template <typename RenderEffect, typename RestoreWorldCamera>
    inline void RunSceneEffectThenRestoreView(
        RenderEffect&& renderEffect, RestoreWorldCamera&& restoreWorldCamera)
    {
        {
            ScopedSceneEffect effect{};
            std::forward<RenderEffect>(renderEffect)();
        }
        std::forward<RestoreWorldCamera>(restoreWorldCamera)();
    }
}
