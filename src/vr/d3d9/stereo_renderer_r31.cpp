// R31 high-draw-count performance overlay.
//
// R29 removed the steady-state mono replay, but the validated R7 world path
// still read c64..c67 and rebuilt all eye transforms for every draw. Complex
// OutRun stages can submit several thousand top-level draws per Present, so the
// validation itself becomes measurable even after the third geometry pass is
// gone.
//
// R31 now owns StateBlock/cache recovery plus shared fast-path helpers consumed by R33:
//  * verified c64..c67 from the renderer hook is the authoritative stock WVP;
//  * shader epoch + pose sequence must still match exactly;
//  * eyeInverse*eyeProjection is cached per pose/projection/world-scale;
//  * one live c64 validation is retained every 16 fast world draws only after
//    StateBlock interception is proven; otherwise every candidate is validated;
//  * Begin/End/Apply invalidate and resynchronize WVP, projection, shader,
//    effect, viewport and scissor caches as one state generation;
//  * R31 no longer submits physical world/HUD draws; R33 is the sole executor;
//  * a five-second route summary separates main/offscreen/aux/world/HUD/fallback
//    work so stage-specific 300 -> 3000+ draw explosions can be diagnosed.

#ifndef OUTRUN_VR_REFACTOR_SPLIT_R31_R30
#include "stereo_renderer_r30.cpp"
#endif
#include "../core/r30_support_api.hpp"
#include "../core/r31_support_api.hpp"
#include "../../hook_mgr.hpp"
#include <algorithm>
#include <atomic>
#include <cstring>
#include "../state/state_block_tracker.hpp"
#include "../state/state_block_recovery.hpp"
#include "../state/state_block_events.hpp"
#include "draw_state_helpers.hpp"
#include "vr_shared.hpp"
#include <spdlog/spdlog.h>

namespace OutRunVRStereo
{
    namespace
    {
        constexpr std::uint64_t LiveWvpValidationInterval = 16;


        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R31InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        std::uint32_t R31BlockedVerifiedGeneration = 0;
        std::uint64_t R31FastWorldCandidates = 0;
        std::uint64_t R31FastWorldDraws = 0;
        std::uint64_t R31FastWorldLiveValidations = 0;
        std::uint64_t R31FastWorldValidationRejects = 0;
        std::uint64_t R31HudDraws = 0;
        bool R31FirstStateBlockLogged = false;

        struct R31EyeTailCache
        {
            bool valid = false;
            std::uint32_t poseSequence = 0;
            float worldScale = 0.0f;
            D3DMATRIX projection{};
            D3DMATRIX inverseProjection{};
            // Recenter/reconnect can change a view before poseSequence advances.
            // Include exact eye geometry in the fast-path cache identity.
            decltype(OutRunVRRenderer::LatchedStereoFrame::eyeOrientation) eyeOrientation{};
            decltype(OutRunVRRenderer::LatchedStereoFrame::eyeOffset) eyeOffset{};
            decltype(OutRunVRRenderer::LatchedStereoFrame::eyeFov) eyeFov{};
            D3DMATRIX eyeTail[2]{};
        };
        R31EyeTailCache R31EyeCache{};

        struct R31FramePerf
        {
            std::uint64_t epoch = 0;
            std::uint64_t draws = 0;
            std::uint64_t main = 0;
            std::uint64_t offscreen = 0;
            std::uint64_t aux = 0;
            std::uint64_t fastWorld = 0;
            std::uint64_t hud = 0;
            std::uint64_t fragile = 0;
            std::uint64_t unstable = 0;
            std::uint64_t fallback = 0;
        };
        R31FramePerf R31Frame{};

        inline void R31TelemetryNoteFastWorld() noexcept
        {
            ++R31FastWorldDraws;
            ++R31Frame.fastWorld;
        }

        inline void R31TelemetryNoteHud() noexcept
        {
            ++R31HudDraws;
            ++R31Frame.hud;
        }

