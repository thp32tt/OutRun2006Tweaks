#include <d3d11.h>
#include <cstdint>
#include <iostream>
#include "runtime/native_direct_stereo_pair.hpp"
#include "runtime/native_stereo_source_route.hpp"
#include "runtime/native_xr_swapchain_image.hpp"

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
    // Exercise the actual x64 DirectGPU importer resource-identity gate with
    // genuine D3D11 texture objects, not only made-up handle integers.
    ID3D11Device* warpDevice = nullptr;
    ID3D11DeviceContext* warpContext = nullptr;
    const HRESULT deviceHr = D3D11CreateDevice(
        nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0,
        nullptr, 0, D3D11_SDK_VERSION,
        &warpDevice, nullptr, &warpContext);
    if (!require(SUCCEEDED(deviceHr) && warpDevice != nullptr,
                 "WARP eye resource identity validation device unavailable"))
        return 1;
    ID3D11Texture2D* gpuLeft = nullptr;
    ID3D11Texture2D* gpuRight = nullptr;
    const bool created =
        SUCCEEDED(warpDevice->CreateTexture2D(&left, nullptr, &gpuLeft)) &&
        SUCCEEDED(warpDevice->CreateTexture2D(&right, nullptr, &gpuRight));
    const bool distinctGpuPair = created &&
        OutRunVrNativeEyePair::DistinctSourceAllocations<IUnknown>(
            gpuLeft, gpuRight, IID_IUnknown);
    const bool duplicateGpuEyeDenied = gpuLeft &&
        !OutRunVrNativeEyePair::DistinctSourceAllocations<IUnknown>(
            gpuLeft, gpuLeft, IID_IUnknown);
    const bool nullGpuEyeDenied = gpuLeft &&
        !OutRunVrNativeEyePair::DistinctSourceAllocations<IUnknown>(
            gpuLeft, static_cast<ID3D11Texture2D*>(nullptr), IID_IUnknown);
    if (gpuLeft) gpuLeft->Release();
    if (gpuRight) gpuRight->Release();
    if (warpContext) warpContext->Release();
    warpDevice->Release();
    if (!require(distinctGpuPair,
                 "two independent live D3D11 game eyes must reach OpenXR") ||
        !require(duplicateGpuEyeDenied && nullGpuEyeDenied,
                 "duplicated or absent real GPU eye must keep SBS fallback"))
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
    // Real OpenXR stereo race and world-locked menu require two RTVs;
    // theater only needs one. Never index an invalid runtime image slot.
    int leftRtv = 1, rightRtv = 2;
    std::vector<std::array<int*, 2>> xrTargets{
        { &leftRtv, &rightRtv }, { &leftRtv, &rightRtv }};
    using OutRunVrNativeXrSwapchain::ImageViewsReady;
    if (!require(ImageViewsReady(0u, 2u, 2u, xrTargets, 2u) &&
                 ImageViewsReady(1u, 2u, 2u, xrTargets, 2u),
                 "both native/menu XR stereo projections need live views") ||
        !require(!ImageViewsReady(2u, 2u, 2u, xrTargets, 2u) &&
                 !ImageViewsReady(1u, 1u, 2u, xrTargets, 2u),
                 "out-of-range and stale XR indices must fail closed") ||
        !require(!ImageViewsReady(0u, 2u, 1u, xrTargets, 2u),
                 "mono swapchain must reject stereo projection"))
        return 1;
    xrTargets[1][1] = nullptr;
    if (!require(!ImageViewsReady(1u, 2u, 2u, xrTargets, 2u),
                 "partial stereo target cannot reach OpenXR") ||
        !require(ImageViewsReady(1u, 2u, 1u, xrTargets, 1u),
                 "valid mono theater image remains renderable"))
        return 1;
    xrTargets.pop_back();
    if (!require(!ImageViewsReady(1u, 2u, 2u, xrTargets, 2u),
                 "truncated RTV array must never reach D3D11"))
        return 1;

    // The last successfully copied frame wins over the preceding path.
    // Test both transition directions and incomplete native eye snapshots.
    using OutRunVrNativeEyePair::StereoSourceRoute;
    using OutRunVrNativeEyePair::ChooseStereoSource;
    if (!require(ChooseStereoSource(true,true,true,false,false) ==
                     StereoSourceRoute::DirectGpu,
                 "native direct game eyes must reach OpenXR projection") ||
        !require(ChooseStereoSource(false,true,true,true,true) ==
                     StereoSourceRoute::Sbs,
                 "DirectGPU to SBS fallback must display the NEW SBS capture") ||
        !require(ChooseStereoSource(true,true,true,false,true) ==
                     StereoSourceRoute::DirectGpu,
                 "SBS to DirectGPU recovery must display two new game eyes") ||
        !require(ChooseStereoSource(true,false,true,false,false) ==
                     StereoSourceRoute::None,
                 "missing DirectGPU left eye must fail closed") ||
        !require(ChooseStereoSource(false,false,false,true,false) ==
                     StereoSourceRoute::None,
                 "missing SBS view must never submit an OpenXR layer"))
        return 1;
    // New-generation OpenXR eyes must not be blocked by old high IDs.
    using OutRunVrNativeEyePair::PreferNativeDirectFrame;
    using OutRunVrNativeEyePair::DirectFrameAlreadyProcessed;
    if (!require(PreferNativeDirectFrame(8u, 1u, 6000, 7u, 400u, 5000),
                 "new generation must beat old high frame ID") ||
        !require(!PreferNativeDirectFrame(7u, 400u, 5000, 8u, 1u, 6000),
                 "stale transport must not replace current eyes") ||
        !require(PreferNativeDirectFrame(8u, 2u, 6050, 8u, 1u, 6000),
                 "later same-generation Present wins") ||
        !require(!PreferNativeDirectFrame(8u, 1u, 6000, 8u, 2u, 6050),
                 "older Present must not regress the native eyes") ||
        !require(!PreferNativeDirectFrame(7u, 30u, 0, 8u, 2u, 6050),
                 "unknown QPC from stale generation must fail closed") ||
        !require(!PreferNativeDirectFrame(8u, 2u, 6000, 9u, 1u, 6000),
                 "equal-QPC generations are ambiguous") ||
        !require(DirectFrameAlreadyProcessed(7u, 400u, 7u, 400u),
                 "duplicate consumed native frame must be rejected") ||
        !require(PreferNativeDirectFrame(8u, 3u, 5000, 8u, 2u, 6000),
                 "same-generation producer frame order wins despite QPC jitter") ||
        !require(!PreferNativeDirectFrame(8u, 2u, 9000, 8u, 3u, 6000),
                 "stale same-generation frame cannot regress on late QPC") ||
        !require(!PreferNativeDirectFrame(8u, 3u, 0, 7u, 400u, 5000),
                 "missing timestamp cannot replace known older generation") ||
        !require(PreferNativeDirectFrame(8u, 3u, 7000, 7u, 400u, 0),
                 "known new transport Present replaces unknown older generation") ||
        !require(!DirectFrameAlreadyProcessed(8u, 1u, 7u, 400u),
                 "new transport frame must not inherit stale consumed ID") ||
        !require(DirectFrameAlreadyProcessed(8u, 1u, 8u, 2u),
                 "old frame within same generation must remain rejected") ||
        !require(!DirectFrameAlreadyProcessed(8u, 3u, 8u, 2u),
                 "fresh same-generation native frame must progress"))
        return 1;
    std::cout << "Native two-eye host source/projection contract PASS\n";
    return 0;
}
