#include "../../src/vr/d3d9/pause_menu_eye_affine.hpp"
#include <cmath>
#include <iostream>
#include <limits>
#include <initializer_list>

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
    // Source 3440x1440 -> Quest3 recommended per-eye 2496x2688:
    // retain X/Y aspect while reversing part of the portrait-size loss.
    const float questAspect = (3440.0f / 1440.0f) /
                              (2496.0f / 2688.0f);
    const float questScale = ResponsiveMenuScale(1.25f, questAspect, true);
    if (!(questScale > 1.90f && questScale < 2.10f) ||
        !(questScale < 2.25f) ||
        !Near(questScale,
              1.95f + 0.30f *
              (1.25f * std::sqrt(questAspect) - 1.95f) /
              (0.30f + 1.25f * std::sqrt(questAspect) - 1.95f)))
        return 8;

    // 4:3, 16:9 and 21:9 keep a monotonic, bounded pause-only boost.
    const float portraitEye = 2496.0f / 2688.0f;
    const float s43 = ResponsiveMenuScale(
        1.25f, (4.0f/3.0f)/portraitEye, true);
    const float s169 = ResponsiveMenuScale(
        1.25f, (16.0f/9.0f)/portraitEye, true);
    const float s219 = ResponsiveMenuScale(
        1.25f, (21.0f/9.0f)/portraitEye, true);
    if (!(1.25f < s43 && s43 < s169 && s169 < s219 &&
          s219 <= 2.25f)) return 9;

    // The entire pause slider must now affect BOTH sprite shell and exact
    // option-arrow optics, including values below the former 1.25 floor.
    const float low = ResponsiveUserScale(0.55f, true);
    const float normal = ResponsiveUserScale(1.0f, true);
    const float highSetting = ResponsiveUserScale(1.50f, true);
    if (!Near(low, 0.55f) || !Near(normal, 1.25f) ||
        !Near(highSetting, 1.50f) ||
        !(low < ResponsiveUserScale(0.75f, true) &&
          ResponsiveUserScale(0.75f, true) < normal &&
          normal < ResponsiveUserScale(1.25f, true) &&
          ResponsiveUserScale(1.25f, true) < highSetting)) return 12;
    const float smallOptical = ResponsiveMenuScale(low, questAspect, true);
    const float defaultOptical = ResponsiveMenuScale(normal, questAspect, true);
    const float largeOptical = ResponsiveMenuScale(highSetting, questAspect, true);
    if (!(smallOptical < defaultOptical &&
          defaultOptical < largeOptical && largeOptical < 2.25f))
        return 13;
    if (!Near(ResponsiveUserScale(0.55f, false), 0.55f) ||
        !Near(ResponsiveUserScale(1.00f, false), 1.00f) ||
        !Near(ResponsiveUserScale(1.50f, false), 1.50f) ||
        !Near(ResponsiveUserScale(-1.0f, true), -1.0f) ||
        !std::isnan(ResponsiveUserScale(
            std::numeric_limits<float>::quiet_NaN(), true))) return 14;

    // Gameplay HUD, F11, GOAL/+TIME, desktop and explicit legacy opt-out:
    // caller must leave their already-tested containment exactly untouched.
    for (float factor : {0.75f, 1.0f, 1.5f, questAspect, 9.0f})
        if (!Near(ResponsiveMenuScale(1.25f, factor, false), 1.25f))
            return 10;
    if (!Near(ResponsiveMenuScale(1.25f, 0.0f, true), 1.25f) ||
        !Near(ResponsiveMenuScale(1.25f, 1.0f, true), 1.25f) ||
        !Near(ResponsiveMenuScale(1.25f,
              std::numeric_limits<float>::quiet_NaN(), true), 1.25f) ||
        !(ResponsiveMenuScale(1.5f, 9.0f, true) < 2.25f) ||
        !(ResponsiveMenuScale(1.5f, 9.0f, true) >
          ResponsiveMenuScale(1.25f, 9.0f, true)))
        return 11;
    std::cout << "DX9Ex pause vertical affine + responsive optical size PASS\n";
    return 0;
}