        inline void R31TelemetryNoteFallback() noexcept
        {
            ++R31Frame.fallback;
        }

        inline void R31TelemetryNoteUnstable() noexcept
        {
            ++R31Frame.unstable;
        }

        inline void R31TelemetryNoteFragile() noexcept
        {
            ++R31Frame.fragile;
        }

        inline R31FramePerf R31TelemetryFrameSnapshot() noexcept
        {
            return R31Frame;
        }

        inline std::uint64_t R31TelemetryLiveWvpChecks() noexcept
        {
            return R31FastWorldLiveValidations;
        }

        inline std::uint64_t R31TelemetryLiveWvpRejects() noexcept
        {
            return R31FastWorldValidationRejects;
        }

        struct R31WindowPerf
        {
            std::uint64_t presents = 0;
            std::uint64_t draws = 0;
            std::uint64_t main = 0;
            std::uint64_t offscreen = 0;
            std::uint64_t aux = 0;
            std::uint64_t fastWorld = 0;
            std::uint64_t hud = 0;
            std::uint64_t fragile = 0;
            std::uint64_t unstable = 0;
            std::uint64_t fallback = 0;
            std::uint64_t maxDraws = 0;
            ULONGLONG lastLogMs = 0;
        };
        R31WindowPerf R31Window{};

        inline void R31TelemetryResetFrameWindow() noexcept
        {
            R31Frame = {};
            R31Window = {};
        }

        inline void R31ResetFastPathState() noexcept
        {
            R31BlockedVerifiedGeneration = 0;
            R31FastWorldCandidates = 0;
            R31EyeCache = {};
            R31TelemetryResetFrameWindow();
            // Reset/ResetEx opens a new performance epoch. Never mix
            // pre-reset route counts with recovered-device telemetry.
            R31Window = {};
        }

        void R31FinalizePerfFrame() noexcept
        {
            if (R31Frame.epoch == 0 || R31Frame.draws == 0)
                return;
            // A disabled diagnostic window must not contaminate the next
            // enabled five-second measurement with historical frames.
            // Per-frame routing counters remain available to R32/R33.
            if (!R30SupportTelemetryEnabled())
            {
                R31Window = {};
                return;
            }
            ++R31Window.presents;
            R31Window.draws += R31Frame.draws;
            R31Window.main += R31Frame.main;
            R31Window.offscreen += R31Frame.offscreen;
            R31Window.aux += R31Frame.aux;
            R31Window.fastWorld += R31Frame.fastWorld;
            R31Window.hud += R31Frame.hud;
            R31Window.fragile += R31Frame.fragile;
            R31Window.unstable += R31Frame.unstable;
            R31Window.fallback += R31Frame.fallback;
            R31Window.maxDraws = std::max(R31Window.maxDraws, R31Frame.draws);

            const ULONGLONG now = GetTickCount64();
            if (R31Window.lastLogMs == 0)
                R31Window.lastLogMs = now;
            if (R30SupportTelemetryEnabled() && now - R31Window.lastLogMs >= 5000 &&
                R31Window.presents != 0)
            {
                const double avg = static_cast<double>(R31Window.draws) /
                    static_cast<double>(R31Window.presents);
                spdlog::info(
                    "VR R31 PERF: topLevelGameCalls/present avg={:.1f} max={} presents={} targets[main={},offscreen={},auxOverlay={}] ownedEyeRoutes[fastWorld={},hud={}] fallbackReasons[fragile={},unstable={}] fallbackDispatch={} liveWvpCheck={} liveReject={} stateBlock[record={},apply={}]",
                    avg, R31Window.maxDraws, R31Window.presents,
                    R31Window.main, R31Window.offscreen, R31Window.aux,
                    R31Window.fastWorld, R31Window.hud, R31Window.fragile,
                    R31Window.unstable, R31Window.fallback,
                    R31TelemetryLiveWvpChecks(), R31TelemetryLiveWvpRejects(),
                    OutRunVR::State::StateBlockTracker::RecordingGeneration(),
                    OutRunVR::State::StateBlockTracker::ApplyGeneration());
                R31Window = {};
                R31Window.lastLogMs = now;
            }
        }

