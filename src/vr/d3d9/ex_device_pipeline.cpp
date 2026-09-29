// R70 production D3D9Ex device owner.
// F04 phase 3 composes the validated R14/R13/base chain plus the R15 correctness
// overlay directly. The historical R15 TU remains a compatibility owner for
// diagnostic/build-graph paths, but production no longer nests that versioned TU.

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <mutex>

#include "ex_device_upgrade_r14.cpp"
#include "../runtime_eligibility.hpp"
#include "ex_device_upgrade_r15_overlay.inc"
