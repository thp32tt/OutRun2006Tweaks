// R70 production D3D9Ex device owner.
// F04 phase 4 composes the validated R13/base chain plus the R14 and R15
// correctness overlays directly. Historical R14/R15 TUs remain compatibility
// owners for diagnostic/build-graph paths, but production no longer nests them.

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>

#include "ex_device_upgrade_r13.cpp"
#include "ex_device_upgrade_r14_overlay.inc"
#include "../runtime_eligibility.hpp"
#include "ex_device_upgrade_r15_overlay.inc"