        void R31ObserveDraw(IDirect3DDevice9* device) noexcept
        {
            if (!R30SupportIsGameDevice(device) || R30SupportInternalStereoPassActive())
                return;
            if (R31Frame.epoch != R30SupportPresentEpoch())
            {
                R31FinalizePerfFrame();
                R31Frame = {};
                R31Frame.epoch = R30SupportPresentEpoch();
            }
            ++R31Frame.draws;
            if (R30SupportTargetIsBackBuffer()) ++R31Frame.main;
            else ++R31Frame.offscreen;
            if (R30SupportAnyAuxRenderTargetActive()) ++R31Frame.aux;
        }

        bool R31GetSavedViewport(IDirect3DDevice9* device,
            D3DVIEWPORT9& viewport) noexcept
        {
            if (R30SupportTryGetTrackedViewport(viewport))
                return true;
            return OutRunVR::D3D9::ReadViewport(device, viewport);
        }

        bool R31ProjectionMatches(const D3DMATRIX& a,
            const D3DMATRIX& b) noexcept
        {
            return std::memcmp(&a, &b, sizeof(D3DMATRIX)) == 0;
        }

        void R31DiscardUnreliableDrawCaches() noexcept
        {
            if (OutRunVR::State::StateBlockTracker::Reliable())
                return;
            R30SupportInvalidateEffectStateCache();
            R30SupportInvalidateTrackedRasterShadow();
            R30SupportInvalidateLiveStateSample();
        }

        bool R31PrepareEyeTailCache(
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            const D3DMATRIX& projection,
            const D3DMATRIX& inverseProjection) noexcept
        {
            const float worldScale = R30SupportWorldScale();
            if (R31EyeCache.valid &&
                R31EyeCache.poseSequence == stereo.poseSequence &&
                R31EyeCache.worldScale == worldScale &&
                R31ProjectionMatches(R31EyeCache.projection, projection) &&
                R31ProjectionMatches(R31EyeCache.inverseProjection, inverseProjection) &&
                std::memcmp(R31EyeCache.eyeOrientation, stereo.eyeOrientation,
                    sizeof(stereo.eyeOrientation)) == 0 &&
                std::memcmp(R31EyeCache.eyeOffset, stereo.eyeOffset,
                    sizeof(stereo.eyeOffset)) == 0 &&
                std::memcmp(R31EyeCache.eyeFov, stereo.eyeFov,
                    sizeof(stereo.eyeFov)) == 0)
                return true;

            R31EyeTailCache next{};
            next.poseSequence = stereo.poseSequence;
            next.worldScale = worldScale;
            next.projection = projection;
            next.inverseProjection = inverseProjection;
            std::memcpy(next.eyeOrientation, stereo.eyeOrientation,
                sizeof(stereo.eyeOrientation));
            std::memcpy(next.eyeOffset, stereo.eyeOffset,
                sizeof(stereo.eyeOffset));
            std::memcpy(next.eyeFov, stereo.eyeFov, sizeof(stereo.eyeFov));
            for (int eye = 0; eye < 2; ++eye)
            {
                const D3DMATRIX eyePose = R30SupportMatrixFromQuaternionTranslation(
                    stereo.eyeOrientation[eye], stereo.eyeOffset[eye], worldScale);
                const D3DMATRIX eyeInverse = R30SupportInverseRigid(eyePose);
                const D3DMATRIX eyeProjection = R30SupportProjectionFromFov(
                    projection, stereo.eyeFov[eye]);
                next.eyeTail[eye] = R30SupportMultiplyMatrix(eyeInverse, eyeProjection);
                if (!R30SupportMatrixFinite(next.eyeTail[eye]))
                    return false;
            }
            next.valid = true;
            R31EyeCache = next;
            return true;
        }

