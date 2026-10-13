#include "../../src/vr/d3d9/pause_menu_eye_affine.hpp"
#include <cmath>
#include <iostream>
#include <limits>

static bool Near(float a, float b, float tolerance = 0.0002f)
{
    return std::fabs(a - b) <= tolerance;
}
int main()
{
    using namespace OutRunVrPauseEye;
    const auto centered = Compute(-0.75f, 0.75f, -0.75f, 0.75f);
    if (!centered.valid || !Near(centered.scale[0], 1.0f) ||
        !Near(centered.scale[1], 1.0f) ||
        !Near(centered.offset[0], 0.0f) ||
        !Near(centered.offset[1], 0.0f)) return 1;
    // Both eyes share a high-biased vertical FOV: the authored ESC midpoint
    // must map back to the physical head-forward tangent, not the FOV midpoint.
    const auto high = Compute(-0.60f, 0.90f, -0.60f, 0.90f);
    if (!high.valid || !(high.offset[0] < 0.0f) ||
        !Near(high.offset[0], high.offset[1])) return 2;
    const auto unequal = Compute(-0.70f, 0.85f, -0.62f, 0.92f);
    if (!unequal.valid) return 3;
    const float down[2]{-0.70f, -0.62f};
    const float up[2]{0.85f, 0.92f};
    for (int eye = 0; eye < 2; ++eye)
    {
        const float tDown = std::tan(down[eye]);
        const float tUp = std::tan(up[eye]);
        // Both eye-zero rays align with the headset-forward optical axis.
        if (!Near(unequal.offset[eye] * (tUp-tDown) + tUp + tDown,
                  0.0f)) return 4;
    }
    const auto failOne = Compute(-0.6f, 0.9f,
        std::numeric_limits<float>::quiet_NaN(), 0.8f);
    if (failOne.valid || !Near(failOne.scale[0], 1.0f) ||
        !Near(failOne.scale[1], 1.0f) ||
        !Near(failOne.offset[0], 0.0f) ||
        !Near(failOne.offset[1], 0.0f)) return 5;
    const auto inverted = Compute(-0.6f, 0.9f, 0.8f, -0.3f);
    if (inverted.valid || !Near(inverted.scale[0], 1.0f)) return 6;
    const auto extreme = Compute(-1.42f, 1.42f, -0.3f, 0.3f);
    if (extreme.valid || !Near(extreme.scale[1], 1.0f)) return 7;
    std::cout << "DX9Ex pause vertical affine PASS: stereo/forward/invalid\n";
    return 0;
}
