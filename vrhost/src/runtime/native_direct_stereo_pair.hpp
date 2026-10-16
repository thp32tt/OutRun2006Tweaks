#pragma once
#include <cstdint>
#include <cstring>
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
    // Genuine DirectGPU game frames may use the packed DXGI 10:10:10:2
    // backbuffer path. Decode the exact little-endian DXGI channel layout
    // for the host's nonblocking source/projection pixel evidence. This is
    // not the HMD compositor's sRGB/HDR transfer, which stays unchanged.
    [[nodiscard]] inline bool DecodeR10G10B10A2Rgb(
        const std::uint8_t* pixel, float* rgb) noexcept
    {
        if (!pixel || !rgb) return false;
        std::uint32_t value = 0;
        std::memcpy(&value, pixel, sizeof(value));
        constexpr float inverse1023 = 1.0f / 1023.0f;
        rgb[0] = static_cast<float>(value & 0x3ffu) * inverse1023;
        rgb[1] = static_cast<float>((value >> 10) & 0x3ffu) * inverse1023;
        rgb[2] = static_cast<float>((value >> 20) & 0x3ffu) * inverse1023;
        return true;
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


    // A recreated OpenXR/D3D11 device can have the same source size and
    // DXGI format as the previous session. Descriptor equality is not proof
    // that a cached game-eye or host hold texture belongs to the current
    // immediate context. The host must reopen/recreate it before GPU copy.
    // Keep this templated so restricted descriptor-only test headers need
    // not provide the complete D3D11 COM interfaces until instantiated.
    template <typename Texture, typename Device>
    [[nodiscard]] inline bool TextureOwnedByDevice(
        Texture* texture, Device* device) noexcept
    {
        if (!texture || !device) return false;
        Device* owner = nullptr;
        texture->GetDevice(&owner);
        const bool same = owner != nullptr && owner == device;
        if (owner) owner->Release();
        return same;
    }

    // Native game-produced independent L/R eyes may be copied directly into
    // matching OpenXR array slices. Unlike an SBS atlas this is already one
    // complete full-size image per eye, so there is no UV crop or color
    // conversion to perform. Keep the shader path for every other case.
    [[nodiscard]] inline bool CopyToStereoSwapchainCompatible(
        const D3D11_TEXTURE2D_DESC& left,
        const D3D11_TEXTURE2D_DESC& right,
        const D3D11_TEXTURE2D_DESC& projection) noexcept
    {
        const bool exactColor =
            left.Format == DXGI_FORMAT_B8G8R8A8_UNORM ||
            left.Format == DXGI_FORMAT_R8G8B8A8_UNORM;
        const auto source = [&](const D3D11_TEXTURE2D_DESC& d) noexcept {
            return d.Width != 0u && d.Height != 0u &&
                d.Width == left.Width && d.Height == left.Height &&
                d.Format == left.Format && d.MipLevels == 1u &&
                d.ArraySize == 1u && d.SampleDesc.Count == 1u &&
                d.SampleDesc.Quality == 0u &&
                d.Usage == D3D11_USAGE_DEFAULT && d.CPUAccessFlags == 0u &&
                d.MiscFlags == 0u &&
                (d.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0u;
        };
        return exactColor && source(left) && source(right) &&
            projection.Width == left.Width &&
            projection.Height == left.Height &&
            projection.Format == left.Format &&
            projection.ArraySize == 2u && projection.MipLevels == 1u &&
            projection.SampleDesc.Count == 1u &&
            projection.SampleDesc.Quality == 0u &&
            projection.Usage == D3D11_USAGE_DEFAULT &&
            projection.CPUAccessFlags == 0u &&
            (projection.BindFlags & D3D11_BIND_RENDER_TARGET) != 0u;
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