        bool R31BuildFastWorldConstants(IDirect3DDevice9* device,
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            R31SupportFastWorldConstants& draw) noexcept
        {
            float verified[16]{};
            std::uint32_t generation = 0;
            std::uint32_t poseSequence = 0;
            std::uintptr_t verifiedShader = 0;
            std::uint64_t verifiedShaderSerial = 0;
            if (!OutRunVRRenderer::GetLastVerifiedWvp(verified, generation,
                    poseSequence, verifiedShader, verifiedShaderSerial))
                return false;
            if (!generation || generation == R31BlockedVerifiedGeneration ||
                poseSequence != stereo.poseSequence)
                return false;

            std::uintptr_t currentShader = 0;
            std::uint64_t currentShaderSerial = 0;
            if (!R30SupportCurrentShaderEpoch(currentShader, currentShaderSerial) ||
                currentShader == 0 || currentShader != verifiedShader ||
                currentShaderSerial != verifiedShaderSerial)
                return false;

            if (!OutRunVR::State::StateBlockTracker::Reliable() &&
                !OutRunVR::D3D9::LiveVertexShaderMatches(device, verifiedShader))
                return false;

            ++R31FastWorldCandidates;
            float live[16]{};
            bool liveValidated = false;
            if (!OutRunVR::State::StateBlockTracker::Reliable() ||
                (R31FastWorldCandidates % LiveWvpValidationInterval) == 0)
            {
                ++R31FastWorldLiveValidations;
                if (!R30SupportValidateVerifiedWvp(
                        device, verified, live))
                {
                    R31BlockedVerifiedGeneration = generation;
                    ++R31FastWorldValidationRejects;
                    return false;
                }
                liveValidated = true;
            }

            D3DMATRIX projection{};
            D3DMATRIX inverseProjection{};
            float verifiedProjection[16]{};
            std::uint32_t projectionGeneration = 0;
            std::uint32_t projectionPoseSequence = 0;
            if (!R30SupportGetVerifiedProjection(
                    verifiedProjection, projectionGeneration,
                    projectionPoseSequence) ||
                projectionGeneration != generation ||
                projectionPoseSequence != poseSequence)
                return false;
            std::memcpy(&projection, verifiedProjection, sizeof(projection));
            if (!R30SupportMatrixFinite(projection) ||
                !R30SupportGetInverseProjection(projection, inverseProjection) ||
                !R31PrepareEyeTailCache(stereo, projection, inverseProjection))
                return false;

            // A successful live WVP sample may differ within the verified epsilon.
            // Original eye restoration and stereo transforms must use one exact source.
            const float* originalWvp = liveValidated ? live : verified;
            std::memcpy(draw.originalConstants, originalWvp, sizeof(verified));
            D3DMATRIX uploadedT{};
            std::memcpy(&uploadedT, originalWvp, sizeof(uploadedT));
            const D3DMATRIX currentWvp = R30SupportTransposeMatrix(uploadedT);
            const D3DMATRIX correctedWorldView = R30SupportMultiplyMatrix(
                currentWvp, R31EyeCache.inverseProjection);
            if (!R30SupportMatrixFinite(correctedWorldView))
                return false;

            for (int eye = 0; eye < 2; ++eye)
            {
                const D3DMATRIX eyeWvp = R30SupportMultiplyMatrix(
                    correctedWorldView, R31EyeCache.eyeTail[eye]);
                if (!R30SupportMatrixFinite(eyeWvp))
                    return false;
                const D3DMATRIX eyeWvpT = R30SupportTransposeMatrix(eyeWvp);
                std::memcpy(draw.eyeConstants[eye], &eyeWvpT,
                    sizeof(eyeWvpT));
            }
            draw.poseSequence = stereo.poseSequence;
            return true;
        }

