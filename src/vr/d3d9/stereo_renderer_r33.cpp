// R33 final dispatch + post-review hot-path hardening.
//
// R32 owns hook-free direct-transport review-2 safety plus Reset/Present helpers
// and no longer has an async install/status shim.
// R33 is the sole upper physical Reset/Present/DirectGPU/draw dispatcher:
// Reset hooks R22, Present/DirectGPU hook R13, and draws hook R30 while lower
// owner semantics stay intact.
// R33 owns depth/stencil write-state caching,
// exact single-count draw dispatch, final raster replay preservation, and the
// ResetEx replay-health guard previously implemented by a separate R34 hook
// layer. R33 now also owns initial replay-health synchronization and terminal
// readiness publication. The obsolete R34 compatibility observer/status alias
// is retired; R33 is the sole final dispatcher status owner.
//
// R33 is also the final top-level draw boundary: when telemetry is disabled,
// route accounting and diagnostic counter writes are skipped so the steady
// draw path pays only for correctness checks required by stereo rendering.

#ifndef OUTRUN_VR_REFACTOR_SPLIT_R33_R32
#include "stereo_renderer_r32.cpp"
#endif
#include "../core/r32_review_api.hpp"
#include "../core/r30_support_api.hpp"
#include "hook_mgr.hpp"
#include "../game/render_semantics.hpp"
#include "../runtime_eligibility.hpp"
#include "../state/state_block_recovery.hpp"
#include "../state/state_block_tracker.hpp"
#include "gpu_water_profiler.hpp"
#include "stereo_completion_gate.hpp"
#include "lens_centre_source_provenance.hpp"
#include "../game/car_base_shadow_stereo.hpp"
#include "../game/goal_progress_physical_source.hpp"
#include "../game/stage_extension_physical_source.hpp"
#include "../game/hud_native_source_transaction.hpp"
#include "../core/r29_owner_api.hpp"

namespace OutRunVRRenderer {
    std::uint64_t GetCurrentLatchedPoseEpoch() noexcept;
    std::uint64_t GetLastGameWvpPoseEpoch() noexcept;
    std::uint64_t GetLastGameWvpLensCentreCallEpoch() noexcept;
    bool GetLastRawGameWvpWrite(float outConstants[16],
        std::uint64_t& writeSerial, std::uint64_t& topLevelDrawSerial,
        std::uintptr_t& shaderIdentity, std::uint64_t& shaderSerial) noexcept;
    bool GetLastGameWvpSemanticProvenance(
        OutRunVR::GameSemantic::RenderScope& semanticScope,
        std::uint64_t& queueNodeEpoch, const void*& queueNode,
        OutRunVR::GameSemantic::ProducerToken& producerToken) noexcept;
}
namespace OutRunVRD3D9ExUpgradeR13
{
    bool IsCompatDevice(IDirect3DDevice9* device) noexcept;
    bool LastResetStateReplaySucceeded() noexcept;
}

namespace OutRunVRStereo
{
    inline void R33SynchronizeResetReplayGuardState(
        IDirect3DDevice9* device) noexcept;
    inline void FailClosedDepthStencilState() noexcept;

    namespace
    {
        SafetyHookInline R33ResetR22Hook{};
        SafetyHookInline R33PresentR13Hook{};
        SafetyHookInline R33ResolveDirectR13Hook{};
        SafetyHookInline R33SetRenderStateR29Hook{};
        SafetyHookInline R33DrawPrimitiveR30Hook{};
        SafetyHookInline R33DrawIndexedPrimitiveR30Hook{};
        SafetyHookInline R33DrawPrimitiveUPR30Hook{};
        SafetyHookInline R33DrawIndexedPrimitiveUPR30Hook{};

        struct R33DepthStencilWriteState
        {
            DWORD zEnable = D3DZB_TRUE;
            DWORD zWrite = TRUE;
            DWORD stencilEnable = FALSE;
            DWORD stencilWriteMask = 0xFFFFFFFFu;
            DWORD stencilFail = D3DSTENCILOP_KEEP;
            DWORD stencilZFail = D3DSTENCILOP_KEEP;
            DWORD stencilPass = D3DSTENCILOP_KEEP;
            DWORD twoSided = FALSE;
            DWORD ccwStencilFail = D3DSTENCILOP_KEEP;
            DWORD ccwStencilZFail = D3DSTENCILOP_KEEP;
            DWORD ccwStencilPass = D3DSTENCILOP_KEEP;
            // Recompute the stencil-op predicate only when the snapshot or
            // a tracked setter changes; ordinary stereo draws reuse it.
            bool mayWriteDepth = false;
            bool stencilWritesIfPresent = false;
            std::uint64_t depthGeneration = 0;
            std::uint64_t stateBlockRecordings = 0;
            std::uint64_t stateBlockApplies = 0;
            bool valid = false;
        };

        // SetRenderTarget(0, rightEye) resets the D3D9 viewport to the
        // complete target. Cache immutable surface extents while the device
        // generation is alive; avoid one redundant synchronous SetViewport per
        // world/HUD stereo primitive when the game's viewport is already full.
        struct R33RightViewportExtent
        {
            IDirect3DSurface9* surface = nullptr; // borrowed, never AddRef
            UINT width = 0;
            UINT height = 0;
            bool valid = false;
        };
        R33RightViewportExtent R33RightViewport{};

        bool R33TargetResetViewportMatches(
            IDirect3DSurface9* rightEye,
            const D3DVIEWPORT9& saved) noexcept
        {
            if (!rightEye || saved.X != 0 || saved.Y != 0 ||
                saved.MinZ != 0.0f || saved.MaxZ != 1.0f)
                return false;
            if (!R33RightViewport.valid ||
                R33RightViewport.surface != rightEye)
            {
                // Never skip when GetDesc fails or an untracked render target
                // replaces the eye surface. Reset clears borrowed identity.
                R33RightViewport = {};
                D3DSURFACE_DESC desc{};
                if (FAILED(rightEye->GetDesc(&desc)) ||
                    desc.Width == 0 || desc.Height == 0)
                    return false;
                R33RightViewport = {
                    rightEye, desc.Width, desc.Height, true
                };
            }
            return saved.Width == R33RightViewport.width &&
                saved.Height == R33RightViewport.height;
        }

        // Separate original-target and right-eye extent leases. A successful
        // game RT0 rebind resets to this full viewport; keep inset/offset/Z
        // viewport restoration explicit. Borrowed identities expire on Reset.
        R33RightViewportExtent R33SavedViewport{};

        bool R33SavedTargetResetViewportMatches(
            IDirect3DSurface9* savedRt,
            const D3DVIEWPORT9& saved) noexcept
        {
            if (!savedRt || saved.X != 0 || saved.Y != 0 ||
                saved.MinZ != 0.0f || saved.MaxZ != 1.0f ||
                saved.Width == 0 || saved.Height == 0)
                return false;
            if (!R33SavedViewport.valid ||
                R33SavedViewport.surface != savedRt)
            {
                R33SavedViewport = {};
                D3DSURFACE_DESC desc{};
                if (FAILED(savedRt->GetDesc(&desc)) ||
                    desc.Width == 0 || desc.Height == 0)
                    return false;
                R33SavedViewport = { savedRt, desc.Width, desc.Height, true };
            }
            return saved.Width == R33SavedViewport.width &&
                saved.Height == R33SavedViewport.height;
        }

        thread_local R33DepthStencilWriteState R33DepthStencilState{};
        std::uint64_t R33DepthStencilSyncs = 0;
        std::uint64_t R33DepthStencilCacheHits = 0;
        std::uint64_t R33DepthStencilLiveFallbacks = 0;
        std::uint64_t R33DepthStencilReadFailures = 0;
        std::uint64_t R33ResetSuccesses = 0;
        std::uint64_t R33ResetFailures = 0;
        bool R33FirstDepthStencilCacheLogged = false;
        bool R33FirstResetLifecycleLogged = false;

        std::atomic<bool> R33ResetReplayBlocked{false};
        std::uint64_t R33ReplayBlocks = 0;
        std::uint64_t R33RasterGuardDraws = 0;
        std::uint64_t R33LostDeviceBypasses = 0;
        bool R33FirstReplayBlockLogged = false;
        bool R33FirstLostDeviceBypassLogged = false;
        bool R33FirstRasterGuardLogged = false;

        struct R33PerfSnapshot
        {
            ULONGLONG lastLogMs = 0;
            std::uint64_t syncs = 0;
            std::uint64_t hits = 0;
            std::uint64_t live = 0;
            std::uint64_t readFail = 0;
            std::uint64_t resetOk = 0;
            std::uint64_t resetFail = 0;
        };
        R33PerfSnapshot R33Perf{};

        inline bool R33TelemetryEnabled() noexcept
        {
            return R32ReviewTelemetryEnabled();
        }

        void R33ReportInstallResult(bool active) noexcept
        {
            HookManager::ReportAsyncResult(
                "OpenXRVRStereoR33Dispatch", active);
        }

        void R33ForceResetReplayFailClosed(IDirect3DDevice9* device,
            const char* site) noexcept
        {
            if (!device || !R32ReviewIsGameDevice(device))
                return;

            OutRunVR::RuntimeEligibility::SetExternalSafetyBlock(true);
            R32ReviewFailClosedResetBaselineState();
            FailClosedDepthStencilState();
            R32ReviewArmStereoRecoverySafety();

            if (!R33FirstReplayBlockLogged)
            {
                R33FirstReplayBlockLogged = true;
                spdlog::error(
                    "VR R33 RESET REPLAY: classic D3D9 state replay is unhealthy at {}; stereo remains fail-closed until a later clean ResetEx replay",
                    site ? site : "unknown");
            }
        }

        void R33SetResetReplayGuardState(IDirect3DDevice9* device,
            bool healthy, const char* site, bool countBlock) noexcept
        {
            if (!device || !R32ReviewIsGameDevice(device))
                return;

            if (!OutRunVRD3D9ExUpgradeR13::IsCompatDevice(device))
            {
                R33ResetReplayBlocked.store(false, std::memory_order_release);
                OutRunVR::RuntimeEligibility::SetExternalSafetyBlock(false);
                return;
            }

            R33ResetReplayBlocked.store(!healthy, std::memory_order_release);
            OutRunVR::RuntimeEligibility::SetExternalSafetyBlock(!healthy);
            if (!healthy)
            {
                if (countBlock)
                    ++R33ReplayBlocks;
                R33ForceResetReplayFailClosed(device, site);
            }
        }

