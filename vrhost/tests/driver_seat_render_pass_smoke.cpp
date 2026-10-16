#include "vr/game/driver_seat_render_pass.hpp"
using namespace OutRunVR::DriverSeatRenderPass;
int main()
{
    if (!IsWorldOrCockpitPass() || !UseCockpitForCamera(true) ||
        UseCockpitForCamera(false))
        return 1;
    {
        ScopedSceneEffect effect{};
        if (IsWorldOrCockpitPass() || UseCockpitForCamera(true) ||
            SceneEffectDepth != 1)
            return 2;
        {
            // A nested HUD/flare pass must not reactivate the real seat.
            ScopedSceneEffect nested{};
            if (SceneEffectDepth != 2 || UseCockpitForCamera(true))
                return 3;
        }
        if (SceneEffectDepth != 1 || IsWorldOrCockpitPass())
            return 4;
    }
    if (!IsWorldOrCockpitPass() || SceneEffectDepth != 0 ||
        !UseCockpitForCamera(true))
        return 5;

    // The actual game effect callback first replaces the seat matrix with
    // the native short-near-plane view. A stale SceneEffectDepth during the
    // restoration would keep the world camera unshifted (regression).
    int cameraView = 2; // 2: native seat, 1: original game/effect camera.
    int failure = 0;
    auto recalculateView = [&](bool seatEligible) {
        cameraView = UseCockpitForCamera(seatEligible) ? 2 : 1;
    };
    RunSceneEffectThenRestoreView(
        [&]() {
            recalculateView(true);
            if (cameraView != 1 || SceneEffectDepth != 1)
                failure = 6;
            RunSceneEffectThenRestoreView(
                [&]() {
                    if (SceneEffectDepth != 2 || UseCockpitForCamera(true))
                        failure = 7;
                },
                [&]() {
                    recalculateView(true);
                    if (SceneEffectDepth != 1 || cameraView != 1)
                        failure = 8;
                });
            if (SceneEffectDepth != 1 || cameraView != 1)
                failure = 9;
        },
        [&]() {
            recalculateView(true);
            if (SceneEffectDepth != 0 || cameraView != 2)
                failure = 10;
        });
    if (failure)
        return failure;

    // Disabled/transitioning native seat must remain the original camera.
    RunSceneEffectThenRestoreView(
        [&]() {
            recalculateView(false);
            if (cameraView != 1 || SceneEffectDepth != 1)
                failure = 11;
        },
        [&]() {
            recalculateView(false);
            if (cameraView != 1 || SceneEffectDepth != 0)
                failure = 12;
        });
    if (failure)
        return failure;
    return 0;
}
