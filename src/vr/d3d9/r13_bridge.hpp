#pragma once

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
    // Renderer-pose injection must only affect the main game backbuffer.
    // Reflection/shadow/auxiliary world passes intentionally retain the stock
    // game WVP and are sampled by both eyes later.
    bool IsMainBackbufferPoseInjectionPass() noexcept;
}