        template <typename DrawCall>
        HRESULT R33GuardStereoRasterState(IDirect3DDevice9* device,
            DrawCall&& drawCall, const char* site) noexcept
        {
            // The same game-device/internal-pass tests gate both semantic
            // consumption and stereo routing. Reuse their result for every
            // primitive instead of repeating the R30/R29 dispatch bridges.
            const bool gameDevice = device && R32ReviewIsGameDevice(device);
            const bool internalPass = gameDevice && R32ReviewInternalStereoPass();
            const auto drawSemanticValue =
                (gameDevice && !internalPass)
                ? OutRunVR::GameSemantic::ConsumeForDraw()
                : OutRunVR::GameSemantic::CurrentScope;
            OutRunVR::GameSemantic::ScopedRenderSemantic drawSemantic(
                drawSemanticValue);

            if (!gameDevice || internalPass ||
                OutRunVR::State::StateBlockTracker::Recording() ||
                !R32ReviewStereoWanted() || !R32ReviewTargetIsBackBuffer())
            {
                return drawCall(false);
            }

            // The guarded route flushes recovery once before taking a raster
            // snapshot. Pass that fact to R33Dispatch instead of repeating two
            // atomic recovery loads for every active stereo primitive.
            OutRunVR::State::StateBlockRecovery::FlushPendingResync(device);
            auto onGuardActive = [&]() noexcept {
                // Count routing diagnostics only while telemetry is enabled.
                if (R33TelemetryEnabled())
                    ++R33RasterGuardDraws;
                if (!R33FirstRasterGuardLogged)
                {
                    R33FirstRasterGuardLogged = true;
                    spdlog::info(
                        "VR R33 RASTER GUARD: final physical draw boundary preserves viewport/scissor across fast, HUD and R29 fallback eye-target switches");
                }
            };
            return R32ReviewRunRasterReplayGuard(
                device, site, [&]() noexcept { return drawCall(true); },
                onGuardActive);
        }

        void R33InvalidateDepthStencilCache() noexcept
        {
            R33DepthStencilState.valid = false;
        }

        // Preserve the original stencil-op semantics while removing repeated
        // 9-field checks from thousands of valid-cache stereo draws. The
        // attachment format is still checked live when stencil can be written.
        void R33RefreshWriteFlags(R33DepthStencilWriteState& s) noexcept
        {
            s.mayWriteDepth = s.zEnable != D3DZB_FALSE &&
                s.zWrite != FALSE;
            const bool frontWrites =
                s.stencilFail != D3DSTENCILOP_KEEP ||
                s.stencilZFail != D3DSTENCILOP_KEEP ||
                s.stencilPass != D3DSTENCILOP_KEEP;
            const bool backWrites = s.twoSided != FALSE &&
                (s.ccwStencilFail != D3DSTENCILOP_KEEP ||
                 s.ccwStencilZFail != D3DSTENCILOP_KEEP ||
                 s.ccwStencilPass != D3DSTENCILOP_KEEP);
            s.stencilWritesIfPresent = s.stencilEnable != FALSE &&
                s.stencilWriteMask != 0 && (frontWrites || backWrites);
        }

        bool R33ReadDepthStencilWriteState(IDirect3DDevice9* device) noexcept
        {
            if (!device)
                return false;

            R33DepthStencilWriteState next{};
            if (!R32ReviewTrackedDepthStencil())
            {
                next.valid = true;
                next.depthGeneration = R32ReviewMainDepthGeneration();
                next.stateBlockRecordings = OutRunVR::State::StateBlockTracker::RecordingGeneration();
                next.stateBlockApplies = OutRunVR::State::StateBlockTracker::ApplyGeneration();
                R33RefreshWriteFlags(next);
                R33DepthStencilState = next;
                if (R33TelemetryEnabled())
                    ++R33DepthStencilSyncs;
                return true;
            }

            // When Z testing is off, ZWRITEENABLE cannot modify depth.
            // Defer that driver read until ZENABLE is restored; the tracked
            // setter invalidates this partial snapshot on the transition.
            if (FAILED(device->GetRenderState(D3DRS_ZENABLE, &next.zEnable)))
            {
                if (R33TelemetryEnabled())
                    ++R33DepthStencilReadFailures;
                R33InvalidateDepthStencilCache();
                return false;
            }
            if (next.zEnable != D3DZB_FALSE &&
                FAILED(device->GetRenderState(D3DRS_ZWRITEENABLE, &next.zWrite)))
            {
                if (R33TelemetryEnabled())
                    ++R33DepthStencilReadFailures;
                R33InvalidateDepthStencilCache();
                return false;
            }

            if (R32ReviewMainDepthHasStencil())
            {
                // On the common stencil-disabled draw only the enable bit is
                // needed. Skip eight synchronous driver getters; the setter
                // invalidates this partial snapshot before re-enabling stencil.
                if (FAILED(device->GetRenderState(
                        D3DRS_STENCILENABLE, &next.stencilEnable)))
                {
                    if (R33TelemetryEnabled())
                        ++R33DepthStencilReadFailures;
                    R33InvalidateDepthStencilCache();
                    return false;
                }
                if (next.stencilEnable != FALSE)
                {
                    if (FAILED(device->GetRenderState(
                            D3DRS_STENCILWRITEMASK, &next.stencilWriteMask)))
                    {
                        if (R33TelemetryEnabled())
                            ++R33DepthStencilReadFailures;
                        R33InvalidateDepthStencilCache();
                        return false;
                    }
                    // A zero write mask likewise makes the seven stencil ops
                    // irrelevant until the mask transitions to nonzero.
                    if (next.stencilWriteMask != 0)
                    {
                        if (FAILED(device->GetRenderState(
                                D3DRS_STENCILFAIL, &next.stencilFail)) ||
                            FAILED(device->GetRenderState(
                                D3DRS_STENCILZFAIL, &next.stencilZFail)) ||
                            FAILED(device->GetRenderState(
                                D3DRS_STENCILPASS, &next.stencilPass)) ||
                            FAILED(device->GetRenderState(
                                D3DRS_TWOSIDEDSTENCILMODE, &next.twoSided)))
                        {
                            if (R33TelemetryEnabled())
                                ++R33DepthStencilReadFailures;
                            R33InvalidateDepthStencilCache();
                            return false;
                        }
                        // Single-sided stencil cannot execute the CCW ops.
                        // Save three live driver reads until two-sided mode
                        // is enabled; that tracked transition invalidates
                        // the partial snapshot before any stereo draw.
                        if (next.twoSided != FALSE &&
                            (FAILED(device->GetRenderState(
                                D3DRS_CCW_STENCILFAIL, &next.ccwStencilFail)) ||
                             FAILED(device->GetRenderState(
                                D3DRS_CCW_STENCILZFAIL, &next.ccwStencilZFail)) ||
                             FAILED(device->GetRenderState(
                                D3DRS_CCW_STENCILPASS, &next.ccwStencilPass))))
                        {
                            if (R33TelemetryEnabled())
                                ++R33DepthStencilReadFailures;
                            R33InvalidateDepthStencilCache();
                            return false;
                        }
                    }
                }
            }

            next.valid = true;
            R33RefreshWriteFlags(next);
            next.depthGeneration = R32ReviewMainDepthGeneration();
            next.stateBlockRecordings = OutRunVR::State::StateBlockTracker::RecordingGeneration();
            next.stateBlockApplies = OutRunVR::State::StateBlockTracker::ApplyGeneration();
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
            return R33DepthStencilState.valid &&
                R33DepthStencilState.depthGeneration == R32ReviewMainDepthGeneration() &&
                R33DepthStencilState.stateBlockRecordings ==
                    OutRunVR::State::StateBlockTracker::RecordingGeneration() &&
                R33DepthStencilState.stateBlockApplies == OutRunVR::State::StateBlockTracker::ApplyGeneration();
        }

        // Keep the per-world-draw right-eye attachment snapshot single-use.
        // The fragile-alpha promotion gate can check the generation-fenced
        // depth eligibility independently of the post-left-draw snapshot.
        bool R33FragileWorldDepthEligible() noexcept
        {
            return R32ReviewTrackedDepthStencil() &&
                R33DepthStencilCacheCurrent() &&
                R33DepthStencilState.zEnable != D3DZB_FALSE;
        }

