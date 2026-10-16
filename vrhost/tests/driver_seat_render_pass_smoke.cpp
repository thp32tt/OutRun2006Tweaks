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
    return 0;
}
