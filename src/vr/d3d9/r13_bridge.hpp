#pragma once

// This header is included before the legacy renderer implementation by the R13
// wrapper translation units. Define the lean Windows contract here, before the
// first Windows.h include, so Win32 multimedia/min/max macros cannot rewrite
// OutRun's SOUND_CMD names or std::min/std::max expressions in the included
// implementation.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <Windows.h>
#include <d3d9.h>
#include <cstdint>

#include "vr/ipc/direct_ack_r13.hpp"

namespace OutRunVRD3D9ExUpgradeR13
{
    // Reset ownership contract (second review pass): once a game device is
    // promoted to D3D9Ex, every stereo Reset path must retain a direct ResetEx
    // fallback. R13 may replace the later callback policy, but a failed/partial
    // R13 overlay is never allowed to strand the promoted device with neither
    // a legacy Reset shim nor a ResetEx-capable stereo callback.
    bool IsCompatDevice(IDirect3DDevice9* device) noexcept;
    bool ResetCompatDevice(IDirect3DDevice9* device,
        D3DPRESENT_PARAMETERS* params, HRESULT& result) noexcept;
    void DisarmLegacyResetHook() noexcept;
}

namespace OutRunVRStereo
{
    // Installer ownership contract: R7 publishes its completed device/hooks via
    // release/acquire atomics, R9 publishes its callback-policy state the same
    // way, and R13 consumes only those states. R13 also publishes an explicit
    // Pending/Ready/Failed transaction state for diagnostics. SafetyHookInline
    // objects are not used as cross-thread readiness flags.
    //
    // The renderer-side c64/WVP hook follows the same policy: the base renderer
    // publishes RendererInstallState, while R13 consumes that atomic state and
    // disables pose injection through an atomic policy flag if its offscreen
    // classification guard cannot be installed. It never clears another
    // thread's SafetyHookInline as a readiness/failure signal.
    //
    // Occlusion-query tracking is a correctness boundary. If IDirect3DQuery9::
    // Issue cannot be observed, stereo duplication fails closed to one execution
    // instead of risking duplicated query/MRT side effects.

    // Renderer-pose injection must only affect the main game backbuffer.
    // Reflection/shadow/auxiliary world passes intentionally retain the stock
    // game WVP and are sampled by both eyes later.
    bool IsMainBackbufferPoseInjectionPass() noexcept;
}