        bool R33GetWriteFlags(IDirect3DDevice9* device,
            bool& mayWriteDepth, bool& mayWriteStencil) noexcept
        {
            mayWriteDepth = false;
            mayWriteStencil = false;
            if (!R32ReviewTrackedDepthStencil())
                return true;

            if (!OutRunVR::State::StateBlockTracker::Reliable())
            {
                if (R33TelemetryEnabled())
                    ++R33DepthStencilLiveFallbacks;
                mayWriteDepth = R32ReviewLeftDrawMayWriteDepth(device);
                mayWriteStencil = R32ReviewLeftDrawMayWriteStencil(device);
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
            mayWriteDepth = s.mayWriteDepth;
            // Keep the current depth-format gate authoritative. In the common
            // stencil-disabled / KEEP / zero-mask case this also avoids the
            // attachment-format probe on each stereo primitive.
            mayWriteStencil = s.stencilWritesIfPresent &&
                R32ReviewMainDepthHasStencil();
            return true;
        }

        // Single shared depth/stencil readiness path for world and HUD.
        // Normal synchronized draws make only one read of each sync bit.
        bool R33PrepareRightDepthStereo(IDirect3DDevice9* device) noexcept
        {
            if (!R32ReviewTrackedDepthStencil())
                return true;

            bool depthInSync = R32ReviewRightDepthInSync();
            bool stencilInSync = R32ReviewRightStencilInSync();
            if (!depthInSync || !stencilInSync)
            {
                R32ReviewTryBootstrapRightDepth(device);
                // Bootstrap can change depth ownership; preserve the original
                // post-bootstrap tracked-attachment and live-test veto.
                if (!R32ReviewTrackedDepthStencil())
                    return true;
                depthInSync = R32ReviewRightDepthInSync();
                stencilInSync = R32ReviewRightStencilInSync();
            }
            if (!depthInSync && R32ReviewDepthTestActive(device))
                return false;
            if (!stencilInSync && R32ReviewStencilTestActive(device))
                return false;
            return true;
        }

        void R33InvalidateRightForLeftWrite(
            bool mayWriteDepth, bool mayWriteStencil) noexcept
        {
            R32ReviewInvalidateRightDepthStencilSync(
                mayWriteDepth, mayWriteStencil);
        }

        HRESULT __stdcall SetRenderStateDestR33(IDirect3DDevice9* device,
            D3DRENDERSTATETYPE state, DWORD value)
        {
            const HRESULT hr = R33SetRenderStateR29Hook.stdcall<HRESULT>(
                device, state, value);
            if (FAILED(hr) || !R32ReviewIsGameDevice(device) || R32ReviewInternalStereoPass())
                return hr;

            if (OutRunVR::State::StateBlockTracker::Recording())
            {
                R33InvalidateDepthStencilCache();
                return hr;
            }
            if (!R33DepthStencilState.valid)
                return hr;

            // A repeated successful game state setter already matches the
            // tracked snapshot. Avoid re-evaluating depth/stencil write flags
            // on dense-scene state churn; changed values still invalidate
            // partial stencil snapshots and refresh the derived predicates.
            switch (state)
            {
            case D3DRS_ZENABLE:
                if (R33DepthStencilState.zEnable == value)
                    return hr;
                // ZWRITEENABLE was intentionally not read under disabled Z.
                // Transitioning to live depth tests must resample the device.
                if (R33DepthStencilState.zEnable == D3DZB_FALSE &&
                    value != D3DZB_FALSE)
                    R33InvalidateDepthStencilCache();
                R33DepthStencilState.zEnable = value;
                break;
            case D3DRS_ZWRITEENABLE:
                if (R33DepthStencilState.zWrite == value)
                    return hr;
                R33DepthStencilState.zWrite = value;
                break;
            case D3DRS_STENCILENABLE:
                if (R33DepthStencilState.stencilEnable == value)
                    return hr;
                // A disabled snapshot did not read stencil ops. Resample
                // before the next draw if stencil is switched back on.
                if (R33DepthStencilState.stencilEnable == FALSE && value != FALSE)
                    R33InvalidateDepthStencilCache();
                R33DepthStencilState.stencilEnable = value;
                break;
            case D3DRS_STENCILWRITEMASK:
                if (R33DepthStencilState.stencilWriteMask == value)
                    return hr;
                // A zero-mask snapshot omitted ops as well; re-read them
                // before the next eligible stencil-writing draw.
                if (R33DepthStencilState.stencilWriteMask == 0 && value != 0)
                    R33InvalidateDepthStencilCache();
                R33DepthStencilState.stencilWriteMask = value;
                break;
            case D3DRS_STENCILFAIL:
                if (R33DepthStencilState.stencilFail == value)
                    return hr;
                R33DepthStencilState.stencilFail = value;
                break;
            case D3DRS_STENCILZFAIL:
                if (R33DepthStencilState.stencilZFail == value)
                    return hr;
                R33DepthStencilState.stencilZFail = value;
                break;
            case D3DRS_STENCILPASS:
                if (R33DepthStencilState.stencilPass == value)
                    return hr;
                R33DepthStencilState.stencilPass = value;
                break;
            case D3DRS_TWOSIDEDSTENCILMODE:
                if (R33DepthStencilState.twoSided == value)
                    return hr;
                // The CCW ops are not sampled under single-sided stencil.
                if (R33DepthStencilState.twoSided == FALSE && value != FALSE)
                    R33InvalidateDepthStencilCache();
                R33DepthStencilState.twoSided = value;
                break;
            case D3DRS_CCW_STENCILFAIL:
                if (R33DepthStencilState.ccwStencilFail == value)
                    return hr;
                R33DepthStencilState.ccwStencilFail = value;
                break;
            case D3DRS_CCW_STENCILZFAIL:
                if (R33DepthStencilState.ccwStencilZFail == value)
                    return hr;
                R33DepthStencilState.ccwStencilZFail = value;
                break;
            case D3DRS_CCW_STENCILPASS:
                if (R33DepthStencilState.ccwStencilPass == value)
                    return hr;
                R33DepthStencilState.ccwStencilPass = value;
                break;
            default:
                return hr;
            }
            R33RefreshWriteFlags(R33DepthStencilState);

            // Do not rewrite depth/state-block generations here. If a StateBlock
            // made this snapshot stale, changing one tracked render state cannot
            // make the untouched fields authoritative again.
            return hr;
        }

        template <typename ActualDraw>
        R32ReviewOwnedResult R33TryFastWorld(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, const char* site)
        {
            if (OutRunVR::State::StateBlockTracker::Recording() || !R32ReviewStableStereoBase(device))
            {
                if (R33TelemetryEnabled() && R32ReviewIsGameDevice(device) &&
                    !R32ReviewInternalStereoPass() && R32ReviewTargetIsBackBuffer())
                    R32ReviewNoteDispatchUnstable();
                return {};
            }

            bool fragile = true;
            const bool stateBlocksReliable =
                OutRunVR::State::StateBlockTracker::Reliable();
            const bool effectKnown = stateBlocksReliable
                ? R32ReviewFragileEffectCached(device, fragile)
                : R32ReviewEffectIsFragileLive(device, fragile);
            if (!effectKnown)
                return {};
            // Fragile translucent geometry uses the existing R29/R30
            // fail-closed eye path; semantic tags cannot authorize the R33
            // cached-WVP fast route for alpha/depth-write-disabled draws.
            if (fragile)
            {
                if (R33TelemetryEnabled())
                    R32ReviewNoteDispatchFragile();
                return {};
            }

            if (!R32ReviewEnsureStereoResources(device))
                return {};
            // Avoid redundant cross-TU sync reads on the stereo draw path;
            // the helper resamples after bootstrap and keeps the live vetoes.
            if (!R33PrepareRightDepthStereo(device))
                return {};

            // Read the one BeginScene-latched pose in place: avoid copying both
            // eye transforms for every world/HUD primitive. This pointer is
            // never retained across a scene/reset boundary.
            const auto* stereo = OutRunVRRenderer::GetLatchedStereoFrameView();
            if (!stereo)
                return {};
            const std::uint32_t framePoseSequence =
                R32ReviewFrameStereoPoseSequence();
            if (framePoseSequence != 0 &&
                framePoseSequence != stereo->poseSequence)
                return {};

            R32ReviewFastWorldConstants draw{};
            if (!R32ReviewBuildFastWorldConstants(device, *stereo, draw))
                return {};

            D3DVIEWPORT9 savedViewport{};
            if (!R32ReviewGetSavedViewport(device, savedViewport))
                return {};

            bool mayWriteDepth = false;
            bool mayWriteStencil = false;
            if (!R33GetWriteFlags(device, mayWriteDepth, mayWriteStencil))
                return {};
            bool leftWvpOk = false;
            {
                R32ReviewInternalStereoPassScope guard;
                leftWvpOk = R32ReviewSetWvpBatch(device, draw.eyeConstants[0]);
            }
            if (!leftWvpOk)
            {
                bool rolledBack = false;
                {
                    R32ReviewInternalStereoPassScope guard;
                    rolledBack = R32ReviewSetWvpBatch(device, draw.originalConstants);
                }
                if (!rolledBack)
                {
                    // A failed original-WVP rollback invalidates this Present,
                    // not only future mono-safety frames.
                    R32ReviewMarkFrameRightDrawFailed();
                    R32ReviewReportStereoFailure(OutRunVR::StereoFailureRestoreFailed,
                        "R33/fast-left-WVP-rollback");
                    R32ReviewNoteRestoreFailure("R33 fast left-eye c64 rollback");
                    R32ReviewArmStereoRecoverySafety();
                    return { true, E_FAIL };
                }
                return {};
            }

            R32ReviewNoteStereoDrawWithoutMonoBackup();
            if (mayWriteDepth || mayWriteStencil)
                R32ReviewNoteMainDepthContentWrite();

            R32ReviewOwnedResult result{ true, actualDraw() };
            if (FAILED(result.hr))
            {
                // R30's lower owner already vetoes this frame on a failed
                // left-eye draw. Match it in both R84 fast-world and HUD paths:
                // future mono safety cannot retract a pending stereo Present.
                R32ReviewMarkFrameRightDrawFailed();
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                R32ReviewReportStereoFailure(OutRunVR::StereoFailureLeftDrawFailed, site, result.hr);
                bool restored = false;
                {
                    R32ReviewInternalStereoPassScope guard;
                    restored = R32ReviewSetWvpBatch(device, draw.originalConstants);
                }
                if (!restored)
                    R32ReviewNoteRestoreFailure("R33 fast left draw c64");
                R32ReviewArmStereoRecoverySafety();
                return result;
            }

            IDirect3DSurface9* savedRt = R32ReviewTrackedRenderTarget();
            IDirect3DSurface9* savedDepth = R32ReviewTrackedDepthStencil();
            // Reliable StateBlock/setter tracking proves that neither eye has
            // a depth attachment. Do not submit null depth bindings twice per
            // primitive; unreliable tracking retains the full restore path.
            const bool depthlessPass = savedDepth == nullptr &&
                OutRunVR::State::StateBlockTracker::Reliable();
            const bool skipSavedViewportRestore =
                OutRunVR::State::StateBlockTracker::Reliable() &&
                R33SavedTargetResetViewportMatches(savedRt, savedViewport);
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                R32ReviewInternalStereoPassScope guard;
                IDirect3DSurface9* rightEye = R32ReviewRightEyeSurface();
                const bool viewportAlreadyFull =
                    R33TargetResetViewportMatches(rightEye, savedViewport);
                rightHr = R32ReviewSetRenderTarget(device, 0u, rightEye);
                if (SUCCEEDED(rightHr) && !depthlessPass)
                    rightHr = R32ReviewSetDepthStencilSurface(
                        device, savedDepth ? R32ReviewRightEyeDepth() : nullptr);
                // SetRenderTarget already established this exact full
                // viewport. Keep the setter for all inset, offset, depth-range,
                // resized or unknown targets; only the proven case elides it.
                if (SUCCEEDED(rightHr) && !viewportAlreadyFull)
                    rightHr = device->SetViewport(&savedViewport);
                if (SUCCEEDED(rightHr) &&
                    !R32ReviewSetWvpBatch(device, draw.eyeConstants[1]))
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
                restoreOk = R32ReviewRestoreRightPassState(
                    device, savedRt, savedDepth, savedViewport,
                    draw.originalConstants, true, depthlessPass, skipSavedViewportRestore);
            }

            // Never publish a completed stereo draw or its pose metadata
            // before BOTH physical eyes and the game render state are valid.
            if (OutRunVR::StereoCompletion::CanPublishStereoDraw(
                    SUCCEEDED(result.hr), SUCCEEDED(rightHr), restoreOk))
            {
                R32ReviewRecordWorldStereoDuplicate(
                    draw.poseSequence, *stereo);
                R32ReviewNoteStableTwoEyeDraw();
                if (R33TelemetryEnabled())
                {
                    R32ReviewNoteDispatchFastWorld();
                }
            }

            if (FAILED(rightHr))
            {
                R32ReviewMarkFrameRightDrawFailed();
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                R32ReviewReportStereoFailure(rightFailure, site, rightHr);
                R32ReviewArmStereoRecoverySafety();
            }
            if (!restoreOk)
            {
                // Even a successful right draw is unusable if RT/depth,
                // viewport or c64 restoration fails on this frame. Keep the
                // immediate publication veto separate from future mono safety.
                R32ReviewMarkFrameRightDrawFailed();
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                R32ReviewNoteRestoreFailure("R33 fast right-eye draw");
                R32ReviewArmStereoRecoverySafety();
            }
            return result;
        }

