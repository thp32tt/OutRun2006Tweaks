// R23 host entry point.
//
// Reuse the validated host implementation types, but replace the frame loop so
// a candidate capture/direct source is never made presentation-authoritative
// until the surrounding Frame.v2 metadata has been re-read and proven stable.
// Pixel diagnostics use reusable non-blocking staging resources and independently
// probe source, left/right projection output, and theater output.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define XR_USE_PLATFORM_WIN32
#define XR_USE_GRAPHICS_API_D3D11
#include <Windows.h>
#include <TlHelp32.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dxgi1_5.h>
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "vr_shared.hpp"
#include "stereo_shader.hpp"
#include "runtime/r23_verified_bundle.hpp"

// main.cpp keeps compositor implementation details private. R23 is an overlay
// TU over that exact implementation and needs access only to stage/commit
// candidate resources without duplicating the whole compositor. All headers are
// already included above, so this visibility override is confined to the class
// definitions in main.cpp and does not leak into STL/Windows headers.
#define private public
#define protected public
#define main OutRunVrLegacyMainR23
#include "main.cpp"
#undef main
#undef protected
#undef private

// sbs_capture_override.hpp used a legacy ReleaseFrame macro while preprocessing
// main.cpp. R23 performs the production publication explicitly below.
#ifdef ReleaseFrame
#undef ReleaseFrame
#endif

namespace
{
    constexpr ULONGLONG R23PixelIntervalMs = 5000;
    constexpr UINT R23SourceSamples = 8;
    constexpr DWORD R23TheaterRefreshWaitMs = 2;
    constexpr ULONGLONG R23TheaterRefreshLogIntervalMs = 5000;
    // OpenXR/VDXR commonly runs at 90 Hz while OutRun produces stereo at
    // roughly 60 Hz. Re-rendering the same Desktop Duplication source into the
    // projection swapchain on every HMD tick wastes GPU work, while falling
    // back to the theater quad exposes the raw SBS image. Keep the last
    // successfully released projection alive for intermediate HMD frames and
    // for short game-state/capture gaps.
    constexpr ULONGLONG R23CachedProjectionHoldMs = 1000;
    constexpr ULONGLONG R23PresentationDebounceMs = 750;
    constexpr ULONGLONG R23CachedProjectionLogIntervalMs = 5000;
    std::uint64_t R23CachedProjectionSubmits = 0;
    ULONGLONG R23LastCachedProjectionLogMs = 0;
    std::uint64_t R23PresentationGraceFrames = 0;
    std::uint64_t R23TheaterRefreshAttempts = 0;
    std::uint64_t R23TheaterRefreshFresh = 0;
    ULONGLONG R23LastTheaterRefreshLogMs = 0;
    std::uint64_t R23GameplayTheaterFallbacks = 0;
    ULONGLONG R23LastGameplayFallbackLogMs = 0;


    struct R23DirectHoldState
    {
        ID3D11Texture2D* eye[2]{};
        ID3D11ShaderResourceView* srv[2]{};
        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        UINT width = 0;
        UINT height = 0;
        UINT mipLevels = 0;
        UINT arraySize = 0;
        std::uint32_t frameId = 0;
        std::uint32_t generation = 0;
        bool valid = false;

        ~R23DirectHoldState()
        {
            for (int eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
            {
                if (srv[eyeIndex]) srv[eyeIndex]->Release();
                if (eye[eyeIndex]) eye[eyeIndex]->Release();
            }
        }
    };
    R23DirectHoldState R23DirectHold{};
    bool R23FirstDirectHoldLogged = false;

    void R23ReleaseDirectHoldResources() noexcept
    {
        for (int eye = 0; eye < 2; ++eye)
        {
            ReleaseCom(R23DirectHold.srv[eye]);
            ReleaseCom(R23DirectHold.eye[eye]);
        }
        R23DirectHold.format = DXGI_FORMAT_UNKNOWN;
        R23DirectHold.width = 0;
        R23DirectHold.height = 0;
        R23DirectHold.mipLevels = 0;
        R23DirectHold.arraySize = 0;
        R23DirectHold.frameId = 0;
        R23DirectHold.generation = 0;
        R23DirectHold.valid = false;
    }

    void R23InvalidateDirectHold() noexcept
    {
        R23DirectHold.frameId = 0;
        R23DirectHold.generation = 0;
        R23DirectHold.valid = false;
    }

    bool R23StageDirectHold(StereoCompositor& c,
        const OutRunVR::SharedRenderFrameState& frame)
    {
        const std::uint32_t slot =
            frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];
        const std::uint32_t generation =
            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
        if (!c.context_ || !c.device_ || slot >= OutRunVR::RenderFrameRingSize ||
            !frame.frameId || !generation || !c.directLeft_[slot] ||
            !c.directRight_[slot])
            return false;

        D3D11_TEXTURE2D_DESC left{};
        D3D11_TEXTURE2D_DESC right{};
        c.directLeft_[slot]->GetDesc(&left);
        c.directRight_[slot]->GetDesc(&right);
        if (!left.Width || !left.Height || left.Width != right.Width ||
            left.Height != right.Height || left.MipLevels != right.MipLevels ||
            left.ArraySize != right.ArraySize || left.Format != right.Format ||
            left.SampleDesc.Count != 1 || right.SampleDesc.Count != 1 ||
            left.Width != frame.backbufferWidth ||
            left.Height != frame.backbufferHeight)
            return false;

        const bool recreate =
            !R23DirectHold.eye[0] || !R23DirectHold.eye[1] ||
            !R23DirectHold.srv[0] || !R23DirectHold.srv[1] ||
            R23DirectHold.width != left.Width ||
            R23DirectHold.height != left.Height ||
            R23DirectHold.mipLevels != left.MipLevels ||
            R23DirectHold.arraySize != left.ArraySize ||
            R23DirectHold.format != left.Format;
        if (recreate)
        {
            R23ReleaseDirectHoldResources();
            D3D11_TEXTURE2D_DESC hold = left;
            hold.Usage = D3D11_USAGE_DEFAULT;
            hold.BindFlags = D3D11_BIND_SHADER_RESOURCE;
            hold.CPUAccessFlags = 0;
            hold.MiscFlags = 0;
            for (int eye = 0; eye < 2; ++eye)
            {
                if (FAILED(c.device_->CreateTexture2D(
                        &hold, nullptr, &R23DirectHold.eye[eye])) ||
                    !R23DirectHold.eye[eye] ||
                    FAILED(c.device_->CreateShaderResourceView(
                        R23DirectHold.eye[eye], nullptr,
                        &R23DirectHold.srv[eye])) ||
                    !R23DirectHold.srv[eye])
                {
                    R23ReleaseDirectHoldResources();
                    return false;
                }
            }
            R23DirectHold.width = left.Width;
            R23DirectHold.height = left.Height;
            R23DirectHold.mipLevels = left.MipLevels;
            R23DirectHold.arraySize = left.ArraySize;
            R23DirectHold.format = left.Format;
        }

        // Immediate-context ordering guarantees that both copies execute before
        // the following projection draw samples this host-owned pair. The R32
        // EVENT fence then covers the copy + projection work before producer ACK.
        c.context_->CopyResource(R23DirectHold.eye[0], c.directLeft_[slot]);
        c.context_->CopyResource(R23DirectHold.eye[1], c.directRight_[slot]);
        R23DirectHold.frameId = frame.frameId;
        R23DirectHold.generation = generation;
        R23DirectHold.valid = true;
        if (!R23FirstDirectHoldLogged)
        {
            R23FirstDirectHoldLogged = true;
            std::cout
                << "DirectGPU single-copy production path active; legacy private snapshot/fence bypassed and grace projection samples only host-owned hold textures.\n";
        }
        return true;
    }

