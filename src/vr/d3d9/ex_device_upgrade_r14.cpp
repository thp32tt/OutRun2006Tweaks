// R14 D3D9Ex managed-texture compatibility wrapper.
// F04 phase 4 keeps this historical owner for diagnostic/build-graph paths,
// while production ex_device_pipeline composes R13/base + the R14 overlay
// directly without nesting this versioned translation unit.

#include <algorithm>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>

#include "ex_device_upgrade_r13.cpp"
#include "ex_device_upgrade_r14_overlay.inc"
