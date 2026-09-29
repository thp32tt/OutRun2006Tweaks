// R70 production stereo owner.
// F04 phase 6 keeps diagnostic comparison paths unchanged while the default
// production path composes R33 plus the include-free R34 reset/raster overlay
// directly. Historical R34 remains a compatibility/build-graph wrapper.

#if defined(OUTRUN_VR_SAFE_DRAW_COMPARE)
#include "stereo_renderer_r26_compare.cpp"
#elif defined(OUTRUN_VR_C1_COMPARE)
#include "stereo_renderer_r29_c1_compare.cpp"
#elif defined(OUTRUN_VR_C2_COMPARE)
#include "stereo_renderer_r30_c2_compare.cpp"
#elif defined(OUTRUN_VR_R26_HUD_COMPARE)
#include "stereo_renderer_r30_r26_safe.cpp"
#else
#include "r32_policy.hpp"
#include "stereo_renderer_r31.cpp"
#include "stereo_renderer_r32_overlay.inc"
#include "stereo_renderer_r33_overlay.inc"
#include "vr/game/render_semantics.hpp"

namespace OutRunVRD3D9ExUpgradeR13
{
    bool LastResetStateReplaySucceeded() noexcept;
}

#include "stereo_renderer_r34_overlay.inc"
#endif
