#pragma once

// R22 non-blocking production-capture diagnostics.
//
// R19 publishes the production StereoCompositor source after its only Desktop
// Duplication ReleaseFrame. R22 keeps that single-owner design, then samples
// several 1x1 points inside the actual game UV into a reusable staging/query
// ring. A later capture polls the query with DONOTFLUSH and maps only a completed
// staging texture; diagnostic scheduling itself never waits for the GPU.

#include "sbs_capture_override.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>

namespace OutRunVrR22CaptureDiagnostics
{
    inline constexpr const char* BuildId =
        "R22-async-gameuv-capture-diagnostic-20260916";
    inline constexpr UINT SampleCount = 6;
    inline constexpr ULONGLONG ScheduleIntervalMs = 5000;

    struct Slot
    {
        ID3D11Texture2D* staging = nullptr;
        ID3D11Query* query = nullptr;
        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        bool pending = false;
        OutRunVrSbsCaptureOverride::UvRect uv{};
        std::array<POINT, SampleCount> sourcePoints{};
    };

    inline std::array<Slot, 2> Slots{};
    inline std::uint32_t NextSlot = 0;
    inline ULONGLONG LastScheduleMs = 0;
    inline bool FirstActiveLogged = false;

    template <typename T>
    inline void ReleaseCom(T*& value) noexcept
    {
        if (value)
        {
            value->Release();
            value = nullptr;
        }
    }

