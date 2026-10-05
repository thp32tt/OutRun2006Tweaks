#pragma once

#include <cstdint>
#include <d3d9.h>

namespace OutRunVR::D3D9
{
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
