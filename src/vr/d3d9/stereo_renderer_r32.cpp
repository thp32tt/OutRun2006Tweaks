// R32 review-consolidation overlay.
//
// Keeps R31/R29/R14 correctness policy while consolidating the reviewed hot
// paths. Review-2 additionally makes R22 the reset owner and prevents reuse of a
// DirectGPU producer slot while a timed-out D3D9 EVENT query is still pending.

#include "r32_policy.hpp"
#include "stereo_renderer_r31.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R32ResetR22Hook{};
        SafetyHookInline R32ResolveDirectR13Hook{};
        SafetyHookInline R32PresentR13Hook{};

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R32InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        std::uint64_t R32BatchWvpUploads = 0;
        std::uint64_t R32BatchWvpFailures = 0;
        std::uint64_t R32StateSnapshotFailures = 0;
        std::uint64_t R32FailClosedZeroDisparityDraws = 0;
        std::uint64_t R32ResetEpochRearms = 0;
        std::uint64_t R32ResetFailures = 0;
        std::uint64_t R32DirectProbeCacheHits = 0;
        std::uint64_t R32DirectFenceSuccess = 0;
        std::uint64_t R32DirectFenceBudgetFallbacks = 0;
        std::uint64_t R32DirectFenceWaitSamples = 0;
        std::uint64_t R32DirectFencePolls = 0;
        std::uint64_t R32DirectFenceWaitUsTotal = 0;
        std::uint64_t R32DirectFenceWaitUsMax = 0;
        std::uint64_t R32DirectIdentityInvalidations = 0;
        std::uint64_t R32PendingFenceDrains = 0;
        std::uint64_t R32PendingFenceBlocks = 0;
        std::uint64_t R32PendingFenceErrors = 0;
        bool R32FirstStateSnapshotFailureLogged = false;
        bool R32FirstBatchWvpLogged = false;
        bool R32FirstFenceBudgetLogged = false;
        bool R32FirstResetRearmLogged = false;
        bool R32FirstPendingFenceLogged = false;
        bool R32FirstDirectCopyRejectLogged = false;
        bool R32DirectCopyPathRejected = false;
        HRESULT R32DirectCopyRejectHr = D3D_OK;

        std::uint32_t R32DirectHostPid = 0;
        std::uint32_t R32DirectHostLuidLow = 0;
        std::uint32_t R32DirectHostLuidHigh = 0;
        std::array<bool, OutRunVR::RenderFrameRingSize> R32ProducerFencePending{};
        std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> R32ProducerPendingFrame{};

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
            std::uint64_t directFenceWaitSamples = 0;
            std::uint64_t directFencePolls = 0;
            std::uint64_t directFenceWaitUs = 0;
            std::uint64_t directBackpressure = 0;
            std::uint64_t pendingDrain = 0;
            std::uint64_t pendingBlock = 0;
            std::uint64_t pendingError = 0;
            std::uint64_t resetRearm = 0;
            std::uint64_t resetFail = 0;
        };
        R32CounterSnapshot R32Counters{};

        struct R32FrameWorkload
        {
            std::uint64_t draws = 0;
            std::uint64_t primitives = 0;
            std::uint64_t triangles = 0;
            std::uint64_t pointLinePrimitives = 0;
            std::uint64_t indexedDraws = 0;
            std::uint64_t upDraws = 0;
            std::uint64_t alphaBlendDraws = 0;
            std::uint64_t alphaBlendPrimitives = 0;
            std::uint64_t alphaTestDraws = 0;
            std::uint64_t particleLikeDraws = 0;
            std::uint64_t particleLikePrimitives = 0;
            std::uint64_t effectUnknownDraws = 0;
            std::uint64_t fenceWaitUs = 0;
            std::uint64_t fencePolls = 0;
        };
        thread_local R32FrameWorkload R32FrameWorkloadCounters{};

        struct R32PerfWindow
        {
            std::uint64_t frames = 0;
            std::uint64_t spikes = 0;
            std::uint64_t frameUsTotal = 0;
            std::uint64_t maxFrameUs = 0;
            std::uint64_t presentUsTotal = 0;
            std::uint64_t maxPresentUs = 0;
            std::uint64_t drawsTotal = 0;
            std::uint64_t maxDraws = 0;
            std::uint64_t primitivesTotal = 0;
            std::uint64_t maxPrimitives = 0;
            std::uint64_t maxTriangles = 0;
            std::uint64_t maxUpDraws = 0;
            std::uint64_t maxAlphaBlendDraws = 0;
            std::uint64_t maxParticleLikeDraws = 0;
            std::uint64_t maxParticleLikePrimitives = 0;
        };
        thread_local R32PerfWindow R32PerfWindowCounters{};
        thread_local std::uint64_t R32PerfBaselineUs = 0;
        thread_local LONGLONG R32LastPresentEndQpc = 0;
        thread_local ULONGLONG R32LastSpikeLogMs = 0;

        struct R32StereoWorkloadSnapshot
        {
            std::uint64_t main = 0;
            std::uint64_t offscreen = 0;
            std::uint64_t aux = 0;
            std::uint64_t fastWorld = 0;
            std::uint64_t hud = 0;
            std::uint64_t fallback = 0;
            std::uint64_t fragile = 0;
            std::uint64_t unstable = 0;
        };

        LONGLONG R32PerfQpcFrequency() noexcept
        {
            static const LONGLONG frequency = []() noexcept {
                LARGE_INTEGER value{};
                return QueryPerformanceFrequency(&value) != FALSE
                    ? value.QuadPart : 0;
            }();
            return frequency;
        }

        std::uint64_t R32ElapsedUs(
            LONGLONG begin,
            LONGLONG end) noexcept
        {
            const LONGLONG frequency = R32PerfQpcFrequency();
            if (frequency <= 0 || begin <= 0 || end < begin)
                return 0;
            return static_cast<std::uint64_t>(
                ((end - begin) * 1000000LL) / frequency);
        }

        R32StereoWorkloadSnapshot R32CaptureStereoWorkload() noexcept
        {
            const auto route = R31TelemetryFrameSnapshot();
            return {
                route.main,
                route.offscreen,
                route.aux,
                route.fastWorld,
                route.hud,
                route.fallback,
                route.fragile,
                route.unstable
            };
        }

        void R32ObserveFrameWorkload(
            IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type,
            UINT primitiveCount,
            bool indexed,
            bool up) noexcept
        {
            if (!Settings::VRTelemetry || !IsGameDevice(device) ||
                InternalStereoPass)
                return;

            auto& frame = R32FrameWorkloadCounters;
            ++frame.draws;
            frame.primitives += primitiveCount;
            if (indexed) ++frame.indexedDraws;
            if (up) ++frame.upDraws;

            const bool triangleTopology =
                type == D3DPT_TRIANGLELIST ||
                type == D3DPT_TRIANGLESTRIP ||
                type == D3DPT_TRIANGLEFAN;
            if (triangleTopology)
                frame.triangles += primitiveCount;
            else
                frame.pointLinePrimitives += primitiveCount;

            R29EffectTelemetrySnapshot effect{};
            if (!TryGetEffectTelemetrySnapshot(effect))
            {
                ++frame.effectUnknownDraws;
                return;
            }

            if (effect.alphaBlend != FALSE)
            {
                ++frame.alphaBlendDraws;
                frame.alphaBlendPrimitives += primitiveCount;
            }
            if (effect.alphaTest != FALSE)
                ++frame.alphaTestDraws;

            // Heuristic only: alpha-blended, non-Z-writing point/triangle work
            // is a useful proxy for sand/smoke/spray/flare-style effects, but is
            // deliberately not labelled as a proven game particle draw.
            if (effect.alphaBlend != FALSE &&
                effect.zWrite == FALSE &&
                (triangleTopology || type == D3DPT_POINTLIST))
            {
                ++frame.particleLikeDraws;
                frame.particleLikePrimitives += primitiveCount;
            }
        }

        void R32FinalizeFramePerf(
            LONGLONG presentStartQpc,
            LONGLONG presentEndQpc,
            const R32StereoWorkloadSnapshot& stereo) noexcept
        {
            if (!Settings::VRTelemetry)
            {
                R32FrameWorkloadCounters = {};
                R32LastPresentEndQpc = presentEndQpc;
                return;
            }

            auto frame = R32FrameWorkloadCounters;
            R32FrameWorkloadCounters = {};

            const std::uint64_t presentUs =
                R32ElapsedUs(presentStartQpc, presentEndQpc);
            const std::uint64_t frameUs =
                R32ElapsedUs(R32LastPresentEndQpc, presentEndQpc);
            R32LastPresentEndQpc = presentEndQpc;

            if (frameUs == 0)
                return;

            const std::uint64_t baselineBefore = R32PerfBaselineUs;
            const bool spike =
                OutRunVR::R32::IsPerfFrameSpike(frameUs, baselineBefore);
            R32PerfBaselineUs = OutRunVR::R32::UpdatePerfBaselineUs(
                R32PerfBaselineUs, frameUs, spike);

            auto& window = R32PerfWindowCounters;
            ++window.frames;
            if (spike) ++window.spikes;
            window.frameUsTotal += frameUs;
            window.presentUsTotal += presentUs;
            window.drawsTotal += frame.draws;
            window.primitivesTotal += frame.primitives;
            window.maxFrameUs = (std::max)(window.maxFrameUs, frameUs);
            window.maxPresentUs = (std::max)(window.maxPresentUs, presentUs);
            window.maxDraws = (std::max)(window.maxDraws, frame.draws);
            window.maxPrimitives =
                (std::max)(window.maxPrimitives, frame.primitives);
            window.maxTriangles =
                (std::max)(window.maxTriangles, frame.triangles);
            window.maxUpDraws =
                (std::max)(window.maxUpDraws, frame.upDraws);
            window.maxAlphaBlendDraws =
                (std::max)(window.maxAlphaBlendDraws, frame.alphaBlendDraws);
            window.maxParticleLikeDraws =
                (std::max)(window.maxParticleLikeDraws, frame.particleLikeDraws);
            window.maxParticleLikePrimitives = (std::max)(
                window.maxParticleLikePrimitives,
                frame.particleLikePrimitives);

            if (!spike)
                return;

            const ULONGLONG nowMs = GetTickCount64();
            const bool hardSpike = frameUs >= OutRunVR::R32::PerfSpikeHardUs;
            if (!hardSpike && R32LastSpikeLogMs != 0 &&
                nowMs - R32LastSpikeLogMs <
                    OutRunVR::R32::PerfSpikeLogCooldownMs)
                return;
            R32LastSpikeLogMs = nowMs;

            spdlog::warn(
                "VR R32 FRAME SPIKE: frameUs={} baselineUs={} presentUs={} workload[draws={},primitives={},triangles={},indexed={},up={},alphaBlend={},alphaBlendPrimitives={},alphaTest={},particleLikeDraws={},particleLikePrimitives={},effectUnknown={}] stereo[main={},offscreen={},aux={},fastWorld={},hud={},fallback={},fragile={},unstable={}] direct[fenceWaitUs={},fencePolls={}]",
                frameUs, baselineBefore, presentUs,
                frame.draws, frame.primitives, frame.triangles,
                frame.indexedDraws, frame.upDraws,
                frame.alphaBlendDraws, frame.alphaBlendPrimitives,
                frame.alphaTestDraws, frame.particleLikeDraws,
                frame.particleLikePrimitives, frame.effectUnknownDraws,
                stereo.main, stereo.offscreen, stereo.aux,
                stereo.fastWorld, stereo.hud, stereo.fallback,
                stereo.fragile, stereo.unstable,
                frame.fenceWaitUs, frame.fencePolls);
        }

        bool R32ReadEffectSnapshot(IDirect3DDevice9* device,
            OutRunVR::D3D9::LiveEffectRenderStateSnapshot& out) noexcept
        {
            const bool ok =
                OutRunVR::D3D9::ReadLiveEffectRenderStateSnapshot(device, out);
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
            OutRunVR::D3D9::LiveEffectRenderStateSnapshot state{};
            if (!R32ReadEffectSnapshot(device, state))
                return false;
            const auto policy = OutRunVR::PassPolicy::ClassifyEffectStereo(
                state.alphaBlend != FALSE,
                state.alphaTest != FALSE,
                state.zWrite != FALSE,
                state.zEnable != D3DZB_FALSE,
                state.cullMode == D3DCULL_NONE);
            fragile = !OutRunVR::PassPolicy::AllowsEffectWorldStereo(policy);
            return true;
        }

        bool R32SetWvpBatch(IDirect3DDevice9* device,
            const float* constants) noexcept
        {
            if (!device || !constants)
                return false;
            if (Settings::VRTelemetry)
                ++R32BatchWvpUploads;
            if (!OutRunVR::D3D9::SetVertexShaderConstantBatch(
                    device, OutRunWvpRegister, constants,
                    OutRunWvpRegisterCount))
            {
                ++R32BatchWvpFailures;
                return false;
            }
            if (Settings::VRTelemetry && !R32FirstBatchWvpLogged)
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
            if (OutRunVR::State::StateBlockTracker::Reliable())
                return R31GetSavedViewport(device, viewport);
            return OutRunVR::D3D9::ReadViewport(device, viewport);
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

        template <typename LowerDraw>
        HRESULT R32LowerFailClosed(IDirect3DDevice9* device,
            LowerDraw&& lowerDraw) noexcept
        {
            if (!IsGameDevice(device) || InternalStereoPass ||
                !TargetIsBackBuffer() || !StereoWanted() || !R9StereoBaselineSeeded())
                return lowerDraw();

            OutRunVR::D3D9::LiveEffectRenderStateSnapshot snapshot{};
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

        void R32ForgetDirectIdentity() noexcept
        {
            R32DirectHostPid = 0;
            R32DirectHostLuidLow = 0;
            R32DirectHostLuidHigh = 0;
        }

        void R32ClearPendingProducerFences() noexcept
        {
            R32ProducerFencePending.fill(false);
            R32ProducerPendingFrame.fill(0);
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
            R32ClearPendingProducerFences();
            R32DirectCopyPathRejected = false;
            R32DirectCopyRejectHr = D3D_OK;
            ReleaseDirectTransportSlots();
            RetireDirectInteropProbePublication();
            ReleaseCom(DirectInteropProbeFence);
            ReleaseCom(DirectInteropProbeSurface);
            ReleaseCom(DirectInteropProbeTexture);
            DirectInteropProbeHandle = nullptr;
            DirectInteropProbeToken = 0;
            DirectInteropVerified = false;
            R32ForgetDirectIdentity();
            ++R32DirectIdentityInvalidations;
        }

        bool R32EnsureDirectResources(IDirect3DDevice9* device) noexcept
        {
            if (DirectTransportResourcesReady && R32DirectIdentityMatches())
            {
                if (Settings::VRTelemetry) ++R32DirectProbeCacheHits;
                return true;
            }

            if (DirectTransportResourcesReady && !R32DirectIdentityMatches())
                R32InvalidateDirectInteropOnly();

            if (!DirectTransportResourcesReady)
                R32ClearPendingProducerFences();
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

            static const LONGLONG qpcFrequency = []() noexcept {
                LARGE_INTEGER value{};
                return QueryPerformanceFrequency(&value) != FALSE
                    ? value.QuadPart : 0;
            }();
            LARGE_INTEGER start{};
            const bool highResolutionClock = qpcFrequency > 0 &&
                QueryPerformanceCounter(&start) != FALSE;
            const ULONGLONG fallbackStartMs = highResolutionClock ? 0 :
                GetTickCount64();
            const ULONGLONG fallbackDeadline = highResolutionClock ? 0 :
                fallbackStartMs + OutRunVR::R32::ProducerFenceBudgetMs;
            std::uint64_t pollCount = 0;
            auto recordFenceWait = [&]() noexcept {
                if (!Settings::VRTelemetry)
                    return;
                std::uint64_t elapsedUs = 0;
                if (highResolutionClock)
                {
                    LARGE_INTEGER now{};
                    if (QueryPerformanceCounter(&now) != FALSE &&
                        now.QuadPart >= start.QuadPart)
                    {
                        elapsedUs = static_cast<std::uint64_t>(
                            ((now.QuadPart - start.QuadPart) * 1000000LL) /
                            qpcFrequency);
                    }
                }
                else
                {
                    const ULONGLONG nowMs = GetTickCount64();
                    elapsedUs = nowMs >= fallbackStartMs
                        ? (nowMs - fallbackStartMs) * 1000ULL : 0ULL;
                }
                ++R32DirectFenceWaitSamples;
                R32DirectFencePolls += pollCount;
                R32DirectFenceWaitUsTotal += elapsedUs;
                R32DirectFenceWaitUsMax =
                    (std::max)(R32DirectFenceWaitUsMax, elapsedUs);
                R32FrameWorkloadCounters.fenceWaitUs += elapsedUs;
                R32FrameWorkloadCounters.fencePolls += pollCount;
            };
            const LONGLONG budgetTicks = highResolutionClock
                ? (qpcFrequency *
                    static_cast<LONGLONG>(OutRunVR::R32::ProducerFenceBudgetMs) +
                    999) / 1000
                : 0;

            // Budget starts before the FLUSH request so a slow first GetData is
            // accounted for instead of being hidden outside the 2 ms window.
            HRESULT ready = query->GetData(nullptr, 0, D3DGETDATA_FLUSH);
            if (ready == S_OK)
            {
                if (Settings::VRTelemetry) ++R32DirectFenceSuccess;
                recordFenceWait();
                return true;
            }
            if (ready != S_FALSE)
            {
                recordFenceWait();
                return false;
            }

            for (;;)
            {
                ++pollCount;
                ready = query->GetData(nullptr, 0, 0);
                if (ready == S_OK)
                {
                    if (Settings::VRTelemetry) ++R32DirectFenceSuccess;
                    recordFenceWait();
                    return true;
                }

                bool expired = ready != S_FALSE;
                if (!expired && highResolutionClock)
                {
                    LARGE_INTEGER now{};
                    expired = QueryPerformanceCounter(&now) == FALSE ||
                        now.QuadPart - start.QuadPart >= budgetTicks;
                }
                else if (!expired)
                {
                    expired = GetTickCount64() >= fallbackDeadline;
                }

                if (expired)
                {
                    if (Settings::VRTelemetry) ++R32DirectFenceBudgetFallbacks;
                    ++DirectTransportFenceTimeouts;
                    if (!R32FirstFenceBudgetLogged)
                    {
                        R32FirstFenceBudgetLogged = true;
                        spdlog::warn(
                            "VR R32 D3D9Ex: producer copy fence exceeded {}ms; falling back to SBS instead of stalling up to 12ms",
                            OutRunVR::R32::ProducerFenceBudgetMs);
                    }
                    recordFenceWait();
                    return false;
                }
                SwitchToThread();
            }
        }

        bool R32DrainPendingProducerFence(std::uint32_t slotIndex) noexcept
        {
            if (slotIndex >= R32ProducerFencePending.size() ||
                !R32ProducerFencePending[slotIndex])
                return true;

            auto& slot = DirectTransportSlots[slotIndex];
            if (!slot.fence)
            {
                R32DirectCopyPathRejected = true;
                R32DirectCopyRejectHr = E_FAIL;
                if (Settings::VRTelemetry) ++R32PendingFenceErrors;
                return false;
            }

            const HRESULT ready = slot.fence->GetData(nullptr, 0, 0);
            if (ready == S_OK)
            {
                R32ProducerFencePending[slotIndex] = false;
                R32ProducerPendingFrame[slotIndex] = 0;
                if (Settings::VRTelemetry) ++R32PendingFenceDrains;
                return true;
            }
            if (ready == S_FALSE)
            {
                if (Settings::VRTelemetry) ++R32PendingFenceBlocks;
                ++DirectTransportRingBackpressure;
                if (!R32FirstPendingFenceLogged)
                {
                    R32FirstPendingFenceLogged = true;
                    spdlog::info(
                        "VR R32 D3D9Ex: timed-out producer EVENT remains pending; the ring slot is blocked from reuse until the GPU reports completion");
                }
                return false;
            }

            // A query error does not prove GPU completion. Keep the pending
            // marker intact and quarantine DirectGPU until Reset or interop
            // identity regeneration recreates the ring.
            R32DirectCopyPathRejected = true;
            R32DirectCopyRejectHr = ready;
            if (Settings::VRTelemetry) ++R32PendingFenceErrors;
            return false;
        }

        bool ResolveDirectTransportR32(IDirect3DDevice9* device,
            std::uint32_t frameId) noexcept
        {
            if (!R13OverlayReadyForTransport())
                return R32ResolveDirectR13Hook.call<bool>(device, frameId);
            if (!frameId || !R32EnsureDirectResources(device) ||
                !BackBuffer || !RightEyeSurface)
                return false;
            // R32EnsureDirectResources must run before this cached rejection:
            // host PID/LUID or transport-generation changes invalidate the old
            // interop identity and clear the rejection automatically.
            if (R32DirectCopyPathRejected)
                return false;

            const std::uint32_t slotIndex =
                (frameId - 1u) % OutRunVR::RenderFrameRingSize;
            if (!R32DrainPendingProducerFence(slotIndex))
                return false;

            auto& slot = DirectTransportSlots[slotIndex];
            if (slot.frameId)
            {
                std::uint32_t gpuCompleted = 0;
                const bool ackValid =
                    R13TryGetGpuCompletedFrame(slotIndex, gpuCompleted);
                if (!ackValid || !FrameIdAtOrAfter(gpuCompleted, slot.frameId))
                {
                    R13NoteSafeAckBackpressure();
                    ++DirectTransportRingBackpressure;
                    return false;
                }
            }

            {
                InternalPassScope guard;
                const HRESULT leftCopy = device->StretchRect(BackBuffer, nullptr,
                    slot.leftSurface, nullptr, D3DTEXF_NONE);
                const HRESULT rightCopy = SUCCEEDED(leftCopy)
                    ? device->StretchRect(RightEyeSurface, nullptr,
                        slot.rightSurface, nullptr, D3DTEXF_NONE)
                    : leftCopy;
                if (FAILED(leftCopy) || FAILED(rightCopy))
                {
                    R32DirectCopyPathRejected = true;
                    R32DirectCopyRejectHr = FAILED(leftCopy)
                        ? leftCopy : rightCopy;
                    if (!R32FirstDirectCopyRejectLogged)
                    {
                        R32FirstDirectCopyRejectLogged = true;
                        spdlog::warn(
                            "VR R32 D3D9Ex: shared-eye StretchRect rejected hr=0x{:08X}; DirectGPU copy path is disabled until Reset/interop revalidation instead of retrying every Present",
                            static_cast<unsigned>(R32DirectCopyRejectHr));
                    }
                    return false;
                }
                const HRESULT issueHr = slot.fence->Issue(D3DISSUE_END);
                if (FAILED(issueHr))
                {
                    // StretchRect commands are already queued. Without a valid
                    // EVENT we cannot prove when this producer slot is reusable,
                    // so quarantine the whole DirectGPU path until reset/interop
                    // revalidation rather than cycling back into this slot.
                    R32DirectCopyPathRejected = true;
                    R32DirectCopyRejectHr = issueHr;
                    if (Settings::VRTelemetry) ++R32PendingFenceErrors;
                    return false;
                }
            }

            R32ProducerFencePending[slotIndex] = true;
            R32ProducerPendingFrame[slotIndex] = frameId;
            if (!R32WaitProducerFence(slot.fence))
                return false;

            R32ProducerFencePending[slotIndex] = false;
            R32ProducerPendingFrame[slotIndex] = 0;

            // Bridge the R32-private producer fence into the base R7/R13
            // post-Present publication contract. DirectTransportFrameReadyAfterPresent()
            // is still the sole owner that marks the slot published after Present;
            // it requires this exact frame identity plus producerPending.
            slot.producerPending = true;
            slot.pendingFrameId = frameId;
            slot.frameId = frameId;
            slot.published = false;
            ActiveDirectTransportSlot = slotIndex;
            return true;
        }

        void R32InvalidateResetCaches() noexcept
        {
            InvalidateEffectStateCache();
            R31ResetFastPathState();
            InvalidateLiveStateSample();
            OutRunVRRenderer::R29InvalidateRendererStateAfterExternalRestore();
            R32ForgetDirectIdentity();
            R32ClearPendingProducerFences();
            R32DirectCopyPathRejected = false;
            R32DirectCopyRejectHr = D3D_OK;
            R32FrameWorkloadCounters = {};
            R32PerfWindowCounters = {};
            R32PerfBaselineUs = 0;
            R32LastPresentEndQpc = 0;
            R32LastSpikeLogMs = 0;
        }

        void R32ResetAfterGameReset() noexcept
        {
            SetStereoRecoverySafetyThroughEpoch(
                OutRunVR::R32::RearmMonoSafetyEpoch(PresentEpoch));
            R32InvalidateResetCaches();
            ++R32ResetEpochRearms;
            if (!R32FirstResetRearmLogged)
            {
                R32FirstResetRearmLogged = true;
                spdlog::info(
                    "VR R32 RESET: R22 completed Reset lifecycle first; mono-safety/cache generations were rearmed without discarding the freshly primed viewport/scissor shadow");
            }
        }

        HRESULT __stdcall ResetDestR32(IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            const bool gameDevice = IsGameDevice(device);
            if (gameDevice)
                R32ClearPendingProducerFences();

            const HRESULT hr = R32ResetR22Hook.stdcall<HRESULT>(device, params);
            if (gameDevice)
            {
                if (SUCCEEDED(hr))
                    R32ResetAfterGameReset();
                else
                {
                    R32InvalidateResetCaches();
                    ++R32ResetFailures;
                }
            }
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
                R32Counters.liveWvp = R31TelemetryLiveWvpChecks();
                R32Counters.liveReject = R31TelemetryLiveWvpRejects();
                R32Counters.stateRecord = OutRunVR::State::StateBlockTracker::RecordingGeneration();
                R32Counters.stateApply = OutRunVR::State::StateBlockTracker::ApplyGeneration();
                R32Counters.batch = R32BatchWvpUploads;
                R32Counters.batchFail = R32BatchWvpFailures;
                R32Counters.stateFail = R32StateSnapshotFailures;
                R32Counters.zeroFallback = R32FailClosedZeroDisparityDraws;
                R32Counters.directCache = R32DirectProbeCacheHits;
                R32Counters.directFenceOk = R32DirectFenceSuccess;
                R32Counters.directFenceFallback = R32DirectFenceBudgetFallbacks;
                R32Counters.directFenceWaitSamples = R32DirectFenceWaitSamples;
                R32Counters.directFencePolls = R32DirectFencePolls;
                R32Counters.directFenceWaitUs = R32DirectFenceWaitUsTotal;
                R32Counters.directBackpressure = DirectTransportRingBackpressure;
                R32Counters.pendingDrain = R32PendingFenceDrains;
                R32Counters.pendingBlock = R32PendingFenceBlocks;
                R32Counters.pendingError = R32PendingFenceErrors;
                R32Counters.resetRearm = R32ResetEpochRearms;
                R32Counters.resetFail = R32ResetFailures;
                return;
            }
            if (now - R32Counters.lastLogMs < 5000)
                return;

            const std::uint64_t fenceSamples =
                R32DirectFenceWaitSamples - R32Counters.directFenceWaitSamples;
            const std::uint64_t fencePolls =
                R32DirectFencePolls - R32Counters.directFencePolls;
            const std::uint64_t fenceWaitUs =
                R32DirectFenceWaitUsTotal - R32Counters.directFenceWaitUs;
            const std::uint64_t fenceAvgUs =
                fenceSamples ? fenceWaitUs / fenceSamples : 0;
            const std::uint64_t frameAvgUs = R32PerfWindowCounters.frames
                ? R32PerfWindowCounters.frameUsTotal /
                    R32PerfWindowCounters.frames : 0;
            const std::uint64_t presentAvgUs = R32PerfWindowCounters.frames
                ? R32PerfWindowCounters.presentUsTotal /
                    R32PerfWindowCounters.frames : 0;
            const std::uint64_t drawAvg = R32PerfWindowCounters.frames
                ? R32PerfWindowCounters.drawsTotal /
                    R32PerfWindowCounters.frames : 0;
            const std::uint64_t primitiveAvg = R32PerfWindowCounters.frames
                ? R32PerfWindowCounters.primitivesTotal /
                    R32PerfWindowCounters.frames : 0;

            spdlog::info(
                "VR R32 PERF 5s: frame[frames={},spikes={},avgUs={},maxUs={},presentAvgUs={},presentMaxUs={}] workload[drawAvg={},drawMax={},primitiveAvg={},primitiveMax={},triangleMax={},upMax={},alphaBlendMax={},particleLikeDrawMax={},particleLikePrimitiveMax={}] liveWvpCheck={} liveReject={} stateBlock[record={},apply={}] batchWvp[ok={},fail={}] safety[stateReadFail={},forcedZero={}] direct[probeCacheHit={},producerFenceOk={},producerBudgetFallback={},fenceSamples={},fencePolls={},fenceAvgUs={},fenceMaxUs={},backpressure={},pendingDrain={},pendingBlock={},pendingError={}] reset[rearm={},fail={}]",
                R32PerfWindowCounters.frames,
                R32PerfWindowCounters.spikes,
                frameAvgUs,
                R32PerfWindowCounters.maxFrameUs,
                presentAvgUs,
                R32PerfWindowCounters.maxPresentUs,
                drawAvg,
                R32PerfWindowCounters.maxDraws,
                primitiveAvg,
                R32PerfWindowCounters.maxPrimitives,
                R32PerfWindowCounters.maxTriangles,
                R32PerfWindowCounters.maxUpDraws,
                R32PerfWindowCounters.maxAlphaBlendDraws,
                R32PerfWindowCounters.maxParticleLikeDraws,
                R32PerfWindowCounters.maxParticleLikePrimitives,
                R31TelemetryLiveWvpChecks() - R32Counters.liveWvp,
                R31TelemetryLiveWvpRejects() - R32Counters.liveReject,
                OutRunVR::State::StateBlockTracker::RecordingGeneration() - R32Counters.stateRecord,
                OutRunVR::State::StateBlockTracker::ApplyGeneration() - R32Counters.stateApply,
                R32BatchWvpUploads - R32Counters.batch,
                R32BatchWvpFailures - R32Counters.batchFail,
                R32StateSnapshotFailures - R32Counters.stateFail,
                R32FailClosedZeroDisparityDraws - R32Counters.zeroFallback,
                R32DirectProbeCacheHits - R32Counters.directCache,
                R32DirectFenceSuccess - R32Counters.directFenceOk,
                R32DirectFenceBudgetFallbacks - R32Counters.directFenceFallback,
                fenceSamples,
                fencePolls,
                fenceAvgUs,
                R32DirectFenceWaitUsMax,
                DirectTransportRingBackpressure - R32Counters.directBackpressure,
                R32PendingFenceDrains - R32Counters.pendingDrain,
                R32PendingFenceBlocks - R32Counters.pendingBlock,
                R32PendingFenceErrors - R32Counters.pendingError,
                R32ResetEpochRearms - R32Counters.resetRearm,
                R32ResetFailures - R32Counters.resetFail);

            R32Counters.lastLogMs = now;
            R32Counters.liveWvp = R31TelemetryLiveWvpChecks();
            R32Counters.liveReject = R31TelemetryLiveWvpRejects();
            R32Counters.stateRecord = OutRunVR::State::StateBlockTracker::RecordingGeneration();
            R32Counters.stateApply = OutRunVR::State::StateBlockTracker::ApplyGeneration();
            R32Counters.batch = R32BatchWvpUploads;
            R32Counters.batchFail = R32BatchWvpFailures;
            R32Counters.stateFail = R32StateSnapshotFailures;
            R32Counters.zeroFallback = R32FailClosedZeroDisparityDraws;
            R32Counters.directCache = R32DirectProbeCacheHits;
            R32Counters.directFenceOk = R32DirectFenceSuccess;
            R32Counters.directFenceFallback = R32DirectFenceBudgetFallbacks;
            R32Counters.directFenceWaitSamples = R32DirectFenceWaitSamples;
            R32Counters.directFencePolls = R32DirectFencePolls;
            R32Counters.directFenceWaitUs = R32DirectFenceWaitUsTotal;
            R32Counters.directBackpressure = DirectTransportRingBackpressure;
            R32Counters.pendingDrain = R32PendingFenceDrains;
            R32Counters.pendingBlock = R32PendingFenceBlocks;
            R32Counters.pendingError = R32PendingFenceErrors;
            R32Counters.resetRearm = R32ResetEpochRearms;
            R32Counters.resetFail = R32ResetFailures;
            R32DirectFenceWaitUsMax = 0;
            R32PerfWindowCounters = {};
        }

        HRESULT __stdcall PresentDestR32(IDirect3DDevice9* device,
            const RECT* sourceRect, const RECT* destRect,
            HWND destWindowOverride, const RGNDATA* dirtyRegion)
        {
            const bool gameDevice = IsGameDevice(device);
            const R32StereoWorkloadSnapshot stereo =
                gameDevice ? R32CaptureStereoWorkload()
                           : R32StereoWorkloadSnapshot{};
            LARGE_INTEGER presentStart{};
            if (gameDevice && Settings::VRTelemetry)
                QueryPerformanceCounter(&presentStart);

            const HRESULT hr = R32PresentR13Hook.stdcall<HRESULT>(device,
                sourceRect, destRect, destWindowOverride, dirtyRegion);

            if (gameDevice)
            {
                LARGE_INTEGER presentEnd{};
                if (Settings::VRTelemetry)
                    QueryPerformanceCounter(&presentEnd);
                R32FinalizeFramePerf(
                    presentStart.QuadPart, presentEnd.QuadPart, stereo);
                R32LogPerfWindow();
            }
            return hr;
        }

        void R32RollbackHooks() noexcept
        {
            R32PresentR13Hook = {};
            R32ResolveDirectR13Hook = {};
            R32ResetR22Hook = {};
        }

        bool R32EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R32ResetR22Hook,
                &R32ResolveDirectR13Hook,
                &R32PresentR13Hook
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
                const auto r31 = R31InstallStatus();
                const auto r22 = R22InstallStatus();
                const auto r13 = R13InstallStatus();
                if (r31 == State::Failed || r22 == State::Failed ||
                    r13 == R13InstallStatusValue::Failed)
                {
                    R32InstallState.store(State::Failed, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR32Review", false);
                    return 0;
                }
                if (r31 == State::Ready && r22 == State::Ready &&
                    r13 == R13InstallStatusValue::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R32ResetR22Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR22), ResetDestR32, disabled);
                    R32ResolveDirectR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResolveDirectTransportR13),
                        ResolveDirectTransportR32, disabled);
                    R32PresentR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&PresentDestR13), PresentDestR32, disabled);
                    if (!R32EnableHooks())
                    {
                        R32RollbackHooks();
                        R32InstallState.store(State::Failed,
                            std::memory_order_release);
                        HookManager::ReportAsyncResult(
                            "OpenXRVRStereoR32Review", false);
                        spdlog::error(
                            "VR R32: lifecycle/DirectGPU hook transaction was partial; R30 draw + R31 StateBlock/R22 lifecycle remain authoritative");
                        return 0;
                    }

                    R32InstallState.store(State::Ready, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR32Review", true);
                    spdlog::info(
                        "VR R32 REVIEW2: Reset/Present/DirectGPU lifecycle + fail-closed helpers + cached D3D9Ex interop + pending-fence-safe producer ring READY; R33 owns draw dispatch");
                    return 0;
                }
                Sleep(25);
            }

            R32InstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVRStereoR32Review", false);
            spdlog::error("VR R32: timed out waiting for R31/R22/R13 prerequisites");
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

    inline OutRunVR::RuntimeEligibility::InstallState
    R32InstallStatus() noexcept
    {
        return R32InstallState.load(std::memory_order_acquire);
    }
}
