// R29 stereo hot-path/effect-safety compatibility wrapper.
// F04 phase 11 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R26 plus this include-free R29
// overlay directly.

#include "stereo_renderer_r26.cpp"
#include "vr/game/render_semantics.hpp"\n
#include "stereo_renderer_r29_overlay.inc"
