// R26/R27 tracked-occlusion + world-effect correction overlay.
//
// R23 remains the recovery/baseline authority. R26 keeps proven write-free
// D3D9 occlusion-query proxy draws single-execution without poisoning the whole
// Present. R27 also removes R13's draw-time shader-identity masking for a
// perspective world effect whose c64 upload is now handled by the verified
// per-eye WVP path. Orthographic UI and auxiliary passes are untouched.
//
// MRT hazards, query tracking failures, and occlusion draws that may write color,
// depth, or stencil remain fail-closed through the existing R13/R23 chain.

#include "stereo_renderer_r23.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R26DrawPrimitiveR23Hook{};
        SafetyHookInline R26DrawIndexedPrimitiveR23Hook{};
        SafetyHookInline R26DrawPrimitiveUPR23Hook{};
        SafetyHookInline R26DrawIndexedPrimitiveUPR23Hook{};
        SafetyHookInline R27PresentR23Hook{};

        // Lower-layer correction hooks: these intercept R13 only after R23/R22
        // have already performed top-level accounting and safety checks.
        SafetyHookInline R27DrawPrimitiveR13Hook{};
        SafetyHookInline R27DrawIndexedPrimitiveR13Hook{};
        SafetyHookInline R27DrawPrimitiveUPR13Hook{};
        SafetyHookInline R27DrawIndexedPrimitiveUPR13Hook{};

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R26InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        std::uint64_t R26TrackedOcclusionSingleExec = 0;
        std::uint64_t R26OcclusionWriteRejects = 0;
        std::uint64_t R27WorldEffectDraws = 0;
        std::uint64_t R27EffectStateResyncs = 0;
        std::uint64_t R27LastEffectStateSyncDrawSerial = 0;
        std::uint64_t R27EffectStateSyncEpoch = ~std::uint64_t{0};
        bool R26FirstTrackedOcclusionLogged = false;
        bool R26FirstOcclusionWriteRejectLogged = false;
        bool R27FirstWorldEffectLogged = false;

        LARGE_INTEGER R27PerfFrequency{};
        ULONGLONG R27PerfLastLogMs = 0;
        double R27PresentTotalMs = 0.0;
        double R27PresentMaxMs = 0.0;
        std::uint64_t R27PresentSamples = 0;
        std::uint64_t R27PerfLastDrawSerial = 0;
        std::uint64_t R27PerfLastPresentSamples = 0;

        bool R26TrackedOcclusionNeedsSingleExecution(
            IDirect3DDevice9* device) noexcept
        {
            if (!IsGameDevice(device) || InternalStereoPass ||
                !TargetIsBackBuffer())
                return false;

            if (AnyAuxRenderTargetActive() || R13ForceMonoShadow ||
                OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire))
                return false;

            if (!StereoWanted() || !R9StereoSeeded)
                return false;

            return ActiveOcclusionQueries.load(std::memory_order_acquire) > 0;
        }

        bool R26TrackedOcclusionDrawIsWriteFree(
            IDirect3DDevice9* device) noexcept
        {
            if (!device)
                return false;

            DWORD colorWrite = 0xFFFFFFFFu;
            DWORD zWrite = TRUE;
            DWORD stencilEnable = FALSE;
            DWORD stencilWriteMask = 0xFFFFFFFFu;
            if (FAILED(device->GetRenderState(D3DRS_COLORWRITEENABLE, &colorWrite)) ||
                FAILED(device->GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)) ||
                FAILED(device->GetRenderState(D3DRS_STENCILENABLE, &stencilEnable)) ||
                FAILED(device->GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)))
                return false;

            return colorWrite == 0 && zWrite == FALSE &&
                (stencilEnable == FALSE || stencilWriteMask == 0);
        }

        template <typename ActualDraw, typename NormalR23Draw>
        HRESULT R26GuardTrackedOcclusion(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, NormalR23Draw&& normalR23Draw,
            const char* site)
        {
            if (!R26TrackedOcclusionNeedsSingleExecution(device))
                return normalR23Draw();

            // Only a proven query-only proxy may bypass replay. A regular scene
            // draw bracketed by an occlusion query can still write visible color
            // or depth and therefore must take the existing fail-closed path.
            if (!R26TrackedOcclusionDrawIsWriteFree(device))
            {
                ++R26OcclusionWriteRejects;
                if (!R26FirstOcclusionWriteRejectLogged)
                {
                    R26FirstOcclusionWriteRejectLogged = true;
                    spdlog::warn(
                        "VR R27 occlusion: active query draw can write color/depth/stencil (or state is unreadable); keeping fail-closed replay policy");
                }
                return normalR23Draw();
            }

            // R23 normally owns this top-level boundary. Because this one draw
            // intentionally bypasses the R23->R22->R13->R9 replay chain, keep
            // its draw serial/live-state accounting explicitly in sync.
            R23BeforeTopLevelDraw(device);

            ++R26TrackedOcclusionSingleExec;
            ++OcclusionStereoRejects;
            if (!R26FirstTrackedOcclusionLogged)
            {
                R26FirstTrackedOcclusionLogged = true;
                spdlog::info(
                    "VR R27 occlusion: proven write-free active-query proxy executes once on the real game target; stereo Present remains eligible");
            }

            const HRESULT hr = actualDraw();
            if (FAILED(hr))
                R9Poison(OutRunVR::StereoFailureLeftDrawFailed, site, hr);
            return hr;
        }

        bool R27ShouldBypassLegacyZeroDisparity(
            IDirect3DDevice9* device) noexcept
        {
            if (!IsGameDevice(device) || InternalStereoPass ||
                !TargetIsBackBuffer() || !StereoWanted() || !R9StereoSeeded)
                return false;
            if (AnyAuxRenderTargetActive() || R13ForceMonoShadow ||
                OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire) ||
                ActiveOcclusionQueries.load(std::memory_order_acquire) > 0)
                return false;
            if (!R13DrawTimeFragileEffectNeedsZeroDisparity(device))
                return false;

            // StateBlock::Apply can bypass tracked setters. Resynchronize live
            // viewport/scissor at least once per Present and periodically during
            // effect-heavy passes, without restoring the old per-draw query cost.
            if (R27EffectStateSyncEpoch != PresentEpoch ||
                R23GameDrawSerial - R27LastEffectStateSyncDrawSerial >= 256)
            {
                R22ScissorSnapshot actual{};
                if (!R23CaptureActualGameState(
                        device, actual, "R27EffectDraw", true))
                    return false;
                R27EffectStateSyncEpoch = PresentEpoch;
                R27LastEffectStateSyncDrawSerial = R23GameDrawSerial;
                ++R27EffectStateResyncs;
            }
            return true;
        }

        template <typename R9Draw, typename LegacyR13Draw>
        HRESULT R27GuardWorldEffect(IDirect3DDevice9* device,
            R9Draw&& r9Draw, LegacyR13Draw&& legacyR13Draw)
        {
            if (!R27ShouldBypassLegacyZeroDisparity(device))
                return legacyR13Draw();

            ++R27WorldEffectDraws;
            if (!R27FirstWorldEffectLogged)
            {
                R27FirstWorldEffectLogged = true;
                spdlog::info(
                    "VR R27 EFFECT: legacy alpha/billboard/shadow shader-identity mask bypassed; perspective effect draw keeps verified per-eye world WVP");
            }
            return r9Draw();
        }

        HRESULT __stdcall DrawPrimitiveDestR27Effect(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto world = [&]() {
                return R13DrawPrimitiveR9Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto legacy = [&]() {
                return R27DrawPrimitiveR13Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R27GuardWorldEffect(device, world, legacy);
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR27Effect(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            auto world = [&]() {
                return R13DrawIndexedPrimitiveR9Hook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            auto legacy = [&]() {
                return R27DrawIndexedPrimitiveR13Hook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            return R27GuardWorldEffect(device, world, legacy);
        }

        HRESULT __stdcall DrawPrimitiveUPDestR27Effect(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT primitiveCount, const void* data, UINT stride)
        {
            auto world = [&]() {
                return R13DrawPrimitiveUPR9Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto legacy = [&]() {
                return R27DrawPrimitiveUPR13Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R27GuardWorldEffect(device, world, legacy);
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR27Effect(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            auto world = [&]() {
                return R13DrawIndexedPrimitiveUPR9Hook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            auto legacy = [&]() {
                return R27DrawIndexedPrimitiveUPR13Hook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            return R27GuardWorldEffect(device, world, legacy);
        }

        HRESULT __stdcall DrawPrimitiveDestR26(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto normal = [&]() {
                return R26DrawPrimitiveR23Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R26GuardTrackedOcclusion(
                device, actual, normal, "R27/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR26(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, INT baseVertexIndex, UINT minVertexIndex,
            UINT numVertices, UINT startIndex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            auto normal = [&]() {
                return R26DrawIndexedPrimitiveR23Hook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            return R26GuardTrackedOcclusion(
                device, actual, normal, "R27/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR26(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT primitiveCount, const void* data,
            UINT stride)
        {
            auto actual = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto normal = [&]() {
                return R26DrawPrimitiveUPR23Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R26GuardTrackedOcclusion(
                device, actual, normal, "R27/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR26(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            auto normal = [&]() {
                return R26DrawIndexedPrimitiveUPR23Hook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            return R26GuardTrackedOcclusion(
                device, actual, normal, "R27/DrawIndexedPrimitiveUP");
        }

        HRESULT __stdcall PresentDestR27(IDirect3DDevice9* device,
            const RECT* sourceRect, const RECT* destRect,
            HWND destWindowOverride, const RGNDATA* dirtyRegion)
        {
            LARGE_INTEGER begin{}, end{};
            QueryPerformanceCounter(&begin);
            const HRESULT hr = R27PresentR23Hook.stdcall<HRESULT>(device,
                sourceRect, destRect, destWindowOverride, dirtyRegion);
            QueryPerformanceCounter(&end);

            if (R27PerfFrequency.QuadPart <= 0)
                QueryPerformanceFrequency(&R27PerfFrequency);
            if (R27PerfFrequency.QuadPart > 0)
            {
                const double ms = static_cast<double>(end.QuadPart - begin.QuadPart) *
                    1000.0 / static_cast<double>(R27PerfFrequency.QuadPart);
                R27PresentTotalMs += ms;
                if (ms > R27PresentMaxMs) R27PresentMaxMs = ms;
                ++R27PresentSamples;
            }

            if (Settings::VRTelemetry)
            {
                const ULONGLONG now = GetTickCount64();
                if (R27PerfLastLogMs == 0 || now - R27PerfLastLogMs >= 5000)
                {
                    const std::uint64_t sampleDelta =
                        R27PresentSamples - R27PerfLastPresentSamples;
                    const std::uint64_t drawDelta =
                        R23GameDrawSerial - R27PerfLastDrawSerial;
                    const double avg = R27PresentSamples ?
                        R27PresentTotalMs / static_cast<double>(R27PresentSamples) : 0.0;
                    const double drawsPerPresent = sampleDelta ?
                        static_cast<double>(drawDelta) / static_cast<double>(sampleDelta) : 0.0;
                    spdlog::info(
                        "VR R27 PERF: lower-Present avgMs={:.3f} maxMs={:.3f} drawsPerPresent={:.1f} worldEffectDraws={} effectStateResync={} occSingle={} occWriteReject={}",
                        avg, R27PresentMaxMs, drawsPerPresent,
                        R27WorldEffectDraws, R27EffectStateResyncs,
                        R26TrackedOcclusionSingleExec, R26OcclusionWriteRejects);
                    R27PerfLastLogMs = now;
                    R27PerfLastDrawSerial = R23GameDrawSerial;
                    R27PerfLastPresentSamples = R27PresentSamples;
                }
            }
            return hr;
        }

        void R26RollbackHooks() noexcept
        {
            R27PresentR23Hook = {};
            R27DrawIndexedPrimitiveUPR13Hook = {};
            R27DrawPrimitiveUPR13Hook = {};
            R27DrawIndexedPrimitiveR13Hook = {};
            R27DrawPrimitiveR13Hook = {};
            R26DrawIndexedPrimitiveUPR23Hook = {};
            R26DrawPrimitiveUPR23Hook = {};
            R26DrawIndexedPrimitiveR23Hook = {};
            R26DrawPrimitiveR23Hook = {};
        }

        bool R26EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R27DrawPrimitiveR13Hook,
                &R27DrawIndexedPrimitiveR13Hook,
                &R27DrawPrimitiveUPR13Hook,
                &R27DrawIndexedPrimitiveUPR13Hook,
                &R26DrawPrimitiveR23Hook,
                &R26DrawIndexedPrimitiveR23Hook,
                &R26DrawPrimitiveUPR23Hook,
                &R26DrawIndexedPrimitiveUPR23Hook,
                &R27PresentR23Hook
            };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                    return false;
            }
            return true;
        }

        DWORD WINAPI R26OcclusionInstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R26InstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r23 = R23InstallState.load(std::memory_order_acquire);
                if (r23 == State::Failed)
                {
                    R26InstallState.store(State::Failed, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVROcclusionR26", false);
                    spdlog::error(
                        "VR R26/R27: R23 prerequisite failed; correction overlay not installed");
                    return 0;
                }

                if (r23 == State::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;

                    R27DrawPrimitiveR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR13),
                        DrawPrimitiveDestR27Effect, disabled);
                    R27DrawIndexedPrimitiveR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR13),
                        DrawIndexedPrimitiveDestR27Effect, disabled);
                    R27DrawPrimitiveUPR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR13),
                        DrawPrimitiveUPDestR27Effect, disabled);
                    R27DrawIndexedPrimitiveUPR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR13),
                        DrawIndexedPrimitiveUPDestR27Effect, disabled);

                    R26DrawPrimitiveR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR23),
                        DrawPrimitiveDestR26, disabled);
                    R26DrawIndexedPrimitiveR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR23),
                        DrawIndexedPrimitiveDestR26, disabled);
                    R26DrawPrimitiveUPR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR23),
                        DrawPrimitiveUPDestR26, disabled);
                    R26DrawIndexedPrimitiveUPR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR23),
                        DrawIndexedPrimitiveUPDestR26, disabled);
                    R27PresentR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&PresentDestR23),
                        PresentDestR27, disabled);

                    if (!R26EnableHooks())
                    {
                        R26RollbackHooks();
                        R26InstallState.store(State::Failed, std::memory_order_release);
                        HookManager::ReportAsyncResult("OpenXRVROcclusionR26", false);
                        spdlog::error(
                            "VR R26/R27: disabled-first correction transaction failed; R23 remains active");
                        return 0;
                    }

                    R26InstallState.store(State::Ready, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVROcclusionR26", true);
                    spdlog::info(
                        "VR R26/R27 GAME: world-effect WVP/draw correction + write-free occlusion single-execution + bounded live-state resync ACTIVE");
                    return 0;
                }
                Sleep(25);
            }

            R26InstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVROcclusionR26", false);
            spdlog::error(
                "VR R26/R27: timed out waiting for R23; correction overlay not installed");
            return 0;
        }

        class VROcclusionR26Hook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVROcclusionR26";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R26InstallState.store(State::Pending, std::memory_order_release);
                HANDLE thread = CreateThread(nullptr, 0,
                    R26OcclusionInstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R26InstallState.store(State::Failed, std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VROcclusionR26Hook instance;
        };

        VROcclusionR26Hook VROcclusionR26Hook::instance;
    }
}
