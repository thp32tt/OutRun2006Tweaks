#pragma once

#include <Windows.h>
#include <d3d9.h>
#include <cstdint>

namespace OutRunVRR13
{
    // SharedPoseState::reserved slot owned by R13.  The legacy
    // hostDirectConsumedFrameId means that the host opened/accepted a direct
    // frame.  This slot means the D3D11 GPU has finished sampling that frame,
    // which is the only acknowledgement the D3D9 producer may use for slot
    // reuse.
    inline constexpr std::uint32_t HostDirectGpuCompletedFrameIndex = 15;
}

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
