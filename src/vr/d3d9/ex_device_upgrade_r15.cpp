// R15 D3D9Ex compatibility correctness overlay.
//
// Keeps the validated R14 managed-texture implementation intact while fixing
// three review findings at the final Ex translation boundary:
//   * a failed partial-RECT upload may never fall back to a whole-mip copy;
//   * GenerateMipSubLevels keeps the coherent level-0 CPU backing while
//     invalidating generated lower-mip shadows;
//   * ResetEx replays the classic D3D9 baseline plus the state families that
//     R14/R13 did not explicitly restore, and publishes a health bit so the
//     stereo layer can remain fail-closed if that replay is incomplete.

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <mutex>

#include "ex_device_upgrade_r14.cpp"
#include "../runtime_eligibility.hpp"

#include "ex_device_upgrade_r15_overlay.inc"