    inline float HalfToFloat(std::uint16_t value) noexcept
    {
        const std::uint32_t sign = static_cast<std::uint32_t>(value & 0x8000u) << 16;
        std::uint32_t exponent = (value >> 10) & 0x1Fu;
        std::uint32_t mantissa = value & 0x03FFu;
        std::uint32_t bits = 0;
        if (exponent == 0)
        {
            if (mantissa == 0)
                bits = sign;
            else
            {
                int unbiased = -14;
                while ((mantissa & 0x0400u) == 0)
                {
                    mantissa <<= 1;
                    --unbiased;
                }
                mantissa &= 0x03FFu;
                bits = sign |
                    (static_cast<std::uint32_t>(unbiased + 127) << 23) |
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

    inline void ResetSlot(Slot& slot) noexcept
    {
        ReleaseCom(slot.query);
        ReleaseCom(slot.staging);
        slot = {};
    }

    inline bool EnsureSlot(Slot& slot, DXGI_FORMAT format) noexcept
    {
        using namespace OutRunVrFinalTest;
        if (!Device)
            return false;
        if (slot.staging && slot.query && slot.format == format)
            return true;

        ResetSlot(slot);
        D3D11_TEXTURE2D_DESC desc{};
        desc.Width = SampleCount;
        desc.Height = 1;
        desc.MipLevels = 1;
        desc.ArraySize = 1;
        desc.Format = format;
        desc.SampleDesc.Count = 1;
        desc.Usage = D3D11_USAGE_STAGING;
        desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        const HRESULT textureHr = Device->CreateTexture2D(
            &desc, nullptr, &slot.staging);
        if (FAILED(textureHr) || !slot.staging)
        {
            std::cerr << "[R22 capture-async] staging create failed hr=0x"
                      << std::hex << static_cast<unsigned long>(textureHr)
                      << std::dec << "\n";
            ResetSlot(slot);
            return false;
        }

        D3D11_QUERY_DESC queryDesc{};
        queryDesc.Query = D3D11_QUERY_EVENT;
        const HRESULT queryHr = Device->CreateQuery(&queryDesc, &slot.query);
        if (FAILED(queryHr) || !slot.query)
        {
            std::cerr << "[R22 capture-async] query create failed hr=0x"
                      << std::hex << static_cast<unsigned long>(queryHr)
                      << std::dec << "\n";
            ResetSlot(slot);
            return false;
        }
        slot.format = format;
        return true;
    }

    inline void PollSlot(Slot& slot) noexcept
    {
        using namespace OutRunVrFinalTest;
        if (!slot.pending || !slot.query || !slot.staging || !Context)
            return;

        const HRESULT ready = Context->GetData(
            slot.query, nullptr, 0, D3D11_ASYNC_GETDATA_DONOTFLUSH);
        if (ready == S_FALSE)
            return;
        if (FAILED(ready))
        {
            std::cerr << "[R22 capture-async] query poll failed hr=0x"
                      << std::hex << static_cast<unsigned long>(ready)
                      << std::dec << "\n";
            slot.pending = false;
            return;
        }

        D3D11_MAPPED_SUBRESOURCE mapped{};
        const HRESULT mapHr = Context->Map(
            slot.staging, 0, D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
        if (mapHr == DXGI_ERROR_WAS_STILL_DRAWING)
            return;
        if (FAILED(mapHr) || !mapped.pData)
        {
            std::cerr << "[R22 capture-async] completed staging Map failed hr=0x"
                      << std::hex << static_cast<unsigned long>(mapHr)
                      << std::dec << "\n";
            slot.pending = false;
            return;
        }

        std::cout << "[R22 capture-async] build=" << BuildId
                  << " fmt=" << static_cast<int>(slot.format)
                  << " uv=[" << slot.uv.x << "," << slot.uv.y << ","
                  << slot.uv.w << "," << slot.uv.h << "]";

        const auto* row = static_cast<const std::uint8_t*>(mapped.pData);
        for (UINT i = 0; i < SampleCount; ++i)
        {
            float rgb[3]{};
            bool finite = true;
            if (slot.format == DXGI_FORMAT_B8G8R8A8_UNORM)
            {
                const auto* px = row + static_cast<std::size_t>(i) * 4;
                rgb[0] = static_cast<float>(px[2]) / 255.0f;
                rgb[1] = static_cast<float>(px[1]) / 255.0f;
                rgb[2] = static_cast<float>(px[0]) / 255.0f;
            }
            else
            {
                const auto* px = reinterpret_cast<const std::uint16_t*>(
                    row + static_cast<std::size_t>(i) * 8);
                rgb[0] = HalfToFloat(px[0]);
                rgb[1] = HalfToFloat(px[1]);
                rgb[2] = HalfToFloat(px[2]);
            }
            finite = std::isfinite(rgb[0]) &&
                std::isfinite(rgb[1]) && std::isfinite(rgb[2]);
            std::cout << " p" << i << "@" << slot.sourcePoints[i].x
                      << "," << slot.sourcePoints[i].y << "=";
            if (finite)
                std::cout << rgb[0] << "," << rgb[1] << "," << rgb[2];
            else
                std::cout << "nonfinite";
        }
        std::cout << "\n";
        Context->Unmap(slot.staging, 0);
        slot.pending = false;
    }

    inline bool ScheduleSlot(Slot& slot) noexcept
    {
        using namespace OutRunVrFinalTest;
        using namespace OutRunVrSbsCaptureOverride;
        if (!Context || !Source || !SourceWidth || !SourceHeight || slot.pending)
            return false;
        if (SourceFormat != DXGI_FORMAT_B8G8R8A8_UNORM &&
            SourceFormat != DXGI_FORMAT_R16G16B16A16_FLOAT)
            return false;
        if (!EnsureSlot(slot, SourceFormat))
            return false;

        UvRect uv{};
        if (!GetGameUv(uv))
            return false;
        slot.uv = uv;

        constexpr float points[SampleCount][2] = {
            { 0.25f, 0.50f }, // left-eye/SBS half center
            { 0.75f, 0.50f }, // right-eye/SBS half center
            { 0.10f, 0.15f },
            { 0.90f, 0.15f },
            { 0.10f, 0.85f },
            { 0.90f, 0.85f }
        };
        for (UINT i = 0; i < SampleCount; ++i)
        {
            const float u = std::clamp(uv.x + uv.w * points[i][0], 0.0f, 0.999999f);
            const float v = std::clamp(uv.y + uv.h * points[i][1], 0.0f, 0.999999f);
            const UINT sx = std::min<UINT>(
                SourceWidth - 1, static_cast<UINT>(u * SourceWidth));
            const UINT sy = std::min<UINT>(
                SourceHeight - 1, static_cast<UINT>(v * SourceHeight));
            slot.sourcePoints[i] = {
                static_cast<LONG>(sx), static_cast<LONG>(sy) };
            D3D11_BOX box{ sx, sy, 0, sx + 1, sy + 1, 1 };
            Context->CopySubresourceRegion(
                slot.staging, 0, i, 0, 0, Source, 0, &box);
        }
        Context->End(slot.query);
        slot.pending = true;
        return true;
    }

    inline bool PublishProductionCaptureR22(ID3D11Texture2D* productionSource,
        const RECT& outputDesktop, HMONITOR monitor, float sdrWhiteScale,
        std::int64_t lastPresentQpc) noexcept
    {
        const bool published =
            OutRunVrSbsCaptureOverride::PublishProductionCapture(
                productionSource, outputDesktop, monitor, sdrWhiteScale,
                lastPresentQpc);

        for (auto& slot : Slots)
            PollSlot(slot);

        if (published)
        {
            if (!FirstActiveLogged)
            {
                FirstActiveLogged = true;
                std::cerr
                    << "[R22 capture-async] non-blocking game-UV source sampling ACTIVE; "
                       "left/right centers + distributed points, two-slot staging/query ring\n";
            }
            const ULONGLONG now = GetTickCount64();
            if (!LastScheduleMs || now - LastScheduleMs >= ScheduleIntervalMs)
            {
                Slot& slot = Slots[NextSlot++ % Slots.size()];
                if (!slot.pending && ScheduleSlot(slot))
                    LastScheduleMs = now;
            }
        }
        return published;
    }
}

// Replace only the instrumentation appended by R19's ReleaseFrame macro. The
// actual IDXGIOutputDuplication::ReleaseFrame remains the original call and is
// still executed exactly once by StereoCompositor::Capture().
#ifdef ReleaseFrame
#undef ReleaseFrame
#endif
#define ReleaseFrame() ReleaseFrame(); \
    OutRunVrR22CaptureDiagnostics::PublishProductionCaptureR22( \
        copied ? source_ : nullptr, outputDesktop_, targetMonitor_, sdrWhiteScale_, \
        fi.LastPresentTime.QuadPart)