        template <typename ActualDraw>
        R32ReviewOwnedResult R33TryHud(IDirect3DDevice9* device,
            R32ReviewScreenSpaceKind screenKind,
            ActualDraw&& actualDraw, const char* site)
        {
            // R33Dispatch has already classified this draw. Reclassifying
            // a flat-perspective HUD here repeats up to three D3D9 render-state
            // queries on the per-primitive hot path without changing routing.
            if (OutRunVR::State::StateBlockTracker::Recording() || !R32ReviewStableStereoBase(device) ||
                screenKind == R32ReviewScreenSpaceKind::None)
                return {};

            if (!OutRunVR::State::StateBlockTracker::Reliable())
            {
                R32ReviewDiscardUnreliableDrawCaches();
                const std::uintptr_t cachedShader =
                    R32ReviewCurrentVertexShaderIdentity();
                if (!R32ReviewLiveVertexShaderMatches(device, cachedShader))
                    return {};
            }

            if (!R32ReviewEnsureStereoResources(device))
                return {};
            // Avoid redundant cross-TU sync reads on the stereo draw path;
            // the helper resamples after bootstrap and keeps the live vetoes.
            if (!R33PrepareRightDepthStereo(device))
                return {};

            // Read the one BeginScene-latched pose in place: avoid copying both
            // eye transforms for every world/HUD primitive. This pointer is
            // never retained across a scene/reset boundary.
            const auto* stereo = OutRunVRRenderer::GetLatchedStereoFrameView();
            if (!stereo)
                return {};
            const std::uint32_t framePoseSequence =
                R32ReviewFrameStereoPoseSequence();
            if (framePoseSequence != 0 &&
                framePoseSequence != stereo->poseSequence)
                return {};

            float original[16]{};
            float eyeConstants[2][16]{};
            float eyeScale[2]{};
            float eyeOffset[2]{};
            if (!R32ReviewBuildScreenSpaceEyeConstants(device, *stereo, screenKind,
                    original, eyeConstants, eyeScale, eyeOffset))
                return {};

            D3DVIEWPORT9 savedViewport{};
            if (!R32ReviewGetSavedViewport(device, savedViewport))
                return {};

            bool mayWriteDepth = false;
            bool mayWriteStencil = false;
            if (!R33GetWriteFlags(device, mayWriteDepth, mayWriteStencil))
                return {};

            bool leftWvpOk = false;
            {
                R32ReviewInternalStereoPassScope guard;
                leftWvpOk = R32ReviewSetWvpBatch(device, eyeConstants[0]);
            }
            if (!leftWvpOk)
            {
                bool rolledBack = false;
                {
                    R32ReviewInternalStereoPassScope guard;
                    rolledBack = R32ReviewSetWvpBatch(device, original);
                }
                if (!rolledBack)
                {
                    // A failed original-WVP rollback invalidates this Present,
                    // not only future mono-safety frames.
                    R32ReviewMarkFrameRightDrawFailed();
                    R32ReviewReportStereoFailure(OutRunVR::StereoFailureRestoreFailed,
                        "R33/HUD-left-WVP-rollback");
                    R32ReviewNoteRestoreFailure("R33 HUD left-eye c64 rollback");
                    R32ReviewArmStereoRecoverySafety();
                    return { true, E_FAIL };
                }
                return {};
            }

            // The exact C993 centre is a source-owned world billboard.
            // A native left-eye Draw can reenter another producer or shader.
            // Do not send the old left-eye constants to an unrelated right
            // eye merely because the original left Draw returned S_OK.
            auto captureCentreSource = [&]() noexcept {
                const auto command =
                    OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
                // Use the BeginScene-borrowed live pose; a second view
                // acquisition per Draw defeats R33's frame-pose contract.
                // Reset invalidates this same slot, so validate it again.
                std::uintptr_t shader = 0;
                std::uint64_t shaderEpoch = 0;
                const bool validShader =
                    R29OwnerCurrentShaderEpoch(shader, shaderEpoch);
                return OutRunVR::LensCentre::StereoDrawSource{
                    command.lensCentreCallEpoch,
                    R29OwnerTopLevelDrawSerial(),
                    shaderEpoch,
                    (stereo && stereo->valid)
                        ? stereo->poseSequence : 0u,
                    shader,
                    command.IsDirectWorldLensCentre() && validShader
                };
            };
            // R30 admitted an original source-owned WVP. Its native upload
            // serial must survive the reentrant left GPU Draw before R33
            // may submit the already-computed right-eye c64.
            auto captureCentreRawSource = [&]() noexcept {
                const auto command =
                    OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
                float gameRaw[16]{};
                std::uint64_t serial = 0, writtenDraw = 0;
                std::uint64_t writtenShaderEpoch = 0;
                std::uintptr_t writtenShader = 0, shader = 0;
                std::uint64_t shaderEpoch = 0, queueEpoch = 0;
                const void* queueNode = nullptr;
                OutRunVR::GameSemantic::RenderScope writtenScope =
                    OutRunVR::GameSemantic::RenderScope::None;
                OutRunVR::GameSemantic::ProducerToken writtenProducer =
                    OutRunVR::GameSemantic::ProducerToken::None;
                const auto pose = OutRunVRRenderer::GetCurrentLatchedPoseEpoch();
                const auto writtenPose =
                    OutRunVRRenderer::GetLastGameWvpPoseEpoch();
                const auto writtenCall =
                    OutRunVRRenderer::GetLastGameWvpLensCentreCallEpoch();
                const bool exactRaw = command.IsDirectWorldLensCentre() &&
                    OutRunVRRenderer::GetLastRawGameWvpWrite(
                        gameRaw, serial, writtenDraw,
                        writtenShader, writtenShaderEpoch) &&
                    OutRunVRRenderer::GetLastGameWvpSemanticProvenance(
                        writtenScope, queueEpoch, queueNode, writtenProducer) &&
                    R29OwnerCurrentShaderEpoch(shader, shaderEpoch) &&
                    OutRunVR::LensCentre::AdmitsCentreRawSourceScope(
                        writtenScope, writtenProducer, queueNode,
                        command.lensCentreCallEpoch, writtenCall,
                        R29OwnerTopLevelDrawSerial() + 1u, writtenDraw) &&
                    command.lensCentreCallEpoch != 0 &&
                    command.lensCentreCallEpoch == writtenCall &&
                    pose != 0 && pose == writtenPose &&
                    writtenShader != 0 && writtenShader == shader &&
                    writtenShaderEpoch != 0 &&
                    writtenShaderEpoch == shaderEpoch;
                return OutRunVR::LensCentre::RawStereoSource{
                    serial, writtenDraw, command.lensCentreCallEpoch,
                    writtenCall, pose, writtenPose, writtenShader,
                    writtenShaderEpoch, exactRaw};
            };
            const bool exactCentreEye =
                screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld;
            const auto centreBeforeLeft = exactCentreEye
                ? captureCentreSource()
                : OutRunVR::LensCentre::StereoDrawSource{};
            const auto centreRawBeforeLeft = exactCentreEye
                ? captureCentreRawSource()
                : OutRunVR::LensCentre::RawStereoSource{};

            // Only the original player shadow's game WVP may feed the right
            // eye. Native left Draw may synchronously reenter another producer,
            // overwrite game c64, switch shader or invalidate the latched pose.
            // Never use the already eye-corrected live GPU c64 as evidence.
            auto captureShadowSource = [&]() noexcept {
                const auto command =
                    OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
                // A nested native callback may have selected another physical
                // owner. Fail before reading a foreign game's raw GPU c64.
                if (!command.IsDirectCarBaseShadow())
                    return OutRunVR::CarShadowStereo::StereoDrawSource{};
                float rawGameWvp[16]{};
                std::uint64_t uploadSerial=0, uploadDraw=0;
                std::uint64_t writeShaderEpoch=0, shaderEpoch=0;
                std::uintptr_t writeShader=0, shader=0;
                std::uint64_t queueEpoch=0;
                const void* queueNode=nullptr;
                OutRunVR::GameSemantic::RenderScope writtenScope =
                    OutRunVR::GameSemantic::RenderScope::None;
                OutRunVR::GameSemantic::ProducerToken writtenProducer =
                    OutRunVR::GameSemantic::ProducerToken::None;
                const auto drawSerial = R29OwnerTopLevelDrawSerial();
                // R30 proved this same direct original WVP before building
                // the two eyes. Reject a now-foreign/shader/pose/queue
                // source before native LEFT (not only after it).
                const bool sourceOwned =
                    OutRunVRRenderer::GetLastRawGameWvpWrite(
                        rawGameWvp, uploadSerial, uploadDraw,
                        writeShader, writeShaderEpoch) &&
                    uploadSerial != 0 &&
                    OutRunVRRenderer::GetLastGameWvpSemanticProvenance(
                        writtenScope, queueEpoch, queueNode, writtenProducer) &&
                    R29OwnerCurrentShaderEpoch(shader, shaderEpoch) &&
                    drawSerial != UINT64_MAX &&
                    OutRunVR::CarShadowStereo::OwnsDirectGameWvp({
                        OutRunVRRenderer::GetCurrentLatchedPoseEpoch(),
                        OutRunVRRenderer::GetLastGameWvpPoseEpoch(),
                        drawSerial + 1u, uploadDraw,
                        shader, writeShader, shaderEpoch, writeShaderEpoch,
                        writtenScope, writtenProducer, queueNode, queueEpoch
                    });
                return OutRunVR::CarShadowStereo::StereoDrawSource{
                    uploadSerial, uploadDraw,
                    OutRunVRRenderer::GetCurrentLatchedPoseEpoch(),
                    OutRunVRRenderer::GetLastGameWvpPoseEpoch(),
                    drawSerial, shaderEpoch, shader,
                    (stereo && stereo->valid) ? stereo->poseSequence : 0u,
                    command.IsDirectCarBaseShadow() && sourceOwned
                };
            };
            const bool exactShadowEye =
                screenKind == R32ReviewScreenSpaceKind::ExactCarBaseShadowWorld;
            const auto shadowBeforeLeft = exactShadowEye
                ? captureShadowSource()
                : OutRunVR::CarShadowStereo::StereoDrawSource{};

            // Shader/c64 HUD bypasses R30's fixedfn/XYZRHW source fence.
            // A native left callback may select a foreign GOAL result child;
            // never bind the old per-eye matrix to that new GPU owner.
            auto captureGoalSource = [&]() noexcept {
                const auto cmd = OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
                std::uintptr_t shader = 0;
                std::uint64_t shaderEpoch = 0;
                if (!R29OwnerCurrentShaderEpoch(shader, shaderEpoch) &&
                    R29OwnerCurrentVertexShaderIdentity() != 0)
                    return OutRunVR::GoalPhysical::Source{};
                // GOAL 0-99 and result child draws can reenter another
                // original c64 writer without changing queue, shader or
                // current pose. Keep native LEFT and RIGHT on that writer.
                // R32's temporary stereo eye uploads are excluded here.
                float originalRawWvp[16]{};
                std::uint64_t rawWriteSerial = 0, rawDrawSerial = 0;
                std::uintptr_t rawShader = 0;
                std::uint64_t rawShaderEpoch = 0;
                if (!OutRunVRRenderer::GetLastRawGameWvpWrite(
                        originalRawWvp, rawWriteSerial, rawDrawSerial,
                        rawShader, rawShaderEpoch) ||
                    rawWriteSerial == 0 || rawDrawSerial == 0)
                {
                    rawWriteSerial = 0;
                    rawDrawSerial = 0;
                }
                return OutRunVR::GoalPhysical::Source{
                    cmd.scope, cmd.producer, cmd.queued, cmd.queueNode,
                    cmd.queueEpoch, OutRunVRRenderer::GetCurrentLatchedPoseEpoch(),
                    R29OwnerTopLevelDrawSerial(), shader, shaderEpoch,
                    rawWriteSerial, rawDrawSerial};
            };
            const auto goalCommand =
                OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
            // The full original +TIME family has a distinct physical owner
            // from GOAL, including direct numeric glyphs and queued sprites.
            // R30 checks fixedfn/XYZRHW, but shader/c64 uses this R33 path;
            // the native left GPU Draw must not reenter a foreign producer
            // before the right eye is submitted.
            auto captureStageSource = [&]() noexcept {
                const auto cmd =
                    OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
                std::uintptr_t shader = 0;
                std::uint64_t shaderEpoch = 0;
                if (!R29OwnerCurrentShaderEpoch(shader, shaderEpoch) &&
                    R29OwnerCurrentVertexShaderIdentity() != 0)
                    return OutRunVR::StageExtensionPhysical::Source{};
                // The native LEFT callback can synchronously invoke another
                // original game c64 writer without changing the queue,
                // producer, shader or pose. Private R32 eye uploads do not
                // advance this original game WVP generation.
                float originalRawWvp[16]{};
                std::uint64_t rawWriteSerial = 0, rawDrawSerial = 0;
                std::uintptr_t rawShader = 0;
                std::uint64_t rawShaderEpoch = 0;
                if (!OutRunVRRenderer::GetLastRawGameWvpWrite(
                        originalRawWvp, rawWriteSerial, rawDrawSerial,
                        rawShader, rawShaderEpoch) ||
                    rawWriteSerial == 0 || rawDrawSerial == 0)
                {
                    rawWriteSerial = 0;
                    rawDrawSerial = 0;
                }
                return OutRunVR::StageExtensionPhysical::Source{
                    cmd.scope, cmd.producer, cmd.queued, cmd.queueNode,
                    cmd.queueEpoch,
                    OutRunVRRenderer::GetCurrentLatchedPoseEpoch(),
                    R29OwnerTopLevelDrawSerial(), shader, shaderEpoch,
                    rawWriteSerial, rawDrawSerial};
            };
            const bool exactStageEye = goalCommand.IsExactFiniteResultHud() &&
                goalCommand.producer ==
                    OutRunVR::GameSemantic::ProducerToken::StageExtensionTime;
            const auto stageBeforeLeft = exactStageEye
                ? captureStageSource()
                : OutRunVR::StageExtensionPhysical::Source{};
            const bool exactGoalEye = goalCommand.IsExactFiniteResultHud() &&
                !exactStageEye;
            const auto goalBeforeLeft = exactGoalEye
                ? captureGoalSource() : OutRunVR::GoalPhysical::Source{};
            // Native shader HUD must preserve the same physical owner across
            // both eye draws. A left Draw callback may reenter a different
            // original SpriteNode without changing its shader or render state.
            const bool exactNativeHud = goalCommand.IsSourceProvenHud() &&
                !exactStageEye && !exactGoalEye;
            auto captureNativeHudSource = [&]() noexcept {
                const auto cmd = OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
                std::uintptr_t shader = 0;
                std::uint64_t shaderEpoch = 0;
                if (!R29OwnerCurrentShaderEpoch(shader, shaderEpoch))
                    return OutRunVR::HudNativeSource::SourceStamp{};
                return OutRunVR::HudNativeSource::StampPhysicalCommand(
                    cmd, OutRunVRRenderer::GetCurrentLatchedPoseEpoch(),
                    shader, shaderEpoch, R29OwnerTopLevelDrawSerial());
            };
            const auto hudBeforeLeft = exactNativeHud
                ? captureNativeHudSource()
                : OutRunVR::HudNativeSource::SourceStamp{};
            if ((exactCentreEye &&
                 !OutRunVR::LensCentre::IsCoherentNativeCentrePair(
                     centreBeforeLeft, centreRawBeforeLeft)) ||
                (exactNativeHud &&
                 !OutRunVR::HudNativeSource::IsExactHudSource(hudBeforeLeft)) ||
                (exactShadowEye &&
                 !OutRunVR::CarShadowStereo::IsCoherentBeforeNativeLeft(
                     shadowBeforeLeft)) ||
                (exactStageEye &&
                 !OutRunVR::StageExtensionPhysical::IsValid(stageBeforeLeft)) ||
                (exactGoalEye &&
                 !OutRunVR::GoalPhysical::IsValid(goalBeforeLeft)))
            {
                // Temporary left c64 already uploaded; preserve original
                // game Draw only after rolling back the uploaded matrix.
                bool restored = false;
                {
                    R32ReviewInternalStereoPassScope guard;
                    restored = R32ReviewSetWvpBatch(device, original);
                }
                if (!restored)
                {
                    R32ReviewMarkFrameRightDrawFailed();
                    R32ReviewNoteRestoreFailure(
                        exactCentreEye ? "R33 C993 pre-left c64 rollback"
                        : exactShadowEye ? "R33 car shadow pre-left c64 rollback"
                        : exactStageEye ? "R33 +TIME pre-left c64 rollback"
                                       : "R33 GOAL pre-left c64 rollback");
                    R32ReviewArmStereoRecoverySafety();
                    return {true, E_FAIL};
                }
                return {};
            }

            R32ReviewNoteStereoDrawWithoutMonoBackup();
            if (mayWriteDepth || mayWriteStencil)
                R32ReviewNoteMainDepthContentWrite();

            R32ReviewOwnedResult result{ true, actualDraw() };
            if (FAILED(result.hr))
            {
                // R30's lower owner already vetoes this frame on a failed
                // left-eye draw. Match it in both R84 fast-world and HUD paths:
                // future mono safety cannot retract a pending stereo Present.
                R32ReviewMarkFrameRightDrawFailed();
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                bool restored = false;
                {
                    R32ReviewInternalStereoPassScope guard;
                    restored = R32ReviewSetWvpBatch(device, original);
                }
                R32ReviewReportStereoFailure(OutRunVR::StereoFailureLeftDrawFailed,
                    site, result.hr);
                if (!restored)
                    R32ReviewNoteRestoreFailure("R33 HUD left draw c64");
                R32ReviewArmStereoRecoverySafety();
                return result;
            }

            const auto centreAfterLeft = exactCentreEye
                ? captureCentreSource()
                : OutRunVR::LensCentre::StereoDrawSource{};
            const auto centreRawAfterLeft = exactCentreEye
                ? captureCentreRawSource()
                : OutRunVR::LensCentre::RawStereoSource{};
            const bool centreSourceChanged = exactCentreEye &&
                (!OutRunVR::LensCentre::SameStereoDrawSource(
                    centreBeforeLeft, centreAfterLeft) ||
                 !OutRunVR::LensCentre::SameRawStereoSource(
                    centreRawBeforeLeft, centreRawAfterLeft) ||
                 !OutRunVR::LensCentre::IsCoherentNativeCentrePair(
                    centreAfterLeft, centreRawAfterLeft));
            const auto shadowAfterLeft = exactShadowEye
                ? captureShadowSource()
                : OutRunVR::CarShadowStereo::StereoDrawSource{};
            const bool shadowSourceChanged = exactShadowEye &&
                (!OutRunVR::CarShadowStereo::IsCoherentBeforeNativeLeft(
                     shadowAfterLeft) ||
                 !OutRunVR::CarShadowStereo::SameStereoDrawSource(
                     shadowBeforeLeft, shadowAfterLeft));
            const bool goalSourceChanged = exactGoalEye &&
                !OutRunVR::GoalPhysical::SameAfterNativeLeft(
                    goalBeforeLeft, captureGoalSource());
            const bool stageSourceChanged = exactStageEye &&
                !OutRunVR::StageExtensionPhysical::SameAfterNativeLeft(
                    stageBeforeLeft, captureStageSource());
            const bool nativeHudSourceChanged = exactNativeHud &&
                !OutRunVR::HudNativeSource::SameSourceAfterNativeUpload(
                    hudBeforeLeft, captureNativeHudSource());
            if (centreSourceChanged || shadowSourceChanged ||
                goalSourceChanged || stageSourceChanged ||
                nativeHudSourceChanged)
            {
                // Left native Draw already ran once; never replay it.
                // Restore the game's original GPU c64 without submitting
                // an unrelated right-eye flare, invalidate this stereo frame
                // and preserve the original left Draw HRESULT.
                bool restored = false;
                {
                    R32ReviewInternalStereoPassScope guard;
                    restored = R32ReviewSetWvpBatch(device, original);
                }
                R32ReviewMarkFrameRightDrawFailed();
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                R32ReviewReportStereoFailure(
                    restored ? OutRunVR::StereoFailureRightStateFailed
                             : OutRunVR::StereoFailureRestoreFailed,
                    shadowSourceChanged ? "R33/car-shadow-source-changed"
                        : goalSourceChanged ? "R33/GOAL-source-changed"
                        : stageSourceChanged ? "R33/+TIME-source-changed"
                        : nativeHudSourceChanged ? "R33/HUD-source-changed"
                                                 : "R33/C993-centre-source-changed",
                    E_FAIL);
                if (!restored)
                    R32ReviewNoteRestoreFailure(
                        shadowSourceChanged
                            ? "R33 car shadow original c64 rollback"
                          : goalSourceChanged
                            ? "R33 GOAL original c64 rollback"
                          : stageSourceChanged
                            ? "R33 +TIME original c64 rollback"
                          : nativeHudSourceChanged
                            ? "R33 HUD original c64 rollback"
                            : "R33 C993 original c64 rollback");
                R32ReviewArmStereoRecoverySafety();
                return result;
            }

            IDirect3DSurface9* savedRt = R32ReviewTrackedRenderTarget();
            IDirect3DSurface9* savedDepth = R32ReviewTrackedDepthStencil();
            // Reliable StateBlock/setter tracking proves that neither eye has
            // a depth attachment. Do not submit null depth bindings twice per
            // primitive; unreliable tracking retains the full restore path.
            const bool depthlessPass = savedDepth == nullptr &&
                OutRunVR::State::StateBlockTracker::Reliable();
            const bool skipSavedViewportRestore =
                OutRunVR::State::StateBlockTracker::Reliable() &&
                R33SavedTargetResetViewportMatches(savedRt, savedViewport);
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                R32ReviewInternalStereoPassScope guard;
                IDirect3DSurface9* rightEye = R32ReviewRightEyeSurface();
                const bool viewportAlreadyFull =
                    R33TargetResetViewportMatches(rightEye, savedViewport);
                rightHr = R32ReviewSetRenderTarget(device, 0u, rightEye);
                if (SUCCEEDED(rightHr) && !depthlessPass)
                    rightHr = R32ReviewSetDepthStencilSurface(
                        device, savedDepth ? R32ReviewRightEyeDepth() : nullptr);
                // SetRenderTarget already established this exact full
                // viewport. Keep the setter for all inset, offset, depth-range,
                // resized or unknown targets; only the proven case elides it.
                if (SUCCEEDED(rightHr) && !viewportAlreadyFull)
                    rightHr = device->SetViewport(&savedViewport);
                if (SUCCEEDED(rightHr) &&
                    !R32ReviewSetWvpBatch(device, eyeConstants[1]))
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
                restoreOk = R32ReviewRestoreRightPassState(
                    device, savedRt, savedDepth, savedViewport, original, true, depthlessPass, skipSavedViewportRestore);
            }

