// R32 review-consolidation overlay.
//
// Keeps R31/R29/R14 correctness policy while consolidating the reviewed hot
// paths. Review-2 additionally makes R22 the reset owner and prevents reuse of a
// DirectGPU producer slot while a timed-out D3D9 EVENT query is still pending.

#include "r32_policy.hpp"
#include "../core/r32_review_api.hpp"
#include "../core/r31_support_api.hpp"
#include "../core/r30_support_api.hpp"
#ifndef OUTRUN_VR_REFACTOR_SPLIT_R32_R31
#include "stereo_renderer_r31.cpp"
#endif

namespace OutRunVRStereo
{
    namespace
    {

        std::uint64_t R32BatchWvpUploads = 0;
        std::uint64_t R32BatchWvpFailures = 0;
        std::uint64_t R32StateSnapshotFailures = 0;
        std::uint64_t R32FailClosedZeroDisparityDraws = 0;
        std::uint64_t R32ResetEpochRearms = 0;
        std::uint64_t R32ResetFailures = 0;
        std::uint64_t R32DirectProbeCacheHits = 0;
        std::uint64_t R32DirectIdentityInvalidations = 0;
        std::uint64_t R32PendingFenceErrors = 0;
        bool R32FirstStateSnapshotFailureLogged = false;
        bool R32FirstBatchWvpLogged = false;
        bool R32FirstResetRearmLogged = false;
        bool R32FirstDirectCopyRejectLogged = false;
        bool R32DirectCopyPathRejected = false;
        HRESULT R32DirectCopyRejectHr = D3D_OK;

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
            std::uint64_t directBackpressure = 0;
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
            const auto route = R31SupportTelemetryFrameSnapshot();
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
            if (!R30SupportTelemetryEnabled() || !R30SupportIsGameDevice(device) ||
                R30SupportInternalStereoPassActive())
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

            R30SupportEffectTelemetrySnapshot effect{};
            if (!R30SupportTryGetEffectTelemetrySnapshot(effect))
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
            if (!R30SupportTelemetryEnabled())
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
                "VR R32 FRAME SPIKE: frameUs={} baselineUs={} presentUs={} workload[draws={},primitives={},triangles={},indexed={},up={},alphaBlend={},alphaBlendPrimitives={},alphaTest={},particleLikeDraws={},particleLikePrimitives={},effectUnknown={}] stereo[main={},offscreen={},aux={},fastWorld={},hud={},fallback={},fragile={},unstable={}]",
                frameUs, baselineBefore, presentUs,
                frame.draws, frame.primitives, frame.triangles,
                frame.indexedDraws, frame.upDraws,
                frame.alphaBlendDraws, frame.alphaBlendPrimitives,
                frame.alphaTestDraws, frame.particleLikeDraws,
                frame.particleLikePrimitives, frame.effectUnknownDraws,
                stereo.main, stereo.offscreen, stereo.aux,
                stereo.fastWorld, stereo.hud, stereo.fallback,
                stereo.fragile, stereo.unstable);
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
            if (R30SupportTelemetryEnabled())
                ++R32BatchWvpUploads;
            if (!OutRunVR::D3D9::SetVertexShaderConstantBatch(
                    device, OutRunWvpRegister, constants,
                    OutRunWvpRegisterCount))
            {
                ++R32BatchWvpFailures;
                return false;
            }
            if (R30SupportTelemetryEnabled() && !R32FirstBatchWvpLogged)
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
                return R31SupportGetSavedViewport(device, viewport);
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
            if (!R30SupportIsGameDevice(device) || R30SupportInternalStereoPassActive() ||
                !R30SupportTargetIsBackBuffer() || !R30SupportStereoWanted() ||
                !R30SupportStereoBaselineSeeded())
                return lowerDraw();

            OutRunVR::D3D9::LiveEffectRenderStateSnapshot snapshot{};
            if (R32ReadEffectSnapshot(device, snapshot))
                return lowerDraw();