    const char* R23SourceKindName(OutRunVrR23VerifiedBundle::SourceKind kind)
    {
        using OutRunVrR23VerifiedBundle::SourceKind;
        switch (kind)
        {
        case SourceKind::ClassicSbs: return "classic-sbs";
        case SourceKind::DirectGpu: return "direct-gpu";
        default: return "none";
        }
    }

    float R23HalfToFloat(std::uint16_t value)
    {
        const std::uint32_t sign = static_cast<std::uint32_t>(value & 0x8000u) << 16;
        std::uint32_t exponent = (value >> 10) & 0x1Fu;
        std::uint32_t mantissa = value & 0x03FFu;
        std::uint32_t bits = 0;
        if (exponent == 0)
        {
            if (mantissa == 0) bits = sign;
            else
            {
                int unbiased = -14;
                while ((mantissa & 0x0400u) == 0) { mantissa <<= 1; --unbiased; }
                mantissa &= 0x03FFu;
                bits = sign | (static_cast<std::uint32_t>(unbiased + 127) << 23) |
                    (mantissa << 13);
            }
        }
        else if (exponent == 0x1Fu)
            bits = sign | 0x7F800000u | (mantissa << 13);
        else
            bits = sign | ((exponent + 112u) << 23) | (mantissa << 13);
        float out = 0.0f;
        std::memcpy(&out, &bits, sizeof(out));
        return out;
    }

    bool R23DecodeRgb(const std::uint8_t* p, DXGI_FORMAT format, float rgb[3])
    {
        if (!p || !rgb) return false;
        if (format == DXGI_FORMAT_B8G8R8A8_UNORM ||
            format == DXGI_FORMAT_B8G8R8A8_UNORM_SRGB)
        {
            rgb[0] = p[2] / 255.0f; rgb[1] = p[1] / 255.0f; rgb[2] = p[0] / 255.0f;
            return true;
        }
        if (format == DXGI_FORMAT_R8G8B8A8_UNORM ||
            format == DXGI_FORMAT_R8G8B8A8_UNORM_SRGB)
        {
            rgb[0] = p[0] / 255.0f; rgb[1] = p[1] / 255.0f; rgb[2] = p[2] / 255.0f;
            return true;
        }
        if (format == DXGI_FORMAT_R16G16B16A16_FLOAT)
        {
            const auto* h = reinterpret_cast<const std::uint16_t*>(p);
            rgb[0] = R23HalfToFloat(h[0]); rgb[1] = R23HalfToFloat(h[1]); rgb[2] = R23HalfToFloat(h[2]);
            return true;
        }
        return false;
    }

    UINT R23BytesPerPixel(DXGI_FORMAT format)
    {
        return format == DXGI_FORMAT_R16G16B16A16_FLOAT ? 8u : 4u;
    }

    struct R23AsyncPixelProbe
    {
        ID3D11Texture2D* sourceStage = nullptr;
        ID3D11Texture2D* projectionStage = nullptr;
        ID3D11Texture2D* theaterStage = nullptr;
        DXGI_FORMAT sourceFormat = DXGI_FORMAT_UNKNOWN;
        DXGI_FORMAT projectionFormat = DXGI_FORMAT_UNKNOWN;
        DXGI_FORMAT theaterFormat = DXGI_FORMAT_UNKNOWN;
        bool sourcePending = false;
        bool projectionPending = false;
        bool theaterPending = false;
        ULONGLONG lastSourceScheduleMs = 0;
        ULONGLONG lastProjectionScheduleMs = 0;
        ULONGLONG lastTheaterScheduleMs = 0;
        std::uint64_t sourceMapDefers = 0;
        std::uint64_t projectionMapDefers = 0;
        std::uint64_t theaterMapDefers = 0;
        std::uint32_t projectionFrameId = 0;
        OutRunVrR23VerifiedBundle::SourceKind projectionKind =
            OutRunVrR23VerifiedBundle::SourceKind::None;
        bool projectionFinalKnown = false;
        bool projectionFinalSubmitted = false;
        bool theaterFinalKnown = false;
        bool theaterFinalSubmitted = false;

        ~R23AsyncPixelProbe()
        {
            ReleaseCom(sourceStage);
            ReleaseCom(projectionStage);
            ReleaseCom(theaterStage);
        }

        bool EnsureStage(ID3D11Device* device, ID3D11Texture2D*& stage,
            DXGI_FORMAT& cachedFormat, DXGI_FORMAT format, UINT width)
        {
            if (stage && cachedFormat == format)
                return true;
            ReleaseCom(stage);
            cachedFormat = DXGI_FORMAT_UNKNOWN;
            D3D11_TEXTURE2D_DESC d{};
            d.Width = width; d.Height = 1; d.MipLevels = 1; d.ArraySize = 1;
            d.Format = format; d.SampleDesc.Count = 1;
            d.Usage = D3D11_USAGE_STAGING; d.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
            const HRESULT hr = device->CreateTexture2D(&d, nullptr, &stage);
            if (FAILED(hr) || !stage)
            {
                std::cerr << "[R23 pixel] CreateTexture2D staging failed hr=0x"
                          << std::hex << static_cast<unsigned long>(hr) << std::dec << "\n";
                return false;
            }
            cachedFormat = format;
            return true;
        }