            // Never publish a completed stereo draw or its pose metadata
            // before BOTH physical eyes and the game render state are valid.
            if (OutRunVR::StereoCompletion::CanPublishStereoDraw(
                    SUCCEEDED(result.hr), SUCCEEDED(rightHr), restoreOk))
            {
                R32ReviewRecordHudStereoDuplicate();
                R32ReviewNoteStableTwoEyeDraw();
                R32ReviewNoteScreenSpaceFovDraw();
                if (R33TelemetryEnabled())
                {
                    R32ReviewNoteDispatchHud();
                }
            }

            if (FAILED(rightHr))
            {
                R32ReviewMarkFrameRightDrawFailed();
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                R32ReviewReportStereoFailure(rightFailure, site, rightHr);
                R32ReviewArmStereoRecoverySafety();
            }
            if (!restoreOk)
            {
                // Even a successful right draw is unusable if RT/depth,
                // viewport or c64 restoration fails on this frame. Keep the
                // immediate publication veto separate from future mono safety.
                R32ReviewMarkFrameRightDrawFailed();
                R33InvalidateRightForLeftWrite(
                    mayWriteDepth, mayWriteStencil);
                R32ReviewNoteRestoreFailure("R33 HUD right-eye draw");
                R32ReviewArmStereoRecoverySafety();
            }
            // The C993 original-WVP source was merely *eligible* at R30.
            // Only this actual physical R33 draw confirms two per-eye GPU
            // submissions plus state restoration. Keep the diagnostic
            // separately identifiable from original lens CABE halos.
            if (screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld &&
                R33TelemetryEnabled())
            {
                const bool complete = SUCCEEDED(result.hr) &&
                    SUCCEEDED(rightHr) && restoreOk;
                static thread_local bool recordedComplete = false;
                static thread_local bool recordedFailure = false;
                bool& recorded = complete
                    ? recordedComplete : recordedFailure;
                if (!recorded)
                {
                    recorded = true;
                    spdlog::info(
                        "VR R84 C993 EXACT_STEREO_DRAW: {} "
                        "left=0x{:08X} right=0x{:08X} restored={} poseSeq={}",
                        complete ? "BOTH_EYES_OK" : "EYE_OR_RESTORE_FAILED",
                        static_cast<unsigned>(result.hr),
                        static_cast<unsigned>(rightHr), restoreOk,
                        stereo->poseSequence);
                }
            }
            return result;
        }

