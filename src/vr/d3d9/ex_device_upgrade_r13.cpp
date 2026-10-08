// R13 D3D9Ex hardening compatibility wrapper.
// F04 phase 5 keeps this historical owner for diagnostic/build-graph paths,
// while production ex_device_pipeline composes the base implementation plus
// this include-free R13 overlay directly.

#include <array>
#include <atomic>
#include <cstdint>

#include "r13_bridge.hpp"

#pragma optimize("", off)
#include "ex_device_upgrade.cpp"
#pragma optimize("", on)

#include "ex_device_upgrade_r13_overlay.inc"
