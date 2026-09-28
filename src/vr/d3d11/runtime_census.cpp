#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "runtime_census.hpp"

#include <array>
#include <atomic>
#include <cstdint>

#include <spdlog/spdlog.h>

#include "pipeline_translation.hpp"
#include "state_translation.hpp"
#include "vr/core/d3d9_draw_state.hpp"

namespace outrun::vr::dx11
{
    namespace
    {
        constexpr std::uint32_t SampleStride = 64u;
        constexpr std::size_t UnsupportedBitCount = 12;

        std::atomic<int> EnabledCache{-1};
        std::atomic<std::uint64_t> Samples{0};
        std::atomic<std::uint64_t> ExactSamples{0};
        std::atomic<std::uint64_t> FixedFunctionSamples{0};
        std::atomic<std::uint64_t> ProgrammableSamples{0};
        std::atomic<std::uint64_t> UnsupportedTopologySamples{0};
        std::array<std::atomic<std::uint64_t>, UnsupportedBitCount>
            UnsupportedCounts{};
        std::atomic<ULONGLONG> LastLogMs{0};

        bool census_enabled() noexcept
        {
            int cached = EnabledCache.load(std::memory_order_acquire);
            if (cached >= 0)
                return cached != 0;

            char value[8]{};
            const DWORD length = GetEnvironmentVariableA(
                "OUTRUN_VR_DX11_CENSUS", value,
                static_cast<DWORD>(sizeof(value)));
            const bool enabled =
                length > 0 && length < sizeof(value) && value[0] == '1';
            EnabledCache.store(enabled ? 1 : 0, std::memory_order_release);
            if (enabled)
                spdlog::info(
                    "VR DX11 R72 census ACTIVE: passive 1/{} draw sampling; native draw routing remains disabled",
                    SampleStride);
            return enabled;
        }

        void maybe_log() noexcept
        {
            const ULONGLONG now = GetTickCount64();
            ULONGLONG last = LastLogMs.load(std::memory_order_acquire);
            if (now - last < 5000)
                return;
            if (!LastLogMs.compare_exchange_strong(
                    last, now, std::memory_order_acq_rel,
                    std::memory_order_acquire))
                return;

            std::array<std::uint64_t, UnsupportedBitCount> unsupported{};
            for (std::size_t i = 0; i < UnsupportedBitCount; ++i)
                unsupported[i] =
                    UnsupportedCounts[i].load(std::memory_order_relaxed);

            spdlog::info(
                "VR DX11 R72 census: samples={} exact={} fixedFn={} programmable={} topologyUnsupported={} unsupported[incomplete={},wbuffer={},sepAlpha={},alphaTest={},stencil={},fog={},lighting={},srgb={},fill={},blend={},depthCmp={},cull={}]",
                Samples.load(std::memory_order_relaxed),
                ExactSamples.load(std::memory_order_relaxed),
                FixedFunctionSamples.load(std::memory_order_relaxed),
                ProgrammableSamples.load(std::memory_order_relaxed),
                UnsupportedTopologySamples.load(std::memory_order_relaxed),
                unsupported[0], unsupported[1], unsupported[2], unsupported[3],
                unsupported[4], unsupported[5], unsupported[6], unsupported[7],
                unsupported[8], unsupported[9], unsupported[10], unsupported[11]);
        }

        void note_unsupported(std::uint32_t mask) noexcept
        {
            for (std::size_t bit = 0; bit < UnsupportedBitCount; ++bit)
            {
                if ((mask & (1u << bit)) != 0)
                    UnsupportedCounts[bit].fetch_add(
                        1, std::memory_order_relaxed);
            }
        }
    }

    void observe_source_draw(
        IDirect3DDevice9* device,
        D3DPRIMITIVETYPE primitive) noexcept
    {
        if (!device || !census_enabled())
            return;

        thread_local std::uint32_t stride = 0;
        if ((++stride % SampleStride) != 0)
            return;

        OutRunVR::DrawState::RenderStateSnapshot source{};
        const bool captured =
            OutRunVRStereo::CaptureTrackedRenderStateSnapshot(device, source);
        const auto translated = translate_pipeline(source);
        const auto topology = translate_primitive(primitive);

        Samples.fetch_add(1, std::memory_order_relaxed);
        std::uint32_t unsupported = translated.unsupported;
        if (!captured)
            unsupported |= PipelineUnsupportedIncompleteSnapshot;
        note_unsupported(unsupported);

        if (!topology.exact)
            UnsupportedTopologySamples.fetch_add(1, std::memory_order_relaxed);

        IDirect3DVertexShader9* vs = nullptr;
        IDirect3DPixelShader9* ps = nullptr;
        const bool vsOk = SUCCEEDED(device->GetVertexShader(&vs));
        const bool psOk = SUCCEEDED(device->GetPixelShader(&ps));
        const bool fixedFunction =
            (!vsOk || vs == nullptr) && (!psOk || ps == nullptr);
        if (vs) vs->Release();
        if (ps) ps->Release();

        if (fixedFunction)
            FixedFunctionSamples.fetch_add(1, std::memory_order_relaxed);
        else
            ProgrammableSamples.fetch_add(1, std::memory_order_relaxed);

        if (unsupported == PipelineUnsupportedNone && topology.exact)
            ExactSamples.fetch_add(1, std::memory_order_relaxed);

        maybe_log();
    }
}
