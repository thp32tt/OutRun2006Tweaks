#pragma once

// Final hardware-test compatibility/diagnostic shim.
//
// 1) Keep the application API request at OpenXR 1.0 for VDXR 1.0.x.
// 2) Log the exact host executable/build/API/runtime so stale EXE mixes are obvious.
// 3) Count xrEndFrame layerCount=0/1 and sample the game Frame.v2 ring to explain
//    why the host has no projection layer.
// 4) When no game layer is available, submit a small alternating-color LOCAL-space
//    quad. This proves OpenXR swapchain/compositor output independently of the
//    D3D9 game-frame path. Set OUTRUN_VR_TEST_PATTERN=0 to disable it.

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <Windows.h>
#include <d3d11.h>
#include <dxgiformat.h>

// Forced includes run before main.cpp defines these. Define them only while the
// platform header is parsed, then remove them so main.cpp can define them normally.
#ifndef XR_USE_PLATFORM_WIN32
#define OUTRUN_FINALTEST_DEFINED_XR_PLATFORM 1
#define XR_USE_PLATFORM_WIN32
#endif
#ifndef XR_USE_GRAPHICS_API_D3D11
#define OUTRUN_FINALTEST_DEFINED_XR_D3D11 1
#define XR_USE_GRAPHICS_API_D3D11
#endif
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>
#ifdef OUTRUN_FINALTEST_DEFINED_XR_PLATFORM
#undef XR_USE_PLATFORM_WIN32
#undef OUTRUN_FINALTEST_DEFINED_XR_PLATFORM
#endif
#ifdef OUTRUN_FINALTEST_DEFINED_XR_D3D11
#undef XR_USE_GRAPHICS_API_D3D11
#undef OUTRUN_FINALTEST_DEFINED_XR_D3D11
#endif

#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <vector>

#include "vr_shared.hpp"

#undef XR_CURRENT_API_VERSION
#define XR_CURRENT_API_VERSION XR_MAKE_VERSION(1, 0, 0)

static_assert(XR_VERSION_MAJOR(XR_CURRENT_API_VERSION) == 1 &&
              XR_VERSION_MINOR(XR_CURRENT_API_VERSION) == 0,
    "OutRun VR host must request the OpenXR 1.0 application API baseline");

namespace OutRunVrFinalTest
{
    inline constexpr const char* BuildId = "R9-finaltest-host-20260915";

    inline XrSession Session = XR_NULL_HANDLE;
    inline XrSpace LocalSpace = XR_NULL_HANDLE;
    inline XrSwapchain PatternSwapchain = XR_NULL_HANDLE;
    inline ID3D11Device* Device = nullptr;
    inline ID3D11DeviceContext* Context = nullptr;
    inline std::vector<XrSwapchainImageD3D11KHR> PatternImages;
    inline std::uint32_t PatternWidth = 640;
    inline std::uint32_t PatternHeight = 360;

    inline std::uint64_t EndFrames = 0;
    inline std::uint64_t LayerFrames = 0;
    inline std::uint64_t ZeroLayerFrames = 0;
    inline std::uint64_t PatternFrames = 0;
    inline std::uint64_t PatternFailures = 0;
    inline std::uint64_t LastSummaryFrame = 0;

    inline HANDLE FrameMapping = nullptr;
    inline const OutRunVR::SharedRenderFrameRing* FrameRing = nullptr;
    inline std::uint32_t LastPublishSequence = 0;
    inline std::array<std::uint64_t, 32> FailureReasons{};
    inline std::uint64_t RejectNoMapping = 0;
    inline std::uint64_t RejectPresentInFlight = 0;
    inline std::uint64_t RejectNotStereoActive = 0;
    inline std::uint64_t RejectZeroFrameId = 0;
    inline std::uint64_t RejectZeroPose = 0;
    inline std::uint64_t RejectMissingFlags = 0;
    inline std::uint64_t AcceptedMetadata = 0;