        template <typename ActualDraw, typename LowerR29Draw>
        HRESULT R33Dispatch(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, LowerR29Draw&& lowerR29Draw,
            const char* site, bool resyncAlreadyFlushed,
            bool telemetry) noexcept
        {
            // Only the early raster-guard bypass reaches this path without an
            // earlier flush; keep StateBlock recovery there, including when
            // stereo is disabled, without paying for a duplicate active flush.
            if (!resyncAlreadyFlushed &&
                !OutRunVR::State::StateBlockTracker::Recording())
                OutRunVR::State::StateBlockRecovery::FlushPendingResync(device);
            // Use the same per-draw diagnostics publication as the workload
            // observer: do not call across the R32 TU a second time.
            if (telemetry)
                R32ReviewObserveDispatchDraw(device);

            if (OutRunVR::State::StateBlockTracker::Recording())
            {
                if (telemetry)
                    R32ReviewNoteDispatchFallback();
                if (GpuWaterProbe::Enabled())
                    GpuWaterProbe::instance().noteRoute(device, 
                        GpuWaterProbe::DrawRoute::RecordingRaw);
                return actualDraw();
            }

            // The raster guard has already rejected mono/non-game, auxiliary
            // targets and StateBlock recording. A false flush flag after the
            // recording case means this draw cannot enter a stereo route.
            // Keep the lower R29 fail-closed policy and semantic ownership,
            // but avoid its redundant R33 screen-pass classification (which
            // may perform live D3D9 render-state reads per primitive).
            auto fallbackToR29 = [&]() -> HRESULT {
                R32ReviewDiscardUnreliableDrawCaches();
                if (telemetry)
                    R32ReviewNoteDispatchFallback();
                if (GpuWaterProbe::Enabled())
                    GpuWaterProbe::instance().noteRoute(device, 
                        GpuWaterProbe::DrawRoute::R29Fallback);
                return R32ReviewRunLowerFailClosed(device,
                    std::forward<LowerR29Draw>(lowerR29Draw));
            };
            // R33's raster guard may reject an otherwise source-owned C993
            // sun before any source/WVP classification (mono, lost eye,
            // auxiliary RT, incomplete StateBlock replay). R29's historical
            // world route has no authority to reproject this exact producer.
            // Preserve ONE unmodified original draw in that case; the normal
            // ready raster path below still attempts exact binocular stereo.
            // Capture the producer->GPU sink owner once per physical
            // primitive; never re-infer it from render-state or alpha.
            const auto drawCommand =
                OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
            // The independent R84 dispatcher can reject/delegate a native
            // ESC SpriteNode before R30TryHud succeeds. R26 captured the
            // unpainted stereo world at this *physical* pre-screen boundary.
            // Preserve that invariant for every R33 fallback without moving
            // non-screen world/sky/lens sources to the HUD pipeline.
            R30SupportBeforeScreenDrawForSkyGlow(device,
                OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(
                    drawCommand.scope));
            const bool directLensCentre =
                drawCommand.IsDirectWorldLensCentre();
            const bool directCarShadow =
                drawCommand.IsDirectCarBaseShadow();
            const bool exactResultHud = drawCommand.IsExactFiniteResultHud();
            const bool sourceScreenRequiresProof =
                drawCommand.NeedsScreenStereoOrOriginal();
            if (!resyncAlreadyFlushed)
            {
                // Raster resync failed before R30 could prove HUD stereo.
                // An exact +TIME/GOAL producer must keep its original draw,
                // never borrow R29's preceding road/world source.
                // Preserve the older exact-result/shadow/lens native draw
                // oracle unchanged. Other original-game source HUD and
                // queued rank markers now have an independent, equally
                // source-proven veto rather than weakening that safety gate.
                if (sourceScreenRequiresProof && !exactResultHud)
                {
                    if (telemetry)
                        R32ReviewNoteDispatchFallback();
                    return actualDraw();
                }
                if (exactResultHud || directCarShadow ||
                    OutRunVR::LensCentre::PreserveOriginalBeforeRasterResync(
                        directLensCentre, resyncAlreadyFlushed))
                {
                    if (telemetry)
                        R32ReviewNoteDispatchFallback();
                    return actualDraw();
                }
                // No stereo eligibility: never let a screen/HUD/SkyGlow
                // producer fall through to the lower cached world WVP.
                // The unmodified original draw is the only safe fallback.
                if (drawCommand.DeniesGenericWorldFallback())
                {
                    if (telemetry)
                        R32ReviewNoteDispatchFallback();
                    return actualDraw();
                }
                return fallbackToR29();
            }

            // Classify exactly once for the physical draw. Flat-perspective
            // effects may require three GetRenderState calls; do not repeat
            // that work inside R33TryHud after choosing the HUD route.
            const R32ReviewScreenSpaceKind screenKind =
                R32ReviewClassifyScreenSpacePass(device);
            // R30::None is NOT generic-world ownership for the D3A5/C993
            // sun. If the original c64/call/shader/pose proof is missing,
            // bypass both R33 fast world and the R29 cached-WVP fallback.
            const bool provenLensStereo =
                screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld;
            const bool provenCarShadowStereo =
                screenKind == R32ReviewScreenSpaceKind::ExactCarBaseShadowWorld;
            // Shadow stereo requires its independently source-proven car
            // WVP. A missing source never inherits R29's previous road WVP.
            if (directCarShadow && !provenCarShadowStereo)
            {
                if (telemetry)
                    R32ReviewNoteDispatchFallback();
                return actualDraw();
            }
            // R30 cannot establish a source-owned HUD/marker eye plane.
            // Even an ordinary 6th/6 or anchored rank SpriteNode must not
            // borrow R31's previous road WVP when this proof is missing.
            // R31's shader+pose cache may still match an earlier road WVP:
            // using that cache for original +TIME/GOAL produces a displaced
            // or doubled result. Fail open to exactly one game draw instead.
            if (sourceScreenRequiresProof && !exactResultHud &&
                screenKind == R32ReviewScreenSpaceKind::None)
            {
                if (telemetry)
                    R32ReviewNoteDispatchFallback();
                return actualDraw();
            }
            if ((exactResultHud || directCarShadow) &&
                screenKind == R32ReviewScreenSpaceKind::None)
            {
                if (telemetry)
                    R32ReviewNoteDispatchFallback();
                return actualDraw();
            }
            if (OutRunVR::LensCentre::PreserveOriginalAtUpperDispatch(
                    directLensCentre, provenLensStereo, false) &&
                !provenLensStereo)
            {
                // The game's exact original draw occurs once; no effect is
                // suppressed or borrowed road/particle WVP submitted.
                if (telemetry)
                    R32ReviewNoteDispatchFallback();
                return actualDraw();
            }
            if (screenKind != R32ReviewScreenSpaceKind::None)
            {
                const auto hud = R33TryHud(device, screenKind,
                    std::forward<ActualDraw>(actualDraw), site);
                if (GpuWaterProbe::Enabled() && hud.handled)
                    GpuWaterProbe::instance().noteRoute(device, 
                        GpuWaterProbe::DrawRoute::ScreenHud);
                if (hud.handled)
                    return hud.hr;
                // HUD classification alone is not proof of physical stereo.
                // Missing GPU-eye resources, pose or c64 must leave the
                // exact original +TIME/GOAL path alone, not hand it to R29.
                if (sourceScreenRequiresProof && !exactResultHud)
                {
                    if (telemetry)
                        R32ReviewNoteDispatchFallback();
                    return actualDraw();
                }
                if (exactResultHud ||
                    (directCarShadow && !hud.handled))
                {
                    if (telemetry)
                        R32ReviewNoteDispatchFallback();
                    return actualDraw();
                }
                // A fully source-proven C993 centre whose stereo path was
                // unavailable must likewise never borrow generic world c64.
                if (OutRunVR::LensCentre::PreserveOriginalAtUpperDispatch(
                        directLensCentre, provenLensStereo, hud.handled))
                {
                    if (telemetry)
                        R32ReviewNoteDispatchFallback();
                    return actualDraw();
                }
            }
            else
            {
                // Screen pass classified as None still retains its ORIGINAL
                // producer scope. In particular, queued ScreenOverlay2D and
                // SkyGlow otherwise borrowed a coincidentally matching
                // shader-epoch/pose from R31's previous road WVP.
                if (drawCommand.DeniesGenericWorldFallback())
                {
                    if (telemetry)
                        R32ReviewNoteDispatchFallback();
                    return actualDraw();
                }
                const auto fast = R33TryFastWorld(device,
                    std::forward<ActualDraw>(actualDraw), site);
                if (GpuWaterProbe::Enabled() && fast.handled)
                    GpuWaterProbe::instance().noteRoute(device, 
                        GpuWaterProbe::DrawRoute::FastWorld);
                if (fast.handled)
                    return fast.hr;
            }

            // A screen classifier may recognize an effect whose R30 eye
            // builder still rejects due to missing source c64/pose/resources.
            // An R29 fallback must not turn that screen into road geometry.
            if (drawCommand.DeniesGenericWorldFallback())
            {
                if (telemetry)
                    R32ReviewNoteDispatchFallback();
                return actualDraw();
            }

            // Preserve the same lower R29 fail-closed policy when neither
            // HUD nor world stereo owns this otherwise eligible draw.
            return fallbackToR29();
        }