            const std::uintptr_t savedIdentity =
                R30SupportExchangeVertexShaderIdentity(0);
            const HRESULT hr = lowerDraw();
            R30SupportRestoreVertexShaderIdentityIfEmpty(savedIdentity);
            ++R32FailClosedZeroDisparityDraws;
            return hr;
        }

        void R32ForgetDirectIdentity() noexcept
        {
            R32DirectHostPid = 0;
            R32DirectHostLuidLow = 0;
            R32DirectHostLuidHigh = 0;
        }

        bool R32DirectIdentityMatches() noexcept
        {
            R30SupportDirectTransportIdentity identity{};
            return R30SupportTryGetDirectTransportIdentity(identity) &&
                R32DirectHostPid != 0 &&
                R32DirectHostPid == identity.hostPid &&
                R32DirectHostLuidLow == identity.hostAdapterLuidLow &&
                R32DirectHostLuidHigh == identity.hostAdapterLuidHigh;
        }

        void R32InvalidateDirectInteropOnly() noexcept
        {
            // Host PID/LUID changed. The dedicated ACK mapping belongs to the
            // previous host process object too, so drop that view/handle before
            // rebuilding the shared-eye transport against the new identity.
            R30SupportReleaseDirectAckState();
            R32DirectCopyPathRejected = false;
            R32DirectCopyRejectHr = D3D_OK;
            R30SupportReleaseDirectTransportInterop();
            R32ForgetDirectIdentity();
            ++R32DirectIdentityInvalidations;
        }

        bool R32EnsureDirectResources(IDirect3DDevice9* device) noexcept
        {
            if (R30SupportDirectTransportResourcesReady() &&
                R32DirectIdentityMatches())
            {
                if (R30SupportTelemetryEnabled()) ++R32DirectProbeCacheHits;
                return true;
            }

            if (R30SupportDirectTransportResourcesReady() &&
                !R32DirectIdentityMatches())
                R32InvalidateDirectInteropOnly();

            if (!R30SupportEnsureDirectTransportResources(device))
                return false;

            R30SupportDirectTransportIdentity identity{};
            if (!R30SupportTryGetDirectTransportIdentity(identity))
                return false;

            R32DirectHostPid = identity.hostPid;
            R32DirectHostLuidLow = identity.hostAdapterLuidLow;
            R32DirectHostLuidHigh = identity.hostAdapterLuidHigh;
            return true;
        }

        template <typename LowerResolve>
        bool R32ResolveDirectTransport(IDirect3DDevice9* device,
            std::uint32_t frameId, LowerResolve&& lowerResolve) noexcept
        {
            if (!R30SupportOverlayReadyForTransport())
                return lowerResolve();
            R30SupportDirectTransportSourceSurfaces sourceSurfaces{};
            if (!frameId || !R32EnsureDirectResources(device) ||
                !R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces))
                return false;
            // R32EnsureDirectResources must run before this cached rejection:
            // host PID/LUID or transport-generation changes invalidate the old
            // interop identity and clear the rejection automatically.
            if (R32DirectCopyPathRejected)
                return false;

            const std::uint32_t preferred =
                (frameId - 1u) % OutRunVR::RenderFrameRingSize;
            std::uint32_t selected = OutRunVR::RenderFrameRingSize;
            bool ackBlocked = false;
            R30SupportGpuCompletionSnapshot ackSnapshot{};
            bool ackSnapshotRead = false;
            bool ackSnapshotValid = false;

            // Preserve the R38 free-slot contract at the final R33/R32 owner.
            // A slow producer fence or host ACK on the preferred modulo slot
            // must not force DirectGPU fallback while another ring slot is free.
            for (std::uint32_t offset = 0;
                 offset < OutRunVR::RenderFrameRingSize; ++offset)
            {
                const std::uint32_t index =
                    (preferred + offset) % OutRunVR::RenderFrameRingSize;
                auto& candidate = DirectTransportSlots[index];

                // DirectTransportFrameReadyAfterPresent() may leave an
                // unpublished slot quarantined on S_FALSE. Reclaim it only
                // after the same EVENT proves completion; a query error keeps
                // the whole DirectGPU path fail-closed.
                const HRESULT ready =
                    R30SupportPollDirectTransportSlotProducer(index);
                if (ready == S_FALSE)
                {
                    continue;
                }
                if (FAILED(ready))
                {
                    R32DirectCopyPathRejected = true;
                    R32DirectCopyRejectHr = ready;
                    if (R30SupportTelemetryEnabled()) ++R32PendingFenceErrors;
                    return false;
                }

                if (candidate.published && candidate.frameId)
                {
                    // R13 still owns ACK mapping/rebind policy behind the R30
                    // support facade. It performs at most one bounded stale-mapping reopen/retry,
                    // so this final owner samples that whole-ring state exactly
                    // once per resolve scan and reuses it for every candidate.
                    if (!ackSnapshotRead)
                    {
                        ackSnapshotValid =
                            R30SupportTryGetGpuCompletionSnapshot(ackSnapshot);
                        ackSnapshotRead = true;
                    }

                    const bool ackValid = ackSnapshotValid;
                    const std::uint32_t gpuCompleted = ackValid
                        ? ackSnapshot.completedFrameId[index] : 0;

                    if (!ackValid ||
                        !FrameIdAtOrAfter(gpuCompleted, candidate.frameId))
                    {
                        ackBlocked = true;
                        continue;
                    }

                    // The host completed this exact published frame. Retire the
                    // old publication before writing new eye pixels into the
                    // shared textures.
                    R30SupportRetireDirectTransportSlotPublication(index);
                }

                selected = index;
                break;
            }

            if (selected >= OutRunVR::RenderFrameRingSize)
            {
                if (ackBlocked)
                    R30SupportNoteSafeAckBackpressure();
                R30SupportNoteDirectTransportRingBackpressure();
                return false;
            }

            auto& slot = DirectTransportSlots[selected];
            {
                InternalPassScope guard;
                const HRESULT leftCopy = device->StretchRect(
                    sourceSurfaces.left, nullptr,
                    slot.leftSurface, nullptr, D3DTEXF_NONE);
                const HRESULT rightCopy = SUCCEEDED(leftCopy)
                    ? device->StretchRect(sourceSurfaces.right, nullptr,
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
                    if (R30SupportTelemetryEnabled()) ++R32PendingFenceErrors;
                    return false;
                }
            }

            // Do not spin on the producer EVENT before Present. Present is the
            // flush boundary, and DirectTransportFrameReadyAfterPresent() is
            // already the sole publication gate: it waits a bounded 1 ms after
            // Present, publishes only on completion, and leaves S_FALSE slots
            // quarantined for the next ring scan. Avoiding the redundant
            // pre-Present 2 ms wait removes a frame-pacing stall without
            // weakening shared-eye immutability or host ACK ownership.
            R30SupportMarkDirectTransportSlotPending(selected, frameId);
            R30SupportSetActiveDirectTransportSlot(selected);
            return true;
        }

        void R32InvalidateResetCaches() noexcept
        {
            R30SupportInvalidateEffectStateCache();
            R31SupportResetFastPathState();
            R30SupportInvalidateLiveStateSample();
            R30SupportInvalidateRendererStateAfterExternalRestore();
            R32ForgetDirectIdentity();
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
                OutRunVR::R32::RearmMonoSafetyEpoch(R30SupportPresentEpoch()));
            R32InvalidateResetCaches();
            ++R32ResetEpochRearms;
            if (!R32FirstResetRearmLogged)
            {
                R32FirstResetRearmLogged = true;
                spdlog::info(
                    "VR R32 RESET: R22 completed Reset lifecycle first; mono-safety/cache generations were rearmed without discarding the freshly primed viewport/scissor shadow");
            }
        }

        template <typename LowerReset>
        HRESULT R32WithResetLifecycle(IDirect3DDevice9* device,
            LowerReset&& lowerReset) noexcept
        {
            const HRESULT hr = lowerReset();
            const bool gameDevice = R30SupportIsGameDevice(device);
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
            if (!R30SupportTelemetryEnabled())
                return;
            const ULONGLONG now = GetTickCount64();
            if (R32Counters.lastLogMs == 0)
            {
                R32Counters.lastLogMs = now;
                R32Counters.liveWvp = R31SupportTelemetryLiveWvpChecks();
                R32Counters.liveReject = R31SupportTelemetryLiveWvpRejects();
                R32Counters.stateRecord = OutRunVR::State::StateBlockTracker::RecordingGeneration();
                R32Counters.stateApply = OutRunVR::State::StateBlockTracker::ApplyGeneration();
                R32Counters.batch = R32BatchWvpUploads;
                R32Counters.batchFail = R32BatchWvpFailures;
                R32Counters.stateFail = R32StateSnapshotFailures;
                R32Counters.zeroFallback = R32FailClosedZeroDisparityDraws;
                R32Counters.directCache = R32DirectProbeCacheHits;
                R32Counters.directBackpressure =
                    R30SupportDirectTransportRingBackpressureCount();
                R32Counters.pendingError = R32PendingFenceErrors;
                R32Counters.resetRearm = R32ResetEpochRearms;
                R32Counters.resetFail = R32ResetFailures;
                return;
            }
            if (now - R32Counters.lastLogMs < 5000)
                return;

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
                "VR R32 PERF 5s: frame[frames={},spikes={},avgUs={},maxUs={},presentAvgUs={},presentMaxUs={}] workload[drawAvg={},drawMax={},primitiveAvg={},primitiveMax={},triangleMax={},upMax={},alphaBlendMax={},particleLikeDrawMax={},particleLikePrimitiveMax={}] liveWvpCheck={} liveReject={} stateBlock[record={},apply={}] batchWvp[ok={},fail={}] safety[stateReadFail={},forcedZero={}] direct[probeCacheHit={},backpressure={},pendingError={}] reset[rearm={},fail={}]",
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
                R31SupportTelemetryLiveWvpChecks() - R32Counters.liveWvp,
                R31SupportTelemetryLiveWvpRejects() - R32Counters.liveReject,
                OutRunVR::State::StateBlockTracker::RecordingGeneration() - R32Counters.stateRecord,
                OutRunVR::State::StateBlockTracker::ApplyGeneration() - R32Counters.stateApply,
                R32BatchWvpUploads - R32Counters.batch,
                R32BatchWvpFailures - R32Counters.batchFail,
                R32StateSnapshotFailures - R32Counters.stateFail,
                R32FailClosedZeroDisparityDraws - R32Counters.zeroFallback,
                R32DirectProbeCacheHits - R32Counters.directCache,
                R30SupportDirectTransportRingBackpressureCount() -
                    R32Counters.directBackpressure,
                R32PendingFenceErrors - R32Counters.pendingError,
                R32ResetEpochRearms - R32Counters.resetRearm,
                R32ResetFailures - R32Counters.resetFail);

            R32Counters.lastLogMs = now;
            R32Counters.liveWvp = R31SupportTelemetryLiveWvpChecks();
            R32Counters.liveReject = R31SupportTelemetryLiveWvpRejects();
            R32Counters.stateRecord = OutRunVR::State::StateBlockTracker::RecordingGeneration();
            R32Counters.stateApply = OutRunVR::State::StateBlockTracker::ApplyGeneration();
            R32Counters.batch = R32BatchWvpUploads;
            R32Counters.batchFail = R32BatchWvpFailures;
            R32Counters.stateFail = R32StateSnapshotFailures;
            R32Counters.zeroFallback = R32FailClosedZeroDisparityDraws;
            R32Counters.directCache = R32DirectProbeCacheHits;
            R32Counters.directBackpressure =
                R30SupportDirectTransportRingBackpressureCount();
            R32Counters.pendingError = R32PendingFenceErrors;
            R32Counters.resetRearm = R32ResetEpochRearms;
            R32Counters.resetFail = R32ResetFailures;
            R32PerfWindowCounters = {};
        }

        template <typename LowerPresent>
        HRESULT R32WithPresentTelemetry(IDirect3DDevice9* device,
            LowerPresent&& lowerPresent) noexcept
        {
            const bool gameDevice = R30SupportIsGameDevice(device);
            const R32StereoWorkloadSnapshot stereo =
                gameDevice ? R32CaptureStereoWorkload()
                           : R32StereoWorkloadSnapshot{};
            LARGE_INTEGER presentStart{};
            if (gameDevice && R30SupportTelemetryEnabled())
                QueryPerformanceCounter(&presentStart);

            const HRESULT hr = lowerPresent();

            if (gameDevice)
            {
                LARGE_INTEGER presentEnd{};
                if (R30SupportTelemetryEnabled())
                    QueryPerformanceCounter(&presentEnd);
                R32FinalizeFramePerf(
                    presentStart.QuadPart, presentEnd.QuadPart, stereo);
                R32LogPerfWindow();
            }
            return hr;
        }

        // R32 is a hook-free functional owner. Its helpers are consumed by
        // the R33 final dispatcher after R33 verifies R31/R22/R13 readiness.
    }

    bool R32ReviewEffectIsFragileLive(
        IDirect3DDevice9* device, bool& fragile) noexcept
    {
        return R32EffectIsFragileLive(device, fragile);
    }

    bool R32ReviewGetSavedViewport(
        IDirect3DDevice9* device, D3DVIEWPORT9& viewport) noexcept
    {
        return R32GetSavedViewport(device, viewport);
    }

    bool R32ReviewSetWvpBatch(
        IDirect3DDevice9* device, const float* constants) noexcept
    {
        return R32SetWvpBatch(device, constants);
    }

    bool R32ReviewRestoreRightPassState(
        IDirect3DDevice9* device,
        IDirect3DSurface9* savedRt,
        IDirect3DSurface9* savedDepth,
        const D3DVIEWPORT9& savedViewport,
        const float* originalConstants,
        bool restoreWvp) noexcept
    {
        return R32RestoreRightPassState(
            device, savedRt, savedDepth, savedViewport,
            originalConstants, restoreWvp);
    }

    void R32ReviewObserveFrameWorkload(
        IDirect3DDevice9* device,
        D3DPRIMITIVETYPE type,
        UINT primitiveCount,
        bool indexed,
        bool up) noexcept
    {
        R32ObserveFrameWorkload(device, type, primitiveCount, indexed, up);
    }

    HRESULT R32ReviewRunLowerFailClosedCallback(
        IDirect3DDevice9* device,
        R32HResultCallback callback,
        void* context) noexcept
    {
        if (!callback)
            return E_INVALIDARG;
        return R32LowerFailClosed(device, [callback, context]() noexcept {
            return callback(context);
        });
    }

    bool R32ReviewResolveDirectTransportCallback(
        IDirect3DDevice9* device,
        std::uint32_t frameId,
        R32BoolCallback callback,
        void* context) noexcept
    {
        if (!callback)
            return false;
        return R32ResolveDirectTransport(
            device, frameId, [callback, context]() noexcept {
                return callback(context);
            });
    }

    HRESULT R32ReviewRunResetLifecycleCallback(
        IDirect3DDevice9* device,
        R32HResultCallback callback,
        void* context) noexcept
    {
        if (!callback)
            return E_INVALIDARG;
        return R32WithResetLifecycle(device, [callback, context]() noexcept {
            return callback(context);
        });
    }

    HRESULT R32ReviewRunPresentTelemetryCallback(
        IDirect3DDevice9* device,
        R32HResultCallback callback,
        void* context) noexcept
    {
        if (!callback)
            return E_INVALIDARG;
        return R32WithPresentTelemetry(device, [callback, context]() noexcept {
            return callback(context);
        });
    }
    R32ReviewInternalStereoPassScope::R32ReviewInternalStereoPassScope() noexcept
        : previous_(R30SupportExchangeInternalStereoPass(true)) {}
    R32ReviewInternalStereoPassScope::~R32ReviewInternalStereoPassScope()
    {
        R30SupportExchangeInternalStereoPass(previous_);
    }

    bool R32ReviewTelemetryEnabled() noexcept { return R30SupportTelemetryEnabled(); }
    bool R32ReviewIsGameDevice(IDirect3DDevice9* d) noexcept { return R30SupportIsGameDevice(d); }
    bool R32ReviewInternalStereoPass() noexcept { return R30SupportInternalStereoPassActive(); }
    bool R32ReviewStereoWanted() noexcept { return R30SupportStereoWanted(); }
    bool R32ReviewTargetIsBackBuffer() noexcept { return R30SupportTargetIsBackBuffer(); }
    void R32ReviewFailClosedResetBaselineState() noexcept { FailClosedResetBaselineState(); }
    void R32ReviewArmStereoRecoverySafety(std::uint64_t n) noexcept { ArmStereoRecoverySafety(n); }

    HRESULT R32ReviewRunRasterReplayGuardCallback(
        IDirect3DDevice9* d, const char* site,
        R32VoidCallback active, void* activeCtx,
        R32HResultCallback draw, void* drawCtx) noexcept
    {
        if (!draw) return E_INVALIDARG;
        R22RasterReplayGuard replay(d, site);
        if (!replay.StateValid()) return draw(drawCtx);
        if (active) active(activeCtx);
        return draw(drawCtx);
    }

    std::uint64_t R32ReviewMainDepthGeneration() noexcept { return R9MainDepthGenerationValue(); }
    bool R32ReviewMainDepthHasStencil() noexcept { return R9TrackedMainDepthHasStencil(); }
    bool R32ReviewLeftDrawMayWriteDepth(IDirect3DDevice9* d) noexcept { return LeftDrawMayWriteDepth(d); }
    bool R32ReviewLeftDrawMayWriteStencil(IDirect3DDevice9* d) noexcept { return LeftDrawMayWriteStencil(d); }
    void R32ReviewInvalidateRightDepthStencilSync(bool d, bool s) noexcept { R9InvalidateRightDepthStencilSync(d, s); }
    bool R32ReviewRightDepthInSync() noexcept { return R9IsRightDepthInSync(); }
    bool R32ReviewRightStencilInSync() noexcept { return R9IsRightStencilInSync(); }
    void R32ReviewNoteStereoDrawWithoutMonoBackup() noexcept { R9NoteStereoDrawWithoutMonoBackup(); }
    void R32ReviewNoteMainDepthContentWrite() noexcept { R9NoteMainDepthContentWrite(); }
    void R32ReviewReportStereoFailure(OutRunVR::StereoFailureReason r, const char* s, HRESULT hr) noexcept { R9Poison(r,s,hr); }
    void R32ReviewNoteRestoreFailure(const char* what) noexcept { NoteRestoreFailure(what); }

    IDirect3DSurface9* R32ReviewTrackedRenderTarget() noexcept { return TrackedRenderTarget; }
    IDirect3DSurface9* R32ReviewTrackedDepthStencil() noexcept { return TrackedDepthStencil; }
    IDirect3DSurface9* R32ReviewRightEyeSurface() noexcept { return R30SupportBorrowedRightEyeSurface(); }
    IDirect3DSurface9* R32ReviewRightEyeDepth() noexcept { return RightEyeDepth; }
    bool R32ReviewEnsureStereoResources(IDirect3DDevice9* d) noexcept { return EnsureStereoResources(d); }
    bool R32ReviewTryBootstrapRightDepth(IDirect3DDevice9* d) noexcept { return TryBootstrapRightDepthFromRecentClear(d); }
    bool R32ReviewDepthTestActive(IDirect3DDevice9* d) noexcept { return DepthTestActive(d); }
    bool R32ReviewStencilTestActive(IDirect3DDevice9* d) noexcept { return StencilTestActive(d); }
    HRESULT R32ReviewSetRenderTarget(IDirect3DDevice9* d, DWORD i, IDirect3DSurface9* s) noexcept { return SetRenderTargetHook.stdcall<HRESULT>(d,i,s); }
    HRESULT R32ReviewSetDepthStencilSurface(IDirect3DDevice9* d, IDirect3DSurface9* s) noexcept { return SetDepthStencilSurfaceHook ? SetDepthStencilSurfaceHook.stdcall<HRESULT>(d,s) : d->SetDepthStencilSurface(s); }

    std::uintptr_t R32ReviewCurrentVertexShaderIdentity() noexcept { return R30SupportCurrentVertexShaderIdentity(); }
    bool R32ReviewLiveVertexShaderMatches(IDirect3DDevice9* d, std::uintptr_t e) noexcept { return OutRunVR::D3D9::LiveVertexShaderMatches(d,e); }
    std::uint32_t R32ReviewFrameStereoPoseSequence() noexcept { return FrameStereoPoseSequence; }

    void R32ReviewRecordWorldStereoDuplicate(std::uint32_t p, const OutRunVRRenderer::LatchedStereoFrame& s) noexcept
    {
        FrameHadDuplicatedDraw = true; FrameHadWorldStereo = true; ++DuplicatedDraws; ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0) { FrameStereoPoseSequence = p; FrameStereoMetadata = s; }
    }
    void R32ReviewRecordHudStereoDuplicate() noexcept { FrameHadDuplicatedDraw = true; ++DuplicatedDraws; ++NonWorldDuplicatedDraws; }
    void R32ReviewMarkFrameRightDrawFailed() noexcept { FrameRightDrawFailed = true; }

    bool R32ReviewStableStereoBase(IDirect3DDevice9* d) noexcept { return R29StableStereoBase(d); }
    bool R32ReviewFragileEffectCached(IDirect3DDevice9* d, bool& f) noexcept { return R29FragileEffectCached(d,f); }
    void R32ReviewNoteStableTwoEyeDraw() noexcept { R29TelemetryNoteStableTwoEyeDraw(); }
    void R32ReviewObserveDispatchDraw(IDirect3DDevice9* d) noexcept { R31SupportObserveDraw(d); }
    void R32ReviewDiscardUnreliableDrawCaches() noexcept { R31SupportDiscardUnreliableDrawCaches(); }
    void R32ReviewNoteDispatchFallback() noexcept { R31SupportNoteFallback(); }
    void R32ReviewNoteDispatchFastWorld() noexcept { R31SupportNoteFastWorld(); }
    void R32ReviewNoteDispatchFragile() noexcept { R31SupportNoteFragile(); }
    void R32ReviewNoteDispatchHud() noexcept { R31SupportNoteHud(); }
    void R32ReviewNoteDispatchUnstable() noexcept { R31SupportNoteUnstable(); }

    bool R32ReviewBuildFastWorldConstants(IDirect3DDevice9* d, const OutRunVRRenderer::LatchedStereoFrame& s, R32ReviewFastWorldConstants& out) noexcept
    {
        R31SupportFastWorldConstants draw{}; if (!R31SupportBuildFastWorldConstants(d,s,draw)) return false;
        std::memcpy(out.originalConstants,draw.originalConstants,sizeof(out.originalConstants));
        std::memcpy(out.eyeConstants,draw.eyeConstants,sizeof(out.eyeConstants));
        out.poseSequence=draw.poseSequence; out.stereoFrame=s; return true;
    }

    R32ReviewScreenSpaceKind R32ReviewClassifyScreenSpacePass(IDirect3DDevice9* d) noexcept
    {
        switch (R30ClassifyScreenSpacePass(d)) {
        case R30ScreenSpaceKind::Hud2D: return R32ReviewScreenSpaceKind::Hud2D;
        case R30ScreenSpaceKind::FlatPerspectiveEffect: return R32ReviewScreenSpaceKind::FlatPerspectiveEffect;
        default: return R32ReviewScreenSpaceKind::None; }
    }
    bool R32ReviewBuildScreenSpaceEyeConstants(IDirect3DDevice9* d, const OutRunVRRenderer::LatchedStereoFrame& s, R32ReviewScreenSpaceKind k, float o[16], float e[2][16], float sc[2], float off[2]) noexcept
    {
        R30ScreenSpaceKind lower=R30ScreenSpaceKind::None;
        if(k==R32ReviewScreenSpaceKind::Hud2D) lower=R30ScreenSpaceKind::Hud2D;
        else if(k==R32ReviewScreenSpaceKind::FlatPerspectiveEffect) lower=R30ScreenSpaceKind::FlatPerspectiveEffect;
        return lower!=R30ScreenSpaceKind::None && R30BuildScreenSpaceEyeConstants(d,s,lower,o,e,sc,off);
    }
    void R32ReviewNoteScreenSpaceFovDraw() noexcept { R30TelemetryNoteScreenSpaceFovDraw(); }

    HRESULT R32ReviewTryXyzrhwPrimitiveVB(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT s,UINT p) noexcept{return R30TryXyzrhwPrimitiveVB(d,t,s,p);}
    HRESULT R32ReviewTryXyzrhwIndexedPrimitiveVB(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,INT b,UINT m,UINT n,UINT s,UINT p) noexcept{return R30TryXyzrhwIndexedPrimitiveVB(d,t,b,m,n,s,p);}
    HRESULT R32ReviewTryXyzrhwPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT p,const void* data,UINT st) noexcept{return R30TryXyzrhwPrimitiveUP(d,t,p,data,st);}
    HRESULT R32ReviewTryXyzrhwIndexedPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT m,UINT n,UINT p,const void* idx,D3DFORMAT f,const void* v,UINT st) noexcept{return R30TryXyzrhwIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st);}

    HRESULT R32ReviewCallRawDrawPrimitive(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT s,UINT p) noexcept{return DrawPrimitiveHook.stdcall<HRESULT>(d,t,s,p);}
    HRESULT R32ReviewCallRawDrawIndexedPrimitive(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,INT b,UINT m,UINT n,UINT s,UINT p) noexcept{return DrawIndexedPrimitiveHook.stdcall<HRESULT>(d,t,b,m,n,s,p);}
    HRESULT R32ReviewCallRawDrawPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT p,const void* data,UINT st) noexcept{return DrawPrimitiveUPHook.stdcall<HRESULT>(d,t,p,data,st);}
    HRESULT R32ReviewCallRawDrawIndexedPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT m,UINT n,UINT p,const void* idx,D3DFORMAT f,const void* v,UINT st) noexcept{return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(d,t,m,n,p,idx,f,v,st);}
    HRESULT R32ReviewCallRawPresent(IDirect3DDevice9* d,const RECT* s,const RECT* dst,HWND w,const RGNDATA* r) noexcept{return PresentHook.stdcall<HRESULT>(d,s,dst,w,r);}

    HRESULT R32ReviewCallLowerDrawPrimitive(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT s,UINT p) noexcept{return R30CallLowerDrawPrimitive(d,t,s,p);}
    HRESULT R32ReviewCallLowerDrawIndexedPrimitive(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,INT b,UINT m,UINT n,UINT s,UINT p) noexcept{return R30CallLowerDrawIndexedPrimitive(d,t,b,m,n,s,p);}
    HRESULT R32ReviewCallLowerDrawPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT p,const void* data,UINT st) noexcept{return R30CallLowerDrawPrimitiveUP(d,t,p,data,st);}
    HRESULT R32ReviewCallLowerDrawIndexedPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT m,UINT n,UINT p,const void* idx,D3DFORMAT f,const void* v,UINT st) noexcept{return R30CallLowerDrawIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st);}

    OutRunVR::RuntimeEligibility::InstallState R32ReviewPrerequisiteStatus() noexcept
    {
        using State=OutRunVR::RuntimeEligibility::InstallState;
        const auto a=R31SupportInstallStatus(), b=R22InstallStatus(); const auto c=R13InstallStatus();
        if(a==State::Failed||b==State::Failed||c==R13InstallStatusValue::Failed) return State::Failed;
        if(a==State::Ready&&b==State::Ready&&c==R13InstallStatusValue::Ready) return State::Ready;
        return State::Pending;
    }
    void* R32ReviewResetTarget() noexcept{return reinterpret_cast<void*>(&ResetDestR22);}
    void* R32ReviewPresentTarget() noexcept{return reinterpret_cast<void*>(&PresentDestR13);}
    void* R32ReviewDirectTransportTarget() noexcept{return reinterpret_cast<void*>(&ResolveDirectTransportR13);}
    void* R32ReviewSetRenderStateTarget() noexcept{return reinterpret_cast<void*>(&SetRenderStateDestR29);}
    void* R32ReviewDrawPrimitiveTarget() noexcept{return reinterpret_cast<void*>(&DrawPrimitiveDestR30);}
    void* R32ReviewDrawIndexedPrimitiveTarget() noexcept{return reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR30);}
    void* R32ReviewDrawPrimitiveUPTarget() noexcept{return reinterpret_cast<void*>(&DrawPrimitiveUPDestR30);}
    void* R32ReviewDrawIndexedPrimitiveUPTarget() noexcept{return reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR30);}
    IDirect3DDevice9* R32ReviewInstalledDevice() noexcept{return StereoInstalledDevice.load(std::memory_order_acquire);}

}