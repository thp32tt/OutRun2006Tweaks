// R33 final dispatch + post-review hot-path hardening.
//
// R32 owns reset/direct-transport review-2 safety. R33 remains the final
// game-side callback boundary and owns depth/stencil write-state caching plus
// exact single-count draw dispatch. Reset now simply chains through R32, whose
// trampoline is installed above R22, so R22 is authoritative in both the R32
// fallback and the final R33 path.
//
// R33 is also the final top-level draw boundary: when telemetry is disabled,
// route accounting and diagnostic counter writes are skipped so the steady
// draw path pays only for correctness checks required by stereo rendering.

#include "stereo_renderer_r32.cpp"
#include "../state/state_block_tracker.hpp"
#include "../core/dispatch_support.hpp"
#include "../render/stereo_base_policy.hpp"
#include "../render/screen_space_api.hpp"
#include "../render/fast_path_support.hpp"
#include "../render/lower_draw_api.hpp"
#include "../state/right_depth_stencil_sync.hpp"
#include "../state/depth_target_state.hpp"
#include "../lifecycle/frame_accounting.hpp"
#include "../lifecycle/mono_safety.hpp"
#include "../state/depth_stencil_write_state.hpp"
#include "../telemetry/depth_stencil_metrics.hpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R33ResetR32Hook{};
        SafetyHookInline R33PresentR32Hook{};
        SafetyHookInline R33SetRenderStateR29Hook{};
        SafetyHookInline R33DrawPrimitiveR32Hook{};
        SafetyHookInline R33DrawIndexedPrimitiveR32Hook{};
        SafetyHookInline R33DrawPrimitiveUPR32Hook{};
        SafetyHookInline R33DrawIndexedPrimitiveUPR32Hook{};
        SafetyHookInline* R33HookTransaction[]{
            &R33ResetR32Hook,
            &R33PresentR32Hook,
            &R33SetRenderStateR29Hook,
            &R33DrawPrimitiveR32Hook,
            &R33DrawIndexedPrimitiveR32Hook,
            &R33DrawPrimitiveUPR32Hook,
            &R33DrawIndexedPrimitiveUPR32Hook
        };

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R33InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        void SetFinalDispatchInstallState(
            OutRunVR::RuntimeEligibility::InstallState state) noexcept
        {
            R33InstallState.store(state, std::memory_order_release);
        }

        OutRunVR::RuntimeEligibility::InstallState
        ReadFinalDispatchInstallState() noexcept
        {
            return R33InstallState.load(std::memory_order_acquire);
        }

        using R33DepthStencilWriteState =
            OutRunVR::State::DepthStencilWriteState;

        thread_local R33DepthStencilWriteState R33DepthStencilState{};
        std::uint64_t R33DepthStencilSyncs = 0;
        std::uint64_t R33DepthStencilCacheHits = 0;
        std::uint64_t R33DepthStencilLiveFallbacks = 0;
        std::uint64_t R33DepthStencilReadFailures = 0;
        std::uint64_t R33ResetSuccesses = 0;
        std::uint64_t R33ResetFailures = 0;
        bool R33FirstDepthStencilCacheLogged = false;
        bool R33FirstResetLifecycleLogged = false;

        using R33PerfSnapshot = OutRunVR::Telemetry::DepthStencilMetrics;
        R33PerfSnapshot R33Perf{};

        inline bool R33TelemetryEnabled() noexcept
        {
            return Settings::VRTelemetry;
        }

        HRESULT CallLowerSetRenderState(
            IDirect3DDevice9* device,
            D3DRENDERSTATETYPE state, DWORD value)
        {
            return R33SetRenderStateR29Hook.stdcall<HRESULT>(
                device, state, value);
        }

        HRESULT CallLowerReset(
            IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            return R33ResetR32Hook.stdcall<HRESULT>(device, params);
        }

        HRESULT CallLowerPresent(
            IDirect3DDevice9* device,
            const RECT* sourceRect, const RECT* destRect,
            HWND destWindowOverride, const RGNDATA* dirtyRegion)
        {
            return R33PresentR32Hook.stdcall<HRESULT>(
                device, sourceRect, destRect,
                destWindowOverride, dirtyRegion);
        }

        void R33InvalidateDepthStencilCache() noexcept
        {
            R33DepthStencilState.valid = false;
        }

        bool R33TrackedDepthHasStencil() noexcept
        {
            const auto depthTarget = MainDepthTargetSnapshot();
            if (!TrackedDepthStencil || !depthTarget.known ||
                TrackedDepthStencil != depthTarget.identity)
                return false;
            return FormatHasStencil(depthTarget.desc.Format);
        }

        bool R33ReadDepthStencilWriteState(IDirect3DDevice9* device) noexcept
        {
            if (!device)
                return false;

            R33DepthStencilWriteState next{};
            const auto depthTarget = MainDepthTargetSnapshot();
            const auto stateBlock =
                OutRunVR::State::StateBlockTracker::Snapshot();
            if (!TrackedDepthStencil)
            {
                next.valid = true;
                next.depthGeneration = depthTarget.generation;
                next.stateBlockRecordings = stateBlock.recordings;
                next.stateBlockApplies = stateBlock.applies;
                R33DepthStencilState = next;
                if (R33TelemetryEnabled())
                    ++R33DepthStencilSyncs;
                return true;
            }

            if (FAILED(device->GetRenderState(D3DRS_ZENABLE, &next.zEnable)) ||
                FAILED(device->GetRenderState(D3DRS_ZWRITEENABLE, &next.zWrite)))
            {
                if (R33TelemetryEnabled())
                    ++R33DepthStencilReadFailures;
                R33InvalidateDepthStencilCache();
                return false;
            }

            if (R33TrackedDepthHasStencil())
            {
                if (FAILED(device->GetRenderState(
                        D3DRS_STENCILENABLE, &next.stencilEnable)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_STENCILWRITEMASK, &next.stencilWriteMask)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_STENCILFAIL, &next.stencilFail)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_STENCILZFAIL, &next.stencilZFail)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_STENCILPASS, &next.stencilPass)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_TWOSIDEDSTENCILMODE, &next.twoSided)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_CCW_STENCILFAIL, &next.ccwStencilFail)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_CCW_STENCILZFAIL, &next.ccwStencilZFail)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_CCW_STENCILPASS, &next.ccwStencilPass)))
                {
                    if (R33TelemetryEnabled())
                        ++R33DepthStencilReadFailures;
                    R33InvalidateDepthStencilCache();
                    return false;
                }
            }

            next.valid = true;
            next.depthGeneration = depthTarget.generation;
            next.stateBlockRecordings = stateBlock.recordings;
            next.stateBlockApplies = stateBlock.applies;
            R33DepthStencilState = next;
            if (R33TelemetryEnabled())
                ++R33DepthStencilSyncs;
            if (!R33FirstDepthStencilCacheLogged)
            {
                R33FirstDepthStencilCacheLogged = true;
                spdlog::info(
                    "VR R33 PERF: depth/stencil write shadow cache ACTIVE; steady draws no longer query Z/stencil state or depth GetDesc when StateBlock tracking is reliable");
            }
            return true;
        }

        bool R33DepthStencilCacheCurrent() noexcept
        {
            const auto depthTarget = MainDepthTargetSnapshot();
            const auto stateBlock =
                OutRunVR::State::StateBlockTracker::Snapshot();
            return R33DepthStencilState.valid &&
                R33DepthStencilState.depthGeneration == depthTarget.generation &&
                R33DepthStencilState.stateBlockRecordings ==
                    stateBlock.recordings &&
                R33DepthStencilState.stateBlockApplies == stateBlock.applies;
        }

        bool R33GetWriteFlags(IDirect3DDevice9* device,
            bool& mayWriteDepth, bool& mayWriteStencil) noexcept
        {
            mayWriteDepth = false;
            mayWriteStencil = false;
            if (!TrackedDepthStencil)
                return true;

            if (!OutRunVR::State::StateBlockTracker::Reliable())
            {
                if (R33TelemetryEnabled())
                    ++R33DepthStencilLiveFallbacks;
                mayWriteDepth = LeftDrawMayWriteDepth(device);
                mayWriteStencil = LeftDrawMayWriteStencil(device);
                return true;
            }

            if (!R33DepthStencilCacheCurrent())
            {
                if (!R33ReadDepthStencilWriteState(device))
                    return false;
            }
            else if (R33TelemetryEnabled())
            {
                ++R33DepthStencilCacheHits;
            }

            const auto& s = R33DepthStencilState;
            mayWriteDepth = s.zEnable != D3DZB_FALSE && s.zWrite != FALSE;

            if (!R33TrackedDepthHasStencil() || s.stencilEnable == FALSE ||
                s.stencilWriteMask == 0)
                return true;

            const bool frontWrites =
                s.stencilFail != D3DSTENCILOP_KEEP ||
                s.stencilZFail != D3DSTENCILOP_KEEP ||
                s.stencilPass != D3DSTENCILOP_KEEP;
            const bool backWrites = s.twoSided != FALSE &&
                (s.ccwStencilFail != D3DSTENCILOP_KEEP ||
                 s.ccwStencilZFail != D3DSTENCILOP_KEEP ||
                 s.ccwStencilPass != D3DSTENCILOP_KEEP);
            mayWriteStencil = frontWrites || backWrites;
            return true;
        }

        void R33InvalidateRightForLeftWrite(
            bool mayWriteDepth, bool mayWriteStencil) noexcept
        {
            if (mayWriteDepth)
                InvalidateRightDepthSync();
            if (mayWriteStencil)
                InvalidateRightStencilSync();
        }

        HRESULT __stdcall SetRenderStateDestR33(IDirect3DDevice9* device,
            D3DRENDERSTATETYPE state, DWORD value)
        {
            const HRESULT hr = CallLowerSetRenderState(
                device, state, value);
            if (FAILED(hr) || !IsGameDevice(device) || InternalStereoPass)
                return hr;

            if (OutRunVR::State::StateBlockTracker::IsRecording())
            {
                R33InvalidateDepthStencilCache();
                return hr;
            }
            if (!R33DepthStencilState.valid)
                return hr;

            switch (state)
            {
            case D3DRS_ZENABLE:
                R33DepthStencilState.zEnable = value;
                break;
            case D3DRS_ZWRITEENABLE:
                R33DepthStencilState.zWrite = value;
                break;
            case D3DRS_STENCILENABLE:
                R33DepthStencilState.stencilEnable = value;
                break;
            case D3DRS_STENCILWRITEMASK:
                R33DepthStencilState.stencilWriteMask = value;
                break;
            case D3DRS_STENCILFAIL:
                R33DepthStencilState.stencilFail = value;
                break;
            case D3DRS_STENCILZFAIL:
                R33DepthStencilState.stencilZFail = value;
                break;
            case D3DRS_STENCILPASS:
                R33DepthStencilState.stencilPass = value;
                break;
            case D3DRS_TWOSIDEDSTENCILMODE:
                R33DepthStencilState.twoSided = value;
                break;
            case D3DRS_CCW_STENCILFAIL:
                R33DepthStencilState.ccwStencilFail = value;
                break;
            case D3DRS_CCW_STENCILZFAIL:
                R33DepthStencilState.ccwStencilZFail = value;
                break;
            case D3DRS_CCW_STENCILPASS:
                R33DepthStencilState.ccwStencilPass = value;
                break;
            default:
                break;
            }

            // Do not rewrite depth/state-block generations here. If a StateBlock
            // made this snapshot stale, changing one tracked render state cannot
            // make the untouched fields authoritative again.
            return hr;
        }

        template <typename ActualDraw>
        OutRunVR::Core::DispatchResult R33TryFastWorld(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, const char* site)
        {
            if (OutRunVR::State::StateBlockTracker::IsRecording() || !StableStereoBase(device))
            {
                if (R33TelemetryEnabled() && IsGameDevice(device) &&
                    !InternalStereoPass && TargetIsBackBuffer())
                    NoteDispatchUnstable();
                return {};
            }

            bool fragile = true;
            const bool stateBlocksReliable =
                OutRunVR::State::StateBlockTracker::Reliable();
            const bool effectKnown = stateBlocksReliable
                ? FragileEffectCached(device, fragile)
                : EffectIsFragileLive(device, fragile);
            if (!effectKnown)
                return {};
            if (fragile)
            {
                if (R33TelemetryEnabled())
                    NoteDispatchFragile();
                return {};
            }

            if (!EnsureStereoResources(device))
                return {};
            if (TrackedDepthStencil &&
                (!IsRightDepthSynchronized() || !IsRightStencilSynchronized()))
                TryBootstrapRightDepthFromRecentClear(device);
            if (TrackedDepthStencil && !IsRightDepthSynchronized() &&
                DepthTestActive(device))
                return {};
            if (TrackedDepthStencil && !IsRightStencilSynchronized() &&
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
            if (!BuildFastWorldConstants(device, stereo, draw))
                return {};

            D3DVIEWPORT9 savedViewport{};
            if (!GetSavedViewport(device, savedViewport))
                return {};

            bool mayWriteDepth = false;
            bool mayWriteStencil = false;
            if (!R33GetWriteFlags(device, mayWriteDepth, mayWriteStencil))
                return {};

            bool leftWvpOk = false;
            {
                InternalPassScope guard;
                leftWvpOk = SetWvpBatch(device, draw.eyeConstants[0]);
            }
            if (!leftWvpOk)
            {
                bool rolledBack = false;
                {
                    InternalPassScope guard;
                    rolledBack = SetWvpBatch(device, draw.originalConstants);
                }
                if (!rolledBack)
                {
                    ReportStereoFailure(OutRunVR::StereoFailureRestoreFailed,
                        "R33/fast-left-WVP-rollback");
                    NoteRestoreFailure("R33 fast left-eye c64 rollback");
                    ArmMonoSafety();
                    return { true, E_FAIL };
                }
                return {};
            }

            NoteStereoLeftDraw();
            if (mayWriteDepth || mayWriteStencil)
                NoteMainDepthContentWrite();

            OutRunVR::Core::DispatchResult result{ true, actualDraw() };
            if (FAILED(result.hr))
            {
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                ReportStereoFailure(OutRunVR::StereoFailureLeftDrawFailed, site, result.hr);
                bool restored = false;
                {
                    InternalPassScope guard;
                    restored = SetWvpBatch(device, draw.originalConstants);
                }
                if (!restored)
                    NoteRestoreFailure("R33 fast left draw c64");
                ArmMonoSafety();
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
                    !SetWvpBatch(device, draw.eyeConstants[1]))
                {
                    rightFailure =
                        OutRunVR::StereoFailureRightWvpUploadFailed;
                    rightHr = E_FAIL;
                }
                if (SUCCEEDED(rightHr))
                {
                    rightFailure = OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = actualDraw();
                }
                restoreOk = RestoreRightPassState(
                    device, savedRt, savedDepth, savedViewport,
                    draw.originalConstants, true);
            }

            FrameHadDuplicatedDraw = true;
            FrameHadWorldStereo = true;
            ++DuplicatedDraws;
            ++WorldStereoDraws;
            NoteStableTwoEyeDraw();
            if (R33TelemetryEnabled())
            {
                NoteDispatchFastWorld();
            }

            if (FrameStereoPoseSequence == 0)
            {
                FrameStereoPoseSequence = draw.poseSequence;
                FrameStereoMetadata = draw.stereoFrame;
            }

            if (FAILED(rightHr))
            {
                FrameRightDrawFailed = true;
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                ReportStereoFailure(rightFailure, site, rightHr);
                ArmMonoSafety();
            }
            if (!restoreOk)
            {
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                NoteRestoreFailure("R33 fast right-eye draw");
                ArmMonoSafety();
            }
            return result;
        }

        template <typename ActualDraw>
        OutRunVR::Core::DispatchResult R33TryHud(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, const char* site)
        {
            const OutRunVR::Render::ScreenSpaceKind screenKind =
                ClassifyScreenSpacePass(device);
            if (OutRunVR::State::StateBlockTracker::IsRecording() || !StableStereoBase(device) ||
                screenKind == OutRunVR::Render::ScreenSpaceKind::None)
                return {};

            if (!OutRunVR::State::StateBlockTracker::Reliable())
            {
                DiscardUnreliableDrawCaches();
                const std::uintptr_t cachedShader =
                    CurrentVertexShaderIdentity.load(std::memory_order_acquire);
                if (!LiveShaderMatches(device, cachedShader))
                    return {};
            }

            if (!EnsureStereoResources(device))
                return {};
            if (TrackedDepthStencil &&
                (!IsRightDepthSynchronized() || !IsRightStencilSynchronized()))
                TryBootstrapRightDepthFromRecentClear(device);
            if (TrackedDepthStencil && !IsRightDepthSynchronized() &&
                DepthTestActive(device))
                return {};
            if (TrackedDepthStencil && !IsRightStencilSynchronized() &&
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
            if (!BuildScreenSpaceEyeConstants(device, stereo, screenKind,
                    original, eyeConstants, eyeScale, eyeOffset))
                return {};

            D3DVIEWPORT9 savedViewport{};
            if (!GetSavedViewport(device, savedViewport))
                return {};

            bool mayWriteDepth = false;
            bool mayWriteStencil = false;
            if (!R33GetWriteFlags(device, mayWriteDepth, mayWriteStencil))
                return {};

            bool leftWvpOk = false;
            {
                InternalPassScope guard;
                leftWvpOk = SetWvpBatch(device, eyeConstants[0]);
            }
            if (!leftWvpOk)
            {
                bool rolledBack = false;
                {
                    InternalPassScope guard;
                    rolledBack = SetWvpBatch(device, original);
                }
                if (!rolledBack)
                {
                    ReportStereoFailure(OutRunVR::StereoFailureRestoreFailed,
                        "R33/HUD-left-WVP-rollback");
                    NoteRestoreFailure("R33 HUD left-eye c64 rollback");
                    ArmMonoSafety();
                    return { true, E_FAIL };
                }
                return {};
            }

            NoteStereoLeftDraw();
            if (mayWriteDepth || mayWriteStencil)
                NoteMainDepthContentWrite();

            OutRunVR::Core::DispatchResult result{ true, actualDraw() };
            if (FAILED(result.hr))
            {
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                bool restored = false;
                {
                    InternalPassScope guard;
                    restored = SetWvpBatch(device, original);
                }
                ReportStereoFailure(OutRunVR::StereoFailureLeftDrawFailed,
                    site, result.hr);
                if (!restored)
                    NoteRestoreFailure("R33 HUD left draw c64");
                ArmMonoSafety();
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
                    !SetWvpBatch(device, eyeConstants[1]))
                {
                    rightFailure =
                        OutRunVR::StereoFailureRightWvpUploadFailed;
                    rightHr = E_FAIL;
                }
                if (SUCCEEDED(rightHr))
                {
                    rightFailure = OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = actualDraw();
                }
                restoreOk = RestoreRightPassState(
                    device, savedRt, savedDepth, savedViewport, original, true);
            }

            FrameHadDuplicatedDraw = true;
            ++DuplicatedDraws;
            ++NonWorldDuplicatedDraws;
            NoteStableTwoEyeDraw();
            NoteScreenSpaceFovDraw();
            if (R33TelemetryEnabled())
            {
                NoteDispatchHud();
            }

            if (FAILED(rightHr))
            {
                FrameRightDrawFailed = true;
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                ReportStereoFailure(rightFailure, site, rightHr);
                ArmMonoSafety();
            }
            if (!restoreOk)
            {
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                NoteRestoreFailure("R33 HUD right-eye draw");
                ArmMonoSafety();
            }
            return result;
        }

        template <typename ActualDraw, typename LowerR29Draw>
        HRESULT R33Dispatch(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, LowerR29Draw&& lowerR29Draw,
            const char* site) noexcept
        {
            if (!OutRunVR::State::StateBlockTracker::IsRecording())
                FlushPendingStateBlockResync(device);
            const bool telemetry = R33TelemetryEnabled();
            if (telemetry)
                ObserveDispatchDraw(device);

            if (OutRunVR::State::StateBlockTracker::IsRecording())
            {
                if (telemetry)
                    NoteDispatchFallback();
                return actualDraw();
            }

            if (ClassifyScreenSpacePass(device) != OutRunVR::Render::ScreenSpaceKind::None)
            {
                const auto hud = R33TryHud(device,
                    std::forward<ActualDraw>(actualDraw), site);
                if (hud.handled)
                    return hud.hr;
            }
            else
            {
                const auto fast = R33TryFastWorld(device,
                    std::forward<ActualDraw>(actualDraw), site);
                if (fast.handled)
                    return fast.hr;
            }

            // Preserve R31's fail-closed boundary when StateBlock tracking
            // is unreliable. Otherwise stale R29 effect/shadow caches can
            // reclassify a draw that R33 already rejected using live state.
            DiscardUnreliableDrawCaches();
            if (telemetry)
                NoteDispatchFallback();
            return LowerFailClosed(device,
                std::forward<LowerR29Draw>(lowerR29Draw));
        }

        HRESULT __stdcall DrawPrimitiveDestR33(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto lower = [&]() {
                return LowerDrawPrimitive(
                    device, type, startVertex, primitiveCount);
            };
            return R33Dispatch(device, actual, lower, "R33/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR33(
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
                return LowerDrawIndexedPrimitive(device,
                    type, baseVertexIndex, minVertexIndex, numVertices,
                    startIndex, primitiveCount);
            };
            return R33Dispatch(device, actual, lower,
                "R33/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR33(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT primitiveCount, const void* data,
            UINT stride)
        {
            auto actual = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto lower = [&]() {
                return LowerDrawPrimitiveUP(
                    device, type, primitiveCount, data, stride);
            };
            return R33Dispatch(device, actual, lower, "R33/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR33(
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
                return LowerDrawIndexedPrimitiveUP(device,
                    type, minVertexIndex, numVertices, primitiveCount,
                    indexData, indexFormat, vertexData, stride);
            };
            return R33Dispatch(device, actual, lower,
                "R33/DrawIndexedPrimitiveUP");
        }

        HRESULT __stdcall ResetDestR33(IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            const bool gameDevice = IsGameDevice(device);
            const HRESULT hr = CallLowerReset(device, params);

            if (gameDevice)
            {
                R33InvalidateDepthStencilCache();
                if (SUCCEEDED(hr))
                    ++R33ResetSuccesses;
                else
                    ++R33ResetFailures;

                if (!R33FirstResetLifecycleLogged)
                {
                    R33FirstResetLifecycleLogged = true;
                    spdlog::info(
                        "VR R33 RESET: chained R33 -> R32 -> R22; R22 owns fail-close/baseline and R32 rearms caches only after successful Reset");
                }
            }
            return hr;
        }

        void R33LogPerfWindow() noexcept
        {
            if (!R33TelemetryEnabled())
                return;
            const ULONGLONG now = GetTickCount64();
            if (R33Perf.lastLogMs == 0)
            {
                R33Perf.lastLogMs = now;
                R33Perf.syncs = R33DepthStencilSyncs;
                R33Perf.hits = R33DepthStencilCacheHits;
                R33Perf.live = R33DepthStencilLiveFallbacks;
                R33Perf.readFail = R33DepthStencilReadFailures;
                R33Perf.resetOk = R33ResetSuccesses;
                R33Perf.resetFail = R33ResetFailures;
                return;
            }
            if (now - R33Perf.lastLogMs < 5000)
                return;

            spdlog::info(
                "VR R33 PERF 5s: depthStencil[cacheHit={},liveSync={},unreliableLive={},readFail={}] reset[ok={},fail={}]",
                R33DepthStencilCacheHits - R33Perf.hits,
                R33DepthStencilSyncs - R33Perf.syncs,
                R33DepthStencilLiveFallbacks - R33Perf.live,
                R33DepthStencilReadFailures - R33Perf.readFail,
                R33ResetSuccesses - R33Perf.resetOk,
                R33ResetFailures - R33Perf.resetFail);

            R33Perf.lastLogMs = now;
            R33Perf.syncs = R33DepthStencilSyncs;
            R33Perf.hits = R33DepthStencilCacheHits;
            R33Perf.live = R33DepthStencilLiveFallbacks;
            R33Perf.readFail = R33DepthStencilReadFailures;
            R33Perf.resetOk = R33ResetSuccesses;
            R33Perf.resetFail = R33ResetFailures;
        }

        HRESULT __stdcall PresentDestR33(IDirect3DDevice9* device,
            const RECT* sourceRect, const RECT* destRect,
            HWND destWindowOverride, const RGNDATA* dirtyRegion)
        {
            const HRESULT hr = CallLowerPresent(device,
                sourceRect, destRect, destWindowOverride, dirtyRegion);
            if (IsGameDevice(device))
                R33LogPerfWindow();
            return hr;
        }

        void R33RollbackHooks() noexcept
        {
            for (auto* hook : R33HookTransaction)
                *hook = {};
        }

        bool R33EnableHooks() noexcept
        {
            for (auto* hook : R33HookTransaction)
                if (!*hook || !hook->enable().has_value())
                    return false;
            return true;
        }

        void R33CreateDisabledHooks() noexcept
        {
            const auto disabled = safetyhook::InlineHook::StartDisabled;
            R33ResetR32Hook = safetyhook::create_inline(
                reinterpret_cast<void*>(&ResetDestR32),
                ResetDestR33, disabled);
            R33PresentR32Hook = safetyhook::create_inline(
                reinterpret_cast<void*>(&PresentDestR32),
                PresentDestR33, disabled);
            R33SetRenderStateR29Hook = safetyhook::create_inline(
                reinterpret_cast<void*>(&SetRenderStateDestR29),
                SetRenderStateDestR33, disabled);
            R33DrawPrimitiveR32Hook = safetyhook::create_inline(
                reinterpret_cast<void*>(&DrawPrimitiveDestR32),
                DrawPrimitiveDestR33, disabled);
            R33DrawIndexedPrimitiveR32Hook = safetyhook::create_inline(
                reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR32),
                DrawIndexedPrimitiveDestR33, disabled);
            R33DrawPrimitiveUPR32Hook = safetyhook::create_inline(
                reinterpret_cast<void*>(&DrawPrimitiveUPDestR32),
                DrawPrimitiveUPDestR33, disabled);
            R33DrawIndexedPrimitiveUPR32Hook = safetyhook::create_inline(
                reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR32),
                DrawIndexedPrimitiveUPDestR33, disabled);
        }

        constexpr int R33PrerequisiteWaitAttempts = 4800;
        constexpr DWORD R33PrerequisiteWaitMs = 25;

        DWORD WINAPI R33InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            SetFinalDispatchInstallState(State::Pending);
            for (int attempt = 0; attempt < R33PrerequisiteWaitAttempts; ++attempt)
            {
                const auto r32 = ReviewInstallState();
                if (r32 == State::Failed)
                {
                    SetFinalDispatchInstallState(State::Failed);
                    HookManager::ReportAsyncResult(
                        "OpenXRVRStereoR33Dispatch", false);
                    return 0;
                }
                if (r32 == State::Ready)
                {
                    R33CreateDisabledHooks();

                    if (!R33EnableHooks())
                    {
                        R33RollbackHooks();
                        SetFinalDispatchInstallState(State::Failed);
                        HookManager::ReportAsyncResult(
                            "OpenXRVRStereoR33Dispatch", false);
                        spdlog::error(
                            "VR R33: final reset/state/draw hook transaction was partial; corrected R32 remains authoritative");
                        return 0;
                    }

                    SetFinalDispatchInstallState(State::Ready);
                    HookManager::ReportAsyncResult(
                        "OpenXRVRStereoR33Dispatch", true);
                    spdlog::info(
                        "VR R33 DISPATCH: R33TryFastWorld/R33TryHud + direct R29 fallback READY; top-level telemetry counted once when enabled; corrected R32->R22 Reset lifecycle + depth/stencil cache ACTIVE");
                    return 0;
                }
                Sleep(R33PrerequisiteWaitMs);
            }

            SetFinalDispatchInstallState(State::Failed);
            HookManager::ReportAsyncResult("OpenXRVRStereoR33Dispatch", false);
            return 0;
        }

        class VRStereoR33DispatchHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR33Dispatch";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(
                    nullptr, 0, R33InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    SetFinalDispatchInstallState(OutRunVR::RuntimeEligibility::InstallState::Failed);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRStereoR33DispatchHook instance;
        };

        VRStereoR33DispatchHook VRStereoR33DispatchHook::instance;
    }

    void InvalidateDepthStencilStateCache() noexcept
    {
        R33InvalidateDepthStencilCache();
    }

    OutRunVR::RuntimeEligibility::InstallState
    FinalDispatchInstallState() noexcept
    {
        return ReadFinalDispatchInstallState();
    }
}
