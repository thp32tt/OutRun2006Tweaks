// R34 final ResetEx replay health guard compatibility wrapper.
// F04 phase 6 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R33 plus this include-free R34
// overlay directly.

#include "stereo_renderer_r33.cpp"
#include "vr/game/render_semantics.hpp"

namespace OutRunVRD3D9ExUpgradeR13
{
    bool LastResetStateReplaySucceeded() noexcept;
}

#include "stereo_renderer_r34_overlay.inc"