    inline bool PatternEnabled()
    {
        const char* value = std::getenv("OUTRUN_VR_TEST_PATTERN");
        return !value || std::strcmp(value, "0") != 0;
    }

    inline void LogExecutableAndApi(const XrInstanceCreateInfo* info)
    {
        wchar_t exe[MAX_PATH]{};
        GetModuleFileNameW(nullptr, exe, static_cast<DWORD>(std::size(exe)));
        const XrVersion v = info ? info->applicationInfo.apiVersion : 0;
        std::wcerr << L"[finaltest] hostExe=" << exe << L"\n";
        std::cerr << "[finaltest] build=" << BuildId
                  << " requestedApi=" << XR_VERSION_MAJOR(v) << "."
                  << XR_VERSION_MINOR(v) << "." << XR_VERSION_PATCH(v)
                  << " testPattern=" << (PatternEnabled() ? "on" : "off") << "\n";
    }

    inline void CloseFrameMapping()
    {
        if (FrameRing)
        {
            UnmapViewOfFile(FrameRing);
            FrameRing = nullptr;
        }
        if (FrameMapping)
        {
            CloseHandle(FrameMapping);
            FrameMapping = nullptr;
        }
    }

    inline void EnsureFrameMapping()
    {
        if (FrameRing)
            return;
        FrameMapping = OpenFileMappingW(FILE_MAP_READ, FALSE, OutRunVR::RenderFrameMemoryName);
        if (!FrameMapping)
            return;
        FrameRing = static_cast<const OutRunVR::SharedRenderFrameRing*>(
            MapViewOfFile(FrameMapping, FILE_MAP_READ, 0, 0, sizeof(OutRunVR::SharedRenderFrameRing)));
        if (!FrameRing)
        {
            CloseHandle(FrameMapping);
            FrameMapping = nullptr;
        }
    }

    inline bool ReadLatestFrame(OutRunVR::SharedRenderFrameState& out, std::uint32_t& publishSequence)
    {
        EnsureFrameMapping();
        if (!FrameRing || FrameRing->magic != OutRunVR::RenderFrameMagic ||
            FrameRing->protocolVersion != OutRunVR::RenderFrameProtocolVersion ||
            FrameRing->slotCount != OutRunVR::RenderFrameRingSize)
            return false;

        for (int attempt = 0; attempt < 4; ++attempt)
        {
            const std::uint32_t before = FrameRing->publishSequence;
            if (before & 1u)
                continue;
            MemoryBarrier();
            const std::uint32_t slot = FrameRing->latestSlot;
            if (slot >= OutRunVR::RenderFrameRingSize)
                return false;
            const auto& src = FrameRing->slots[slot];
            const std::uint32_t frameBefore = src.sequence;
            if (frameBefore & 1u)
                continue;
            MemoryBarrier();
            std::memcpy(&out, &src, sizeof(out));
            MemoryBarrier();
            const std::uint32_t frameAfter = src.sequence;
            const std::uint32_t after = FrameRing->publishSequence;
            if (before == after && frameBefore == frameAfter && !(after & 1u) && !(frameAfter & 1u))
            {
                publishSequence = after;
                return out.magic == OutRunVR::RenderFrameMagic &&
                    out.protocolVersion == OutRunVR::RenderFrameProtocolVersion;
            }
        }
        return false;
    }