        void ConsumeSource(ID3D11DeviceContext* context)
        {
            if (!sourcePending || !sourceStage || !context) return;
            D3D11_MAPPED_SUBRESOURCE mapped{};
            const HRESULT hr = context->Map(sourceStage, 0, D3D11_MAP_READ,
                D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
            if (hr == DXGI_ERROR_WAS_STILL_DRAWING) { ++sourceMapDefers; return; }
            if (FAILED(hr) || !mapped.pData)
            {
                std::cerr << "[R23 pixel] source-game-uv async Map failed hr=0x"
                          << std::hex << static_cast<unsigned long>(hr) << std::dec << "\n";
                sourcePending = false;
                return;
            }

            float minRgb[3]{ 1.0e30f, 1.0e30f, 1.0e30f };
            float maxRgb[3]{ -1.0e30f, -1.0e30f, -1.0e30f };
            double sumRgb[3]{};
            std::uint32_t finitePixels = 0, nonFinitePixels = 0;
            const UINT bpp = R23BytesPerPixel(sourceFormat);
            const auto* row = static_cast<const std::uint8_t*>(mapped.pData);
            for (UINT i = 0; i < R23SourceSamples; ++i)
            {
                float rgb[3]{};
                if (!R23DecodeRgb(row + static_cast<std::size_t>(i) * bpp, sourceFormat, rgb))
                    continue;
                const bool finite = std::isfinite(rgb[0]) && std::isfinite(rgb[1]) && std::isfinite(rgb[2]);
                if (!finite) { ++nonFinitePixels; continue; }
                ++finitePixels;
                for (int c = 0; c < 3; ++c)
                {
                    minRgb[c] = std::min(minRgb[c], rgb[c]);
                    maxRgb[c] = std::max(maxRgb[c], rgb[c]);
                    sumRgb[c] += rgb[c];
                }
            }
            context->Unmap(sourceStage, 0);
            sourcePending = false;
            const double denom = finitePixels ? static_cast<double>(finitePixels) : 1.0;
            std::cout << "[R23 pixel] source-game-uv samples=" << R23SourceSamples
                      << " finite=" << finitePixels << " nonFinitePixels=" << nonFinitePixels
                      << " rgbMin=" << minRgb[0] << "," << minRgb[1] << "," << minRgb[2]
                      << " rgbMax=" << maxRgb[0] << "," << maxRgb[1] << "," << maxRgb[2]
                      << " rgbMean=" << sumRgb[0] / denom << "," << sumRgb[1] / denom << "," << sumRgb[2] / denom
                      << " mapDefers=" << sourceMapDefers << "\n";
        }

        void ConsumeProjection(ID3D11DeviceContext* context)
        {
            if (!projectionPending || !projectionStage || !context) return;
            D3D11_MAPPED_SUBRESOURCE mapped{};
            const HRESULT hr = context->Map(projectionStage, 0, D3D11_MAP_READ,
                D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
            if (hr == DXGI_ERROR_WAS_STILL_DRAWING) { ++projectionMapDefers; return; }
            if (FAILED(hr) || !mapped.pData)
            {
                std::cerr << "[R23 pixel] projection async Map failed hr=0x"
                          << std::hex << static_cast<unsigned long>(hr) << std::dec << "\n";
                projectionPending = false;
                return;
            }

            const UINT bpp = R23BytesPerPixel(projectionFormat);
            const auto* row = static_cast<const std::uint8_t*>(mapped.pData);
            float left[3]{}, right[3]{};
            const bool leftDecoded = R23DecodeRgb(row, projectionFormat, left);
            const bool rightDecoded = R23DecodeRgb(row + bpp, projectionFormat, right);
            const bool leftFinite = leftDecoded && std::isfinite(left[0]) &&
                std::isfinite(left[1]) && std::isfinite(left[2]);
            const bool rightFinite = rightDecoded && std::isfinite(right[0]) &&
                std::isfinite(right[1]) && std::isfinite(right[2]);
            context->Unmap(projectionStage, 0);
            projectionPending = false;

            std::cout << "[R23 pixel] projection frame=" << projectionFrameId
                      << " source=" << R23SourceKindName(projectionKind)
                      << " finalSubmissionKnown=" << (projectionFinalKnown ? 1 : 0)
                      << " finalSubmitted=" << (projectionFinalSubmitted ? 1 : 0)
                      << " leftFinite=" << (leftFinite ? 1 : 0)
                      << " leftRgb=" << left[0] << "," << left[1] << "," << left[2]
                      << " rightFinite=" << (rightFinite ? 1 : 0)
                      << " rightRgb=" << right[0] << "," << right[1] << "," << right[2]
                      << " mapDefers=" << projectionMapDefers << "\n";
        }

        void ConsumeTheater(ID3D11DeviceContext* context)
        {
            if (!theaterPending || !theaterStage || !context) return;
            D3D11_MAPPED_SUBRESOURCE mapped{};
            const HRESULT hr = context->Map(theaterStage, 0, D3D11_MAP_READ,
                D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
            if (hr == DXGI_ERROR_WAS_STILL_DRAWING) { ++theaterMapDefers; return; }
            if (FAILED(hr) || !mapped.pData)
            {
                std::cerr << "[R23 pixel] theater async Map failed hr=0x"
                          << std::hex << static_cast<unsigned long>(hr) << std::dec << "\n";
                theaterPending = false;
                return;
            }
            float rgb[3]{};
            const bool decoded = R23DecodeRgb(
                static_cast<const std::uint8_t*>(mapped.pData), theaterFormat, rgb);
            const bool finite = decoded && std::isfinite(rgb[0]) &&
                std::isfinite(rgb[1]) && std::isfinite(rgb[2]);
            context->Unmap(theaterStage, 0);
            theaterPending = false;
            std::cout << "[R23 pixel] theater finalSubmissionKnown="
                      << (theaterFinalKnown ? 1 : 0)
                      << " finalSubmitted=" << (theaterFinalSubmitted ? 1 : 0)
                      << " finite=" << (finite ? 1 : 0)
                      << " rgb=" << rgb[0] << "," << rgb[1] << "," << rgb[2]
                      << " mapDefers=" << theaterMapDefers << "\n";
        }

        void TryConsume(ID3D11DeviceContext* context)
        {
            ConsumeSource(context);
            ConsumeProjection(context);
            ConsumeTheater(context);
        }

        void NoteFinalSubmission()
        {
            const bool submitted =
                OutRunVrR23RuntimeHardening::LastSubmittedLayer.load(std::memory_order_acquire);
            const std::uint32_t frameId =
                OutRunVrR23RuntimeHardening::LastSubmittedFrameId.load(std::memory_order_acquire);
            const auto kind = static_cast<OutRunVrR23VerifiedBundle::SourceKind>(
                OutRunVrR23RuntimeHardening::LastSubmittedKind.load(std::memory_order_acquire));

            if (projectionPending && !projectionFinalKnown &&
                frameId == projectionFrameId && kind == projectionKind)
            {
                projectionFinalKnown = true;
                projectionFinalSubmitted = submitted;
            }
            if (theaterPending && !theaterFinalKnown &&
                kind == OutRunVrR23VerifiedBundle::SourceKind::None)
            {
                theaterFinalKnown = true;
                theaterFinalSubmitted = submitted;
            }
        }

        void ScheduleSource(StereoCompositor& c)
        {
            const ULONGLONG now = GetTickCount64();
            if (sourcePending || now - lastSourceScheduleMs < R23PixelIntervalMs ||
                !c.source_ || !c.device_ || !c.context_) return;
            UvRect uv{};
            if (!c.GetGameUv(uv)) return;
            if (!EnsureStage(c.device_, sourceStage, sourceFormat,
                    c.sourceFormat_, R23SourceSamples)) return;

            const float xs[4]{ 0.125f, 0.375f, 0.625f, 0.875f };
            const float ys[2]{ 0.35f, 0.65f };
            UINT index = 0;
            for (float yFrac : ys)
            {
                for (float xFrac : xs)
                {
                    const UINT sx = std::min(c.sourceWidth_ - 1,
                        static_cast<UINT>((uv.x + uv.w * xFrac) * c.sourceWidth_));
                    const UINT sy = std::min(c.sourceHeight_ - 1,
                        static_cast<UINT>((uv.y + uv.h * yFrac) * c.sourceHeight_));
                    D3D11_BOX box{ sx, sy, 0, sx + 1, sy + 1, 1 };
                    c.context_->CopySubresourceRegion(sourceStage, 0, index++, 0, 0,
                        c.source_, 0, &box);
                }
            }
            sourcePending = true;
            lastSourceScheduleMs = now;
            std::cout << "[R23 pixel] scheduled game-UV distributed source probe uv=["
                      << uv.x << "," << uv.y << "," << uv.w << "," << uv.h << "]\n";
        }

        void ScheduleProjection(StereoCompositor& c, std::uint32_t image)
        {
            const ULONGLONG now = GetTickCount64();
            if (projectionPending || now - lastProjectionScheduleMs < R23PixelIntervalMs ||
                image >= c.projection_.images.size() || !c.device_ || !c.context_) return;
            if (!EnsureStage(c.device_, projectionStage, projectionFormat,
                    c.projection_.format, 2)) return;
            ID3D11Texture2D* texture = c.projection_.images[image].texture;
            if (!texture) return;
            for (UINT eye = 0; eye < 2; ++eye)
            {
                const UINT sx = c.projection_.width / 2;
                const UINT sy = c.projection_.height / 2;
                D3D11_BOX box{ sx, sy, 0, sx + 1, sy + 1, 1 };
                c.context_->CopySubresourceRegion(projectionStage, 0, eye, 0, 0,
                    texture, D3D11CalcSubresource(0, eye, 1), &box);
            }
            OutRunVrR23VerifiedBundle::Snapshot verified{};
            if (OutRunVrR23VerifiedBundle::ReadFresh(verified))
            {
                projectionFrameId = verified.frameId;
                projectionKind = verified.kind;
            }
            else
            {
                projectionFrameId = 0;
                projectionKind = OutRunVrR23VerifiedBundle::SourceKind::None;
            }
            projectionFinalKnown = false;
            projectionFinalSubmitted = false;
            projectionPending = true;
            lastProjectionScheduleMs = now;
        }

        void ScheduleTheater(StereoCompositor& c, std::uint32_t image)
        {
            const ULONGLONG now = GetTickCount64();
            if (theaterPending || now - lastTheaterScheduleMs < R23PixelIntervalMs ||
                image >= c.theater_.images.size() || !c.device_ || !c.context_) return;
            if (!EnsureStage(c.device_, theaterStage, theaterFormat,
                    c.theater_.format, 1)) return;
            ID3D11Texture2D* texture = c.theater_.images[image].texture;
            if (!texture) return;
            const UINT sx = c.theater_.width / 2;
            const UINT sy = c.theater_.height / 2;
            D3D11_BOX box{ sx, sy, 0, sx + 1, sy + 1, 1 };
            c.context_->CopySubresourceRegion(theaterStage, 0, 0, 0, 0,
                texture, 0, &box);
            theaterFinalKnown = false;
            theaterFinalSubmitted = false;
            theaterPending = true;
            lastTheaterScheduleMs = now;
        }
    };

    R23AsyncPixelProbe R23Pixels{};

    CaptureStatus R23Capture(StereoCompositor& c, DWORD timeoutMs = 0,
        bool allowInitialWarmupWait = true)
    {
        R23Pixels.TryConsume(c.context_);
        if (!IsWindow(c.hwnd_))
            if (HWND replacement = FindGameWindow(c.gamePid_)) c.hwnd_ = replacement;
        const HMONITOR monitorNow = IsWindow(c.hwnd_)
            ? MonitorFromWindow(c.hwnd_, MONITOR_DEFAULTTONEAREST) : nullptr;
        if (!c.duplication_ || (monitorNow && monitorNow != c.targetMonitor_))
            c.BindCaptureOutput(false);
        CaptureStatus status{ c.haveFrame_, false, c.lastCapturePresentQpc_, c.lastCapturePresentQpcLow_ };
        if (!c.duplication_ && !c.RecreateDuplication(false)) return status;

        DXGI_OUTDUPL_FRAME_INFO fi{};
        IDXGIResource* resource = nullptr;
        if (!c.duplication_) return status;
        const DWORD waitMs = (c.haveFrame_ || !allowInitialWarmupWait)
            ? timeoutMs : std::max<DWORD>(timeoutMs, 1000);
        const HRESULT hr = c.duplication_->AcquireNextFrame(waitMs, &fi, &resource);
        if (hr == DXGI_ERROR_WAIT_TIMEOUT) return status;
        if (FAILED(hr) || !resource)
        {
            if (hr == DXGI_ERROR_ACCESS_LOST)
            {
                c.haveFrame_ = false;
                c.stereoSourceValid_ = false;
                c.BindCaptureOutput(false);
            }
            return { c.haveFrame_, false, c.lastCapturePresentQpc_, c.lastCapturePresentQpcLow_ };
        }

        ID3D11Texture2D* texture = nullptr;
        const HRESULT qi = resource->QueryInterface(__uuidof(ID3D11Texture2D),
            reinterpret_cast<void**>(&texture));
        resource->Release();
        bool copied = false;
        if (SUCCEEDED(qi) && texture)
        {
            D3D11_TEXTURE2D_DESC d{};
            texture->GetDesc(&d);
            if ((d.Format == DXGI_FORMAT_B8G8R8A8_UNORM ||
                 d.Format == DXGI_FORMAT_R16G16B16A16_FLOAT) && c.EnsureSource(d))
            {
                c.context_->CopyResource(c.source_, texture);
                copied = true;
            }
            texture->Release();
        }
        c.duplication_->ReleaseFrame();

        if (copied)
        {
            c.haveFrame_ = true;
            if (fi.LastPresentTime.QuadPart != 0)
            {
                c.lastCapturePresentQpc_ = fi.LastPresentTime.QuadPart;
                c.lastCapturePresentQpcLow_ = static_cast<std::uint32_t>(fi.LastPresentTime.QuadPart);
            }
            status.available = true;
            status.fresh = fi.AccumulatedFrames > 0;
            status.lastPresentQpc = c.lastCapturePresentQpc_;
            status.lastPresentQpcLow = c.lastCapturePresentQpcLow_;
            OutRunVrSbsCaptureOverride::PublishProductionCapture(
                c.source_, c.outputDesktop_, c.targetMonitor_, c.sdrWhiteScale_,
                fi.LastPresentTime.QuadPart);
            R23Pixels.ScheduleSource(c);
        }
        return status;
    }

    CaptureStatus R23RefreshTheaterFallbackCapture(StereoCompositor& c)
    {
        ++R23TheaterRefreshAttempts;
        const CaptureStatus status = R23Capture(
            c, R23TheaterRefreshWaitMs, false);
        if (status.fresh)
            ++R23TheaterRefreshFresh;

        const ULONGLONG now = GetTickCount64();
        if (R23LastTheaterRefreshLogMs == 0 ||
            now - R23LastTheaterRefreshLogMs >= R23TheaterRefreshLogIntervalMs)
        {
            R23LastTheaterRefreshLogMs = now;
            const ULONGLONG publishedAt =
                OutRunVrSbsCaptureOverride::LastProductionPublishMs;
            const long long publishAgeMs = publishedAt && now >= publishedAt
                ? static_cast<long long>(now - publishedAt) : -1;
            std::cout
                << "[R23 mono] gameplay stereo pending: bounded Desktop Duplication refresh for theater-only fallback"
                << " attempts=" << R23TheaterRefreshAttempts
                << " fresh=" << R23TheaterRefreshFresh
                << " available=" << (status.available ? 1 : 0)
                << " captureQpc=" << status.lastPresentQpc
                << " publishAgeMs=" << publishAgeMs
                << " waitMs=" << R23TheaterRefreshWaitMs << "\n";
        }
        return status;
    }

    bool R23FrameUnchanged(RenderFrameReader& reader,
        const OutRunVR::SharedRenderFrameState& before)
    {
        OutRunVR::SharedRenderFrameState after{};
        return reader.Read(after) &&
            (after.flags & OutRunVR::RenderFramePresentInFlight) == 0 &&
            after.sequence == before.sequence &&
            after.clientPid == before.clientPid &&
            after.state == before.state && after.frameId == before.frameId &&
            after.sourcePoseSequence == before.sourcePoseSequence &&
            after.presentationMode == before.presentationMode &&
            after.presentQpc == before.presentQpc && after.flags == before.flags &&
            after.failureReason == before.failureReason &&
            after.backbufferWidth == before.backbufferWidth &&
            after.backbufferHeight == before.backbufferHeight &&
            std::memcmp(after.eye, before.eye, sizeof(before.eye)) == 0 &&
            std::memcmp(after.reserved, before.reserved, sizeof(before.reserved)) == 0;
    }

    bool R23ValidateDirectResourceSize(StereoCompositor& c,
        const OutRunVR::SharedRenderFrameState& frame)
    {
        const std::uint32_t slot = frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];
        const std::uint32_t width = frame.reserved[OutRunVR::RenderFrameDirectWidthIndex];
        const std::uint32_t height = frame.reserved[OutRunVR::RenderFrameDirectHeightIndex];
        if (slot >= OutRunVR::RenderFrameRingSize || !width || !height ||
            width != frame.backbufferWidth || height != frame.backbufferHeight ||
            !c.directLeft_[slot] || !c.directRight_[slot]) return false;
        D3D11_TEXTURE2D_DESC l{}, r{};
        c.directLeft_[slot]->GetDesc(&l); c.directRight_[slot]->GetDesc(&r);
        return l.Width == width && l.Height == height && r.Width == width && r.Height == height &&
            l.Format == r.Format && l.SampleDesc.Count == 1 && r.SampleDesc.Count == 1;
    }

    void R23InvalidateDirect(StereoCompositor& c)
    {
        c.directFrameValid_ = false;
        c.directTransportReady_ = false;
        R23InvalidateDirectHold();
    }

    bool R23CommitDirectAfterValidation(StereoCompositor& c,
        const OutRunVR::SharedRenderFrameState& frame)
    {
        if (!c.PrepareDirectStereoSource(frame) ||
            !R23ValidateDirectResourceSize(c, frame) ||
            !R23StageDirectHold(c, frame))
        {
            R23InvalidateDirect(c);
            return false;
        }
        c.directTransportReady_ = true;
        c.directFrameValid_ = true;
        c.stereoSourceValid_ = false;
        return true;
    }

    bool R23CommitClassicAfterValidation(StereoCompositor& c)
    {
        c.directFrameValid_ = false;
        if (!c.CommitStereoSource()) return false;
        c.stereoSourceValid_ = true;
        return true;
    }

    bool R23RenderProjection(StereoCompositor& c,
        const std::array<XrView, 2>& views,
        std::array<XrCompositionLayerProjectionView, 2>& pv)
    {
        R23Pixels.TryConsume(c.context_);
        if (!c.HasStereoSource()) return false;
        UvRect eyes[2]{};
        ID3D11ShaderResourceView* srv[2]{};
        DXGI_FORMAT fmt[2]{ DXGI_FORMAT_UNKNOWN, DXGI_FORMAT_UNKNOWN };
        if (c.directFrameValid_ && R23DirectHold.valid &&
            R23DirectHold.srv[0] && R23DirectHold.srv[1])
        {
            eyes[0] = eyes[1] = { 0.f, 0.f, 1.f, 1.f };
            srv[0] = R23DirectHold.srv[0];
            srv[1] = R23DirectHold.srv[1];
            fmt[0] = fmt[1] = R23DirectHold.format;
        }
        else
        {
            UvRect whole{};
            if (!c.GetGameUv(whole)) return false;
            eyes[0] = { whole.x, whole.y, whole.w * 0.5f, whole.h };
            eyes[1] = { whole.x + whole.w * 0.5f, whole.y, whole.w * 0.5f, whole.h };
            srv[0] = srv[1] = c.stereoSourceSrv_;
            fmt[0] = fmt[1] = c.stereoSourceFormat_;
        }

        std::uint32_t image = 0;
        c.Acquire(c.projection_, image);
        bool ok = c.RenderTo(c.projection_.rtvs[image][0], c.projection_.width,
            c.projection_.height, eyes[0], srv[0], fmt[0]);
        ok = c.RenderTo(c.projection_.rtvs[image][1], c.projection_.width,
            c.projection_.height, eyes[1], srv[1], fmt[1]) && ok;
        if (ok) R23Pixels.ScheduleProjection(c, image);
        c.Release(c.projection_);
        if (!ok) return false;

        for (int eye = 0; eye < 2; ++eye)
        {
            pv[eye] = { XR_TYPE_COMPOSITION_LAYER_PROJECTION_VIEW };
            pv[eye].pose = views[eye].pose;
            pv[eye].fov = views[eye].fov;
            pv[eye].subImage.swapchain = c.projection_.handle;
            pv[eye].subImage.imageRect.offset = { 0, 0 };
            pv[eye].subImage.imageRect.extent = {
                static_cast<int32_t>(c.projection_.width),
                static_cast<int32_t>(c.projection_.height) };
            pv[eye].subImage.imageArrayIndex = eye;
        }
        return true;
    }

    bool R23RenderTheater(StereoCompositor& c, XrSpace viewSpace,
        XrSpace localSpace, XrTime displayTime, XrCompositionLayerQuad& quad)
    {
        R23Pixels.TryConsume(c.context_);
        if (!c.haveFrame_ || !c.sourceSrv_) return false;
        UvRect whole{};
        if (!c.GetGameUv(whole)) return false;
        std::uint32_t image = 0;
        c.Acquire(c.theater_, image);
        const bool ok = c.RenderTo(c.theater_.rtvs[image][0], c.theater_.width,
            c.theater_.height, whole, c.sourceSrv_, c.sourceFormat_);
        if (ok) R23Pixels.ScheduleTheater(c, image);
        c.Release(c.theater_);
        if (!ok || !c.EnsureTheaterAnchor(viewSpace, localSpace, displayTime)) return false;

        quad = { XR_TYPE_COMPOSITION_LAYER_QUAD };
        quad.space = localSpace;
        quad.eyeVisibility = XR_EYE_VISIBILITY_BOTH;
        quad.pose = c.theaterAnchor_;
        quad.subImage.swapchain = c.theater_.handle;
        quad.subImage.imageRect.offset = { 0, 0 };
        quad.subImage.imageRect.extent = {
            static_cast<int32_t>(c.theater_.width), static_cast<int32_t>(c.theater_.height) };
        RECT cr{};
        GetClientRect(c.hwnd_, &cr);
        const float aspect = (cr.bottom > cr.top)
            ? static_cast<float>(cr.right - cr.left) / static_cast<float>(cr.bottom - cr.top)
            : 16.f / 9.f;
        quad.size.width = 2.f;
        quad.size.height = 2.f / aspect;
        return true;
    }

    void R23CopyMatchedViews(const OutRunVR::SharedRenderFrameState& frame,
        std::array<XrView, 2>& matchedViews)
    {
        for (int eye = 0; eye < 2; ++eye)
        {
            matchedViews[eye] = { XR_TYPE_VIEW };
            matchedViews[eye].pose.orientation = {
                frame.eye[eye].orientation[0], frame.eye[eye].orientation[1],
                frame.eye[eye].orientation[2], frame.eye[eye].orientation[3] };
            matchedViews[eye].pose.position = {
                frame.eye[eye].position[0], frame.eye[eye].position[1], frame.eye[eye].position[2] };
            matchedViews[eye].fov = {
                frame.eye[eye].fov.angleLeft, frame.eye[eye].fov.angleRight,
                frame.eye[eye].fov.angleUp, frame.eye[eye].fov.angleDown };
        }
    }
}

int main(int argc, char** argv)
{
    XrInstance instance = XR_NULL_HANDLE;
    XrSession session = XR_NULL_HANDLE;
    XrSpace localSpace = XR_NULL_HANDLE;
    XrSpace viewSpace = XR_NULL_HANDLE;

    try
    {
        SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        ParseRuntimeOverride(argc, argv);
        const float renderScale = ReadRenderScale(argc, argv);
        const bool directTransportEnabled = DirectTransportEnabled();
        HWND gameWindow = WaitForGameWindow();
        DWORD gamePid = 0; GetWindowThreadProcessId(gameWindow, &gamePid);

        if (!HasExtension(XR_KHR_D3D11_ENABLE_EXTENSION_NAME))
            throw std::runtime_error("runtime lacks XR_KHR_D3D11_enable");
        const char* extensions[]{ XR_KHR_D3D11_ENABLE_EXTENSION_NAME };
        XrInstanceCreateInfo ii{ XR_TYPE_INSTANCE_CREATE_INFO };
        strncpy_s(ii.applicationInfo.applicationName, sizeof(ii.applicationInfo.applicationName),
            "OutRun 2006 True Stereo VR", _TRUNCATE);
        ii.applicationInfo.applicationVersion = 1;
        strncpy_s(ii.applicationInfo.engineName, sizeof(ii.applicationInfo.engineName),
            "OutRun2006Tweaks", _TRUNCATE);
        ii.applicationInfo.engineVersion = 1;
        ii.applicationInfo.apiVersion = XR_CURRENT_API_VERSION;
        ii.enabledExtensionCount = 1; ii.enabledExtensionNames = extensions;
        CheckXr(xrCreateInstance(&ii, &instance), "xrCreateInstance");

        XrInstanceProperties ip{ XR_TYPE_INSTANCE_PROPERTIES };
        CheckXr(xrGetInstanceProperties(instance, &ip), "xrGetInstanceProperties");
        std::cout << "OpenXR runtime: " << ip.runtimeName << " "
                  << XR_VERSION_MAJOR(ip.runtimeVersion) << "."
                  << XR_VERSION_MINOR(ip.runtimeVersion) << "."
                  << XR_VERSION_PATCH(ip.runtimeVersion) << "\n";

        XrSystemGetInfo sgi{ XR_TYPE_SYSTEM_GET_INFO };
        sgi.formFactor = XR_FORM_FACTOR_HEAD_MOUNTED_DISPLAY;
        XrSystemId system = XR_NULL_SYSTEM_ID;
        for (;;)
        {
            const XrResult r = xrGetSystem(instance, &sgi, &system);
            if (r == XR_ERROR_FORM_FACTOR_UNAVAILABLE) { Sleep(1000); continue; }
            CheckXr(r, "xrGetSystem"); break;
        }

        PFN_xrGetD3D11GraphicsRequirementsKHR getReq = nullptr;
        CheckXr(xrGetInstanceProcAddr(instance, "xrGetD3D11GraphicsRequirementsKHR",
            reinterpret_cast<PFN_xrVoidFunction*>(&getReq)), "xrGetInstanceProcAddr");
        XrGraphicsRequirementsD3D11KHR req{ XR_TYPE_GRAPHICS_REQUIREMENTS_D3D11_KHR };
        CheckXr(getReq(instance, system, &req), "xrGetD3D11GraphicsRequirementsKHR");
        D3DObjects d3d = CreateD3D11Device(req);

        XrGraphicsBindingD3D11KHR binding{ XR_TYPE_GRAPHICS_BINDING_D3D11_KHR };
        binding.device = d3d.device;
        XrSessionCreateInfo si{ XR_TYPE_SESSION_CREATE_INFO };
        si.next = &binding; si.systemId = system;
        CheckXr(xrCreateSession(instance, &si, &session), "xrCreateSession");

        XrPosef identity{}; identity.orientation.w = 1;
        XrReferenceSpaceCreateInfo li{ XR_TYPE_REFERENCE_SPACE_CREATE_INFO };
        li.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL; li.poseInReferenceSpace = identity;
        CheckXr(xrCreateReferenceSpace(session, &li, &localSpace), "xrCreateReferenceSpace LOCAL");
        XrReferenceSpaceCreateInfo vi{ XR_TYPE_REFERENCE_SPACE_CREATE_INFO };
        vi.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_VIEW; vi.poseInReferenceSpace = identity;
        CheckXr(xrCreateReferenceSpace(session, &vi, &viewSpace), "xrCreateReferenceSpace VIEW");

        std::uint32_t cc = 0;
        CheckXr(xrEnumerateViewConfigurationViews(instance, system,
            XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, 0, &cc, nullptr),
            "xrEnumerateViewConfigurationViews count");
        if (cc < 2) throw std::runtime_error("runtime has fewer than two stereo views");
        std::vector<XrViewConfigurationView> cv(cc);
        for (auto& c : cv) c = { XR_TYPE_VIEW_CONFIGURATION_VIEW };
        CheckXr(xrEnumerateViewConfigurationViews(instance, system,
            XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, cc, &cc, cv.data()),
            "xrEnumerateViewConfigurationViews list");
        std::array<XrViewConfigurationView, 2> configs{ cv[0], cv[1] };

        SharedWriter shared(req.adapterLuid);
        RenderFrameReader renderFrames;
        StereoCompositor compositor(session, d3d.device, d3d.context, gameWindow,
            configs, directTransportEnabled, renderScale);
        compositor.Initialize();
        ViewHistory viewHistory;
        HostTimings timings;
        const XrEnvironmentBlendMode blend = ChooseBlendMode(instance, system);

        bool running = false, quit = false, exitRequested = false;
        ULONGLONG exitRequestMs = 0;
        XrSessionState state = XR_SESSION_STATE_UNKNOWN;
        OutRunVR::ClientPresentationMode lastPresentation = OutRunVR::PresentationUnknown;
        std::array<XrView, 2> matchedViews{};
        bool matchedStereoValid = false;
        std::uint32_t lastProcessedStereoFrame = 0;
        ULONGLONG lastStereoMatchMs = 0;
        std::array<XrCompositionLayerProjectionView, 2>
            cachedProjectionViews{};
        bool cachedProjectionValid = false;
        ULONGLONG cachedProjectionRenderedMs = 0;
        bool pendingReferenceSpaceChange = false;
        XrTime pendingReferenceSpaceChangeTime = 0;

        while (!quit)
        {
            if (!compositor.GameAlive() && !exitRequested)
            {
                exitRequested = true; exitRequestMs = GetTickCount64();
                OutRunVrR23VerifiedBundle::Invalidate();
                if (session != XR_NULL_HANDLE) xrRequestExitSession(session);
                std::cout << "OutRun exited; requesting OpenXR shutdown.\n";
            }

            XrEventDataBuffer event{ XR_TYPE_EVENT_DATA_BUFFER };
            while (xrPollEvent(instance, &event) == XR_SUCCESS)
            {
                if (event.type == XR_TYPE_EVENT_DATA_SESSION_STATE_CHANGED)
                {
                    auto* e = reinterpret_cast<XrEventDataSessionStateChanged*>(&event);
                    state = e->state;
                    if (state == XR_SESSION_STATE_READY && !running)
                    {
                        XrSessionBeginInfo begin{ XR_TYPE_SESSION_BEGIN_INFO };
                        begin.primaryViewConfigurationType = XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
                        CheckXr(xrBeginSession(session, &begin), "xrBeginSession");
                        running = true;
                    }
                    else if (state == XR_SESSION_STATE_STOPPING && running)
                    {
                        CheckXr(xrEndSession(session), "xrEndSession");
                        running = false; viewHistory.Clear(); matchedStereoValid = false;
                        lastStereoMatchMs = 0; cachedProjectionValid = false;
                        cachedProjectionRenderedMs = 0;
                        compositor.ReferenceSpaceChanged();
                        OutRunVrR23VerifiedBundle::Invalidate();
                        OutRunVR::SharedRenderFrameState rf{};
                        if (renderFrames.Read(rf)) lastProcessedStereoFrame = rf.frameId;
                    }
                    else if (state == XR_SESSION_STATE_EXITING || state == XR_SESSION_STATE_LOSS_PENDING)
                        quit = true;
                }
                else if (event.type == XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING)
                {
                    const auto* e = reinterpret_cast<XrEventDataReferenceSpaceChangePending*>(&event);
                    if (e->referenceSpaceType == XR_REFERENCE_SPACE_TYPE_LOCAL)
                    { pendingReferenceSpaceChange = true; pendingReferenceSpaceChangeTime = e->changeTime; }
                }
                event = { XR_TYPE_EVENT_DATA_BUFFER };
            }

            if (quit) break;
            if (exitRequested && GetTickCount64() - exitRequestMs > 2000) break;
            if (!running) { Sleep(10); continue; }

            XrFrameWaitInfo wi{ XR_TYPE_FRAME_WAIT_INFO };
            XrFrameState fs{ XR_TYPE_FRAME_STATE };
            LARGE_INTEGER ws{}, we{}; QueryPerformanceCounter(&ws);
            CheckXr(xrWaitFrame(session, &wi, &fs), "xrWaitFrame");
            QueryPerformanceCounter(&we); timings.wait.Add(timings.Ms(ws, we));

            if (pendingReferenceSpaceChange &&
                (pendingReferenceSpaceChangeTime == 0 || fs.predictedDisplayTime >= pendingReferenceSpaceChangeTime))
            {
                shared.ReferenceSpaceChanged(); compositor.ReferenceSpaceChanged(); viewHistory.Clear();
                matchedStereoValid = false; cachedProjectionValid = false;
                cachedProjectionRenderedMs = 0;
                OutRunVrR23VerifiedBundle::Invalidate();
                OutRunVR::SharedRenderFrameState rf{};
                lastProcessedStereoFrame = renderFrames.Read(rf) ? rf.frameId : shared.ReadStereoMeta().frame;
                pendingReferenceSpaceChange = false; pendingReferenceSpaceChangeTime = 0;
            }

            XrFrameBeginInfo bi{ XR_TYPE_FRAME_BEGIN_INFO };
            CheckXr(xrBeginFrame(session, &bi), "xrBeginFrame");
            XrSpaceLocation head{ XR_TYPE_SPACE_LOCATION };
            CheckXr(xrLocateSpace(viewSpace, localSpace, fs.predictedDisplayTime, &head), "xrLocateSpace");
            std::array<XrView, 2> views{}; for (auto& v : views) v = { XR_TYPE_VIEW };
            XrViewState vs{ XR_TYPE_VIEW_STATE };
            XrViewLocateInfo vl{ XR_TYPE_VIEW_LOCATE_INFO };
            vl.viewConfigurationType = XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
            vl.displayTime = fs.predictedDisplayTime; vl.space = localSpace;
            std::uint32_t vc = 0;
            CheckXr(xrLocateViews(session, &vl, &vs, 2, &vc, views.data()), "xrLocateViews");

            const std::uint32_t hostSequence = shared.Write(head, views, vc, configs,
                state, vs.viewStateFlags, fs.shouldRender == XR_TRUE, directTransportEnabled,
                compositor.DirectTransportReady(), ip.runtimeName);
            if (directTransportEnabled) shared.ServiceInteropProbe(d3d.device, d3d.context);
            const XrViewStateFlags neededViews = XR_VIEW_STATE_ORIENTATION_VALID_BIT |
                XR_VIEW_STATE_POSITION_VALID_BIT;
            if (vc >= 2 && (vs.viewStateFlags & neededViews) == neededViews)
                viewHistory.Store(hostSequence, views);

            XrFrameEndInfo end{ XR_TYPE_FRAME_END_INFO };
            end.displayTime = fs.predictedDisplayTime; end.environmentBlendMode = blend;
            const XrCompositionLayerBaseHeader* layers[1]{};
            std::array<XrCompositionLayerProjectionView, 2> pv{};
            XrCompositionLayerProjection projection{ XR_TYPE_COMPOSITION_LAYER_PROJECTION };
            XrCompositionLayerQuad quad{ XR_TYPE_COMPOSITION_LAYER_QUAD };

            const auto requestedPresentation = shared.Presentation();
            auto presentation = requestedPresentation;
            const ULONGLONG presentationNow = GetTickCount64();

            // Race-adjacent game states can briefly publish Theater between
            // valid gameplay stereo Presents. Do not tear down a healthy
            // projection immediately: a short debounce prevents the headset
            // from flashing the raw SBS/theater image during stage/state
            // transitions. A real menu still switches normally after 750 ms.
            if (requestedPresentation == OutRunVR::PresentationTheater &&
                lastPresentation == OutRunVR::PresentationGameplay &&
                cachedProjectionValid &&
                presentationNow >= cachedProjectionRenderedMs &&
                presentationNow - cachedProjectionRenderedMs <=
                    R23PresentationDebounceMs)
            {
                presentation = OutRunVR::PresentationGameplay;
                ++R23PresentationGraceFrames;
            }

            if (presentation != lastPresentation)
            {
                compositor.ReferenceSpaceChanged(); matchedStereoValid = false;
                OutRunVrR23VerifiedBundle::Invalidate();
                OutRunVR::SharedRenderFrameState rf{};
                lastProcessedStereoFrame = renderFrames.Read(rf) ? rf.frameId : shared.ReadStereoMeta().frame;
                if (presentation != OutRunVR::PresentationGameplay)
                {
                    cachedProjectionValid = false;
                    cachedProjectionRenderedMs = 0;
                }
                lastPresentation = presentation;
                std::cout << "VR presentation: "
                    << (presentation == OutRunVR::PresentationGameplay ? "true stereo projection" : "LOCAL-fixed theater")
                    << ".\n";
            }

            bool layerReady = false;
            if (fs.shouldRender == XR_TRUE && vc >= 2)
            {
                if (presentation == OutRunVR::PresentationGameplay)
                {
                    bool productionCaptureAttempted = false;
                    bool newStereoCommitted = false;
                    OutRunVR::SharedRenderFrameState before{};
                    const bool have = renderFrames.Read(before);
                    constexpr std::uint32_t need = OutRunVR::RenderFrameStereoComplete |
                        OutRunVR::RenderFrameWorldStereo | OutRunVR::RenderFrameDrawDuplicated |
                        OutRunVR::RenderFrameEffectivePoseValid;
                    if (have && (before.flags & OutRunVR::RenderFramePresentInFlight) == 0 &&
                        before.state == OutRunVR::StereoSbsActive && before.frameId &&
                        before.frameId != lastProcessedStereoFrame && before.sourcePoseSequence &&
                        (before.flags & need) == need)
                    {
                        std::array<XrView, 2> history{};
                        if (viewHistory.Find(before.sourcePoseSequence, history))
                        {
                            const bool directFrame = (before.flags & OutRunVR::RenderFrameDirectGpuTransport) != 0;
                            bool candidateReady = directFrame;
                            CaptureStatus capture{};
                            LARGE_INTEGER cs{}, ce{}; QueryPerformanceCounter(&cs);
                            if (!directFrame)
                            {
                                productionCaptureAttempted = true;
                                capture = R23Capture(compositor, 2);
                                candidateReady = capture.available && QpcAtOrAfter(capture.lastPresentQpc, before.presentQpc);
                            }
                            QueryPerformanceCounter(&ce); timings.capture.Add(timings.Ms(cs, ce));

                            const bool same = candidateReady && R23FrameUnchanged(renderFrames, before);
                            bool committed = false;
                            if (same)
                            {
                                committed = directFrame
                                    ? R23CommitDirectAfterValidation(compositor, before)
                                    : R23CommitClassicAfterValidation(compositor);
                            }

                            if (committed)
                            {
                                if (directFrame) shared.AckDirectFrame(before.frameId);
                                R23CopyMatchedViews(before, matchedViews);
                                matchedStereoValid = true;
                                lastProcessedStereoFrame = before.frameId;
                                lastStereoMatchMs = GetTickCount64();
                                newStereoCommitted = true;
                                OutRunVrR23VerifiedBundle::Publish(before,
                                    directFrame ? OutRunVrR23VerifiedBundle::SourceKind::DirectGpu
                                                : OutRunVrR23VerifiedBundle::SourceKind::ClassicSbs);
                            }
                        }
                    }

                    const ULONGLONG projectionNow = GetTickCount64();
                    const bool grace = matchedStereoValid &&
                        compositor.HasStereoSource() &&
                        projectionNow - lastStereoMatchMs <= StereoGraceMs;
                    const bool cachedHold = cachedProjectionValid &&
                        projectionNow >= cachedProjectionRenderedMs &&
                        projectionNow - cachedProjectionRenderedMs <=
                            R23CachedProjectionHoldMs;

                    LARGE_INTEGER rs{}, re{}; QueryPerformanceCounter(&rs);

                    // Only blit a projection image when the game supplied a new
                    // committed stereo frame (or when no cached projection
                    // exists yet). At 90 Hz HMD / 60 Hz game this removes about
                    // one third of the host-side full-eye blits. Intermediate
                    // XR frames resubmit the last released projection and let
                    // the runtime's normal reprojection handle head motion.
                    if (grace &&
                        (newStereoCommitted || !cachedProjectionValid) &&
                        R23RenderProjection(compositor, matchedViews, pv))
                    {
                        projection.space = localSpace;
                        projection.viewCount = 2;
                        projection.views = pv.data();
                        layers[0] =
                            reinterpret_cast<const XrCompositionLayerBaseHeader*>(
                                &projection);
                        layerReady = true;
                        cachedProjectionViews = pv;
                        cachedProjectionValid = true;
                        cachedProjectionRenderedMs = projectionNow;
                    }
                    else if (cachedProjectionValid && (grace || cachedHold))
                    {
                        projection.space = localSpace;
                        projection.viewCount = 2;
                        projection.views = cachedProjectionViews.data();
                        layers[0] =
                            reinterpret_cast<const XrCompositionLayerBaseHeader*>(
                                &projection);
                        layerReady = true;
                        ++R23CachedProjectionSubmits;

                        if (R23LastCachedProjectionLogMs == 0 ||
                            projectionNow - R23LastCachedProjectionLogMs >=
                                R23CachedProjectionLogIntervalMs)
                        {
                            R23LastCachedProjectionLogMs = projectionNow;
                            std::cout
                                << "[R23 projection-hold] reusing last released stereo projection instead of theater/SBS fallback"
                                << " count=" << R23CachedProjectionSubmits
                                << " newFrame=" << (newStereoCommitted ? 1 : 0)
                                << " grace=" << (grace ? 1 : 0)
                                << " presentationGraceFrames="
                                << R23PresentationGraceFrames
                                << "\n";
                        }
                    }
                    QueryPerformanceCounter(&re);
                    timings.render.Add(timings.Ms(rs, re));

                    // Never submit a zero-layer frame just because Desktop
                    // Duplication missed the stereo grace window. VDXR can show a
                    // solid compositor colour / severe HMD stutter even while the
                    // desktop game keeps running normally.
                    if (!layerReady)
                    {
                        LARGE_INTEGER cs{}, ce{}; QueryPerformanceCounter(&cs);
                        const CaptureStatus fallbackCapture =
                            R23RefreshTheaterFallbackCapture(compositor);
                        QueryPerformanceCounter(&ce); timings.capture.Add(timings.Ms(cs, ce));

                        LARGE_INTEGER frs{}, fre{}; QueryPerformanceCounter(&frs);
                        if (fallbackCapture.available &&
                            R23RenderTheater(compositor, viewSpace, localSpace,
                                fs.predictedDisplayTime, quad))
                        {
                            layers[0] =
                                reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);
                            layerReady = true;
                            ++R23GameplayTheaterFallbacks;
                            const ULONGLONG now = GetTickCount64();
                            if (R23LastGameplayFallbackLogMs == 0 ||
                                now - R23LastGameplayFallbackLogMs >= 5000)
                            {
                                R23LastGameplayFallbackLogMs = now;
                                std::cout
                                    << "[R23 fallback] no reusable stereo projection remained; using LOCAL-fixed theater until fresh stereo returns"
                                    << " count=" << R23GameplayTheaterFallbacks
                                    << " productionAttempted=" << (productionCaptureAttempted ? 1 : 0)
                                    << "\n";
                            }
                        }
                        QueryPerformanceCounter(&fre); timings.render.Add(timings.Ms(frs, fre));
                    }
                }
                else
                {
                    LARGE_INTEGER cs{}, ce{}; QueryPerformanceCounter(&cs);
                    const CaptureStatus capture = R23Capture(compositor);
                    QueryPerformanceCounter(&ce); timings.capture.Add(timings.Ms(cs, ce));
                    LARGE_INTEGER rs{}, re{}; QueryPerformanceCounter(&rs);
                    if (capture.available && R23RenderTheater(compositor, viewSpace,
                        localSpace, fs.predictedDisplayTime, quad))
                    {
                        layers[0] = reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);
                        layerReady = true;
                    }
                    QueryPerformanceCounter(&re); timings.render.Add(timings.Ms(rs, re));
                }
            }

            end.layerCount = layerReady ? 1 : 0; end.layers = layerReady ? layers : nullptr;
            LARGE_INTEGER es{}, ee{}; QueryPerformanceCounter(&es);
            const XrResult endResult = xrEndFrame(session, &end);
            R23Pixels.NoteFinalSubmission();
            CheckXr(endResult, "xrEndFrame");
            QueryPerformanceCounter(&ee); timings.end.Add(timings.Ms(es, ee)); timings.MaybeLog();
        }

        OutRunVrR23VerifiedBundle::Invalidate();
        compositor.Shutdown();
        if (viewSpace != XR_NULL_HANDLE) xrDestroySpace(viewSpace);
        if (localSpace != XR_NULL_HANDLE) xrDestroySpace(localSpace);
        if (session != XR_NULL_HANDLE) xrDestroySession(session);
        if (instance != XR_NULL_HANDLE) xrDestroyInstance(instance);
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << "OutRun VR host error: " << e.what() << "\n";
        OutRunVrR23VerifiedBundle::Invalidate();
        if (viewSpace != XR_NULL_HANDLE) xrDestroySpace(viewSpace);
        if (localSpace != XR_NULL_HANDLE) xrDestroySpace(localSpace);
        if (session != XR_NULL_HANDLE) xrDestroySession(session);
        if (instance != XR_NULL_HANDLE) xrDestroyInstance(instance);
        return 1;
    }
}