        struct R31OwnedResult
        {
            bool handled = false;
            HRESULT hr = D3D_OK;
        };

        void R31BlockCurrentVerifiedGeneration() noexcept
        {
            float ignored[16]{};
            std::uint32_t generation = 0, pose = 0;
            std::uintptr_t shader = 0;
            std::uint64_t serial = 0;
            if (OutRunVRRenderer::GetLastVerifiedWvp(
                    ignored, generation, pose, shader, serial))
                R31BlockedVerifiedGeneration = generation;
            R31EyeCache.valid = false;
        }

        void R31ResynchronizeShaderEpoch(IDirect3DDevice9* device) noexcept
        {
            R30SupportResynchronizeShaderEpoch(device);
        }

        void R31MarkStateBlockCachesDirty() noexcept
        {
            R31BlockCurrentVerifiedGeneration();
            R30SupportInvalidateRendererStateAfterExternalRestore();
            R30SupportInvalidateEffectStateCache();
            R30SupportInvalidateTrackedRasterShadow();
            R30SupportInvalidateLiveStateSample();
            R31EyeCache.valid = false;
            OutRunVR::State::StateBlockTracker::RequireResync();
        }

        void R31OnStateBlockBegin(IDirect3DDevice9*) noexcept
        {
            OutRunVR::State::StateBlockTracker::SetRecording(true);
            OutRunVR::State::StateBlockTracker::NoteRecording();
            R31MarkStateBlockCachesDirty();
        }

        void R31OnStateBlockEnd(IDirect3DDevice9*, HRESULT hr) noexcept
        {
            if (SUCCEEDED(hr))
            {
                OutRunVR::State::StateBlockTracker::SetRecording(false);
            }
            else if (OutRunVR::State::StateBlockTracker::Recording())
            {
                OutRunVR::State::StateBlockTracker::MarkCoverageLost();
            }
            R31MarkStateBlockCachesDirty();
        }

        void R31OnStateBlockApply(IDirect3DDevice9*, HRESULT hr) noexcept
        {
            OutRunVR::State::StateBlockTracker::NoteApply();
            R31MarkStateBlockCachesDirty();
            if (!R31FirstStateBlockLogged)
            {
                R31FirstStateBlockLogged = true;
                spdlog::info(
                    "VR R31 STATE: StateBlock::Apply observed hr=0x{:08x}; caches invalidate immediately and live D3D state is lazily re-primed at the next actual draw",
                    static_cast<unsigned>(hr));
            }
        }