        HRESULT __stdcall DrawPrimitiveDestR33(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            // No cross-TU workload observer call when diagnostics are off.
            const bool telemetry = R33TelemetryEnabled();
            if (telemetry)
                R32ReviewObserveFrameWorkload(device, type, primitiveCount, false, false);
            auto call = [&](bool resyncAlreadyFlushed) {
                // The outer raster guard already rejected non-game, aux RT,
                // mono and StateBlock-recording calls. R30PrepareXyzrhwState
                // would reject those same draws in the lower R29 stable-stereo gate;
                // bypass its cross-TU checks on the large mono/aux workload.
                // Reliable setter/StateBlock tracking proves a bound VS is
                // not an XYZRHW fixed-function draw. Unreliable tracking must
                // retain R30's live shader fallback, never assume VS identity.
                const bool tryXyzrhw = resyncAlreadyFlushed &&
                    (!OutRunVR::State::StateBlockTracker::Reliable() ||
                     R32ReviewCurrentVertexShaderIdentity() == 0);
                const HRESULT xyzrhw = tryXyzrhw
                    ? R32ReviewTryXyzrhwPrimitiveVB(
                    device, type, startVertex, primitiveCount)
                    : E_NOTIMPL;
                if (GpuWaterProbe::Enabled() && xyzrhw != E_NOTIMPL)
                    GpuWaterProbe::instance().noteRoute(device, 
                        GpuWaterProbe::DrawRoute::Xyzrhw);
                if (xyzrhw != E_NOTIMPL)
                    return xyzrhw;

                auto actual = [&]() {
                    return R32ReviewCallRawDrawPrimitive(
                        device, type, startVertex, primitiveCount);
                };
                auto lower = [&]() {
                    return R32ReviewCallLowerDrawPrimitive(
                        device, type, startVertex, primitiveCount);
                };
                return R33Dispatch(device, actual, lower, "R33/DrawPrimitive", resyncAlreadyFlushed, telemetry);
            };
            const bool gpuTimed = GpuWaterProbe::Enabled() &&
                device && R32ReviewIsGameDevice(device) &&
                GpuWaterProbe::instance().beforeDraw(device, primitiveCount);
            const HRESULT hr = R33GuardStereoRasterState(
                device, call, "R33/DrawPrimitive/raster-state");
            if (gpuTimed)
                GpuWaterProbe::instance().afterDraw(true);
            return hr;
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR33(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            // No cross-TU workload observer call when diagnostics are off.
            const bool telemetry = R33TelemetryEnabled();
            if (telemetry)
                R32ReviewObserveFrameWorkload(device, type, primitiveCount, true, false);
            auto call = [&](bool resyncAlreadyFlushed) {
                // The outer raster guard already rejected non-game, aux RT,
                // mono and StateBlock-recording calls. R30PrepareXyzrhwState
                // would reject those same draws in the lower R29 stable-stereo gate;
                // bypass its cross-TU checks on the large mono/aux workload.
                // Reliable setter/StateBlock tracking proves a bound VS is
                // not an XYZRHW fixed-function draw. Unreliable tracking must
                // retain R30's live shader fallback, never assume VS identity.
                const bool tryXyzrhw = resyncAlreadyFlushed &&
                    (!OutRunVR::State::StateBlockTracker::Reliable() ||
                     R32ReviewCurrentVertexShaderIdentity() == 0);
                // R62's proven D3DXSprite FVF=0x142 (XYZ, NOT POSITIONT)
                // has separate projected-rank and native-HUD owners. Do not
                // gate this exact-source route on the *cached* shader identity:
                // a stale setter/StateBlock shadow can say VS!=0 while the
                // real device has already returned to fixed function, leaving
                // rank/6th/6 drawn only once in the left eye. R30 checks the
                // actual GetVertexShader and GetFVF state, source semantic,
                // target and bilateral eye resources before touching the GPU.
                // The ordinary XYZRHW hotpath keeps its cached-state gate.
                if (resyncAlreadyFlushed)
                {
                    const HRESULT r62 = R30SupportTryFixedFunctionProjectedRankIndexed(
                        device, type, baseVertexIndex, minVertexIndex,
                        numVertices, startIndex, primitiveCount);
                    if (r62 != E_NOTIMPL)
                        return r62;
                }
                const HRESULT xyzrhw = tryXyzrhw
                    ? R32ReviewTryXyzrhwIndexedPrimitiveVB(
                    device, type, baseVertexIndex, minVertexIndex,
                    numVertices, startIndex, primitiveCount)
                    : E_NOTIMPL;
                if (GpuWaterProbe::Enabled() && xyzrhw != E_NOTIMPL)
                    GpuWaterProbe::instance().noteRoute(device, 
                        GpuWaterProbe::DrawRoute::Xyzrhw);
                if (xyzrhw != E_NOTIMPL)
                    return xyzrhw;

                auto actual = [&]() {
                    return R32ReviewCallRawDrawIndexedPrimitive(device, type,
                        baseVertexIndex, minVertexIndex, numVertices, startIndex,
                        primitiveCount);
                };
                auto lower = [&]() {
                    return R32ReviewCallLowerDrawIndexedPrimitive(device,
                        type, baseVertexIndex, minVertexIndex, numVertices,
                        startIndex, primitiveCount);
                };
                return R33Dispatch(device, actual, lower,
                    "R33/DrawIndexedPrimitive", resyncAlreadyFlushed, telemetry);
            };
            const bool gpuTimed = GpuWaterProbe::Enabled() &&
                device && R32ReviewIsGameDevice(device) &&
                GpuWaterProbe::instance().beforeDraw(device, primitiveCount);
            const HRESULT hr = R33GuardStereoRasterState(
                device, call, "R33/DrawIndexedPrimitive/raster-state");
            if (gpuTimed)
                GpuWaterProbe::instance().afterDraw(true);
            return hr;
        }

        HRESULT __stdcall DrawPrimitiveUPDestR33(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT primitiveCount, const void* data,
            UINT stride)
        {
            // No cross-TU workload observer call when diagnostics are off.
            const bool telemetry = R33TelemetryEnabled();
            if (telemetry)
                R32ReviewObserveFrameWorkload(device, type, primitiveCount, false, true);
            auto call = [&](bool resyncAlreadyFlushed) {
                // The outer raster guard already rejected non-game, aux RT,
                // mono and StateBlock-recording calls. R30PrepareXyzrhwState
                // would reject those same draws in the lower R29 stable-stereo gate;
                // bypass its cross-TU checks on the large mono/aux workload.
                // Reliable setter/StateBlock tracking proves a bound VS is
                // not an XYZRHW fixed-function draw. Unreliable tracking must
                // retain R30's live shader fallback, never assume VS identity.
                const bool tryXyzrhw = resyncAlreadyFlushed &&
                    (!OutRunVR::State::StateBlockTracker::Reliable() ||
                     R32ReviewCurrentVertexShaderIdentity() == 0);
                const HRESULT xyzrhw = tryXyzrhw
                    ? R32ReviewTryXyzrhwPrimitiveUP(
                    device, type, primitiveCount, data, stride)
                    : E_NOTIMPL;
                if (GpuWaterProbe::Enabled() && xyzrhw != E_NOTIMPL)
                    GpuWaterProbe::instance().noteRoute(device, 
                        GpuWaterProbe::DrawRoute::Xyzrhw);
                if (xyzrhw != E_NOTIMPL)
                    return xyzrhw;

                auto actual = [&]() {
                    return R32ReviewCallRawDrawPrimitiveUP(
                        device, type, primitiveCount, data, stride);
                };
                auto lower = [&]() {
                    return R32ReviewCallLowerDrawPrimitiveUP(
                        device, type, primitiveCount, data, stride);
                };
                return R33Dispatch(device, actual, lower, "R33/DrawPrimitiveUP", resyncAlreadyFlushed, telemetry);
            };
            const bool gpuTimed = GpuWaterProbe::Enabled() &&
                device && R32ReviewIsGameDevice(device) &&
                GpuWaterProbe::instance().beforeDraw(device, primitiveCount);
            const HRESULT hr = R33GuardStereoRasterState(
                device, call, "R33/DrawPrimitiveUP/raster-state");
            if (gpuTimed)
                GpuWaterProbe::instance().afterDraw(true);
            return hr;
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR33(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            // No cross-TU workload observer call when diagnostics are off.
            const bool telemetry = R33TelemetryEnabled();
            if (telemetry)
                R32ReviewObserveFrameWorkload(device, type, primitiveCount, true, true);
            auto call = [&](bool resyncAlreadyFlushed) {
                // The outer raster guard already rejected non-game, aux RT,
                // mono and StateBlock-recording calls. R30PrepareXyzrhwState
                // would reject those same draws in the lower R29 stable-stereo gate;
                // bypass its cross-TU checks on the large mono/aux workload.
                // Reliable setter/StateBlock tracking proves a bound VS is
                // not an XYZRHW fixed-function draw. Unreliable tracking must
                // retain R30's live shader fallback, never assume VS identity.
                const bool tryXyzrhw = resyncAlreadyFlushed &&
                    (!OutRunVR::State::StateBlockTracker::Reliable() ||
                     R32ReviewCurrentVertexShaderIdentity() == 0);
                const HRESULT xyzrhw = tryXyzrhw
                    ? R32ReviewTryXyzrhwIndexedPrimitiveUP(
                    device, type, minVertexIndex, numVertices, primitiveCount,
                    indexData, indexFormat, vertexData, stride)
                    : E_NOTIMPL;
                if (GpuWaterProbe::Enabled() && xyzrhw != E_NOTIMPL)
                    GpuWaterProbe::instance().noteRoute(device, 
                        GpuWaterProbe::DrawRoute::Xyzrhw);
                if (xyzrhw != E_NOTIMPL)
                    return xyzrhw;

                auto actual = [&]() {
                    return R32ReviewCallRawDrawIndexedPrimitiveUP(device, type,
                        minVertexIndex, numVertices, primitiveCount, indexData,
                        indexFormat, vertexData, stride);
                };
                auto lower = [&]() {
                    return R32ReviewCallLowerDrawIndexedPrimitiveUP(device,
                        type, minVertexIndex, numVertices, primitiveCount,
                        indexData, indexFormat, vertexData, stride);
                };
                return R33Dispatch(device, actual, lower,
                    "R33/DrawIndexedPrimitiveUP", resyncAlreadyFlushed, telemetry);
            };
            const bool gpuTimed = GpuWaterProbe::Enabled() &&
                device && R32ReviewIsGameDevice(device) &&
                GpuWaterProbe::instance().beforeDraw(device, primitiveCount);
            const HRESULT hr = R33GuardStereoRasterState(
                device, call, "R33/DrawIndexedPrimitiveUP/raster-state");
            if (gpuTimed)
                GpuWaterProbe::instance().afterDraw(true);
            return hr;
        }

        bool ResolveDirectTransportDestR33(IDirect3DDevice9* device,
            std::uint32_t frameId) noexcept
        {
            return R32ReviewResolveDirectTransport(
                device, frameId, [&]() noexcept {
                    return R33ResolveDirectR13Hook.call<bool>(device, frameId);
                });
        }

        HRESULT __stdcall ResetDestR33(IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            const bool gameDevice = R32ReviewIsGameDevice(device);
            if (gameDevice) GpuWaterProbe::instance().reset();
            const HRESULT hr = R32ReviewRunResetLifecycle(
                device, [&]() noexcept {
                    return R33ResetR22Hook.stdcall<HRESULT>(device, params);
                });

            if (gameDevice)
            {
                R33InvalidateDepthStencilCache();
                R33RightViewport = {};
                R33SavedViewport = {};
                if (SUCCEEDED(hr))
                    ++R33ResetSuccesses;
                else
                    ++R33ResetFailures;

                if (!R33FirstResetLifecycleLogged)
                {
                    R33FirstResetLifecycleLogged = true;
                    spdlog::info(
                        "VR R33 RESET: R33 hooks R22 directly and preserves R32 reset lifecycle through its owner helper; R22 owns fail-close/baseline and R32 rearms caches only after successful Reset");
                }

                const bool healthy = SUCCEEDED(hr) &&
                    OutRunVRD3D9ExUpgradeR13::LastResetStateReplaySucceeded();
                R33SetResetReplayGuardState(
                    device, healthy, "Reset", true);
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
            if (device && R32ReviewIsGameDevice(device))
            {
                const HRESULT cooperative = device->TestCooperativeLevel();
                if (cooperative == D3DERR_DEVICELOST ||
                    cooperative == D3DERR_DEVICENOTRESET)
                {
                    ++R33LostDeviceBypasses;
                    GpuWaterProbe::instance().reset();
                    // A lost device may retire stereo surfaces before the
                    // original Reset hook runs. A recycled COM address must
                    // never inherit a prior frame's full-target viewport.
                    R33RightViewport = {};
                    R33SavedViewport = {};
                    R33ResetReplayBlocked.store(
                        true, std::memory_order_release);
                    OutRunVR::RuntimeEligibility::SetExternalSafetyBlock(true);
                    R32ReviewArmStereoRecoverySafety();
                    if (!R33FirstLostDeviceBypassLogged)
                    {
                        R33FirstLostDeviceBypassLogged = true;
                        spdlog::warn(
                            "VR R33 DEVICE LOST: TestCooperativeLevel=0x{:08x}; skipping VR D3D work and forwarding raw Present until Reset restores the device",
                            static_cast<unsigned>(cooperative));
                    }
                    return R32ReviewCallRawPresent(
                        device, sourceRect, destRect,
                        destWindowOverride, dirtyRegion);
                }
            }

            if (device && R32ReviewIsGameDevice(device) && GpuWaterProbe::Enabled())
                GpuWaterProbe::instance().beforePresent(device);
            const bool blocked = R32ReviewIsGameDevice(device) &&
                R33ResetReplayBlocked.load(std::memory_order_acquire);
            if (blocked)
                R33ForceResetReplayFailClosed(device, "Present/pre");

            const HRESULT hr = R32ReviewRunPresentTelemetry(
                device, [&]() noexcept {
                    return R33PresentR13Hook.stdcall<HRESULT>(device,
                        sourceRect, destRect, destWindowOverride, dirtyRegion);
                });
            if (device && R32ReviewIsGameDevice(device))
            {
                // These are frame-local leases, not permanent COM identities:
                // resize/rebuild can recycle the same surface address without
                // a classic Reset. Re-probe each next frame (at most two
                // metadata GetDesc calls per frame, never per stereo draw).
                // Keep the current frame's fast viewport-elision intact.
                R33RightViewport = {};
                R33SavedViewport = {};
                if (GpuWaterProbe::Enabled())
                    GpuWaterProbe::instance().afterPresent(device);
                R33LogPerfWindow();
            }

            if (blocked)
                R33ForceResetReplayFailClosed(device, "Present/post");
            return hr;
        }

        void R33RollbackHooks() noexcept
        {
            R33RightViewport = {};
            R33SavedViewport = {};
            R33DrawIndexedPrimitiveUPR30Hook = {};
            R33DrawPrimitiveUPR30Hook = {};
            R33DrawIndexedPrimitiveR30Hook = {};
            R33DrawPrimitiveR30Hook = {};
            R33SetRenderStateR29Hook = {};
            R33ResolveDirectR13Hook = {};
            R33PresentR13Hook = {};
            R33ResetR22Hook = {};
        }

        bool R33EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R33ResetR22Hook,
                &R33PresentR13Hook,
                &R33ResolveDirectR13Hook,
                &R33SetRenderStateR29Hook,
                &R33DrawPrimitiveR30Hook,
                &R33DrawIndexedPrimitiveR30Hook,
                &R33DrawPrimitiveUPR30Hook,
                &R33DrawIndexedPrimitiveUPR30Hook
            };
            for (auto* hook : hooks)
                if (!*hook || !hook->enable().has_value())
                    return false;
            return true;
        }

        DWORD WINAPI R33InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto prerequisites = R32ReviewPrerequisiteStatus();
                if (prerequisites == State::Failed)
                {
                    R33ReportInstallResult(false);
                    return 0;
                }
                if (prerequisites == State::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R33ResetR22Hook = safetyhook::create_inline(
                        R32ReviewResetTarget(),
                        ResetDestR33, disabled);
                    R33PresentR13Hook = safetyhook::create_inline(
                        R32ReviewPresentTarget(),
                        PresentDestR33, disabled);
                    R33ResolveDirectR13Hook = safetyhook::create_inline(
                        R32ReviewDirectTransportTarget(),
                        ResolveDirectTransportDestR33, disabled);
                    R33SetRenderStateR29Hook = safetyhook::create_inline(
                        R32ReviewSetRenderStateTarget(),
                        SetRenderStateDestR33, disabled);
                    R33DrawPrimitiveR30Hook = safetyhook::create_inline(
                        R32ReviewDrawPrimitiveTarget(),
                        DrawPrimitiveDestR33, disabled);
                    R33DrawIndexedPrimitiveR30Hook = safetyhook::create_inline(
                        R32ReviewDrawIndexedPrimitiveTarget(),
                        DrawIndexedPrimitiveDestR33, disabled);
                    R33DrawPrimitiveUPR30Hook = safetyhook::create_inline(
                        R32ReviewDrawPrimitiveUPTarget(),
                        DrawPrimitiveUPDestR33, disabled);
                    R33DrawIndexedPrimitiveUPR30Hook = safetyhook::create_inline(
                        R32ReviewDrawIndexedPrimitiveUPTarget(),
                        DrawIndexedPrimitiveUPDestR33, disabled);

                    if (!R33EnableHooks())
                    {
                        R33RollbackHooks();
                        R33ReportInstallResult(false);
                        spdlog::error(
                            "VR R33: final hook transaction was partial; R30 draw path plus R13 DirectGPU/R22 Reset lower owners remain authoritative");
                        return 0;
                    }

                    IDirect3DDevice9* const installedDevice =
                        R32ReviewInstalledDevice();
                    if (installedDevice)
                        R33SynchronizeResetReplayGuardState(installedDevice);

                    R33ReportInstallResult(true);
                    spdlog::info(
                        "VR R33 DISPATCH: final Reset/Present/DirectGPU/draw physical ownership READY; R32 is hook-free functional owner with no async install shim; top-level telemetry counted once when enabled; direct R31/R22/R13 prerequisite ownership + R22 Reset + R13 Present/DirectGPU + R30 draw dispatch ACTIVE");
                    return 0;
                }
                Sleep(25);
            }

            R33ReportInstallResult(false);
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
                    R33ReportInstallResult(false);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRStereoR33DispatchHook instance;
        };

        VRStereoR33DispatchHook VRStereoR33DispatchHook::instance;
    }


    inline void R33SynchronizeResetReplayGuardState(
        IDirect3DDevice9* device) noexcept
    {
        if (!device || !R32ReviewIsGameDevice(device))
            return;

        const bool healthy =
            !OutRunVRD3D9ExUpgradeR13::IsCompatDevice(device) ||
            OutRunVRD3D9ExUpgradeR13::LastResetStateReplaySucceeded();
        R33SetResetReplayGuardState(
            device, healthy, "Install/state-sync", false);
    }

    inline void FailClosedDepthStencilState() noexcept
    {
        R33InvalidateDepthStencilCache();
        R32ReviewInvalidateRightDepthStencilSync(true, true);
    }
}