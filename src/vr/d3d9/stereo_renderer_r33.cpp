// R33 final dispatch + post-review hot-path hardening compatibility wrapper.
// F04 phase 7 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R32 plus this include-free R33
// overlay directly.

#include "stereo_renderer_r32.cpp"
#include "stereo_renderer_r33_overlay.inc"