    inline void SampleRejectReason()
    {
        OutRunVR::SharedRenderFrameState frame{};
        std::uint32_t publish = 0;
        if (!ReadLatestFrame(frame, publish))
        {
            ++RejectNoMapping;
            return;
        }
        if (publish == LastPublishSequence)
            return;
        LastPublishSequence = publish;

        if (frame.failureReason < FailureReasons.size())
            ++FailureReasons[frame.failureReason];
        if (frame.flags & OutRunVR::RenderFramePresentInFlight)
            ++RejectPresentInFlight;
        if (frame.state != OutRunVR::StereoSbsActive)
            ++RejectNotStereoActive;
        if (!frame.frameId)
            ++RejectZeroFrameId;
        if (!frame.sourcePoseSequence)
            ++RejectZeroPose;
        constexpr std::uint32_t need = OutRunVR::RenderFrameStereoComplete |
            OutRunVR::RenderFrameWorldStereo | OutRunVR::RenderFrameDrawDuplicated |
            OutRunVR::RenderFrameEffectivePoseValid;
        if ((frame.flags & need) != need)
            ++RejectMissingFlags;
        if ((frame.flags & OutRunVR::RenderFramePresentInFlight) == 0 &&
            frame.state == OutRunVR::StereoSbsActive && frame.frameId &&
            frame.sourcePoseSequence && (frame.flags & need) == need)
            ++AcceptedMetadata;
    }

    inline void MaybeLogSummary()
    {
        if (EndFrames - LastSummaryFrame < 300)
            return;
        LastSummaryFrame = EndFrames;
        std::cerr << "[finaltest] endFrame total=" << EndFrames
                  << " layer1=" << LayerFrames << " layer0=" << ZeroLayerFrames
                  << " pattern=" << PatternFrames << " patternFail=" << PatternFailures
                  << " metaAccepted=" << AcceptedMetadata
                  << " reject[noMap=" << RejectNoMapping
                  << ",inFlight=" << RejectPresentInFlight
                  << ",state=" << RejectNotStereoActive
                  << ",frame0=" << RejectZeroFrameId
                  << ",pose0=" << RejectZeroPose
                  << ",flags=" << RejectMissingFlags << "]"
                  << " reasons[1=" << FailureReasons[1]
                  << ",5=" << FailureReasons[5]
                  << ",6=" << FailureReasons[6]
                  << ",7=" << FailureReasons[7]
                  << ",8=" << FailureReasons[8]
                  << ",9=" << FailureReasons[9]
                  << ",10=" << FailureReasons[10]
                  << ",11=" << FailureReasons[11]
                  << ",13=" << FailureReasons[13]
                  << ",15=" << FailureReasons[15]
                  << ",18=" << FailureReasons[18] << "]\n";
    }

    inline void DestroyPattern()
    {
        PatternImages.clear();
        if (PatternSwapchain != XR_NULL_HANDLE)
        {
            ::xrDestroySwapchain(PatternSwapchain);
            PatternSwapchain = XR_NULL_HANDLE;
        }
        if (Context)
        {
            Context->Release();
            Context = nullptr;
        }
        if (Device)
        {
            Device->Release();
            Device = nullptr;
        }
    }

