// R32 review-consolidation overlay.
//
// Keeps R31/R29/R14 correctness policy while consolidating the reviewed hot
// paths. Review-2 additionally makes R22 the reset owner and prevents reuse of a
// DirectGPU producer slot while a timed-out D3D9 EVENT query is still pending.

#include "r32_policy.hpp"
#include "../core/r32_review_api.hpp"
#include "../core/r31_support_api.hpp"
#include "../core/r30_support_api.hpp"
#include "vr_shared.hpp"
#include "hook_mgr.hpp"
#include "draw_state_helpers.hpp"
#include "vr_pass_policy.hpp"
#include "../state/state_block_tracker.hpp"
#include <spdlog/spdlog.h>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstring>
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
            // Capture the worst frame, not a synchronous warning for each
            // severe hitch. The five-second report keeps its full context.
            std::uint64_t worstBaselineUs = 0;
            std::uint64_t worstPresentUs = 0;
            R32FrameWorkload worstWorkload{};
            R32StereoWorkloadSnapshot worstStereo{};
        };
        thread_local R32PerfWindow R32PerfWindowCounters{};
        thread_local std::uint64_t R32PerfBaselineUs = 0;
        thread_local LONGLONG R32LastPresentEndQpc = 0;

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
            // Divide first: (end - begin) * 1,000,000 can overflow a
            // signed 64-bit counter during long-running diagnostic sessions.
            const auto elapsed = static_cast<std::uint64_t>(end - begin);
            const auto hz = static_cast<std::uint64_t>(frequency);
            const auto whole = elapsed / hz;
            const auto remainder = elapsed % hz;
            if (whole > UINT64_MAX / 1000000ULL)
                return UINT64_MAX;
            return whole * 1000000ULL + (remainder * 1000000ULL) / hz;
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
                R32LastPresentEndQpc = 0;
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
            if (frameUs > window.maxFrameUs)
            {
                window.maxFrameUs = frameUs;
                window.worstBaselineUs = baselineBefore;
                window.worstPresentUs = presentUs;
                window.worstWorkload = frame;
                window.worstStereo = stereo;
            }
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

            // No synchronous per-spike I/O: R32LogPerfWindow owns the
            // bounded report, including the worst workload and spike count.
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
                    device, R30SupportWvpFirstRegister, constants,
                    R30SupportWvpRegisterCount))
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
            const float* originalConstants, bool restoreWvp,
            bool depthlessPass,
            bool skipSavedViewportRestore) noexcept
        {
            bool ok = true;
            // D3D9 RT0 bind resets to the target's full viewport. R33
            // proves this only for a reliable and dimension-matched game RT;
            // failures and unknown RT ownership still run SetViewport.
            bool restoredRt = false;
            if (savedRt)
            {
                restoredRt = SUCCEEDED(R30SupportCallOriginalSetRenderTarget(
                    device, 0u, savedRt));
                if (!restoredRt) ok = false;
            }
            // On the proven depthless path the tracked original and right-eye
            // bindings are both null. Draw calls cannot bind depth, so do not
            // submit another SetDepthStencilSurface(nullptr) on each stereo draw.
            if (!depthlessPass)
            {
                const HRESULT depthHr = R30SupportCallOriginalSetDepthStencilSurface(
                    device, savedDepth);
                if (FAILED(depthHr)) ok = false;
            }
            if ((!restoredRt || !skipSavedViewportRestore) &&
                FAILED(device->SetViewport(&savedViewport))) ok = false;
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

            // Reuse R29's cached effect state only if its StateBlock Apply
            // generation, Present epoch and draw-serial window are trustworthy.
            // This avoids repeated D3D9 GetRenderState calls in R33's frequent
            // R29 fallback path; stale shadows keep the original live-read
            // and zero-disparity failure behavior.
            R30SupportEffectTelemetrySnapshot shadow{};
            if (OutRunVR::State::StateBlockTracker::Reliable() &&
                R30SupportTryGetEffectTelemetrySnapshot(shadow))
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
            // One resource/host-identity probe per Present. On a rebind the
            // previous path queried the identity twice (once for the cache
            // hit, then once for invalidation), even though a failed first
            // comparison already proves that this interop generation is stale.
            const bool resourcesReady =
                R30SupportDirectTransportResourcesReady();
            if (resourcesReady)
            {
                if (R32DirectIdentityMatches())
                {
                    if (R30SupportTelemetryEnabled()) ++R32DirectProbeCacheHits;
                    return true;
                }
                R32InvalidateDirectInteropOnly();
            }

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
            if (!frameId || !R32EnsureDirectResources(device))
                return false;
            // R32EnsureDirectResources must run before this cached rejection:
            // Recheck host PID/LUID first so a new interop generation can
            // clear this per-generation rejection. On a permanently rejected
            // old generation, avoid the per-Present cross-owner source-surface
            // snapshot: no GPU copy can be attempted until revalidation.
            if (R32DirectCopyPathRejected)
                return false;

            const std::uint32_t preferred =
                (frameId - 1u) % OutRunVR::RenderFrameRingSize;
            std::uint32_t selected = OutRunVR::RenderFrameRingSize;
            R30SupportDirectTransportSlotPublication selectedPublication{};
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
                const R30SupportDirectTransportSlotPublication candidate =
                    R30SupportGetDirectTransportSlotPublication(index);

                // A published slot belongs to the host until its per-slot GPU
                // completion ACK. Check that ownership before querying its
                // producer EVENT: even a completed EVENT cannot make an
                // unacknowledged published slot writable, and polling every
                // busy slot adds needless D3D9 GetData work under host load.
                if (candidate.published && candidate.frameId)
                {
                    // R13 owns mapping/rebind policy behind the R30 facade.
                    // Read one whole-ring ACK snapshot for this resolve scan.
                    if (!ackSnapshotRead)
                    {
                        ackSnapshotValid =
                            R30SupportTryGetGpuCompletionSnapshot(ackSnapshot);
                        ackSnapshotRead = true;
                    }

                    const std::uint32_t gpuCompleted = ackSnapshotValid
                        ? ackSnapshot.completedFrameId[index] : 0;
                    if (!ackSnapshotValid ||
                        !R30SupportFrameIdAtOrAfter(gpuCompleted, candidate.frameId))
                    {
                        ackBlocked = true;
                        continue;
                    }
                }

                // An ACKed published slot, or an unpublished slot quarantined
                // by S_FALSE after Present, still needs producer EVENT proof
                // before being reused. A hard query error remains fail-closed.
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

                // Keep ownership until a valid source snapshot exists.
                // The backpressured hot path never needs the cross-owner copy.
                selectedPublication = candidate;
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

            // Only snapshot on an ACK/fence-safe slot. A failed snapshot
            // must not retire the prior host-owned frame publication.
            R30SupportDirectTransportSourceSurfaces sourceSurfaces{};
            if (!R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces))
                return false;
            if (selectedPublication.published && selectedPublication.frameId)
            {
                R30SupportRetireDirectTransportSlotPublication(selected);
            }

            const R30SupportDirectTransportCopyResult copy =
                R30SupportCopyDirectTransportEyesAndIssueFence(
                device, selected, sourceSurfaces);
            if (FAILED(copy.hr))
            {
                // StretchRect commands are already queued when an EVENT
                // Issue fails. Quarantine either copy or fence failure before
                // the transport ring may consider this slot reusable.
                R32DirectCopyPathRejected = true;
                R32DirectCopyRejectHr = copy.hr;
                if (copy.copyFailed)
                {
                    if (!R32FirstDirectCopyRejectLogged)
                    {
                        R32FirstDirectCopyRejectLogged = true;
                        spdlog::warn(
                            "VR R32 D3D9Ex: shared-eye StretchRect rejected hr=0x{:08X}; DirectGPU copy path is disabled until Reset/interop revalidation instead of retrying every Present",
                            static_cast<unsigned>(R32DirectCopyRejectHr));
                    }
                }
                else
                {
                    // Copies are already queued: a failed producer EVENT must
                    // quarantine DirectGPU until Reset/interop revalidation.
                    if (R30SupportTelemetryEnabled()) ++R32PendingFenceErrors;
                }
                return false;
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
        }

        void R32ResetAfterGameReset() noexcept
        {
            R30SupportSetStereoRecoverySafetyThroughEpoch(
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
                "VR R32 PERF 5s: frame[frames={},spikes={},avgUs={},maxUs={},presentAvgUs={},presentMaxUs={}] workload[drawAvg={},drawMax={},primitiveAvg={},primitiveMax={},triangleMax={},upMax={},alphaBlendMax={},particleLikeDrawMax={},particleLikePrimitiveMax={}] liveWvpCheck={} liveReject={} stateBlock[record={},apply={}] batchWvp[ok={},fail={}] safety[stateReadFail={},forcedZero={}] direct[probeCacheHit={},backpressure={},pendingError={}] reset[rearm={},fail={}] worst[baselineUs={},presentUs={},draws={},indexed={},up={},alphaBlend={},alphaTest={},particleLike={},effectUnknown={},stereoWorld={},stereoHud={},stereoFallback={}]",
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
                R32ResetFailures - R32Counters.resetFail,
                R32PerfWindowCounters.worstBaselineUs,
                R32PerfWindowCounters.worstPresentUs,
                R32PerfWindowCounters.worstWorkload.draws,
                R32PerfWindowCounters.worstWorkload.indexedDraws,
                R32PerfWindowCounters.worstWorkload.upDraws,
                R32PerfWindowCounters.worstWorkload.alphaBlendDraws,
                R32PerfWindowCounters.worstWorkload.alphaTestDraws,
                R32PerfWindowCounters.worstWorkload.particleLikeDraws,
                R32PerfWindowCounters.worstWorkload.effectUnknownDraws,
                R32PerfWindowCounters.worstStereo.fastWorld,
                R32PerfWindowCounters.worstStereo.hud,
                R32PerfWindowCounters.worstStereo.fallback);

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
            const bool samplePerf = gameDevice && R30SupportTelemetryEnabled();
            R32StereoWorkloadSnapshot stereo{};
            LARGE_INTEGER presentStart{};
            if (samplePerf)
            {
                // Route snapshots are diagnostic-only; avoid cross-TU reads
                // while telemetry is disabled on the gameplay Present path.
                stereo = R32CaptureStereoWorkload();
                QueryPerformanceCounter(&presentStart);
            }

            const HRESULT hr = lowerPresent();

            if (gameDevice)
            {
                if (samplePerf)
                {
                    LARGE_INTEGER presentEnd{};
                    QueryPerformanceCounter(&presentEnd);
                    R32FinalizeFramePerf(
                        presentStart.QuadPart, presentEnd.QuadPart, stereo);
                    R32LogPerfWindow();
                }
                else
                {
                    // Disable/re-enable begins a new measurement window.
                    R32FrameWorkloadCounters = {};
                    R32PerfWindowCounters = {};
                    R32PerfBaselineUs = 0;
                    R32Counters = {};
                    R32LastPresentEndQpc = 0;
                }
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
        bool restoreWvp, bool depthlessPass,
        bool skipSavedViewportRestore) noexcept
    {
        return R32RestoreRightPassState(
            device, savedRt, savedDepth, savedViewport,
            originalConstants, restoreWvp, depthlessPass,
            skipSavedViewportRestore);
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
    void R32ReviewFailClosedResetBaselineState() noexcept { R30SupportFailClosedResetBaselineState(); }
    void R32ReviewArmStereoRecoverySafety(std::uint64_t n) noexcept { R30SupportArmStereoRecoverySafety(n); }

    HRESULT R32ReviewRunRasterReplayGuardCallback(
        IDirect3DDevice9* d, const char* site,
        R32VoidCallback active, void* activeCtx,
        R32HResultCallback draw, void* drawCtx) noexcept
    {
        return R30SupportRunRasterReplayGuardCallback(
            d, site, active, activeCtx, draw, drawCtx);
    }

    std::uint64_t R32ReviewMainDepthGeneration() noexcept { return R30SupportMainDepthGeneration(); }
    bool R32ReviewMainDepthHasStencil() noexcept { return R30SupportMainDepthHasStencil(); }
    bool R32ReviewLeftDrawMayWriteDepth(IDirect3DDevice9* d) noexcept { return R30SupportLeftDrawMayWriteDepth(d); }
    bool R32ReviewLeftDrawMayWriteStencil(IDirect3DDevice9* d) noexcept { return R30SupportLeftDrawMayWriteStencil(d); }
    void R32ReviewInvalidateRightDepthStencilSync(bool d, bool s) noexcept { R30SupportInvalidateRightDepthStencilSync(d, s); }
    bool R32ReviewRightDepthInSync() noexcept { return R30SupportRightDepthInSync(); }
    bool R32ReviewRightStencilInSync() noexcept { return R30SupportRightStencilInSync(); }
    void R32ReviewNoteStereoDrawWithoutMonoBackup() noexcept { R30SupportNoteStereoDrawWithoutMonoBackup(); }
    void R32ReviewNoteMainDepthContentWrite() noexcept { R30SupportNoteMainDepthContentWrite(); }
    void R32ReviewReportStereoFailure(OutRunVR::StereoFailureReason r, const char* s, HRESULT hr) noexcept { R30SupportReportStereoFailure(r,s,hr); }
    void R32ReviewNoteRestoreFailure(const char* what) noexcept { R30SupportNoteRestoreFailure(what); }

    IDirect3DSurface9* R32ReviewTrackedRenderTarget() noexcept { return R30SupportBorrowedTrackedRenderTarget(); }
    IDirect3DSurface9* R32ReviewTrackedDepthStencil() noexcept { return R30SupportBorrowedTrackedDepthStencil(); }
    IDirect3DSurface9* R32ReviewRightEyeSurface() noexcept { return R30SupportBorrowedRightEyeSurface(); }
    IDirect3DSurface9* R32ReviewRightEyeDepth() noexcept { return R30SupportBorrowedRightEyeDepth(); }
    bool R32ReviewEnsureStereoResources(IDirect3DDevice9* d) noexcept { return R30SupportEnsureStereoResources(d); }
    bool R32ReviewTryBootstrapRightDepth(IDirect3DDevice9* d) noexcept { return R30SupportTryBootstrapRightDepth(d); }
    bool R32ReviewDepthTestActive(IDirect3DDevice9* d) noexcept { return R30SupportDepthTestActive(d); }
    bool R32ReviewStencilTestActive(IDirect3DDevice9* d) noexcept { return R30SupportStencilTestActive(d); }
    HRESULT R32ReviewSetRenderTarget(IDirect3DDevice9* d, DWORD i, IDirect3DSurface9* s) noexcept { return R30SupportCallOriginalSetRenderTarget(d,i,s); }
    HRESULT R32ReviewSetDepthStencilSurface(IDirect3DDevice9* d, IDirect3DSurface9* s) noexcept { return R30SupportCallOriginalSetDepthStencilSurface(d,s); }

    std::uintptr_t R32ReviewCurrentVertexShaderIdentity() noexcept { return R30SupportCurrentVertexShaderIdentity(); }
    bool R32ReviewLiveVertexShaderMatches(IDirect3DDevice9* d, std::uintptr_t e) noexcept { return OutRunVR::D3D9::LiveVertexShaderMatches(d,e); }
    std::uint32_t R32ReviewFrameStereoPoseSequence() noexcept { return R30SupportFrameStereoPoseSequence(); }

    void R32ReviewRecordWorldStereoDuplicate(std::uint32_t p, const OutRunVRRenderer::LatchedStereoFrame& s) noexcept
    {
        R30SupportRecordWorldStereoDuplicate(p, s);
    }
    void R32ReviewRecordHudStereoDuplicate() noexcept { R30SupportRecordHudStereoDuplicate(); }
    void R32ReviewMarkFrameRightDrawFailed() noexcept { R30SupportMarkFrameRightDrawFailed(); }

    bool R32ReviewStableStereoBase(IDirect3DDevice9* d) noexcept { return R30SupportStableStereoBase(d); }
    bool R32ReviewFragileEffectCached(IDirect3DDevice9* d, bool& f) noexcept { return R30SupportFragileEffectCached(d,f); }
    void R32ReviewNoteStableTwoEyeDraw() noexcept { R30SupportNoteStableTwoEyeDraw(); }
    void R32ReviewObserveDispatchDraw(IDirect3DDevice9* d) noexcept { R31SupportObserveDraw(d); }
    void R32ReviewDiscardUnreliableDrawCaches() noexcept { R31SupportDiscardUnreliableDrawCaches(); }
    void R32ReviewNoteDispatchFallback() noexcept { R31SupportNoteFallback(); }
    void R32ReviewNoteDispatchFastWorld() noexcept { R31SupportNoteFastWorld(); }
    void R32ReviewNoteDispatchFragile() noexcept { R31SupportNoteFragile(); }
    void R32ReviewNoteDispatchHud() noexcept { R31SupportNoteHud(); }
    void R32ReviewNoteDispatchUnstable() noexcept { R31SupportNoteUnstable(); }

    bool R32ReviewBuildFastWorldConstants(IDirect3DDevice9* d, const OutRunVRRenderer::LatchedStereoFrame& s, R32ReviewFastWorldConstants& out) noexcept
    {
        // Reuse the caller's validated destination, not a second stack copy.
        return R31SupportBuildFastWorldConstants(d, s, out);
    }

    R32ReviewScreenSpaceKind R32ReviewClassifyScreenSpacePass(
        IDirect3DDevice9* device) noexcept
    {
        switch (R30SupportClassifyScreenSpacePass(device))
        {
        case R30SupportScreenSpaceKind::Hud2D:
            return R32ReviewScreenSpaceKind::Hud2D;
        case R30SupportScreenSpaceKind::FlatPerspectiveEffect:
            return R32ReviewScreenSpaceKind::FlatPerspectiveEffect;
        default:
            return R32ReviewScreenSpaceKind::None;
        }
    }

    bool R32ReviewBuildScreenSpaceEyeConstants(
        IDirect3DDevice9* d, const OutRunVRRenderer::LatchedStereoFrame& s,
        R32ReviewScreenSpaceKind kind, float original[16],
        float eyeConstants[2][16], float eyeScale[2], float eyeOffset[2]) noexcept
    {
        R30SupportScreenSpaceKind lower = R30SupportScreenSpaceKind::None;
        if (kind == R32ReviewScreenSpaceKind::Hud2D)
            lower = R30SupportScreenSpaceKind::Hud2D;
        else if (kind == R32ReviewScreenSpaceKind::FlatPerspectiveEffect)
            lower = R30SupportScreenSpaceKind::FlatPerspectiveEffect;
        return lower != R30SupportScreenSpaceKind::None &&
            R30SupportBuildScreenSpaceEyeConstants(
                d, s, lower, original, eyeConstants, eyeScale, eyeOffset);
    }

    void R32ReviewNoteScreenSpaceFovDraw() noexcept
    {
        R30SupportNoteScreenSpaceFovDraw();
    }

    HRESULT R32ReviewTryXyzrhwPrimitiveVB(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept
    { return R30SupportTryXyzrhwPrimitiveVB(d,t,s,p); }
    HRESULT R32ReviewTryXyzrhwIndexedPrimitiveVB(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        INT b, UINT m, UINT n, UINT s, UINT p) noexcept
    { return R30SupportTryXyzrhwIndexedPrimitiveVB(d,t,b,m,n,s,p); }
    HRESULT R32ReviewTryXyzrhwPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT p,
        const void* data, UINT st) noexcept
    { return R30SupportTryXyzrhwPrimitiveUP(d,t,p,data,st); }
    HRESULT R32ReviewTryXyzrhwIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        UINT m, UINT n, UINT p, const void* idx,
        D3DFORMAT f, const void* v, UINT st) noexcept
    { return R30SupportTryXyzrhwIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st); }

    HRESULT R32ReviewCallRawDrawPrimitive(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT s,UINT p) noexcept{return R30SupportCallRawDrawPrimitive(d,t,s,p);}
    HRESULT R32ReviewCallRawDrawIndexedPrimitive(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,INT b,UINT m,UINT n,UINT s,UINT p) noexcept{return R30SupportCallRawDrawIndexedPrimitive(d,t,b,m,n,s,p);}
    HRESULT R32ReviewCallRawDrawPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT p,const void* data,UINT st) noexcept{return R30SupportCallRawDrawPrimitiveUP(d,t,p,data,st);}
    HRESULT R32ReviewCallRawDrawIndexedPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT m,UINT n,UINT p,const void* idx,D3DFORMAT f,const void* v,UINT st) noexcept{return R30SupportCallRawDrawIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st);}
    HRESULT R32ReviewCallRawPresent(IDirect3DDevice9* d,const RECT* s,const RECT* dst,HWND w,const RGNDATA* r) noexcept{return R30SupportCallRawPresent(d,s,dst,w,r);}

    HRESULT R32ReviewCallLowerDrawPrimitive(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT s,UINT p) noexcept{return R30SupportCallLowerDrawPrimitive(d,t,s,p);}
    HRESULT R32ReviewCallLowerDrawIndexedPrimitive(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,INT b,UINT m,UINT n,UINT s,UINT p) noexcept{return R30SupportCallLowerDrawIndexedPrimitive(d,t,b,m,n,s,p);}
    HRESULT R32ReviewCallLowerDrawPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT p,const void* data,UINT st) noexcept{return R30SupportCallLowerDrawPrimitiveUP(d,t,p,data,st);}
    HRESULT R32ReviewCallLowerDrawIndexedPrimitiveUP(IDirect3DDevice9* d,D3DPRIMITIVETYPE t,UINT m,UINT n,UINT p,const void* idx,D3DFORMAT f,const void* v,UINT st) noexcept{return R30SupportCallLowerDrawIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st);}

    OutRunVR::RuntimeEligibility::InstallState R32ReviewPrerequisiteStatus() noexcept
    {
        using State=OutRunVR::RuntimeEligibility::InstallState;
        const auto r31 = R31SupportInstallStatus();
        const auto lower = R30SupportLowerPrerequisiteStatus();
        if (r31 == State::Failed || lower == State::Failed) return State::Failed;
        if (r31 == State::Ready && lower == State::Ready) return State::Ready;
        return State::Pending;
    }
    void* R32ReviewResetTarget() noexcept{return R30SupportResetTarget();}
    void* R32ReviewPresentTarget() noexcept{return R30SupportPresentTarget();}
    void* R32ReviewDirectTransportTarget() noexcept{return R30SupportDirectTransportTarget();}
    void* R32ReviewSetRenderStateTarget() noexcept{return R30SupportSetRenderStateTarget();}
    void* R32ReviewDrawPrimitiveTarget() noexcept{return R30SupportDrawPrimitiveTarget();}
    void* R32ReviewDrawIndexedPrimitiveTarget() noexcept{return R30SupportDrawIndexedPrimitiveTarget();}
    void* R32ReviewDrawPrimitiveUPTarget() noexcept{return R30SupportDrawPrimitiveUPTarget();}
    void* R32ReviewDrawIndexedPrimitiveUPTarget() noexcept{return R30SupportDrawIndexedPrimitiveUPTarget();}
    IDirect3DDevice9* R32ReviewInstalledDevice() noexcept{return R30SupportInstalledDevice();}

}