#pragma once
#include <cstdint>
#include <d3d11.h>

namespace OutRunVrNativeEyePair
{
    // A typed *_SRGB SRV is automatically decoded to linear RGB by D3D11
    // texture sampling. The host compositor must not apply SrgbToLinear twice.
    [[nodiscard]] constexpr bool IsSrgbView(DXGI_FORMAT format) noexcept
    {
        return format == DXGI_FORMAT_B8G8R8A8_UNORM_SRGB ||
               format == DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
    }

    [[nodiscard]] constexpr bool IsSupportedSourceFormat(DXGI_FORMAT format) noexcept
    {
        return format == DXGI_FORMAT_B8G8R8A8_UNORM ||
               format == DXGI_FORMAT_R8G8B8A8_UNORM ||
               format == DXGI_FORMAT_R10G10B10A2_UNORM ||
               format == DXGI_FORMAT_R16G16B16A16_FLOAT ||
               IsSrgbView(format);
    }
    // The shared handle numbers may differ while both opens refer to the same
    // D3D11 allocation. Compare canonical COM identities *after* opening, not
    // the handle values, before copying a supposedly stereo game frame.
    // This is a secondary host-side check: only native producer provenance
    // may establish independent left/right game renders.
    // Existing portable sRGB/descriptor regressions compile this header with
    // restricted DXGI descriptors. Defer COM type checking until the actual
    // D3D11 host or WARP resource-identity test instantiates this function.
    template <typename Canonical, typename Texture, typename InterfaceId>
    [[nodiscard]] inline bool DistinctSourceAllocations(
        Texture* left, Texture* right, const InterfaceId& unknownIid) noexcept
    {
        if (!left || !right || left == right) return false;
        Canonical* leftIdentity = nullptr;
        Canonical* rightIdentity = nullptr;
        const auto leftResult = left->QueryInterface(
            unknownIid, reinterpret_cast<void**>(&leftIdentity));
        const auto rightResult = right->QueryInterface(
            unknownIid, reinterpret_cast<void**>(&rightIdentity));
        const bool distinct = leftResult >= 0 && rightResult >= 0 &&
            leftIdentity && rightIdentity && leftIdentity != rightIdentity;
        if (leftIdentity) leftIdentity->Release();
        if (rightIdentity) rightIdentity->Release();
        return distinct;
    }

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
                IsSupportedSourceFormat(d.Format);
        };
        return usable(left) && usable(right) &&
            left.Format == right.Format;
    }
}
