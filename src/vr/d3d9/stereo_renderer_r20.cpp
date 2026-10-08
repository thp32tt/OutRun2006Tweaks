// R20 production stabilization compatibility wrapper.
// F04 phase 16 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R13 + runtime eligibility + this
// include-free R20 overlay directly.

#include "stereo_renderer_r13.cpp"
#include "../runtime_eligibility.hpp"

#include "stereo_renderer_r20_overlay.inc"
