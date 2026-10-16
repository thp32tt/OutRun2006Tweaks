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
    // R41: a partially written newest Present must not hide the last
    // complete left/right game frame or ACK any unproven shared eye slot.
    using OutRunVrNativeEyePair::NativeDirectFrameSelectable;
    using OutRunVrNativeEyePair::PreferNativeDirectFrame;
    constexpr std::uint32_t required = 0x0fu;
    const auto eligible = [&](std::uint32_t frame, std::uint32_t flags,
                              std::uint32_t pose, bool inFlight,
                              std::uint32_t slot = 0u) {
        return NativeDirectFrameSelectable(frame, 3u, slot, 4u, pose,
                                           flags, required, true, inFlight, true);
    };
    if (!require(eligible(40u, required, 17u, false),
                 "complete gameplay DirectGPU frame must remain eligible") ||
        !require(!eligible(41u, required & ~0x04u, 18u, false),
                 "newest frame missing eye-pair proof must not preempt OpenXR") ||
        !require(!eligible(42u, required, 0u, false),
                 "missing latched pose must not preempt a valid game frame") ||
        !require(!eligible(42u, required, 18u, true),
                 "present in flight cannot be selected or ACKed") ||
        !require(!eligible(42u, required, 18u, false, 4u),
                 "invalid ring slot cannot be ACKed") ||
        !require(!NativeDirectFrameSelectable(
                     42u, 0u, 0u, 4u, 18u, required, required,
                     true, false, true),
                 "unknown generation must not displace prior DirectGPU eyes") ||
        !require(!NativeDirectFrameSelectable(
                     42u, 3u, 0u, 4u, 18u, required, required,
                     true, false, false),
                 "ordinary SBS source cannot enter the native ring"))
        return 1;
    struct DirectSelectionFixture {
        std::uint32_t frame, flags, pose, slot;
        std::int64_t qpc;
    };
    const std::array<DirectSelectionFixture, 3> history{{
        {39u, required, 17u, 0u, 3900},
        {40u, required, 18u, 1u, 4000},
        {41u, required & ~0x01u, 19u, 2u, 4100}
    }};
    std::uint32_t chosen = 0u;
    std::int64_t chosenQpc = 0;
    for (const auto& candidate : history) {
        if (!eligible(candidate.frame, candidate.flags, candidate.pose,
                      false, candidate.slot))
            continue;
        if (!chosen || PreferNativeDirectFrame(
                3u, candidate.frame, candidate.qpc, 3u, chosen, chosenQpc)) {
            chosen = candidate.frame;
            chosenQpc = candidate.qpc;
        }
    }
    if (!require(chosen == 40u,
                 "select last complete game-eye pair despite incomplete newer frame"))
        return 1;
    for (const auto& candidate : history) {
        const bool skipAck = eligible(candidate.frame, candidate.flags,
                                      candidate.pose, false, candidate.slot) &&
            candidate.frame != chosen && candidate.frame < chosen;
        if (!require(skipAck == (candidate.frame == 39u),
                     "only older proven GPU eyes may be skipped and ACKed"))
            return 1;
    }

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
    // Actual WARP device lifetime regression: the R23 host source importer
    // and global GPU hold may outlive an OpenXR compositor replacement.
    // Equal descriptors must not allow D3D11 CopyResource across devices.
    ID3D11Device* replacementDevice = nullptr;
    ID3D11DeviceContext* replacementContext = nullptr;
    const HRESULT replacementHr = D3D11CreateDevice(
        nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0,
        nullptr, 0, D3D11_SDK_VERSION,
        &replacementDevice, nullptr, &replacementContext);
    ID3D11Texture2D* replacementEye = nullptr;
    const bool secondDeviceReady =
        SUCCEEDED(replacementHr) && replacementDevice &&
        SUCCEEDED(replacementDevice->CreateTexture2D(
            &left, nullptr, &replacementEye)) && replacementEye;
    const bool ownershipSafe = secondDeviceReady &&
        OutRunVrNativeEyePair::TextureOwnedByDevice(gpuLeft, warpDevice) &&
        OutRunVrNativeEyePair::TextureOwnedByDevice(gpuRight, warpDevice) &&
        OutRunVrNativeEyePair::TextureOwnedByDevice(
            replacementEye, replacementDevice) &&
        !OutRunVrNativeEyePair::TextureOwnedByDevice(
            gpuLeft, replacementDevice) &&
        !OutRunVrNativeEyePair::TextureOwnedByDevice(
            replacementEye, warpDevice) &&
        !OutRunVrNativeEyePair::TextureOwnedByDevice(
            static_cast<ID3D11Texture2D*>(nullptr), warpDevice) &&
        !OutRunVrNativeEyePair::TextureOwnedByDevice(
            gpuLeft, static_cast<ID3D11Device*>(nullptr));
    if (!require(ownershipSafe,
                 "host device replacement must reopen both DirectGPU eyes and rebuild stale R23 hold"))
        return 1;

    // The production R23 DirectGPU -> OpenXR path may skip shader blits only
    // for two genuine whole-eye UNORM source images and an exact two-slice
    // XR swapchain destination. Full-size, sRGB and HDR mismatches retain
    // the legacy color-correct shader projection.
    auto xrArray = left;
    xrArray.ArraySize = 2;
    const auto copyEligible = [&](const D3D11_TEXTURE2D_DESC& xr) {
        return OutRunVrNativeEyePair::CopyToStereoSwapchainCompatible(
            left, right, xr);
    };
    if (!require(copyEligible(xrArray),
                 "native L/R whole-eye array copy should be available") ||
        !require(!copyEligible(left),
                 "single-slice compositor cannot receive two native eyes"))
        return 1;
    auto wrongXr = xrArray;
    wrongXr.Width += 1;
    if (!require(!copyEligible(wrongXr),
                 "scaling native eyes requires the shader projection"))
        return 1;
    wrongXr = xrArray;
    wrongXr.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
    if (!require(!copyEligible(wrongXr),
                 "HDR transfer must retain the existing blit"))
        return 1;
    wrongXr = xrArray;
    wrongXr.SampleDesc.Count = 4;
    if (!require(!copyEligible(wrongXr),
                 "multisample OpenXR swapchain requires a different transfer"))
        return 1;
    left.Format = right.Format = DXGI_FORMAT_B8G8R8A8_UNORM_SRGB;
    wrongXr = xrArray;
    wrongXr.Format = left.Format;
    if (!require(!copyEligible(wrongXr),
                 "typed sRGB source must keep shader color-space semantics"))
        return 1;
    left.Format = right.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    right.Width = left.Width + 1u;
    if (!require(!copyEligible(xrArray),
                 "different L/R dimensions must keep the safe fallback"))
        return 1;
    right = left;

    // WARP executes the same two GPU CopySubresourceRegion calls as the
    // production R23 source route. Verify eye 0 and eye 1 retain independent
    // red/green pixels in the XR array instead of sharing a mono slice.
    ID3D11Texture2D* warpXr = nullptr;
    ID3D11Texture2D* holdLeft = nullptr;
    ID3D11Texture2D* holdRight = nullptr;
    ID3D11Texture2D* warpReadback = nullptr;
    ID3D11RenderTargetView* nativeLeftRtv = nullptr;
    ID3D11RenderTargetView* nativeRightRtv = nullptr;
    const bool resourcesReady =
        SUCCEEDED(warpDevice->CreateTexture2D(&xrArray, nullptr, &warpXr)) &&
        SUCCEEDED(warpDevice->CreateTexture2D(&left, nullptr, &holdLeft)) &&
        SUCCEEDED(warpDevice->CreateTexture2D(&right, nullptr, &holdRight)) &&
        SUCCEEDED(warpDevice->CreateRenderTargetView(gpuLeft, nullptr, &nativeLeftRtv)) &&
        SUCCEEDED(warpDevice->CreateRenderTargetView(gpuRight, nullptr, &nativeRightRtv));
    bool pixelsDistinct = false;
    if (resourcesReady && warpXr) {
        const float red[4]{1.f, 0.f, 0.f, 1.f};
        const float green[4]{0.f, 1.f, 0.f, 1.f};
        warpContext->ClearRenderTargetView(nativeLeftRtv, red);
        warpContext->ClearRenderTargetView(nativeRightRtv, green);
        const auto copyEyes = [&](ID3D11DeviceContext* context,
                                  ID3D11Device* device,
                                  ID3D11Texture2D* l,
                                  ID3D11Texture2D* r, bool optIn,
                                  bool directRoute, bool complete) {
            return OutRunVrNativeEyePair::CopyDirectEyesToStereoArray<IUnknown>(
                context, device, l, r, warpXr, optIn, directRoute,
                complete, IID_IUnknown);
        };
        // Exercise the actual R23/legacy host GPU hold-copy function before
        // the XR projection. A foreign-device eye/context, aliased eye or
        // destination that is not a separate allocation must reject BEFORE
        // either GPU CopyResource; otherwise stale racing/menu eyes leak in.
        const auto stageEyes = [&](ID3D11DeviceContext* context,
                ID3D11Device* device, ID3D11Texture2D* leftTarget,
                ID3D11Texture2D* rightTarget, ID3D11Texture2D* gameLeft,
                ID3D11Texture2D* gameRight) {
            return OutRunVrNativeEyePair::CopyDirectEyesToHold<IUnknown>(
                context, device, leftTarget, rightTarget, gameLeft,
                gameRight, IID_IUnknown);
        };
        const bool holdRejected =
            !stageEyes(replacementContext, warpDevice, holdLeft, holdRight,
                       gpuLeft, gpuRight) &&
            !stageEyes(warpContext, warpDevice, holdLeft, holdRight,
                       replacementEye, gpuRight) &&
            !stageEyes(warpContext, warpDevice, holdLeft, holdRight,
                       gpuLeft, gpuLeft) &&
            !stageEyes(warpContext, warpDevice, gpuLeft, holdRight,
                       gpuLeft, gpuRight) &&
            !stageEyes(warpContext, warpDevice, holdLeft, holdLeft,
                       gpuLeft, gpuRight);
        const bool holdCopied = stageEyes(warpContext, warpDevice,
            holdLeft, holdRight, gpuLeft, gpuRight);
        if (!require(holdRejected && holdCopied,
                     "live GPU hold copy must preserve distinct stereo and device provenance"))
            return 1;
        // A ClassicSbs game fallback must NEVER be overwritten by a previous
        // native DirectGPU hold pair. Equally sized old-device eyes/context
        // must not be copied into the new XR swapchain during recreation.
        const bool copyDenied =
            !copyEyes(warpContext, warpDevice, gpuLeft, gpuRight,
                      false, true, true) &&
            !copyEyes(warpContext, warpDevice, gpuLeft, gpuRight,
                      true, false, true) &&
            !copyEyes(warpContext, warpDevice, gpuLeft, gpuRight,
                      true, true, false) &&
            !copyEyes(warpContext, warpDevice, replacementEye, gpuRight,
                      true, true, true) &&
            !copyEyes(replacementContext, warpDevice, gpuLeft, gpuRight,
                      true, true, true) &&
            !copyEyes(warpContext, warpDevice, gpuLeft, gpuLeft,
                      true, true, true);
        // The legacy compositor and R23 use the same real GPU copy
        // implementation. A stale previously valid native pair must not
        // override a newly selected ClassicSbs game/menu frame.
        const auto selectedNative = OutRunVrNativeEyePair::ChooseStereoSource(
            true, true, true, false, false);
        const auto restoredSbs = OutRunVrNativeEyePair::ChooseStereoSource(
            false, true, true, true, true);
        const bool sourceSwitchSafe =
            selectedNative == OutRunVrNativeEyePair::StereoSourceRoute::DirectGpu &&
            restoredSbs == OutRunVrNativeEyePair::StereoSourceRoute::Sbs &&
            !copyEyes(warpContext, warpDevice, holdLeft, holdRight,
                      true,
                      restoredSbs == OutRunVrNativeEyePair::StereoSourceRoute::DirectGpu,
                      true);
        if (!require(sourceSwitchSafe,
                     "legacy XR native-eye route must not overwrite a later SBS frame"))
            return 1;
        // Exercise the real OpenXR direct-copy path with TWO host output
        // targets already bound. The native transfer must preserve both MRT
        // slots for subsequent menu/HUD rendering, not leave OM unbound.
        ID3D11RenderTargetView* originalTargets[2]{nativeLeftRtv, nativeRightRtv};
        warpContext->OMSetRenderTargets(2u, originalTargets, nullptr);
        // The host hold-copy path must preserve both game/output bindings
        // while the actual source-eye RTVs are live. The subsequent XR copy
        // reads these newly staged red/green holds, proving two GPU pixels.
        const bool holdCopyWithMrt = stageEyes(
            warpContext, warpDevice, holdLeft, holdRight, gpuLeft, gpuRight);
        const bool badHoldRejectedWithMrt = !stageEyes(
            warpContext, warpDevice, holdLeft, holdRight, gpuLeft, gpuLeft);
        ID3D11RenderTargetView* holdObserved[2]{};
        ID3D11DepthStencilView* holdDepth = nullptr;
        warpContext->OMGetRenderTargets(2u, holdObserved, &holdDepth);
        const bool holdMrtRestored =
            holdObserved[0] == nativeLeftRtv &&
            holdObserved[1] == nativeRightRtv && holdDepth == nullptr;
        for (auto*& view : holdObserved)
            if (view) { view->Release(); view = nullptr; }
        if (holdDepth) holdDepth->Release();
        if (!require(holdCopyWithMrt && badHoldRejectedWithMrt &&
                     holdMrtRestored,
                     "DirectGPU R23 hold staging must restore native MRT0/MRT1 on success and rejection"))
            return 1;
        ID3D11DeviceContext* deferred = nullptr;
        const bool deferredAvailable =
            SUCCEEDED(warpDevice->CreateDeferredContext(0u, &deferred)) &&
            deferred != nullptr;
        const bool deferredDenied = !deferredAvailable ||
            !copyEyes(deferred, warpDevice, holdLeft, holdRight,
                      true, true, true);
        if (deferred) deferred->Release();
        const bool nativeCopyExecuted =
            copyEyes(warpContext, warpDevice, holdLeft, holdRight,
                     true,
                     selectedNative == OutRunVrNativeEyePair::StereoSourceRoute::DirectGpu,
                     true);
        ID3D11RenderTargetView* observedTargets[2]{};
        ID3D11DepthStencilView* observedDepth = nullptr;
        warpContext->OMGetRenderTargets(2u, observedTargets, &observedDepth);
        const bool mrtRestored =
            observedTargets[0] == nativeLeftRtv &&
            observedTargets[1] == nativeRightRtv &&
            observedDepth == nullptr;
        for (auto*& view : observedTargets)
            if (view) { view->Release(); view = nullptr; }
        if (observedDepth) observedDepth->Release();
        // A source switch rejecting a stale native pair must likewise leave
        // the active output render targets unchanged for the SBS shader path.
        const bool fallbackDenied =
            !copyEyes(warpContext, warpDevice, holdLeft, holdRight,
                      true, false, true);
        warpContext->OMGetRenderTargets(2u, observedTargets, &observedDepth);
        const bool fallbackMrtPreserved =
            observedTargets[0] == nativeLeftRtv &&
            observedTargets[1] == nativeRightRtv &&
            observedDepth == nullptr;
        for (auto*& view : observedTargets)
            if (view) { view->Release(); view = nullptr; }
        if (observedDepth) observedDepth->Release();
        warpContext->OMSetRenderTargets(0u, nullptr, nullptr);
        if (!require(copyDenied && deferredDenied && nativeCopyExecuted &&
                     mrtRestored && fallbackDenied && fallbackMrtPreserved,
                     "XR native stereo GPU copy must preserve full OM/MRT state and reject deferred or SBS sources"))
            return 1;
        auto readDesc = xrArray;
        readDesc.Usage = D3D11_USAGE_STAGING;
        readDesc.BindFlags = 0u;
        readDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        readDesc.MiscFlags = 0u;
        if (SUCCEEDED(warpDevice->CreateTexture2D(
                &readDesc, nullptr, &warpReadback)) && warpReadback) {
            warpContext->CopyResource(warpReadback, warpXr);
            D3D11_MAPPED_SUBRESOURCE first{}, second{};
            const bool gotFirst = SUCCEEDED(warpContext->Map(
                warpReadback, 0u, D3D11_MAP_READ, 0u, &first));
            std::uint8_t firstRed = 0u, firstGreen = 0u;
            if (gotFirst && first.pData) {
                const auto* pixel = static_cast<const std::uint8_t*>(first.pData);
                firstRed = pixel[2]; firstGreen = pixel[1];
            }
            if (gotFirst) warpContext->Unmap(warpReadback, 0u);
            const bool gotSecond = SUCCEEDED(warpContext->Map(
                warpReadback, 1u, D3D11_MAP_READ, 0u, &second));
            std::uint8_t secondRed = 0u, secondGreen = 0u;
            if (gotSecond && second.pData) {
                const auto* pixel = static_cast<const std::uint8_t*>(second.pData);
                secondRed = pixel[2]; secondGreen = pixel[1];
            }
            if (gotSecond) warpContext->Unmap(warpReadback, 1u);
            pixelsDistinct = gotFirst && gotSecond &&
                firstRed >= 250u && firstGreen <= 5u &&
                secondGreen >= 250u && secondRed <= 5u;
        }
    }
    if (nativeLeftRtv) nativeLeftRtv->Release();
    if (nativeRightRtv) nativeRightRtv->Release();
    if (warpReadback) warpReadback->Release();
    if (holdLeft) holdLeft->Release();
    if (holdRight) holdRight->Release();
    if (warpXr) warpXr->Release();
    if (!require(resourcesReady && pixelsDistinct,
                 "native OpenXR left/right array GPU copies lost independent eye pixels"))
        return 1;

    if (replacementEye) replacementEye->Release();
    if (replacementContext) replacementContext->Release();
    if (replacementDevice) replacementDevice->Release();
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
    // R23 host source-pixel staging must accept the same packed RGB10A2
    // game-eye format that the live DirectGPU importer/projector admits.
    left.Format = right.Format = DXGI_FORMAT_R10G10B10A2_UNORM;
    const std::uint32_t rgb10 = 1023u | (511u << 10) | (128u << 20) | (3u << 30);
    float decoded10[3]{};
    if (!require(accepts(0x110u, 0x220u, 2u),
                 "two independent 10-bit native game eyes must reach OpenXR") ||
        !require(OutRunVrNativeEyePair::DecodeR10G10B10A2Rgb(
                     reinterpret_cast<const std::uint8_t*>(&rgb10), decoded10),
                 "host source-pixel decoder must admit packed RGB10A2") ||
        !require(decoded10[0] == 1.0f &&
                 decoded10[1] > 0.49f && decoded10[1] < 0.51f &&
                 decoded10[2] > 0.12f && decoded10[2] < 0.13f,
                 "packed RGB10A2 must retain red/green/blue bit ordering") ||
        !require(!OutRunVrNativeEyePair::DecodeR10G10B10A2Rgb(
                     nullptr, decoded10) &&
                 !OutRunVrNativeEyePair::DecodeR10G10B10A2Rgb(
                     reinterpret_cast<const std::uint8_t*>(&rgb10), nullptr),
                 "missing pixel storage must reject host pixel decoding"))
        return 1;
    right.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    if (!require(!accepts(0x110u, 0x220u, 2u),
                 "10-bit/8-bit mixed native stereo pair must reject"))
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
    // The production R23 DirectGPU source is its hold-eye pair, not
    // main.cpp's legacy directSnapshot SRVs. Exercise the route even when
    // legacy snapshots do not exist, plus partial-eye SBS recovery.
    const bool legacyDirectSnapshotsAllocated = false;
    const bool r23HoldLeft = true, r23HoldRight = true;
    if (!require(!legacyDirectSnapshotsAllocated &&
                 ChooseStereoSource(
                     true, r23HoldLeft, r23HoldRight, false, false) ==
                     StereoSourceRoute::DirectGpu,
                 "R23 DirectGPU must not depend on legacy source snapshots") ||
        !require(ChooseStereoSource(
                     true, true, false, true, true) ==
                     StereoSourceRoute::Sbs,
                 "partial R23 direct hold must use fresh SBS fallback") ||
        !require(ChooseStereoSource(
                     true, false, false, false, false) ==
                     StereoSourceRoute::None,
                 "absent R23 hold must not submit an OpenXR stereo layer"))
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
