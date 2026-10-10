#pragma once
// R29 functional-owner ABI consumed by the independently compiled R30 TU.
// Preserve the original R29 classification, install epoch, stereo recovery,
// and two-eye accounting. This API does not install or relocate physical hooks.
#include <cstdint>
#include <d3d9.h>
#include "../runtime_eligibility.hpp"

namespace OutRunVRStereo
{
    bool R29OwnerStableStereoBase(IDirect3DDevice9* device) noexcept;
    bool R29OwnerFragileEffectCached(
        IDirect3DDevice9* device, bool& fragile) noexcept;
    void R29OwnerArmMonoSafety(std::uint64_t extraPresents = 2) noexcept;
    void R29OwnerNoteStableTwoEyeDraw() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R29OwnerInstallStatus() noexcept;
}
