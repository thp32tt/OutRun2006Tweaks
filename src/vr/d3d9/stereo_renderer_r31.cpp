// R31 high-draw-count performance compatibility wrapper.
// F04 phase 9 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R30 plus this include-free R31
// overlay directly.

#include "stereo_renderer_r30.cpp"
#include "stereo_renderer_r31_overlay.inc"
