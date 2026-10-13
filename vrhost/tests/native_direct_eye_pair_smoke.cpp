#include <d3d11.h>
#include <cstdint>
#include <iostream>
#include "runtime/native_direct_stereo_pair.hpp"

int main()
{
    D3D11_TEXTURE2D_DESC left{};
    left.Width = 96;
    left.Height = 96;
    left.MipLevels = 1;
    left.ArraySize = 1;
    left.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    left.SampleDesc.Count = 1;
    left.Usage = D3D11_USAGE_DEFAULT;
    left.BindFlags = D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_RENDER_TARGET;
    auto right = left;
    const auto accepts = [&](std::uint32_t a, std::uint32_t b,
                             std::uint32_t generation) {
        return OutRunVrNativeEyePair::Compatible(a, b, generation,
                                                 96u, 96u, left, right);
    };
    const auto require = [](bool condition, const char* message) {
        if (!condition) { std::cerr << message << '\n'; return false; }
        return true;
    };
    if (!require(accepts(0x110u, 0x220u, 1u),
                 "two independent, compatible GPU eyes must pass") ||
        !require(!accepts(0x110u, 0x110u, 1u),
                 "aliased stereo shared handles must fail") ||
        !require(!accepts(0u, 0x220u, 1u),
                 "absent left eye must fail") ||
        !require(!accepts(0x110u, 0x220u, 0u),
                 "stale/zero generation must fail"))
        return 1;
    right.Width = 97;
    if (!require(!accepts(0x110u, 0x220u, 1u),
                 "mismatched eyes must not enter OpenXR projection"))
        return 1;
    right = left;
    right.MipLevels = 2;
    if (!require(!accepts(0x110u, 0x220u, 1u),
                 "partial mip copy must fail before CopyResource"))
        return 1;
    right = left;
    right.ArraySize = 2;
    if (!require(!accepts(0x110u, 0x220u, 1u),
                 "texture arrays cannot be sampled as a single native eye"))
        return 1;
    right = left;
    right.SampleDesc.Count = 4;
    if (!require(!accepts(0x110u, 0x220u, 1u),
                 "MSAA stereo mismatch must fail"))
        return 1;
    right = left;
    right.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
    if (!require(!accepts(0x110u, 0x220u, 1u),
                 "cross-eye pixel formats must fail"))
        return 1;
    right = left;
    left.BindFlags = D3D11_BIND_RENDER_TARGET;
    if (!require(!accepts(0x110u, 0x220u, 1u),
                 "unsampleable source must preserve classic fallback"))
        return 1;

    // Same-format sRGB game eyes must traverse the real DirectGPU importer.
    // The PS expects the D3D11 SRV's automatic decode, not a second gamma pass.
    left = right;
    left.Format = right.Format = DXGI_FORMAT_B8G8R8A8_UNORM_SRGB;
    left.BindFlags = D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_RENDER_TARGET;
    if (!require(accepts(0x110u, 0x220u, 2u),
                 "BGRA sRGB native stereo source must enter OpenXR hold") ||
        !require(OutRunVrNativeEyePair::IsSrgbView(left.Format),
                 "BGRA sRGB must request already-linear shader transfer"))
        return 1;
    left.Format = right.Format = DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
    if (!require(accepts(0x110u, 0x220u, 2u),
                 "RGBA sRGB native stereo source must enter OpenXR hold") ||
        !require(OutRunVrNativeEyePair::IsSrgbView(left.Format),
                 "RGBA sRGB must bypass second shader gamma decode"))
        return 1;
    right.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    if (!require(!accepts(0x110u, 0x220u, 2u),
                 "mixed encoded and sRGB eyes must stay on original fallback"))
        return 1;
    left.Format = right.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    if (!require(accepts(0x110u, 0x220u, 2u) &&
                 !OutRunVrNativeEyePair::IsSrgbView(left.Format),
                 "legacy unorm eyes still require software gamma conversion"))
        return 1;
    left.Format = right.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
    if (!require(accepts(0x110u, 0x220u, 2u) &&
                 !OutRunVrNativeEyePair::IsSrgbView(left.Format),
                 "scRGB eyes retain their independent HDR white-scale route"))
        return 1;
    std::cout << "Native two-eye host source/projection contract PASS\n";
    return 0;
}
