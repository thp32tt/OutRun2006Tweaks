// R23/R25 recovery + first-seed coordinator compatibility wrapper.
// F04 phase 13 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R22 plus this include-free R23
// overlay directly.

#include "stereo_renderer_r22.cpp"

#include "stereo_renderer_r23_overlay.inc"
