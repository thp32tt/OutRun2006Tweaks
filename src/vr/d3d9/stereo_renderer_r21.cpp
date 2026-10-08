// R21 game-side host-death fail-closed compatibility wrapper.
// F04 phase 15 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R20 plus this include-free R21
// overlay directly.

#include "stereo_renderer_r20.cpp"

#include "stereo_renderer_r21_overlay.inc"
