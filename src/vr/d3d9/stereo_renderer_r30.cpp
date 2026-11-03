// R30 screen-space asymmetric-FOV correction compatibility wrapper.
// F04 phase 10 keeps this historical owner for diagnostic/build-graph paths,
// while production stereo_pipeline composes R29 plus the include-free R30
// overlay directly with the same support-header prelude.

#include "stereo_renderer_r29.cpp"
#include <d3dcompiler.h>
#include <algorithm>
#include <array>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>
#include "stereo_renderer_r30_overlay.inc"
