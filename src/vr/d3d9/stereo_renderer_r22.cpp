// R22 pre-hardware-test hardening compatibility wrapper.
// F04 phase 14 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R21 plus this include-free R22
// overlay directly.

#include "stereo_renderer_r21.cpp"

#include "stereo_renderer_r22_overlay.inc"
