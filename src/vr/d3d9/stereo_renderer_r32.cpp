// R32 review-consolidation compatibility wrapper.
// F04 phase 8 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R31 plus this include-free R32
// overlay directly.

#include "r32_policy.hpp"
#include "stereo_renderer_r31.cpp"
#include "stereo_renderer_r32_overlay.inc"