    inline bool EnsurePatternSwapchain()
    {
        if (!PatternEnabled() || Session == XR_NULL_HANDLE || LocalSpace == XR_NULL_HANDLE || !Device || !Context)
            return false;
        if (PatternSwapchain != XR_NULL_HANDLE && !PatternImages.empty())
            return true;

        std::uint32_t formatCount = 0;
        if (XR_FAILED(::xrEnumerateSwapchainFormats(Session, 0, &formatCount, nullptr)) || !formatCount)
            return false;
        std::vector<std::int64_t> formats(formatCount);
        if (XR_FAILED(::xrEnumerateSwapchainFormats(Session, formatCount, &formatCount, formats.data())))
            return false;

        std::int64_t selected = formats.front();
        for (const auto f : formats)
        {
            if (f == DXGI_FORMAT_R8G8B8A8_UNORM || f == DXGI_FORMAT_B8G8R8A8_UNORM)
            {
                selected = f;
                break;
            }
        }

        XrSwapchainCreateInfo ci{ XR_TYPE_SWAPCHAIN_CREATE_INFO };
        ci.usageFlags = XR_SWAPCHAIN_USAGE_COLOR_ATTACHMENT_BIT;
        ci.format = selected;
        ci.sampleCount = 1;
        ci.width = PatternWidth;
        ci.height = PatternHeight;
        ci.faceCount = 1;
        ci.arraySize = 1;
        ci.mipCount = 1;
        if (XR_FAILED(::xrCreateSwapchain(Session, &ci, &PatternSwapchain)))
            return false;

        std::uint32_t imageCount = 0;
        if (XR_FAILED(::xrEnumerateSwapchainImages(PatternSwapchain, 0, &imageCount, nullptr)) || !imageCount)
        {
            ::xrDestroySwapchain(PatternSwapchain);
            PatternSwapchain = XR_NULL_HANDLE;
            return false;
        }
        PatternImages.resize(imageCount);
        for (auto& image : PatternImages)
            image = { XR_TYPE_SWAPCHAIN_IMAGE_D3D11_KHR };
        if (XR_FAILED(::xrEnumerateSwapchainImages(PatternSwapchain, imageCount, &imageCount,
            reinterpret_cast<XrSwapchainImageBaseHeader*>(PatternImages.data()))))
        {
            PatternImages.clear();
            ::xrDestroySwapchain(PatternSwapchain);
            PatternSwapchain = XR_NULL_HANDLE;
            return false;
        }

        std::cerr << "[finaltest] no-layer OpenXR test pattern ready "
                  << PatternWidth << "x" << PatternHeight << " format=" << selected << "\n";
        return true;
    }

    inline bool RenderPattern(XrCompositionLayerQuad& quad)
    {
        if (!EnsurePatternSwapchain())
            return false;

        std::uint32_t imageIndex = 0;
        XrSwapchainImageAcquireInfo acquire{ XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO };
        if (XR_FAILED(::xrAcquireSwapchainImage(PatternSwapchain, &acquire, &imageIndex)))
            return false;
        XrSwapchainImageWaitInfo wait{ XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO };
        wait.timeout = XR_INFINITE_DURATION;
        if (XR_FAILED(::xrWaitSwapchainImage(PatternSwapchain, &wait)) || imageIndex >= PatternImages.size())
            return false;

        ID3D11RenderTargetView* rtv = nullptr;
        const HRESULT rtvHr = Device->CreateRenderTargetView(PatternImages[imageIndex].texture, nullptr, &rtv);
        if (FAILED(rtvHr) || !rtv)
            return false;
        const bool phase = ((EndFrames / 60u) & 1u) != 0;
        const float colorA[4] = { 0.02f, 0.65f, 0.95f, 1.0f };
        const float colorB[4] = { 0.95f, 0.05f, 0.55f, 1.0f };
        Context->ClearRenderTargetView(rtv, phase ? colorB : colorA);
        rtv->Release();

        XrSwapchainImageReleaseInfo release{ XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO };
        if (XR_FAILED(::xrReleaseSwapchainImage(PatternSwapchain, &release)))
            return false;

        quad = { XR_TYPE_COMPOSITION_LAYER_QUAD };
        quad.space = LocalSpace;
        quad.eyeVisibility = XR_EYE_VISIBILITY_BOTH;
        quad.subImage.swapchain = PatternSwapchain;
        quad.subImage.imageRect.offset = { 0, 0 };
        quad.subImage.imageRect.extent = { static_cast<std::int32_t>(PatternWidth), static_cast<std::int32_t>(PatternHeight) };
        quad.subImage.imageArrayIndex = 0;
        quad.pose.orientation = { 0.f, 0.f, 0.f, 1.f };
        quad.pose.position = { 0.f, 0.f, -1.5f };
        quad.size = { 1.4f, 0.8f };
        return true;
    }

