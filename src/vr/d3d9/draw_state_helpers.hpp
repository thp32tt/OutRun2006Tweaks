#pragma once

#include <cstdint>
#include <d3d9.h>

namespace OutRunVR::D3D9
{
    inline bool ReadViewport(
        IDirect3DDevice9* device,
        D3DVIEWPORT9& viewport) noexcept
    {
        return device && SUCCEEDED(device->GetViewport(&viewport));
    }

    struct LiveEffectRenderStateSnapshot
    {
        DWORD alphaBlend = FALSE;
        DWORD alphaTest = FALSE;
        DWORD zWrite = TRUE;
        DWORD zEnable = D3DZB_TRUE;
        DWORD cullMode = D3DCULL_CCW;
    };

    inline bool ReadLiveEffectRenderStateSnapshot(
        IDirect3DDevice9* device,
        LiveEffectRenderStateSnapshot& out) noexcept
    {
        return device &&
            SUCCEEDED(device->GetRenderState(
                D3DRS_ALPHABLENDENABLE, &out.alphaBlend)) &&
            SUCCEEDED(device->GetRenderState(
                D3DRS_ALPHATESTENABLE, &out.alphaTest)) &&
            SUCCEEDED(device->GetRenderState(
                D3DRS_ZWRITEENABLE, &out.zWrite)) &&
            SUCCEEDED(device->GetRenderState(
                D3DRS_ZENABLE, &out.zEnable)) &&
            SUCCEEDED(device->GetRenderState(
                D3DRS_CULLMODE, &out.cullMode));
    }

    inline bool SetVertexShaderConstantBatch(
        IDirect3DDevice9* device,
        UINT startRegister,
        const float* constants,
        UINT vector4Count) noexcept
    {
        return device && constants && vector4Count != 0 &&
            SUCCEEDED(device->SetVertexShaderConstantF(
                startRegister, constants, vector4Count));
    }

    inline bool LiveVertexShaderMatches(
        IDirect3DDevice9* device,
        std::uintptr_t expected) noexcept
    {
        if (!device || expected == 0)
            return false;

        IDirect3DVertexShader9* shader = nullptr;
        if (FAILED(device->GetVertexShader(&shader)))
            return false;

        const std::uintptr_t actual =
            reinterpret_cast<std::uintptr_t>(shader);
        if (shader)
            shader->Release();
        return actual == expected;
    }
}
