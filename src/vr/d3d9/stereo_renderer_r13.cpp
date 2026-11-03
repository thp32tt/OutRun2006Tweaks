// R13 hardening compatibility wrapper.
// F04 phase 17 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes r13_bridge + the R9 renderer plus
// this include-free R13 overlay directly.

#include "r13_bridge.hpp"
#include "stereo_renderer.cpp"

#include "stereo_renderer_r13_overlay.inc"
