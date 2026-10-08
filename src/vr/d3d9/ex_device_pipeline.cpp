// R70 production D3D9Ex device owner.
// F04 phase 5 composes the validated base implementation plus R13/R14/R15
// correctness overlays directly. Historical R13/R14/R15 TUs remain
// compatibility owners for diagnostic/build-graph paths, but production no
// longer nests those versioned wrappers.

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>

#include "r13_bridge.hpp"

#pragma optimize("", off)
#include "ex_device_upgrade.cpp"
#pragma optimize("", on)

#include "ex_device_upgrade_r13_overlay.inc"
#include "ex_device_upgrade_r14_overlay.inc"
#include "../runtime_eligibility.hpp"
#include "ex_device_upgrade_r15_overlay.inc"
