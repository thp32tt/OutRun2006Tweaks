// R70 production stereo owner.
// F04 phases 6-15 keep diagnostic comparison paths unchanged while the default
// production path directly composes the R20 base plus include-free R21/R22/R23/R26/R29-R34
// overlays. Historical R21/R22/R23/R26/R29-R34 wrappers remain compatibility/build-graph owners.

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
#include "stereo_renderer_r20.cpp"
#include "stereo_renderer_r21_overlay.inc"
#include "stereo_renderer_r22_overlay.inc"
#include "stereo_renderer_r23_overlay.inc"
#include "shader_fingerprint_gpl.hpp"
#include "../game/render_semantics.hpp"
#include "stereo_renderer_r26_overlay.inc"
#include "vr/game/render_semantics.hpp"\n
#include "stereo_renderer_r29_overlay.inc"
#include <d3dcompiler.h>
#include <algorithm>
#include <array>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>
#include "stereo_renderer_r30_overlay.inc"
#include "stereo_renderer_r31_overlay.inc"
#include "stereo_renderer_r32_overlay.inc"
#include "stereo_renderer_r33_overlay.inc"
#include "vr/game/render_semantics.hpp"

namespace OutRunVRD3D9ExUpgradeR13
{
    bool LastResetStateReplaySucceeded() noexcept;
}

#include "stereo_renderer_r34_overlay.inc"
#endif
