#pragma once

#include <d3d9.h>
#include <cstdint>
#include "../telemetry/stereo_dispatch_counters.hpp"
#include "../runtime_eligibility.hpp"

namespace OutRunVRStereo
{
    void FlushPendingStateBlockResync(IDirect3DDevice9* device) noexcept;
    void DiscardUnreliableDrawCaches() noexcept;
    bool LiveShaderMatches(
        IDirect3DDevice9* device, std::uintptr_t shader) noexcept;
    void ObserveDispatchDraw(IDirect3DDevice9* device) noexcept;
    void NoteDispatchUnstable() noexcept;
    void NoteDispatchFragile() noexcept;
    void NoteDispatchFastWorld() noexcept;
    void NoteDispatchHud() noexcept;
    void NoteDispatchFallback() noexcept;
    bool GetTrackedViewport(
        IDirect3DDevice9* device, D3DVIEWPORT9& viewport) noexcept;
    OutRunVR::Telemetry::StereoFrameCounters
    DispatchFrameCounters() noexcept;
    std::uint64_t FastWorldLiveValidationCount() noexcept;
    std::uint64_t FastWorldValidationRejectCount() noexcept;
    void ResetDispatchSupportState() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    DispatchSupportInstallState() noexcept;
}
