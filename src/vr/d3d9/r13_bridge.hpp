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
    bool IsCompatDevice(IDirect3DDevice9* device) noexcept;
    bool ResetCompatDevice(IDirect3DDevice9* device,
        D3DPRESENT_PARAMETERS* params, HRESULT& result) noexcept;
    void DisarmLegacyResetHook() noexcept;
}

namespace OutRunVRStereo
{
    // Installer ownership contract: R7 publishes its completed device/hooks via
    // release/acquire atomics, R9 publishes its callback-policy state the same
    // way, and R13 consumes only those states. SafetyHookInline objects are not
    // used as cross-thread readiness flags.

    // Renderer-pose injection must only affect the main game backbuffer.
    // Reflection/shadow/auxiliary world passes intentionally retain the stock
    // game WVP and are sampled by both eyes later.
    bool IsMainBackbufferPoseInjectionPass() noexcept;
}