        DWORD WINAPI R31InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R31InstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r30 = R30InstallStatus();
                const auto renderer = R30SupportRendererInstallStatus();
                if (r30 == State::Failed || renderer == State::Failed)
                {
                    R31InstallState.store(State::Failed, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR31Perf", false);
                    spdlog::error(
                        "VR R31 PERF: R30 or renderer prerequisite failed; R30 remains authoritative");
                    return 0;
                }

                if (r30 == State::Ready && renderer == State::Ready)
                {
                    const auto failInstall = [&](const char* reason) noexcept
                    {
                        OutRunVR::State::StateBlockTracker::SetEventConsumerReady(false);
                        OutRunVR::State::StateBlockEvents::Clear();
                        OutRunVR::State::StateBlockRecovery::Clear();
                        OutRunVR::State::StateBlockTracker::MarkCoverageLost();
                        R31InstallState.store(State::Failed, std::memory_order_release);
                        HookManager::ReportAsyncResult("OpenXRVRStereoR31Perf", false);
                        spdlog::error("VR R31 STATE: install transaction failed: {}", reason);
                    };

                    OutRunVR::State::StateBlockTracker::SetEventConsumerReady(false);
                    OutRunVR::State::StateBlockTracker::ResetCoverageLoss();
                    OutRunVR::State::StateBlockRecovery::Configure(
                        &R31ResynchronizeShaderEpoch, &R30SupportPrimeTrackedRasterShadow);
                    OutRunVR::State::StateBlockEvents::Configure(
                        &R31OnStateBlockBegin,
                        &R31OnStateBlockEnd,
                        &R31OnStateBlockApply);
                    if (!OutRunVR::State::StateBlockEvents::Configured())
                    {
                        failInstall("StateBlock event callbacks unavailable");
                        return 0;
                    }
                    const bool lifecycleReady =
                        OutRunVR::State::StateBlockTracker::LifecycleHooksReady();
                    if (lifecycleReady)
                    {
                        spdlog::info(
                            "VR R31 STATE: R22 lifecycle hooks are authoritative; R31 is event-consumer only");
                    }
                    else
                    {
                        OutRunVR::State::StateBlockTracker::MarkCoverageLost();
                        spdlog::warn(
                            "VR R31 STATE: R22 lifecycle coverage unavailable; R31 physical StateBlock fallback retired; fast-path trust remains disabled");
                    }

                    OutRunVR::State::StateBlockTracker::SetEventConsumerReady(true);
                    R31InstallState.store(State::Ready, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR31Perf", true);
                    spdlog::info(
                        "VR R31 STATE: StateBlock cache/recovery ownership READY; R30 remains the draw owner until R33 final dispatch");
                    return 0;
                }
                Sleep(25);
            }

            R31InstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVRStereoR31Perf", false);
            spdlog::error("VR R31 PERF: timed out waiting for R30");
            return 0;
        }

        class VRStereoR31PerfHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR31Perf";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(nullptr, 0,
                    R31InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R31InstallState.store(
                        OutRunVR::RuntimeEligibility::InstallState::Failed,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRStereoR31PerfHook instance;
        };

        VRStereoR31PerfHook VRStereoR31PerfHook::instance;
    }

    inline OutRunVR::RuntimeEligibility::InstallState
    R31InstallStatus() noexcept
    {
        return R31InstallState.load(std::memory_order_acquire);
    }

    R31SupportFrameSnapshot R31SupportTelemetryFrameSnapshot() noexcept
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

    std::uint64_t R31SupportTelemetryLiveWvpChecks() noexcept
    {
        return R31TelemetryLiveWvpChecks();
    }

    std::uint64_t R31SupportTelemetryLiveWvpRejects() noexcept
    {
        return R31TelemetryLiveWvpRejects();
    }

    void R31SupportResetFastPathState() noexcept
    {
        R31ResetFastPathState();
    }

    bool R31SupportGetSavedViewport(
        IDirect3DDevice9* device, D3DVIEWPORT9& viewport) noexcept
    {
        return R31GetSavedViewport(device, viewport);
    }

    void R31SupportObserveDraw(IDirect3DDevice9* device) noexcept
    {
        R31ObserveDraw(device);
    }

    void R31SupportDiscardUnreliableDrawCaches() noexcept
    {
        R31DiscardUnreliableDrawCaches();
    }

    void R31SupportNoteFallback() noexcept
    {
        R31TelemetryNoteFallback();
    }

    void R31SupportNoteFastWorld() noexcept
    {
        R31TelemetryNoteFastWorld();
    }

    void R31SupportNoteFragile() noexcept
    {
        R31TelemetryNoteFragile();
    }

    void R31SupportNoteHud() noexcept
    {
        R31TelemetryNoteHud();
    }

    void R31SupportNoteUnstable() noexcept
    {
        R31TelemetryNoteUnstable();
    }

    bool R31SupportBuildFastWorldConstants(
        IDirect3DDevice9* device,
        const OutRunVRRenderer::LatchedStereoFrame& stereo,
        R31SupportFastWorldConstants& out) noexcept
    {
        return R31BuildFastWorldConstants(device, stereo, out);
    }

    OutRunVR::RuntimeEligibility::InstallState
    R31SupportInstallStatus() noexcept
    {
        return R31InstallStatus();
    }
}
