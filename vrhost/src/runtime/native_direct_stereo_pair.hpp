#pragma once
#include <cstdint>
#include <d3d11.h>

namespace OutRunVrNativeEyePair
{
    // Exact two-eye source admission shared by the real x64 DirectGPU importer
    // and the R23 OpenXR projection staging path. Never treat duplicated
    // handles or incompatible CopyResource shapes as a stereo game frame.
    inline bool Compatible(
        std::uint32_t leftHandle, std::uint32_t rightHandle,
        std::uint32_t generation, std::uint32_t width, std::uint32_t height,
        const D3D11_TEXTURE2D_DESC& left,
        const D3D11_TEXTURE2D_DESC& right) noexcept
    {
        if (!leftHandle || !rightHandle || leftHandle == rightHandle ||
            !generation || !width || !height)
            return false;
        const auto usable = [&](const D3D11_TEXTURE2D_DESC& d) noexcept {
            return d.Width == width && d.Height == height &&
                d.MipLevels == 1 && d.ArraySize == 1 &&
                d.SampleDesc.Count == 1 && d.SampleDesc.Quality == 0 &&
                d.Usage == D3D11_USAGE_DEFAULT && d.CPUAccessFlags == 0 &&
                (d.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0 &&
                (d.Format == DXGI_FORMAT_B8G8R8A8_UNORM ||
                 d.Format == DXGI_FORMAT_R8G8B8A8_UNORM ||
                 d.Format == DXGI_FORMAT_R10G10B10A2_UNORM ||
                 d.Format == DXGI_FORMAT_R16G16B16A16_FLOAT);
        };
        return usable(left) && usable(right) &&
            left.Format == right.Format;
    }
}
