// R32 review-consolidation overlay.
//
// This is the final game-side TU. It keeps R31/R29/R14 correctness policy and
// applies the two 10-pass reviews without weakening recovery behavior:
//  * Reset rearms the R29 mono-safety epoch relative to the reset Present epoch;
//  * render-state snapshot failures fail closed to stock-WVP zero disparity;
//  * verified steady LEFT/RIGHT WVP uploads use one c64..c67 batch call;
//  * unreliable StateBlock mode live-validates the state R32 actually consumes
//    instead of discarding every lower cache on a successfully handled world draw;
//  * D3D9Ex direct transport caches the verified host/LUID identity and bounds
//    the producer event-query stall to a 2 ms budget with one explicit FLUSH;
//  * five-second R32 telemetry reports deltas for counters that R31 logged as
//    lifetime totals.

#include "r32_policy.hpp"
#include "stereo_renderer_r31.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R32ResetR13Hook{};
        SafetyHookInline R32ResolveDirectR13Hook{};
        SafetyHookInline R32PresentR13Hook{};
        SafetyHookInline R32DrawPrimitiveR31Hook{};
        SafetyHookInline R32DrawIndexedPrimitiveR31Hook{};
        SafetyHookInline R32DrawPrimitiveUPR31Hook{};
        SafetyHookInline R32DrawIndexedPrimitiveUPR31Hook{};

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R32InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        std::uint64_t R32BatchWvpUploads = 0;
        std::uint64_t R32BatchWvpFailures = 0;
        std::uint64_t R32StateSnapshotFailures = 0;
        std::uint64_t R32FailClosedZeroDisparityDraws = 0;
        std::uint64_t R32ResetEpochRearms = 0;
        std::uint64_t R32DirectProbeCacheHits = 0;
        std::uint64_t R32DirectFenceSuccess = 0;
        std::uint64_t R32DirectFenceBudgetFallbacks = 0;
        std::uint64_t R32DirectIdentityInvalidations = 0;
        bool R32FirstStateSnapshotFailureLogged = false;
        bool R32FirstBatchWvpLogged = false;
        bool R32FirstFenceBudgetLogged = false;
        bool R32FirstResetRearmLogged = false;

        std::uint32_t R32DirectHostPid = 0;
        std::uint32_t R32DirectHostLuidLow = 0;
        std::uint32_t R32DirectHostLuidHigh = 0;

        struct R32CounterSnapshot
        {
            ULONGLONG lastLogMs = 0;
            std::uint64_t liveWvp = 0;
            std::uint64_t liveReject = 0;
            std::uint64_t stateRecord = 0;
            std::uint64_t stateApply = 0;
            std::uint64_t batch = 0;
            std::uint64_t batchFail = 0;
            std::uint64_t stateFail = 0;
            std::uint64_t zeroFallback = 0;
            std::uint64_t directCache = 0;
            std::uint64_t directFenceOk = 0;
            std::uint64_t directFenceFallback = 0;
            std::uint64_t directBackpressure = 0;
            std::uint64_t resetRearm = 0;
        };
        R32CounterSnapshot R32Counters{};

        struct R32EffectSnapshot
        {
            DWORD alphaBlend = FALSE;
            DWORD alphaTest = FALSE;
            DWORD zWrite = TRUE;
            DWORD cullMode = D3DCULL_CCW;
        };

        bool R32ReadEffectSnapshot(IDirect3DDevice9* device,
            R32EffectSnapshot& out) noexcept
        {
            if (!device)
                return false;
            const bool ok =
                SUCCEEDED(device->GetRenderState(
                    D3DRS_ALPHABLENDENABLE, &out.alphaBlend)) &&
                SUCCEEDED(device->GetRenderState(
                    D3DRS_ALPHATESTENABLE, &out.alphaTest)) &&
                SUCCEEDED(device->GetRenderState(
                    D3DRS_ZWRITEENABLE, &out.zWrite)) &&
                SUCCEEDED(device->GetRenderState(D3DRS_CULLMODE, &out.cullMode));
            if (!ok)
            {
                ++R32StateSnapshotFailures;
                if (!R32FirstStateSnapshotFailureLogged)
                {
                    R32FirstStateSnapshotFailureLogged = true;
                    spdlog::warn(
                        "VR R32 SAFETY: render-state snapshot unavailable; draw is forced to stock-WVP zero disparity instead of fail-open world stereo");
                }
            }
            return ok;
        }

        bool R32EffectIsFragileLive(IDirect3DDevice9* device,
            bool& fragile) noexcept
        {
            R32EffectSnapshot state{};
            if (!R32ReadEffectSnapshot(device, state))
                return false;
            const auto policy = OutRunVR::PassPolicy::ClassifyEffectStereo(
                state.alphaBlend != FALSE,
                state.alphaTest != FALSE,
                state.zWrite != FALSE,
                state.cullMode == D3DCULL_NONE);
            fragile = !OutRunVR::PassPolicy::AllowsEffectWorldStereo(policy);
            return true;
        }

        bool R32SetWvpBatch(IDirect3DDevice9* device,
            const float* constants) noexcept
        {
            if (!device || !constants)
                return false;
            ++R32BatchWvpUploads;
            const HRESULT hr = device->SetVertexShaderConstantF(
                OutRunWvpRegister, constants, OutRunWvpRegisterCount);
            if (FAILED(hr))
            {
                ++R32BatchWvpFailures;
                return false;
            }
            if (!R32FirstBatchWvpLogged)
            {
                R32FirstBatchWvpLogged = true;
                spdlog::info(
                    "VR R32 PERF: verified stereo WVP uploads are batched as one c64..c67 call instead of four register calls");
            }
            return true;
        }

        bool R32GetSavedViewport(IDirect3DDevice9* device,
            D3DVIEWPORT9& viewport) noexcept
        {
            if (!device)
                return false;
            if (R31StateBlockTrackingReliable.load(std::memory_order_acquire))
                return R31GetSavedViewport(device, viewport);
            return SUCCEEDED(device->GetViewport(&viewport));
        }

        bool R32RestoreRightPassState(IDirect3DDevice9* device,
            IDirect3DSurface9* savedRt, IDirect3DSurface9* savedDepth,
            const D3DVIEWPORT9& savedViewport,
            const float* originalConstants, bool restoreWvp) noexcept
        {
            bool ok = true;
            if (savedRt && FAILED(SetRenderTargetHook.stdcall<HRESULT>(
                    device, 0u, savedRt)))
                ok = false;
            const HRESULT depthHr = SetDepthStencilSurfaceHook
                ? SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, savedDepth)
                : device->SetDepthStencilSurface(savedDepth);
            if (FAILED(depthHr)) ok = false;
            if (FAILED(device->SetViewport(&savedViewport))) ok = false;
            if (restoreWvp && !R32SetWvpBatch(device, originalConstants)) ok = false;
            return ok;
        }

        template <typename ActualDraw>
        R31OwnedResult R32TryFastWorld(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, const char* site)
        {
            if (R31StateBlockRecording || !R29StableStereoBase(device))
            {
                if (IsGameDevice(device) && !InternalStereoPass && TargetIsBackBuffer())
                    ++R31Frame.unstable;
                return {};
            }

            bool fragile = true;
            const bool stateBlocksReliable =
                R31StateBlockTrackingReliable.load(std::memory_order_acquire);
            const bool effectKnown = stateBlocksReliable
                ? R29FragileEffectCached(device, fragile)
                : R32EffectIsFragileLive(device, fragile);
            if (!effectKnown)
                return {};
            if (fragile)
            {
                ++R31Frame.fragile;
                return {};
            }

            if (!EnsureStereoResources(device))
                return {};
            if (TrackedDepthStencil &&
                (!RightDepthSynchronized || !RightStencilSynchronized))
                TryBootstrapRightDepthFromRecentClear(device);
            if (TrackedDepthStencil && !RightDepthSynchronized &&
                DepthTestActive(device))
                return {};
            if (TrackedDepthStencil && !RightStencilSynchronized &&
                StencilTestActive(device))
                return {};

            OutRunVRRenderer::LatchedStereoFrame stereo{};
            if (!OutRunVRRenderer::GetLatchedStereoFrame(stereo) ||
                stereo.poseSequence == 0)
                return {};
            if (FrameStereoPoseSequence != 0 &&
                FrameStereoPoseSequence != stereo.poseSequence)
                return {};

            DrawStereoState draw{};
            if (!R31BuildFastWorldConstants(device, stereo, draw))
                return {};

            D3DVIEWPORT9 savedViewport{};
            if (!R32GetSavedViewport(device, savedViewport))
                return {};

            bool leftWvpOk = false;
            {
                InternalPassScope guard;
                leftWvpOk = R32SetWvpBatch(device, draw.eyeConstants[0]);
            }
            if (!leftWvpOk)
            {
                bool rolledBack = false;
                {
                    InternalPassScope guard;
                    rolledBack = R32SetWvpBatch(device, draw.originalConstants);
                }
                if (!rolledBack)
                {
                    R9Poison(OutRunVR::StereoFailureRestoreFailed,
                        "R32/fast-left-WVP-rollback");
                    NoteRestoreFailure("R32 fast left-eye c64 rollback");
                    R29ArmMonoSafety();
                    return { true, E_FAIL };
                }
                return {};
            }

            ++R9DrawCalls;
            R9MonoBackupGap = true;
            if (LeftDrawMayWriteDepth(device) || LeftDrawMayWriteStencil(device))
                ++R9MainDepthContentSerial;

            R31OwnedResult result{ true, D3D_OK };
            result.hr = actualDraw();
            if (FAILED(result.hr))
            {
                InvalidateRightDepthStencilIfLeftMayWrite(device);
                R9Poison(OutRunVR::StereoFailureLeftDrawFailed, site, result.hr);
                bool restored = false;
                {
                    InternalPassScope guard;
                    restored = R32SetWvpBatch(device, draw.originalConstants);
                }
                if (!restored) NoteRestoreFailure("R32 fast left draw c64");
                R29ArmMonoSafety();
                return result;
            }

            IDirect3DSurface9* savedRt = TrackedRenderTarget;
            IDirect3DSurface9* savedDepth = TrackedDepthStencil;
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                InternalPassScope guard;
                rightHr = SetRenderTargetHook.stdcall<HRESULT>(
                    device, 0u, RightEyeSurface);
                if (SUCCEEDED(rightHr))
                    rightHr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(
                        device, TrackedDepthStencil ? RightEyeDepth : nullptr);
                if (SUCCEEDED(rightHr))
                    rightHr = device->SetViewport(&savedViewport);
                if (SUCCEEDED(rightHr) &&
                    !R32SetWvpBatch(device, draw.eyeConstants[1]))
                {
                    rightFailure = OutRunVR::StereoFailureRightWvpUploadFailed;
                    rightHr = E_FAIL;
                }
                if (SUCCEEDED(rightHr))
                {
                    rightFailure = OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = actualDraw();
                }
                restoreOk = R32RestoreRightPassState(device, savedRt, savedDepth,
                    savedViewport, draw.originalConstants, true);
            }

            FrameHadDuplicatedDraw = true;
            FrameHadWorldStereo = true;
            ++DuplicatedDraws;
            ++WorldStereoDraws;
            ++R29StableTwoEyeDraws;
            ++R31FastWorldDraws;
            ++R31Frame.fastWorld;

            if (FrameStereoPoseSequence == 0)
            {
                FrameStereoPoseSequence = draw.poseSequence;
                FrameStereoMetadata = draw.stereoFrame;
            }

            if (FAILED(rightHr))
            {
                FrameRightDrawFailed = true;
                InvalidateRightDepthStencilIfLeftMayWrite(device);
                R9Poison(rightFailure, site, rightHr);
                R29ArmMonoSafety();
            }
            if (!restoreOk)
            {
                InvalidateRightDepthStencilIfLeftMayWrite(device);
                NoteRestoreFailure("R32 fast right-eye draw");
                R29ArmMonoSafety();
            }
            return result;
        }

        template <typename ActualDraw>
        R31OwnedResult R32TryHud(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, const char* site)
        {
            if (R31StateBlockRecording || !R29StableStereoBase(device) ||
                !R30CurrentPassIsScreenSpace2D())
                return {};
            if (!R31StateBlockTrackingReliable.load(std::memory_order_acquire))
            {
                R31DiscardUnreliableDrawCaches();
                const std::uintptr_t cachedShader =
                    CurrentVertexShaderIdentity.load(std::memory_order_acquire);
                if (!R31LiveShaderMatches(device, cachedShader))
                    return {};
            }
            if (!EnsureStereoResources(device))
                return {};
            if (TrackedDepthStencil &&
                (!RightDepthSynchronized || !RightStencilSynchronized))
                TryBootstrapRightDepthFromRecentClear(device);
            if (TrackedDepthStencil && !RightDepthSynchronized &&
                DepthTestActive(device))
                return {};
            if (TrackedDepthStencil && !RightStencilSynchronized &&
                StencilTestActive(device))
                return {};

            OutRunVRRenderer::LatchedStereoFrame stereo{};
            if (!OutRunVRRenderer::GetLatchedStereoFrame(stereo) ||
                stereo.poseSequence == 0)
                return {};
            if (FrameStereoPoseSequence != 0 &&
                FrameStereoPoseSequence != stereo.poseSequence)
                return {};

            float original[16]{};
            float eyeConstants[2][16]{};
            float eyeScale[2]{};
            float eyeOffset[2]{};
            if (!R30BuildScreenSpaceEyeConstants(device, stereo, original,
                    eyeConstants, eyeScale, eyeOffset))
                return {};

            D3DVIEWPORT9 savedViewport{};
            if (!R32GetSavedViewport(device, savedViewport))
                return {};

            bool leftWvpOk = false;
            {
                InternalPassScope guard;
                leftWvpOk = R32SetWvpBatch(device, eyeConstants[0]);
            }
            if (!leftWvpOk)
            {
                bool rolledBack = false;
                {
                    InternalPassScope guard;
                    rolledBack = R32SetWvpBatch(device, original);
                }
                if (!rolledBack)
                {
                    R9Poison(OutRunVR::StereoFailureRestoreFailed,
                        "R32/HUD-left-WVP-rollback");
                    NoteRestoreFailure("R32 HUD left-eye c64 rollback");
                    R29ArmMonoSafety();
                    return { true, E_FAIL };
                }
                return {};
            }

            ++R9DrawCalls;
            R9MonoBackupGap = true;
            if (LeftDrawMayWriteDepth(device) || LeftDrawMayWriteStencil(device))
                ++R9MainDepthContentSerial;

            R31OwnedResult result{ true, actualDraw() };
            if (FAILED(result.hr))
            {
                bool restored = false;
                {
                    InternalPassScope guard;
                    restored = R32SetWvpBatch(device, original);
                }
                R9Poison(OutRunVR::StereoFailureLeftDrawFailed, site, result.hr);
                if (!restored) NoteRestoreFailure("R32 HUD left draw c64");
                R29ArmMonoSafety();
                return result;
            }

            IDirect3DSurface9* savedRt = TrackedRenderTarget;
            IDirect3DSurface9* savedDepth = TrackedDepthStencil;
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                InternalPassScope guard;
                rightHr = SetRenderTargetHook.stdcall<HRESULT>(
                    device, 0u, RightEyeSurface);
                if (SUCCEEDED(rightHr))
                    rightHr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(
                        device, TrackedDepthStencil ? RightEyeDepth : nullptr);
                if (SUCCEEDED(rightHr))
                    rightHr = device->SetViewport(&savedViewport);
                if (SUCCEEDED(rightHr) &&
                    !R32SetWvpBatch(device, eyeConstants[1]))
                {
                    rightFailure = OutRunVR::StereoFailureRightWvpUploadFailed;
                    rightHr = E_FAIL;
                }
                if (SUCCEEDED(rightHr))
                {
                    rightFailure = OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = actualDraw();
                }
                restoreOk = R32RestoreRightPassState(device, savedRt, savedDepth,
                    savedViewport, original, true);
            }

            FrameHadDuplicatedDraw = true;
            ++DuplicatedDraws;
            ++NonWorldDuplicatedDraws;
            ++R29StableTwoEyeDraws;
            ++R30ScreenSpaceFovDraws;
            ++R31HudDraws;
            ++R31Frame.hud;

            if (FAILED(rightHr))
            {
                FrameRightDrawFailed = true;
                InvalidateRightDepthStencilIfLeftMayWrite(device);
                R9Poison(rightFailure, site, rightHr);
                R29ArmMonoSafety();
            }
            if (!restoreOk)
            {
                InvalidateRightDepthStencilIfLeftMayWrite(device);
                NoteRestoreFailure("R32 HUD right-eye draw");
                R29ArmMonoSafety();
            }
            return result;
        }

        template <typename LowerDraw>
        HRESULT R32LowerFailClosed(IDirect3DDevice9* device,
            LowerDraw&& lowerDraw) noexcept
        {
            if (!IsGameDevice(device) || InternalStereoPass ||
                !TargetIsBackBuffer() || !StereoWanted() || !R9StereoSeeded)
                return lowerDraw();

            R32EffectSnapshot snapshot{};
            if (R32ReadEffectSnapshot(device, snapshot))
                return lowerDraw();

            const std::uintptr_t savedIdentity =
                CurrentVertexShaderIdentity.exchange(0, std::memory_order_acq_rel);
            const HRESULT hr = lowerDraw();
            if (savedIdentity != 0)
            {
                std::uintptr_t expected = 0;
                CurrentVertexShaderIdentity.compare_exchange_strong(
                    expected, savedIdentity,
                    std::memory_order_acq_rel, std::memory_order_acquire);
            }
            ++R32FailClosedZeroDisparityDraws;
            return hr;
        }

        template <typename ActualDraw, typename LowerDraw>
        HRESULT R32Dispatch(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, LowerDraw&& lowerDraw,
            const char* site) noexcept
        {
            R31ObserveDraw(device);

            if (!R31StateBlockRecording)
            {
                if (R30CurrentPassIsScreenSpace2D())
                {
                    const auto hud = R32TryHud(device,
                        std::forward<ActualDraw>(actualDraw), site);
                    if (hud.handled)
                        return hud.hr;
                }
                else
                {
                    const auto fast = R32TryFastWorld(device,
                        std::forward<ActualDraw>(actualDraw), site);
                    if (fast.handled)
                        return fast.hr;
                }
            }

            ++R31Frame.fallback;
            return R32LowerFailClosed(device,
                std::forward<LowerDraw>(lowerDraw));
        }

        HRESULT __stdcall DrawPrimitiveDestR32(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto lower = [&]() {
                return R32DrawPrimitiveR31Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R32Dispatch(device, actual, lower, "R32/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR32(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            auto lower = [&]() {
                return R32DrawIndexedPrimitiveR31Hook.stdcall<HRESULT>(device,
                    type, baseVertexIndex, minVertexIndex, numVertices,
                    startIndex, primitiveCount);
            };
            return R32Dispatch(device, actual, lower,
                "R32/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR32(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT primitiveCount, const void* data,
            UINT stride)
        {
            auto actual = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto lower = [&]() {
                return R32DrawPrimitiveUPR31Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R32Dispatch(device, actual, lower, "R32/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR32(
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
            auto lower = [&]() {
                return R32DrawIndexedPrimitiveUPR31Hook.stdcall<HRESULT>(device,
                    type, minVertexIndex, numVertices, primitiveCount,
                    indexData, indexFormat, vertexData, stride);
            };
            return R32Dispatch(device, actual, lower,
                "R32/DrawIndexedPrimitiveUP");
        }

        void R32ForgetDirectIdentity() noexcept
        {
            R32DirectHostPid = 0;
            R32DirectHostLuidLow = 0;
            R32DirectHostLuidHigh = 0;
        }

        bool R32DirectIdentityMatches() noexcept
        {
            return SharedState && DirectInteropVerified &&
                R32DirectHostPid != 0 &&
                R32DirectHostPid == SharedState->hostPid &&
                R32DirectHostLuidLow == SharedState->hostAdapterLuidLow &&
                R32DirectHostLuidHigh == SharedState->hostAdapterLuidHigh;
        }

        void R32InvalidateDirectInteropOnly() noexcept
        {
            ReleaseDirectTransportSlots();
            ReleaseCom(DirectInteropProbeFence);
            ReleaseCom(DirectInteropProbeSurface);
            ReleaseCom(DirectInteropProbeTexture);
            DirectInteropProbeHandle = nullptr;
            DirectInteropProbeToken = 0;
            DirectInteropVerified = false;
            if (SharedState && SharedState->magic == OutRunVR::SharedMagic)
            {
                InterlockedExchange(reinterpret_cast<volatile LONG*>(
                    &SharedState->clientInteropProbeHandle), 0);
                InterlockedExchange(reinterpret_cast<volatile LONG*>(
                    &SharedState->clientInteropProbeToken), 0);
            }
            R32ForgetDirectIdentity();
            ++R32DirectIdentityInvalidations;
        }

        bool R32EnsureDirectResources(IDirect3DDevice9* device) noexcept
        {
            if (DirectTransportResourcesReady && R32DirectIdentityMatches())
            {
                ++R32DirectProbeCacheHits;
                return true;
            }

            if (DirectTransportResourcesReady && !R32DirectIdentityMatches())
                R32InvalidateDirectInteropOnly();

            if (!EnsureDirectTransportResources(device))
                return false;
            if (!SharedState || !DirectInteropVerified)
                return false;

            R32DirectHostPid = SharedState->hostPid;
            R32DirectHostLuidLow = SharedState->hostAdapterLuidLow;
            R32DirectHostLuidHigh = SharedState->hostAdapterLuidHigh;
            return true;
        }

        bool R32WaitProducerFence(IDirect3DQuery9* query) noexcept
        {
            if (!query)
                return false;
            HRESULT ready = query->GetData(nullptr, 0, D3DGETDATA_FLUSH);
            if (ready == S_OK)
            {
                ++R32DirectFenceSuccess;
                return true;
            }
            if (ready != S_FALSE)
                return false;

            const ULONGLONG deadline = GetTickCount64() +
                OutRunVR::R32::ProducerFenceBudgetMs;
            for (;;)
            {
                ready = query->GetData(nullptr, 0, 0);
                if (ready == S_OK)
                {
                    ++R32DirectFenceSuccess;
                    return true;
                }
                if (ready != S_FALSE || GetTickCount64() >= deadline)
                {
                    ++R32DirectFenceBudgetFallbacks;
                    ++DirectTransportFenceTimeouts;
                    if (!R32FirstFenceBudgetLogged)
                    {
                        R32FirstFenceBudgetLogged = true;
                        spdlog::warn(
                            "VR R32 D3D9Ex: producer copy fence exceeded {}ms; falling back to SBS instead of stalling up to 12ms",
                            OutRunVR::R32::ProducerFenceBudgetMs);
                    }
                    return false;
                }
                SwitchToThread();
            }
        }

        bool ResolveDirectTransportR32(IDirect3DDevice9* device,
            std::uint32_t frameId) noexcept
        {
            if (!R13OverlayReady.load(std::memory_order_acquire))
                return R32ResolveDirectR13Hook.call<bool>(device, frameId);
            if (!frameId || !R32EnsureDirectResources(device) ||
                !BackBuffer || !RightEyeSurface)
                return false;

            const std::uint32_t slotIndex =
                (frameId - 1u) % OutRunVR::RenderFrameRingSize;
            auto& slot = DirectTransportSlots[slotIndex];
            if (slot.frameId)
            {
                std::uint32_t gpuCompleted = 0;
                const bool ackValid =
                    R13ReadGpuCompletedFrame(slotIndex, gpuCompleted);
                if (!ackValid || !FrameIdAtOrAfter(gpuCompleted, slot.frameId))
                {
                    ++R13SafeAckBackpressure;
                    ++DirectTransportRingBackpressure;
                    return false;
                }
            }

            {
                InternalPassScope guard;
                if (FAILED(device->StretchRect(BackBuffer, nullptr,
                        slot.leftSurface, nullptr, D3DTEXF_NONE)) ||
                    FAILED(device->StretchRect(RightEyeSurface, nullptr,
                        slot.rightSurface, nullptr, D3DTEXF_NONE)) ||
                    FAILED(slot.fence->Issue(D3DISSUE_END)))
                    return false;
            }
            if (!R32WaitProducerFence(slot.fence))
                return false;

            slot.frameId = frameId;
            ActiveDirectTransportSlot = slotIndex;
            return true;
        }

        void R32ResetAfterGameReset() noexcept
        {
            R29MonoSafetyThroughEpoch = OutRunVR::R32::RearmMonoSafetyEpoch(
                PresentEpoch);
            R29Effect = {};
            R31BlockedVerifiedGeneration = 0;
            R31FastWorldCandidates = 0;
            R31EyeCache = {};
            R31Frame = {};
            R31Window = {};
            R22ShadowState = {};
            R23LastStateSampleDrawSerial = 0;
            R23LastStateSampleEpoch = 0;
            OutRunVRRenderer::R29InvalidateRendererStateAfterExternalRestore();
            R32ForgetDirectIdentity();
            ++R32ResetEpochRearms;
            if (!R32FirstResetRearmLogged)
            {
                R32FirstResetRearmLogged = true;
                spdlog::info(
                    "VR R32 RESET: R29 mono-safety horizon rearmed relative to reset PresentEpoch; stale pre-reset epoch can no longer suppress fast stereo for thousands of Presents");
            }
        }

        HRESULT __stdcall ResetDestR32(IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            const HRESULT hr = R32ResetR13Hook.stdcall<HRESULT>(device, params);
            if (IsGameDevice(device))
                R32ResetAfterGameReset();
            return hr;
        }

        void R32LogPerfWindow() noexcept
        {
            if (!Settings::VRTelemetry)
                return;
            const ULONGLONG now = GetTickCount64();
            if (R32Counters.lastLogMs == 0)
            {
                R32Counters.lastLogMs = now;
                R32Counters.liveWvp = R31FastWorldLiveValidations;
                R32Counters.liveReject = R31FastWorldValidationRejects;
                R32Counters.stateRecord = R31StateBlockRecordings;
                R32Counters.stateApply = R31StateBlockApplies;
                R32Counters.batch = R32BatchWvpUploads;
                R32Counters.batchFail = R32BatchWvpFailures;
                R32Counters.stateFail = R32StateSnapshotFailures;
                R32Counters.zeroFallback = R32FailClosedZeroDisparityDraws;
                R32Counters.directCache = R32DirectProbeCacheHits;
                R32Counters.directFenceOk = R32DirectFenceSuccess;
                R32Counters.directFenceFallback = R32DirectFenceBudgetFallbacks;
                R32Counters.directBackpressure = DirectTransportRingBackpressure;
                R32Counters.resetRearm = R32ResetEpochRearms;
                return;
            }
            if (now - R32Counters.lastLogMs < 5000)
                return;

            spdlog::info(
                "VR R32 PERF 5s: liveWvpCheck={} liveReject={} stateBlock[record={},apply={}] batchWvp[ok={},fail={}] safety[stateReadFail={},forcedZero={}] direct[probeCacheHit={},producerFenceOk={},producerBudgetFallback={},backpressure={}] resetRearm={}",
                R31FastWorldLiveValidations - R32Counters.liveWvp,
                R31FastWorldValidationRejects - R32Counters.liveReject,
                R31StateBlockRecordings - R32Counters.stateRecord,
                R31StateBlockApplies - R32Counters.stateApply,
                R32BatchWvpUploads - R32Counters.batch,
                R32BatchWvpFailures - R32Counters.batchFail,
                R32StateSnapshotFailures - R32Counters.stateFail,
                R32FailClosedZeroDisparityDraws - R32Counters.zeroFallback,
                R32DirectProbeCacheHits - R32Counters.directCache,
                R32DirectFenceSuccess - R32Counters.directFenceOk,
                R32DirectFenceBudgetFallbacks - R32Counters.directFenceFallback,
                DirectTransportRingBackpressure - R32Counters.directBackpressure,
                R32ResetEpochRearms - R32Counters.resetRearm);

            R32Counters.lastLogMs = now;
            R32Counters.liveWvp = R31FastWorldLiveValidations;
            R32Counters.liveReject = R31FastWorldValidationRejects;
            R32Counters.stateRecord = R31StateBlockRecordings;
            R32Counters.stateApply = R31StateBlockApplies;
            R32Counters.batch = R32BatchWvpUploads;
            R32Counters.batchFail = R32BatchWvpFailures;
            R32Counters.stateFail = R32StateSnapshotFailures;
            R32Counters.zeroFallback = R32FailClosedZeroDisparityDraws;
            R32Counters.directCache = R32DirectProbeCacheHits;
            R32Counters.directFenceOk = R32DirectFenceSuccess;
            R32Counters.directFenceFallback = R32DirectFenceBudgetFallbacks;
            R32Counters.directBackpressure = DirectTransportRingBackpressure;
            R32Counters.resetRearm = R32ResetEpochRearms;
        }

        HRESULT __stdcall PresentDestR32(IDirect3DDevice9* device,
            const RECT* sourceRect, const RECT* destRect,
            HWND destWindowOverride, const RGNDATA* dirtyRegion)
        {
            const HRESULT hr = R32PresentR13Hook.stdcall<HRESULT>(device,
                sourceRect, destRect, destWindowOverride, dirtyRegion);
            if (IsGameDevice(device))
                R32LogPerfWindow();
            return hr;
        }

        void R32RollbackHooks() noexcept
        {
            R32DrawIndexedPrimitiveUPR31Hook = {};
            R32DrawPrimitiveUPR31Hook = {};
            R32DrawIndexedPrimitiveR31Hook = {};
            R32DrawPrimitiveR31Hook = {};
            R32PresentR13Hook = {};
            R32ResolveDirectR13Hook = {};
            R32ResetR13Hook = {};
        }

        bool R32EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R32ResetR13Hook,
                &R32ResolveDirectR13Hook,
                &R32PresentR13Hook,
                &R32DrawPrimitiveR31Hook,
                &R32DrawIndexedPrimitiveR31Hook,
                &R32DrawPrimitiveUPR31Hook,
                &R32DrawIndexedPrimitiveUPR31Hook
            };
            for (auto* hook : hooks)
                if (!*hook || !hook->enable().has_value())
                    return false;
            return true;
        }

        DWORD WINAPI R32InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R32InstallState.store(State::Pending, std::memory_order_release);
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r31 = R31InstallState.load(std::memory_order_acquire);
                const auto r13 = R13InstallState.load(std::memory_order_acquire);
                if (r31 == State::Failed || r13 == R13InstallFailed)
                {
                    R32InstallState.store(State::Failed, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR32Review", false);
                    return 0;
                }
                if (r31 == State::Ready && r13 == R13InstallReady)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R32ResetR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR13), ResetDestR32, disabled);
                    R32ResolveDirectR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResolveDirectTransportR13),
                        ResolveDirectTransportR32, disabled);
                    R32PresentR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&PresentDestR13), PresentDestR32, disabled);
                    R32DrawPrimitiveR31Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR31),
                        DrawPrimitiveDestR32, disabled);
                    R32DrawIndexedPrimitiveR31Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR31),
                        DrawIndexedPrimitiveDestR32, disabled);
                    R32DrawPrimitiveUPR31Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR31),
                        DrawPrimitiveUPDestR32, disabled);
                    R32DrawIndexedPrimitiveUPR31Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR31),
                        DrawIndexedPrimitiveUPDestR32, disabled);

                    if (!R32EnableHooks())
                    {
                        R32RollbackHooks();
                        R32InstallState.store(State::Failed,
                            std::memory_order_release);
                        HookManager::ReportAsyncResult(
                            "OpenXRVRStereoR32Review", false);
                        spdlog::error(
                            "VR R32: review/optimization hook transaction was partial; R31 remains authoritative");
                        return 0;
                    }

                    R32InstallState.store(State::Ready, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR32Review", true);
                    spdlog::info(
                        "VR R32 REVIEW: reset epoch fix + fail-closed state reads + batched WVP + cached D3D9Ex interop + bounded producer fence + delta telemetry READY");
                    return 0;
                }
                Sleep(25);
            }

            R32InstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVRStereoR32Review", false);
            spdlog::error("VR R32: timed out waiting for R31/R13 prerequisites");
            return 0;
        }

        class VRStereoR32ReviewHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR32Review";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(
                    nullptr, 0, R32InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R32InstallState.store(
                        OutRunVR::RuntimeEligibility::InstallState::Failed,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRStereoR32ReviewHook instance;
        };

        VRStereoR32ReviewHook VRStereoR32ReviewHook::instance;
    }
}