    inline XrResult XRAPI_CALL CreateInstance(const XrInstanceCreateInfo* info, XrInstance* instance)
    {
        LogExecutableAndApi(info);
        const XrResult result = ::xrCreateInstance(info, instance);
        if (XR_SUCCEEDED(result) && instance && *instance != XR_NULL_HANDLE)
        {
            XrInstanceProperties props{ XR_TYPE_INSTANCE_PROPERTIES };
            if (XR_SUCCEEDED(::xrGetInstanceProperties(*instance, &props)))
            {
                std::cerr << "[finaltest] runtime=" << props.runtimeName
                          << " runtimeVersion=" << XR_VERSION_MAJOR(props.runtimeVersion) << "."
                          << XR_VERSION_MINOR(props.runtimeVersion) << "." << XR_VERSION_PATCH(props.runtimeVersion) << "\n";
            }
        }
        return result;
    }

    inline XrResult XRAPI_CALL CreateSession(XrInstance instance, const XrSessionCreateInfo* info, XrSession* session)
    {
        const XrResult result = ::xrCreateSession(instance, info, session);
        if (XR_SUCCEEDED(result) && session)
        {
            Session = *session;
            const XrBaseInStructure* next = info ? reinterpret_cast<const XrBaseInStructure*>(info->next) : nullptr;
            while (next)
            {
                if (next->type == XR_TYPE_GRAPHICS_BINDING_D3D11_KHR)
                {
                    const auto* binding = reinterpret_cast<const XrGraphicsBindingD3D11KHR*>(next);
                    if (binding->device)
                    {
                        Device = binding->device;
                        Device->AddRef();
                        Device->GetImmediateContext(&Context);
                    }
                    break;
                }
                next = next->next;
            }
            std::cerr << "[finaltest] xrCreateSession ok d3d11=" << (Device ? "yes" : "no") << "\n";
        }
        return result;
    }

    inline XrResult XRAPI_CALL CreateReferenceSpace(XrSession session, const XrReferenceSpaceCreateInfo* info, XrSpace* space)
    {
        const XrResult result = ::xrCreateReferenceSpace(session, info, space);
        if (XR_SUCCEEDED(result) && info && space && info->referenceSpaceType == XR_REFERENCE_SPACE_TYPE_LOCAL)
        {
            LocalSpace = *space;
            std::cerr << "[finaltest] LOCAL reference space captured for no-layer test pattern\n";
        }
        return result;
    }

    inline XrResult XRAPI_CALL DestroySession(XrSession session)
    {
        DestroyPattern();
        CloseFrameMapping();
        LocalSpace = XR_NULL_HANDLE;
        Session = XR_NULL_HANDLE;
        return ::xrDestroySession(session);
    }

    inline XrResult XRAPI_CALL EndFrame(XrSession session, const XrFrameEndInfo* endInfo)
    {
        ++EndFrames;
        if (endInfo && endInfo->layerCount)
            ++LayerFrames;
        else
            ++ZeroLayerFrames;

        SampleRejectReason();

        XrCompositionLayerQuad quad{ XR_TYPE_COMPOSITION_LAYER_QUAD };
        const XrCompositionLayerBaseHeader* patternLayer = nullptr;
        XrFrameEndInfo patched{};
        const XrFrameEndInfo* submit = endInfo;
        if (endInfo && endInfo->layerCount == 0 && PatternEnabled())
        {
            if (RenderPattern(quad))
            {
                patternLayer = reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);
                patched = *endInfo;
                patched.layerCount = 1;
                patched.layers = &patternLayer;
                submit = &patched;
                ++PatternFrames;
            }
            else
            {
                ++PatternFailures;
            }
        }

        MaybeLogSummary();
        return ::xrEndFrame(session, submit);
    }
}

// Redirect only the host translation units compiled with this forced include.
// The wrappers call the loader entry points above before these macros are defined.
#define xrCreateInstance OutRunVrFinalTest::CreateInstance
#define xrCreateSession OutRunVrFinalTest::CreateSession
#define xrCreateReferenceSpace OutRunVrFinalTest::CreateReferenceSpace
#define xrDestroySession OutRunVrFinalTest::DestroySession
#define xrEndFrame OutRunVrFinalTest::EndFrame
