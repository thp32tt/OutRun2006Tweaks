// R26/R28 tracked-occlusion + world-classification compatibility wrapper.
// F04 phase 12 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R23 plus this include-free R26
// overlay directly.

#include "stereo_renderer_r23.cpp"
#include "shader_fingerprint_gpl.hpp"
#include "../game/render_semantics.hpp"

#include "stereo_renderer_r26_overlay.inc"
