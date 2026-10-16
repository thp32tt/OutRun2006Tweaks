// R29 stereo hot-path and effect-safety overlay.
//
// R26/R28 proved the base stereo path but paid two large costs on every draw:
//  1) R9 rendered an independent mono safety copy before LEFT+RIGHT;
//  2) R28 re-read c64..c67/projection/pose and temporarily impersonated an old
//     vertex-shader epoch to widen world classification.
//
// R29 removes both from the steady-state path. All R23/R22 accounting and
// viewport/scissor preservation still execute first. Once a draw is proven to
// be an ordinary main-backbuffer stereo draw, R29 enters the validated R7
// LEFT+RIGHT replay directly. Recovery, MRT/query hazards, depth transitions,
// and other uncertain states still fall through to the complete R13/R9 safety
// chain. Fragile effects use R13's exact policy but apply zero disparity without
// a third mono replay.

#include "stereo_renderer_r26.cpp"
#include "../core/r29_owner_api.hpp"
#include "../ipc/coherent_host_identity.hpp"
#include "../state/state_block_tracker.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/game/car_base_shadow_stereo.hpp"
namespace OutRunVRRenderer
{
    void R29InvalidateRawWvpGeneration() noexcept;
    void R29InvalidateRendererStateAfterExternalRestore() noexcept;
    OutRunVR::RuntimeEligibility::InstallState R29RendererState() noexcept;
    std::uint64_t GetCurrentLatchedPoseEpoch() noexcept;
    std::uint64_t GetLastGameWvpPoseEpoch() noexcept;
    bool GetLastRawGameWvpWrite(float outConstants[16],
        std::uint64_t& writeSerial, std::uint64_t& topLevelDrawSerial,
        std::uintptr_t& shaderIdentity, std::uint64_t& shaderSerial) noexcept;
    bool GetLastGameWvpSemanticProvenance(
        OutRunVR::GameSemantic::RenderScope& semanticScope,
        std::uint64_t& queueNodeEpoch, const void*& queueNode,
        OutRunVR::GameSemantic::ProducerToken& producerToken) noexcept;
}

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R29DrawPrimitiveR27Hook{};
        SafetyHookInline R29DrawIndexedPrimitiveR27Hook{};
        SafetyHookInline R29DrawPrimitiveUPR27Hook{};
        SafetyHookInline R29DrawIndexedPrimitiveUPR27Hook{};
        SafetyHookInline R29SetRenderStateR22Hook{};

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R29StereoInstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        struct R29EffectState
        {
            DWORD alphaBlend = FALSE;
            DWORD alphaTest = FALSE;
            DWORD zWrite = TRUE;
            DWORD zEnable = D3DZB_TRUE;
            DWORD cullMode = D3DCULL_CCW;
            // The overwhelmingly common disabled-stencil case can avoid
            // up to nine tracked D3D9 state reads for each stereo draw.
            DWORD stencilEnable = FALSE;
            // Derived once at live sync or a tracked policy-state transition.
            // Rechecking ClassifyEffectStereo for every draw is unnecessary.
            bool fragileWorld = true;
            bool valid = false;
            std::uint64_t presentEpoch = 0;
            std::uint64_t drawSerial = 0;
            std::uint64_t applyGeneration = 0;
            std::uint64_t recordingGeneration = 0;
        };

        thread_local R29EffectState R29Effect{};
        // Live stencil-write classification is expensive (up to eight D3D9
        // getters per stereo draw). Keep an independent, generation-fenced
        // snapshot only when R31 StateBlock tracking is authoritative.
        struct R29StencilWriteState
        {
            DWORD writeMask = 0;
            DWORD fail = D3DSTENCILOP_KEEP;
            DWORD zFail = D3DSTENCILOP_KEEP;
            DWORD pass = D3DSTENCILOP_KEEP;
            DWORD twoSided = FALSE;
            DWORD ccwFail = D3DSTENCILOP_KEEP;
            DWORD ccwZFail = D3DSTENCILOP_KEEP;
            DWORD ccwPass = D3DSTENCILOP_KEEP;
            bool mayWrite = true;
            // A zero write mask needs no stencil-op queries. With a nonzero
            // mask and one-sided stencil, the three CCW ops are immaterial.
            // Setter transitions that activate omitted fields invalidate.
            bool maskOnly = false;
            bool frontOnly = false;
            bool valid = false;
            std::uint64_t presentEpoch = 0;
            std::uint64_t applyGeneration = 0;
            std::uint64_t recordingGeneration = 0;
        };
        thread_local R29StencilWriteState R29StencilWrite{};


        void R29RefreshFragilePolicy() noexcept
        {
            // Same R13 effect policy as the draw-time path, but computed only
            // when the six-field live snapshot is synchronized or a relevant
            // tracked setter changes it. StateBlock generation fences remain
            // authoritative for any subsequent draw.
            const auto policy = OutRunVR::PassPolicy::ClassifyEffectStereo(
                R29Effect.alphaBlend != FALSE,
                R29Effect.alphaTest != FALSE,
                R29Effect.zWrite != FALSE,
                R29Effect.zEnable != D3DZB_FALSE,
                R29Effect.cullMode == D3DCULL_NONE);
            R29Effect.fragileWorld =
                !OutRunVR::PassPolicy::AllowsEffectWorldStereo(policy);
        }
        std::uint64_t R29StableTwoEyeDraws = 0;
        std::uint64_t R29ZeroDisparityTwoEyeDraws = 0;
        std::uint64_t R29SafetyFallbackDraws = 0;
        std::uint64_t R29EffectStateSyncs = 0;
        std::uint64_t R29FragileWorldRetries = 0;
        std::uint64_t R29MonoSafetyThroughEpoch = 2;
        bool R29FirstStableLogged = false;
        bool R29FirstZeroDisparityLogged = false;
        bool R29FirstSafetyFallbackLogged = false;


        // StateBlock::Apply can update render state without SetRenderState and
        // can run on another thread; the effect cache is only thread-local.
        bool R29EffectCacheCurrent() noexcept
        {
            // R31/R22 intercept both Apply and Begin/End recording. While
            // coverage remains proven, tracked setters keep the five effect
            // fields current for the whole Present; a 64-draw timeout caused
            // five unnecessary D3D9 getters in busy geometry/particle scenes.
            // Retain the Present boundary, monotonic draw serial, and both
            // generation fences. A lost hook still fails closed to live reads.
            if (OutRunVR::State::StateBlockTracker::Recording() ||
                !OutRunVR::State::StateBlockTracker::Reliable())
                return false;
            if (R29Effect.applyGeneration !=
                    OutRunVR::State::StateBlockTracker::ApplyGeneration() ||
                R29Effect.recordingGeneration !=
                    OutRunVR::State::StateBlockTracker::RecordingGeneration())
                return false;
            return R29Effect.valid &&
                R29Effect.presentEpoch == PresentEpoch &&
                TopLevelDrawSerial() >= R29Effect.drawSerial;
        }

        void R29ArmMonoSafety(std::uint64_t extraPresents = 2) noexcept
        {
            const std::uint64_t target = PresentEpoch + extraPresents;
            if (target > R29MonoSafetyThroughEpoch)
                R29MonoSafetyThroughEpoch = target;
        }


        void R29RefreshStencilWritePolicy() noexcept
        {
            const auto& state = R29StencilWrite;
            R29StencilWrite.mayWrite =
                state.writeMask != 0 &&
                (state.fail != D3DSTENCILOP_KEEP ||
                 state.zFail != D3DSTENCILOP_KEEP ||
                 state.pass != D3DSTENCILOP_KEEP ||
                 (state.twoSided != FALSE &&
                  (state.ccwFail != D3DSTENCILOP_KEEP ||
                   state.ccwZFail != D3DSTENCILOP_KEEP ||
                   state.ccwPass != D3DSTENCILOP_KEEP)));
        }

        bool R29StencilWriteCacheCurrent() noexcept
        {
            return R29StencilWrite.valid && R29EffectCacheCurrent() &&
                R29StencilWrite.presentEpoch == PresentEpoch &&
                R29StencilWrite.applyGeneration == R29Effect.applyGeneration &&
                R29StencilWrite.recordingGeneration == R29Effect.recordingGeneration;
        }

        bool R29SyncStencilWriteState(IDirect3DDevice9* device) noexcept
        {
            if (R29StencilWriteCacheCurrent())
                return true;
            if (!device || !R29EffectCacheCurrent())
                return false;

            // Most stencil-enabled particle/UI passes have a zero write
            // mask. One live getter proves that neither front nor back ops
            // can modify stencil, avoiding seven unnecessary D3D9 getters.
            R29StencilWriteState next{};
            if (FAILED(device->GetRenderState(
                    D3DRS_STENCILWRITEMASK, &next.writeMask)))
            {
                R29StencilWrite.valid = false;
                return false;
            }
            if (next.writeMask == 0)
            {
                next.maskOnly = true;
                next.mayWrite = false;
            }
            else
            {
                if (FAILED(device->GetRenderState(
                        D3DRS_STENCILFAIL, &next.fail)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_STENCILZFAIL, &next.zFail)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_STENCILPASS, &next.pass)) ||
                    FAILED(device->GetRenderState(
                        D3DRS_TWOSIDEDSTENCILMODE, &next.twoSided)))
                {
                    R29StencilWrite.valid = false;
                    return false;
                }

                if (next.twoSided != FALSE)
                {
                    if (FAILED(device->GetRenderState(
                            D3DRS_CCW_STENCILFAIL, &next.ccwFail)) ||
                        FAILED(device->GetRenderState(
                            D3DRS_CCW_STENCILZFAIL, &next.ccwZFail)) ||
                        FAILED(device->GetRenderState(
                            D3DRS_CCW_STENCILPASS, &next.ccwPass)))
                    {
                        R29StencilWrite.valid = false;
                        return false;
                    }
                }
                else
                {
                    // CCW operations cannot write while two-sided stencil is
                    // disabled. Refresh if a tracked setter enables it.
                    next.frontOnly = true;
                }
            }

            // A StateBlock Apply or Begin/End during the partial live read
            // invalidates the sample exactly as on the full-read path.
            if (!R29EffectCacheCurrent())
            {
                R29StencilWrite.valid = false;
                return false;
            }
            next.valid = true;
            next.presentEpoch = PresentEpoch;
            next.applyGeneration = R29Effect.applyGeneration;
            next.recordingGeneration = R29Effect.recordingGeneration;
            R29StencilWrite = next;
            if (!next.maskOnly)
                R29RefreshStencilWritePolicy();
            return true;
        }

        void R29OnStencilWriteSetter(D3DRENDERSTATETYPE state, DWORD value) noexcept
        {
            // Ordinary in-frame setters update the complete live snapshot
            // without new getters. Incomplete or generation-stale snapshots
            // remain invalid and are rebuilt on the next eligible draw.
            switch (state)
            {
            case D3DRS_STENCILWRITEMASK:
            case D3DRS_STENCILFAIL:
            case D3DRS_STENCILZFAIL:
            case D3DRS_STENCILPASS:
            case D3DRS_TWOSIDEDSTENCILMODE:
            case D3DRS_CCW_STENCILFAIL:
            case D3DRS_CCW_STENCILZFAIL:
            case D3DRS_CCW_STENCILPASS:
                break;
            default:
                return;
            }
            if (!R29StencilWriteCacheCurrent())
            {
                R29StencilWrite.valid = false;
                return;
            }
            if (R29StencilWrite.maskOnly)
            {
                // Omitted ops may have changed while the mask was zero.
                // Never promote this one-getter snapshot to a writable state.
                if (state == D3DRS_STENCILWRITEMASK && value != 0)
                    R29StencilWrite.valid = false;
                return;
            }
            if (R29StencilWrite.frontOnly)
            {
                if (state == D3DRS_TWOSIDEDSTENCILMODE && value != FALSE)
                {
                    // CCW ops were not sampled; re-read before allowing them.
                    R29StencilWrite.valid = false;
                    return;
                }
                if (state == D3DRS_CCW_STENCILFAIL ||
                    state == D3DRS_CCW_STENCILZFAIL ||
                    state == D3DRS_CCW_STENCILPASS)
                    return;
            }
            switch (state)
            {
            case D3DRS_STENCILWRITEMASK: R29StencilWrite.writeMask = value; break;
            case D3DRS_STENCILFAIL: R29StencilWrite.fail = value; break;
            case D3DRS_STENCILZFAIL: R29StencilWrite.zFail = value; break;
            case D3DRS_STENCILPASS: R29StencilWrite.pass = value; break;
            case D3DRS_TWOSIDEDSTENCILMODE: R29StencilWrite.twoSided = value; break;
            case D3DRS_CCW_STENCILFAIL: R29StencilWrite.ccwFail = value; break;
            case D3DRS_CCW_STENCILZFAIL: R29StencilWrite.ccwZFail = value; break;
            case D3DRS_CCW_STENCILPASS: R29StencilWrite.ccwPass = value; break;
            default: return;
            }
            R29RefreshStencilWritePolicy();
        }

        bool R29SyncEffectState(IDirect3DDevice9* device) noexcept
        {
            if (!device || OutRunVR::State::StateBlockTracker::Recording())
                return false;

            // A recording block may capture setters without immediately
            // changing live device state. Never sample a cache during it.
            // Age alone cannot prove safety after an untracked Apply.
            if (R29EffectCacheCurrent())
                return true;

            const auto applyGenerationBefore =
                OutRunVR::State::StateBlockTracker::ApplyGeneration();
            const auto recordingGenerationBefore =
                OutRunVR::State::StateBlockTracker::RecordingGeneration();
            DWORD alphaBlend = FALSE;
            DWORD alphaTest = FALSE;
            DWORD zWrite = TRUE;
            DWORD zEnable = D3DZB_TRUE;
            DWORD cullMode = D3DCULL_CCW;
            DWORD stencilEnable = FALSE;
            if (FAILED(device->GetRenderState(
                    D3DRS_ALPHABLENDENABLE, &alphaBlend)) ||
                FAILED(device->GetRenderState(
                    D3DRS_ALPHATESTENABLE, &alphaTest)) ||
                FAILED(device->GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)) ||
                FAILED(device->GetRenderState(D3DRS_ZENABLE, &zEnable)) ||
                FAILED(device->GetRenderState(D3DRS_CULLMODE, &cullMode)) ||
                FAILED(device->GetRenderState(
                    D3DRS_STENCILENABLE, &stencilEnable)))
            {
                R29Effect.valid = false;
                return false;
            }
            // A concurrent Apply between five independent live reads can
            // produce a torn policy. Let existing conservative R13 handle it.
            if (OutRunVR::State::StateBlockTracker::ApplyGeneration() !=
                    applyGenerationBefore ||
                OutRunVR::State::StateBlockTracker::RecordingGeneration() !=
                    recordingGenerationBefore ||
                OutRunVR::State::StateBlockTracker::Recording())
            {
                R29Effect.valid = false;
                return false;
            }

            R29Effect.alphaBlend = alphaBlend;
            R29Effect.alphaTest = alphaTest;
            R29Effect.zWrite = zWrite;
            R29Effect.zEnable = zEnable;
            R29Effect.cullMode = cullMode;
            R29Effect.stencilEnable = stencilEnable;
            R29RefreshFragilePolicy();
            R29Effect.valid = true;
            R29Effect.presentEpoch = PresentEpoch;
            R29Effect.drawSerial = TopLevelDrawSerial();
            R29Effect.applyGeneration = applyGenerationBefore;
            R29Effect.recordingGeneration = recordingGenerationBefore;
            ++R29EffectStateSyncs;
            return true;
        }

        bool R29FragileEffectCached(IDirect3DDevice9* device,
            bool& fragile) noexcept
        {
            fragile = true;
            if (!R29SyncEffectState(device))
                return false;

            fragile = R29Effect.fragileWorld;
            return true;
        }

        // Require original-game shader constants from THIS direct shadow
        // producer. A perspective projection alone can belong to the road,
        // an earlier vehicle, or an unrelated alpha effect; such a draw must
        // retain R29's safe stock-WVP two-eye route instead of an orphaned
        // head-transformed shadow.
        bool R29HasDirectCarShadowGameWvp() noexcept
        {
            using namespace OutRunVR::GameSemantic;
            float rawWvp[16]{};
            std::uint64_t writeSerial = 0, writeDraw = 0;
            std::uintptr_t writeShader = 0, currentShader = 0;
            std::uint64_t writeShaderEpoch = 0, currentShaderEpoch = 0;
            RenderScope writtenScope = RenderScope::None;
            std::uint64_t writtenQueueEpoch = 0;
            const void* writtenQueueNode = nullptr;
            ProducerToken writtenProducer = ProducerToken::None;
            if (!OutRunVRRenderer::GetLastRawGameWvpWrite(
                    rawWvp, writeSerial, writeDraw,
                    writeShader, writeShaderEpoch) ||
                !OutRunVRRenderer::GetLastGameWvpSemanticProvenance(
                    writtenScope, writtenQueueEpoch,
                    writtenQueueNode, writtenProducer) ||
                !OutRunVRStereo::GetCurrentShaderEpoch(
                    currentShader, currentShaderEpoch))
                return false;
            for (const float value : rawWvp)
                if (!std::isfinite(value))
                    return false;

            return OutRunVR::CarShadowStereo::OwnsDirectGameWvp({
                OutRunVRRenderer::GetCurrentLatchedPoseEpoch(),
                OutRunVRRenderer::GetLastGameWvpPoseEpoch(),
                TopLevelDrawSerial() + 1u, writeDraw,
                currentShader, writeShader,
                currentShaderEpoch, writeShaderEpoch,
                writtenScope, writtenProducer,
                writtenQueueNode, writtenQueueEpoch
            });
        }

        bool R29StableStereoBase(IDirect3DDevice9* device) noexcept
        {
            if (!IsGameDevice(device) || InternalStereoPass ||
                !TargetIsBackBuffer() || !StereoWanted() || !R9StereoSeeded)
                return false;

            if (!OutRunVR::RuntimeEligibility::MayInjectStereo() ||
                OutRunVR::RuntimeEligibility::RecoveryPending.load(
                    std::memory_order_acquire) ||
                OutRunVR::RuntimeEligibility::PoseWarmupAllowed())
            {
                R29ArmMonoSafety();
                return false;
            }

            if (PresentEpoch <= R29MonoSafetyThroughEpoch)
                return false;

            if (FrameStereoIncomplete || R9DeferredDepth ||
                !R9CurrentDepthCanMirror() || AnyAuxRenderTargetActive() ||
                R13ForceMonoShadow ||
                OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire) ||
                ActiveOcclusionQueries.load(std::memory_order_acquire) > 0)
            {
                R29ArmMonoSafety();
                return false;
            }
            return true;
        }

        template <typename StereoR7Draw>
        HRESULT R29DirectTwoEye(IDirect3DDevice9* device,
            StereoR7Draw&& stereoR7Draw, bool zeroDisparity,
            const char* site)
        {
            R9NoteStereoDrawWithoutMonoBackup();

            // This frame intentionally does not maintain a complete independent
            // mono history. R9 must therefore never restore a stale/incomplete
            // safety RT if a later hazard poisons the same Present.

            if (R29OwnerLeftDrawMayWriteDepth(device) ||
                R29OwnerLeftDrawMayWriteStencil(device))
                R9NoteMainDepthContentWrite();

            std::uintptr_t savedIdentity = 0;
            if (zeroDisparity)
            {
                savedIdentity = CurrentVertexShaderIdentity.exchange(
                    0, std::memory_order_acq_rel);
            }

            const auto before = FrameFailureReason;
            HRESULT hr = D3D_OK;
            if (!TrackedDepthStencil)
            {
                IDirect3DSurface9* savedRightDepth = RightEyeDepth;
                RightEyeDepth = nullptr;
                hr = stereoR7Draw();
                RightEyeDepth = savedRightDepth;
            }
            else
            {
                hr = stereoR7Draw();
            }

            if (zeroDisparity && savedIdentity != 0)
            {
                std::uintptr_t expected = 0;
                CurrentVertexShaderIdentity.compare_exchange_strong(
                    expected, savedIdentity,
                    std::memory_order_acq_rel, std::memory_order_acquire);
            }

            R9ObserveLegacyFailure(before, site, hr);
            ++R29StableTwoEyeDraws;
            if (zeroDisparity)
            {
                ++R29ZeroDisparityTwoEyeDraws;
                ++R13DrawTimeZeroDisparityDraws;
                if (!R29FirstZeroDisparityLogged)
                {
                    R29FirstZeroDisparityLogged = true;
                    spdlog::info(
                        "VR R29 EFFECT: depth-disabled two-sided alpha effect uses stock-WVP zero disparity; depth-tested projected shadows/cutouts remain spatial world stereo");
                }
            }

            if (!R29FirstStableLogged)
            {
                R29FirstStableLogged = true;
                spdlog::info(
                    "VR R29 PERF: stable main-backbuffer draws now execute LEFT+RIGHT only; per-draw mono safety replay and shader-epoch impersonation are bypassed");
            }

            if (FAILED(hr) || FrameStereoIncomplete ||
                FrameFailureReason != OutRunVR::StereoFailureNone)
                R29ArmMonoSafety();
            return hr;
        }

        template <typename StereoR7Draw, typename LegacyR13Draw>
        HRESULT R29GuardStableDraw(IDirect3DDevice9* device,
            StereoR7Draw&& stereoR7Draw,
            LegacyR13Draw&& legacyR13Draw,
            const char* site)
        {
            if (!R29StableStereoBase(device))
            {
                ++R29SafetyFallbackDraws;
                if (!R29FirstSafetyFallbackLogged)
                {
                    R29FirstSafetyFallbackLogged = true;
                    spdlog::info(
                        "VR R29 SAFETY: recovery/hazard draws retain the complete R13/R9 mono-shadow path");
                }
                return legacyR13Draw();
            }

            // R30 bootstraps depth on HUD/XYZRHW; the R29 world path
            // must preserve the same right-eye depth/stencil contract.
            if (TrackedDepthStencil &&
                (!RightDepthSynchronized || !RightStencilSynchronized))
            {
                TryBootstrapRightDepthFromRecentClear(device);
                if ((!RightDepthSynchronized && DepthTestActive(device)) ||
                    (!RightStencilSynchronized && StencilTestActive(device)))
                {
                    ++R29SafetyFallbackDraws;
                    R29ArmMonoSafety();
                    return legacyR13Draw();
                }
            }

            // Restore R26/R28's user-verified shader-switch world continuation
            // in the independently compiled R84 MAIN, not just C1/C2.
            // Never allow a queued HUD or screen overlay to inherit the last
            // verified road/car WVP, even when live shader constants match.
            // R28CanRebindVerifiedWorld independently requires game target,
            // source perspective, live stock c64, projection, latched pose and
            // current shader-generation mismatch before this synthetic rebind.
            const auto worldRebindScope =
                OutRunVR::GameSemantic::EffectiveScope();
            const bool allowVerifiedWorldRebind =
                worldRebindScope !=
                    OutRunVR::GameSemantic::RenderScope::ScreenHud &&
                worldRebindScope !=
                    OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D &&
                worldRebindScope !=
                    OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D;
            // C1/C2 world-correctness path, now also used by R84.
            //
            // R28's proven path did more than classify the current target as
            // perspective world: when the game changed vertex shader AFTER the
            // verified c64..c67 upload, R28 temporarily rebound the verified
            // shader epoch before entering R9. Without that step R7 sees the
            // shader-epoch mismatch, returns NonWorld, and duplicates the draw
            // with the stock WVP. On hardware this shows up exactly as the road
            // and car having little/incorrect binocular disparity while nearby
            // effect/edge geometry still sits at the correct depth.
            //
            // Keep R29's two-eye accounting/performance path, but run it inside
            // the old strict R28 rebind gate when WVP + projection + pose all
            // still match. If no rebind is needed, fall through to the ordinary
            // perspective fast path.
            std::uintptr_t verifiedShaderIdentity = 0;
            std::uint64_t verifiedShaderSerial = 0;
            if (allowVerifiedWorldRebind &&
                R28CanRebindVerifiedWorld(
                    device, verifiedShaderIdentity, verifiedShaderSerial))
            {
                // Do not reuse R28RunWithVerifiedWorldEpoch's E_NOTIMPL
                // sentinel here: a real D3D draw HRESULT must never be mistaken
                // for "not handled" and executed twice. C1 has a direct boolean
                // decision from R28CanRebindVerifiedWorld, so preserve the
                // actual draw result verbatim.
                const std::uintptr_t savedIdentity =
                    CurrentVertexShaderIdentity.exchange(
                        verifiedShaderIdentity, std::memory_order_acq_rel);
                const std::uint64_t savedSerial =
                    VertexShaderSerial.exchange(
                        verifiedShaderSerial, std::memory_order_acq_rel);

                const HRESULT rebound = R29DirectTwoEye(
                    device, stereoR7Draw, false, site);

                std::uintptr_t expectedIdentity = verifiedShaderIdentity;
                CurrentVertexShaderIdentity.compare_exchange_strong(
                    expectedIdentity, savedIdentity,
                    std::memory_order_acq_rel, std::memory_order_acquire);
                std::uint64_t expectedSerial = verifiedShaderSerial;
                VertexShaderSerial.compare_exchange_strong(
                    expectedSerial, savedSerial,
                    std::memory_order_acq_rel, std::memory_order_acquire);

                ++R28ShaderEpochWorldRebinds;
                if (!R28FirstShaderEpochWorldLogged)
                {
                    R28FirstShaderEpochWorldLogged = true;
                    spdlog::info(
                        "VR C1 WORLD FIX: verified WVP/projection/pose survived a shader switch; R29 fast path rebound the R28 shader epoch so road/car draws keep per-eye world stereo");
                }
                return rebound;
            }

            if (OutRunVRRenderer::R28PerspectiveWorldSemantic())
            {
                return R29DirectTwoEye(device,
                    std::forward<StereoR7Draw>(stereoR7Draw),
                    false, site);
            }

            bool fragile = true;
            if (!R29FragileEffectCached(device, fragile))
            {
                ++R29SafetyFallbackDraws;
                return legacyR13Draw();
            }

            // R27's depth-tested world exception cannot accept a cached
            // Z-disabled draw. The R29 cache was synchronized immediately
            // above under Present/StateBlock generation fences, so skip the
            // expensive R13 live effect snapshot on every depth-off alpha
            // particle/smoke/flare draw without weakening its mono safety.
            // Enabled depth still takes the original R27 probe unchanged.
            const bool r27DepthCandidate =
                R29Effect.zEnable != D3DZB_FALSE;
            // One source/queue ownership snapshot for this physical GPU
            // draw: the Quest native renderer likewise separates producer
            // commands from the later world/effect draw submission.
            const auto drawCommand =
                OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
            const auto semanticScope = drawCommand.scope;
            const bool forceZeroDisparity =
                OutRunVR::GameSemantic::ForceZeroDisparity(semanticScope);
            // R27's no-snapshot overload calls R13CaptureDrawTimeEffect
            // (several live D3D9 GetRenderState reads). The original
            // corroborated-world path could perform the same failed probe
            // twice in one draw. Nothing mutates device state between them.
            bool worldGateChecked = false;
            if (forceZeroDisparity)
            {
                // Exact post-process/ScreenHud ownership is an explicit veto;
                // do not let the generic depth-effect retry override it.
                fragile = true;
            }
            else if (OutRunVR::GameSemantic::CorroboratesWorld(semanticScope))
            {
                worldGateChecked = true;
                if (r27DepthCandidate)
                {
                    if (R27ShouldBypassLegacyZeroDisparity(device))
                    {
                        // The proven R27 gate still owns depth-tested effects.
                        fragile = false;
                        ++R29FragileWorldRetries;
                    }
                }
            }

            // Depth-disabled world smoke/sand may still carry a verified WVP.
            // For untagged draws, retain exactly one conservative R27 probe;
            // forced-zero semantic draws never enter this world fallback.
            if (fragile && !forceZeroDisparity && !worldGateChecked &&
                r27DepthCandidate &&
                R27ShouldBypassLegacyZeroDisparity(device))
            {
                fragile = false;
                ++R29FragileWorldRetries;
            }

            // The original player contact shadow was submitted with a live
            // game world matrix but the generic Z-disabled alpha route flattens
            // both eyes. Only exact direct ownership plus the independent R28
            // original-perspective-WVP proof can lift zero disparity.
            // Other effects, queue nodes, depth/stencil writes and unsafe
            // stereo recovery keep the old conservative path.
            if (fragile && !forceZeroDisparity &&
                drawCommand.IsDirectCarBaseShadow() &&
                R29Effect.zEnable == D3DZB_FALSE &&
                R29Effect.zWrite == FALSE &&
                !R29Effect.stencilEnable)
            {
                const bool originalWvpProven =
                    OutRunVRRenderer::R28PerspectiveWorldSemantic() &&
                    R29HasDirectCarShadowGameWvp();
                if (OutRunVR::CarShadowStereo::CanUseSpatialShadow(
                        drawCommand.producer, drawCommand.scope,
                        drawCommand.queued, originalWvpProven,
                        true, false, false, false))
                {
                    fragile = false;
                    ++R29FragileWorldRetries;
                }
            }

            return R29DirectTwoEye(device,
                std::forward<StereoR7Draw>(stereoR7Draw),
                fragile, site);
        }

        HRESULT __stdcall DrawPrimitiveDestR29(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto stereo = [&]() {
                return R9DrawPrimitiveCallbackHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto legacy = [&]() {
                return R27DrawPrimitiveR13Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R29GuardStableDraw(
                device, stereo, legacy, "R29/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR29(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            auto stereo = [&]() {
                return R9DrawIndexedPrimitiveCallbackHook.stdcall<HRESULT>(
                    device, type, baseVertexIndex, minVertexIndex, numVertices,
                    startIndex, primitiveCount);
            };
            auto legacy = [&]() {
                return R27DrawIndexedPrimitiveR13Hook.stdcall<HRESULT>(
                    device, type, baseVertexIndex, minVertexIndex, numVertices,
                    startIndex, primitiveCount);
            };
            return R29GuardStableDraw(
                device, stereo, legacy, "R29/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR29(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT primitiveCount, const void* data, UINT stride)
        {
            auto stereo = [&]() {
                return R9DrawPrimitiveUPCallbackHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto legacy = [&]() {
                return R27DrawPrimitiveUPR13Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R29GuardStableDraw(
                device, stereo, legacy, "R29/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR29(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            auto stereo = [&]() {
                return R9DrawIndexedPrimitiveUPCallbackHook.stdcall<HRESULT>(
                    device, type, minVertexIndex, numVertices, primitiveCount,
                    indexData, indexFormat, vertexData, stride);
            };
            auto legacy = [&]() {
                return R27DrawIndexedPrimitiveUPR13Hook.stdcall<HRESULT>(
                    device, type, minVertexIndex, numVertices, primitiveCount,
                    indexData, indexFormat, vertexData, stride);
            };
            return R29GuardStableDraw(
                device, stereo, legacy, "R29/DrawIndexedPrimitiveUP");
        }

        HRESULT __stdcall SetRenderStateDestR29(IDirect3DDevice9* device,
            D3DRENDERSTATETYPE state, DWORD value)
        {
            const HRESULT hr = R29SetRenderStateR22Hook.stdcall<HRESULT>(
                device, state, value);
            if (FAILED(hr) || !IsGameDevice(device) || InternalStereoPass)
                return hr;

            // Non-policy render states never alter the cached alpha/depth/cull
            // or stencil-write classification. Forward them unchanged without
            // paying for StateBlock generation/recording and cache checks on
            // each unrelated driver setter (fog, blend factors, color mask...).
            // Relevant setters still take the complete fail-closed path below.
            switch (state)
            {
            case D3DRS_ALPHABLENDENABLE:
            case D3DRS_ALPHATESTENABLE:
            case D3DRS_ZWRITEENABLE:
            case D3DRS_ZENABLE:
            case D3DRS_CULLMODE:
            case D3DRS_STENCILENABLE:
            case D3DRS_STENCILWRITEMASK:
            case D3DRS_STENCILFAIL:
            case D3DRS_STENCILZFAIL:
            case D3DRS_STENCILPASS:
            case D3DRS_TWOSIDEDSTENCILMODE:
            case D3DRS_CCW_STENCILFAIL:
            case D3DRS_CCW_STENCILZFAIL:
            case D3DRS_CCW_STENCILPASS:
                break;
            default:
                return hr;
            }

            // StateBlock recording setters may not update live device state.
            // Begin/End also advances R31's generation and invalidates the
            // older five-field snapshot even if no Apply follows.
            if (OutRunVR::State::StateBlockTracker::Recording())
            {
                R29Effect.valid = false;
                R29StencilWrite.valid = false;
                return hr;
            }
            // A setter cannot revalidate OTHER fields cached before Apply
            // or Begin/End; it may only update a still-current snapshot.
            if (R29Effect.valid &&
                (R29Effect.applyGeneration !=
                     OutRunVR::State::StateBlockTracker::ApplyGeneration() ||
                 R29Effect.recordingGeneration !=
                     OutRunVR::State::StateBlockTracker::RecordingGeneration()))
            {
                R29Effect.valid = false;
                R29StencilWrite.valid = false;
            }
            R29OnStencilWriteSetter(state, value);
            if (state == D3DRS_STENCILENABLE)
                R29StencilWrite.valid = false;

            switch (state)
            {
            case D3DRS_ALPHABLENDENABLE:
                R29Effect.alphaBlend = value;
                break;
            case D3DRS_ALPHATESTENABLE:
                R29Effect.alphaTest = value;
                break;
            case D3DRS_ZWRITEENABLE:
                R29Effect.zWrite = value;
                break;
            case D3DRS_ZENABLE:
                R29Effect.zEnable = value;
                break;
            case D3DRS_CULLMODE:
                R29Effect.cullMode = value;
                break;
            case D3DRS_STENCILENABLE:
                R29Effect.stencilEnable = value;
                break;
            default:
                return hr;
            }

            // If the cache has already been live-synchronized, tracked setters
            // keep it authoritative without any draw-time D3D getter.
            if (R29Effect.valid)
            {
                // Stencil enable affects depth/stencil ownership, not this
                // R13 alpha/depth/cull stereo classification.
                if (state != D3DRS_STENCILENABLE)
                    R29RefreshFragilePolicy();
                R29Effect.presentEpoch = PresentEpoch;
                R29Effect.drawSerial = TopLevelDrawSerial();
            }
            return hr;
        }

        void R29RollbackStereoHooks() noexcept
        {
            R29SetRenderStateR22Hook = {};
            R29DrawIndexedPrimitiveUPR27Hook = {};
            R29DrawPrimitiveUPR27Hook = {};
            R29DrawIndexedPrimitiveR27Hook = {};
            R29DrawPrimitiveR27Hook = {};
        }

        bool R29EnableStereoHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R29DrawPrimitiveR27Hook,
                &R29DrawIndexedPrimitiveR27Hook,
                &R29DrawPrimitiveUPR27Hook,
                &R29DrawIndexedPrimitiveUPR27Hook,
                &R29SetRenderStateR22Hook
            };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                    return false;
            }
            return true;
        }

        DWORD WINAPI R29StereoInstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R29StereoInstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r26 = R26InstallState.load(std::memory_order_acquire);
                const auto rendererR29 = OutRunVRRenderer::R29RendererState();
                if (r26 == State::Failed || rendererR29 == State::Failed)
                {
                    R29StereoInstallState.store(State::Failed,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR29", false);
                    spdlog::error(
                        "VR R29 STEREO: R26 or renderer-R29 prerequisite failed; R26/R28 remains active");
                    return 0;
                }

                if (r26 == State::Ready && rendererR29 == State::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R29DrawPrimitiveR27Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR27Effect),
                        DrawPrimitiveDestR29, disabled);
                    R29DrawIndexedPrimitiveR27Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR27Effect),
                        DrawIndexedPrimitiveDestR29, disabled);
                    R29DrawPrimitiveUPR27Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR27Effect),
                        DrawPrimitiveUPDestR29, disabled);
                    R29DrawIndexedPrimitiveUPR27Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR27Effect),
                        DrawIndexedPrimitiveUPDestR29, disabled);
                    R29SetRenderStateR22Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&SetRenderStateDestR22),
                        SetRenderStateDestR29, disabled);

                    if (!R29EnableStereoHooks())
                    {
                        R29RollbackStereoHooks();
                        R29StereoInstallState.store(State::Failed,
                            std::memory_order_release);
                        HookManager::ReportAsyncResult("OpenXRVRStereoR29", false);
                        spdlog::error(
                            "VR R29 STEREO: disabled-first transaction failed; R26/R28 remains active");
                        return 0;
                    }

                    // First visible stereo frames after install intentionally use
                    // the old complete mono safety path. R23's authoritative
                    // baseline copies the current backbuffer into RightEyeSurface
                    // and clears private right depth/stencil before this opens.
                    R29ArmMonoSafety(2);
                    OutRunVRRenderer::R29InvalidateRawWvpGeneration();
                    R29StereoInstallState.store(State::Ready,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR29", true);
                    spdlog::info(
                        "VR R29 STEREO: conservative effect classification + cached render state + steady-state two-eye path ACTIVE");
                    return 0;
                }
                Sleep(25);
            }

            R29StereoInstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVRStereoR29", false);
            spdlog::error(
                "VR R29 STEREO: timed out waiting for R26/renderer-R29; R26/R28 remains active");
            return 0;
        }

        class VRStereoR29Hook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR29";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R29StereoInstallState.store(State::Pending,
                    std::memory_order_release);
                HANDLE thread = CreateThread(nullptr, 0,
                    R29StereoInstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R29StereoInstallState.store(State::Failed,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRStereoR29Hook instance;
        };

        VRStereoR29Hook VRStereoR29Hook::instance;
    }

    inline void R29TelemetryNoteStableTwoEyeDraw() noexcept
    {
        ++R29StableTwoEyeDraws;
    }

    struct R29EffectTelemetrySnapshot
    {
        DWORD alphaBlend = FALSE;
        DWORD alphaTest = FALSE;
        DWORD zWrite = TRUE;
        DWORD zEnable = D3DZB_TRUE;
    };

    inline bool TryGetEffectTelemetrySnapshot(
        R29EffectTelemetrySnapshot& out) noexcept
    {
        out = {};
        if (!R29EffectCacheCurrent())
            return false;

        out.alphaBlend = R29Effect.alphaBlend;
        out.alphaTest = R29Effect.alphaTest;
        out.zWrite = R29Effect.zWrite;
        out.zEnable = R29Effect.zEnable;
        return true;
    }

    inline void InvalidateEffectStateCache() noexcept
    {
        R29Effect = {};
    }

    inline void ArmStereoRecoverySafety(
        std::uint64_t extraPresents = 2) noexcept
    {
        R29ArmMonoSafety(extraPresents);
    }

    inline void SetStereoRecoverySafetyThroughEpoch(
        std::uint64_t throughEpoch) noexcept
    {
        R29MonoSafetyThroughEpoch = throughEpoch;
    }
    // Export R29 semantics from their only definition TU. R30 must never
    // import R29 anonymous-namespace state via textual .cpp inclusion.
    bool R29OwnerStableStereoBase(IDirect3DDevice9* device) noexcept
    {
        return R29StableStereoBase(device);
    }

    bool R29OwnerFragileEffectCached(
        IDirect3DDevice9* device, bool& fragile) noexcept
    {
        return R29FragileEffectCached(device, fragile);
    }

    void R29OwnerArmMonoSafety(std::uint64_t extraPresents) noexcept
    {
        R29ArmMonoSafety(extraPresents);
    }

    void R29OwnerNoteStableTwoEyeDraw() noexcept
    {
        R29TelemetryNoteStableTwoEyeDraw();
    }

    OutRunVR::RuntimeEligibility::InstallState
    R29OwnerInstallStatus() noexcept
    {
        return R29StereoInstallState.load(std::memory_order_acquire);
    }
    std::uint32_t R29OwnerFrameStereoPoseSequence() noexcept
    {
        return FrameStereoPoseSequence;
    }
    bool R29OwnerSkyGlowCaptureStillValid(std::uint64_t capturedEpoch) noexcept
    {
        // Preserve the eligibility checks that preceded the old epoch hit.
        // Failure, Reset or a new Present must never reuse a stale scene.
        return capturedEpoch != 0 && capturedEpoch == PresentEpoch &&
            FrameHadWorldStereo && FrameHadDuplicatedDraw &&
            !FrameRightDrawFailed && !FrameStereoIncomplete &&
            BackBuffer != nullptr && RightEyeSurface != nullptr;
    }
    R29OwnerFrameSnapshot R29OwnerCaptureFrameSnapshot() noexcept
    {
        R29OwnerFrameSnapshot view{};
        view.width = BackBufferDesc.Width;
        view.height = BackBufferDesc.Height;
        view.backBuffer = BackBuffer;
        view.rightEyeSurface = RightEyeSurface;
        view.rightEyeDepth = RightEyeDepth;
        view.trackedDepthStencil = TrackedDepthStencil;
        view.presentEpoch = PresentEpoch;
        view.poseSequence = FrameStereoPoseSequence;
        view.hadWorldStereo = FrameHadWorldStereo;
        view.hadDuplicatedDraw = FrameHadDuplicatedDraw;
        view.rightDrawFailed = FrameRightDrawFailed;
        view.stereoIncomplete = FrameStereoIncomplete;
        view.rightDepthSynchronized = RightDepthSynchronized;
        view.rightStencilSynchronized = RightStencilSynchronized;
        return view;
    }

    bool R29OwnerRecommendedEyeExtent(std::uint32_t eye,
        std::uint32_t& width, std::uint32_t& height) noexcept
    {
        width = 0;
        height = 0;
        if (eye >= 2 || !SharedState ||
            SharedState->magic != OutRunVR::SharedMagic ||
            SharedState->protocolVersion != OutRunVR::SharedProtocolVersion)
            return false;
        width = SharedState->recommendedWidth[eye];
        height = SharedState->recommendedHeight[eye];
        return width != 0 && height != 0;
    }

    bool R29OwnerReadCoherentEyeExtentPair(std::uint32_t out[4]) noexcept
    {
        if (!out)
            return false;
        out[0] = out[1] = out[2] = out[3] = 0;
        const auto* shared = SharedState;
        if (!shared)
            return false;
        // Host Publish/SetAllocatedEyeExtent writes both eyes between its
        // odd/even sequence transitions.  Reading four independent extents
        // can mix two generations even when both pairs differ by <10%.
        for (unsigned attempt = 0; attempt < 4u; ++attempt)
        {
            const std::uint32_t before = shared->sequence;
            if (before & 1u)
                continue;
            MemoryBarrier();
            const std::uint32_t magic = shared->magic;
            const std::uint32_t version = shared->protocolVersion;
            const std::uint32_t size = shared->structSize;
            const std::uint32_t leftW = shared->recommendedWidth[0];
            const std::uint32_t leftH = shared->recommendedHeight[0];
            const std::uint32_t rightW = shared->recommendedWidth[1];
            const std::uint32_t rightH = shared->recommendedHeight[1];
            MemoryBarrier();
            const std::uint32_t after = shared->sequence;
            if (before != after || (after & 1u))
                continue;
            if (magic != OutRunVR::SharedMagic ||
                version != OutRunVR::SharedProtocolVersion ||
                size != sizeof(OutRunVR::SharedPoseState) ||
                !leftW || !leftH || !rightW || !rightH)
                return false;
            out[0] = leftW;
            out[1] = leftH;
            out[2] = rightW;
            out[3] = rightH;
            return true;
        }
        return false;
    }

    bool R29OwnerTryGetDirectTransportIdentity(
        R29OwnerTransportIdentity& out) noexcept
    {
        out = {};
        if (!DirectInteropVerified)
            return false;
        // PID and adapter LUID are one host generation. A reconnect can
        // update them between three independent reads even after D3D9Ex
        // interop was previously verified. Fail closed on a torn seqlock
        // snapshot so R32 never reuses a slot for a mixed host identity.
        OutRunVR::HostIdentity::Snapshot identity{};
        if (!OutRunVR::HostIdentity::TryRead(SharedState, identity,
                []() noexcept { MemoryBarrier(); }))
            return false;
        out.hostPid = identity.hostPid;
        out.hostAdapterLuidLow = identity.adapterLuidLow;
        out.hostAdapterLuidHigh = identity.adapterLuidHigh;
        return true;
    }

    bool R29OwnerEnsureStereoResources(IDirect3DDevice9* device) noexcept
    {
        return EnsureStereoResources(device);
    }

    bool R29OwnerTryBootstrapRightDepth(IDirect3DDevice9* device) noexcept
    {
        return TryBootstrapRightDepthFromRecentClear(device);
    }

    bool R29OwnerDepthTestActive(IDirect3DDevice9* device) noexcept
    {
        return DepthTestActive(device);
    }

    bool R29OwnerStencilTestActive(IDirect3DDevice9* device) noexcept
    {
        return StencilTestActive(device);
    }

    bool R29OwnerLeftDrawMayWriteDepth(IDirect3DDevice9* device) noexcept
    {
        // R22/R31 cached setters and StateBlock Apply/recording fences make
        // both the positive and negative depth-write predicates authoritative
        // for the current Present. Opaque world draws no longer need two
        // GetRenderState calls per draw while that cache remains coherent.
        // A missing depth attachment can never be written.
        if (!device || !TrackedDepthStencil)
            return false;
        if (R29EffectCacheCurrent())
        {
            return R29Effect.zEnable != D3DZB_FALSE &&
                R29Effect.zWrite != FALSE;
        }
        // Recording, lost hook coverage, a stale generation or an absent
        // effect snapshot still uses the original conservative live reader.
        return LeftDrawMayWriteDepth(device);
    }

    bool R29OwnerLeftDrawMayWriteStencil(IDirect3DDevice9* device) noexcept
    {
        if (!device || !TrackedDepthStencil)
            return false;
        // Only a reliable, same-Present state snapshot may prove that the
        // stencil test is disabled. For enabled or uncertain stencil state,
        // preserve the full write-mask/op/two-sided fail-closed reader.
        if (R29EffectCacheCurrent() && R29Effect.stencilEnable == FALSE)
            return false;
        if (R29EffectCacheCurrent() && R29Effect.stencilEnable != FALSE)
        {
            // A current R29 write-policy snapshot already proves whether any
            // front/back stencil operation can modify the attachment. The
            // common read-only stencil pass must not call SurfaceHasStencil
            // (a live D3D9 surface GetDesc) on every stereo draw. Keep both
            // the depth-format check and full live fallback for writable or
            // generation-stale snapshots; setter/StateBlock fences still own
            // cache invalidation.
            if (R29StencilWriteCacheCurrent() && !R29StencilWrite.mayWrite)
                return false;
            if (!SurfaceHasStencil(TrackedDepthStencil))
                return false;
            if (R29SyncStencilWriteState(device))
                return R29StencilWrite.mayWrite;
        }
        return LeftDrawMayWriteStencil(device);
    }

    void R29OwnerNoteMainDepthContentWrite() noexcept
    {
        R9NoteMainDepthContentWrite();
    }

    void R29OwnerNoteStereoDrawWithoutMonoBackup() noexcept
    {
        R9NoteStereoDrawWithoutMonoBackup();
    }

    void R29OwnerUndoStereoDrawCount() noexcept
    {
        R9UndoStereoDrawCount();
    }

    IDirect3DSurface9* R29OwnerBorrowTrackedRenderTarget() noexcept
    {
        return TrackedRenderTarget;
    }

    IDirect3DSurface9* R29OwnerBorrowTrackedDepthStencil() noexcept
    {
        return TrackedDepthStencil;
    }

    IDirect3DSurface9* R29OwnerBorrowRightEyeSurface() noexcept
    {
        return RightEyeSurface;
    }

    IDirect3DSurface9* R29OwnerBorrowRightEyeDepth() noexcept
    {
        return RightEyeDepth;
    }

    void R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(IDirect3DDevice9* device) noexcept
    {
        InvalidateRightDepthStencilIfLeftMayWrite(device);
    }

    void R29OwnerNoteRestoreFailure(const char* site) noexcept
    {
        NoteRestoreFailure(site);
    }

    void R29OwnerReportStereoFailure(
        OutRunVR::StereoFailureReason reason,
        const char* site, HRESULT hr) noexcept
    {
        R9Poison(reason, site, hr);
    }
    void R29OwnerMarkRightDrawFailed() noexcept
    {
        FrameRightDrawFailed = true;
    }
    HRESULT R29OwnerCallOriginalSetRenderTarget(
        IDirect3DDevice9* device, DWORD index,
        IDirect3DSurface9* surface) noexcept
    {
        return SetRenderTargetHook.stdcall<HRESULT>(device, index, surface);
    }
    HRESULT R29OwnerCallOriginalSetDepthStencilSurface(
        IDirect3DDevice9* device, IDirect3DSurface9* surface) noexcept
    {
        return SetDepthStencilSurfaceHook
            ? SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, surface)
            : device->SetDepthStencilSurface(surface);
    }
    bool R29OwnerRestoreRightPassState(
        IDirect3DDevice9* device, IDirect3DSurface9* target,
        IDirect3DSurface9* depth, const D3DVIEWPORT9& viewport,
        const float* originalWvp, bool restoreWvp) noexcept
    {
        return RestoreRightPassState(
            device, target, depth, viewport, originalWvp, restoreWvp);
    }

    bool R29OwnerStereoWanted() noexcept
    {
        return StereoWanted();
    }

    bool R29OwnerTargetIsBackBuffer() noexcept
    {
        return TargetIsBackBuffer();
    }

    bool R29OwnerExchangeInternalStereoPass(bool active) noexcept
    {
        const bool prior = InternalStereoPass;
        InternalStereoPass = active;
        return prior;
    }

    // R84 owner boundary: keep exactly the lower R9/R29 counters and latch.
    void R29OwnerRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
    void R29OwnerRecordXyzrhwWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        // Preserve original R30 XYZRHW ordering even on pose mismatch:
        // count duplicate, latch/check pose, poison, then world counters.
        // R31's standard duplicate owner intentionally has no pose check.
        FrameHadDuplicatedDraw = true;
        ++DuplicatedDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
        else if (FrameStereoPoseSequence != poseSequence)
        {
            FrameRightDrawFailed = true;
            PoisonFrame(OutRunVR::StereoFailurePoseSequenceMismatch);
        }
        FrameHadWorldStereo = true;
        ++WorldStereoDraws;
    }
    void R29OwnerRecordHudStereoDuplicate() noexcept
    {
        FrameHadDuplicatedDraw = true;
        ++DuplicatedDraws;
        ++NonWorldDuplicatedDraws;
    }
    std::uintptr_t R29OwnerCurrentVertexShaderIdentity() noexcept
    {
        return CurrentVertexShaderIdentity.load(std::memory_order_acquire);
    }
    std::uintptr_t R29OwnerExchangeVertexShaderIdentity(
        std::uintptr_t identity) noexcept
    {
        return CurrentVertexShaderIdentity.exchange(
            identity, std::memory_order_acq_rel);
    }
    void R29OwnerRestoreVertexShaderIdentityIfEmpty(
        std::uintptr_t identity) noexcept
    {
        if (!identity)
            return;
        std::uintptr_t expected = 0;
        CurrentVertexShaderIdentity.compare_exchange_strong(
            expected, identity,
            std::memory_order_acq_rel, std::memory_order_acquire);
    }
    bool R29OwnerCurrentShaderEpoch(
        std::uintptr_t& identity, std::uint64_t& serial) noexcept
    {
        return GetCurrentShaderEpoch(identity, serial);
    }
    std::uint64_t R29OwnerTopLevelDrawSerial() noexcept
    {
        return GetTopLevelDrawSerial();
    }
    void R29OwnerResynchronizeShaderEpoch(
        IDirect3DDevice9* device) noexcept
    {
        IDirect3DVertexShader9* shader = nullptr;
        const HRESULT hr = device
            ? device->GetVertexShader(&shader) : D3DERR_INVALIDCALL;
        const std::uintptr_t identity = SUCCEEDED(hr)
            ? reinterpret_cast<std::uintptr_t>(shader) : 0;
        if (shader)
            shader->Release();
        const std::uintptr_t previous =
            CurrentVertexShaderIdentity.exchange(
                identity, std::memory_order_acq_rel);
        if (previous != identity)
        {
            std::uint64_t serial = VertexShaderSerial.fetch_add(
                1, std::memory_order_acq_rel) + 1;
            if (serial == 0)
                VertexShaderSerial.fetch_add(1, std::memory_order_acq_rel);
        }
    }
    D3DMATRIX R29OwnerIdentityMatrix() noexcept
    {
        return IdentityMatrix();
    }
    D3DMATRIX R29OwnerMatrixFromQuaternionTranslation(
        const float orientation[4], const float position[3],
        float positionScale) noexcept
    {
        return MatrixFromQuaternionTranslation(
            orientation, position, positionScale);
    }
    D3DMATRIX R29OwnerInverseRigid(const D3DMATRIX& matrix) noexcept
    {
        return InverseRigid(matrix);
    }
    D3DMATRIX R29OwnerProjectionFromFov(
        const D3DMATRIX& base, const OutRunVR::SharedFov& fov) noexcept
    {
        return ProjectionFromFov(base, fov);
    }
    D3DMATRIX R29OwnerMultiplyMatrix(
        const D3DMATRIX& a, const D3DMATRIX& b) noexcept
    {
        return MultiplyMatrix(a, b);
    }
    D3DMATRIX R29OwnerTransposeMatrix(const D3DMATRIX& matrix) noexcept
    {
        return TransposeMatrix(matrix);
    }
    bool R29OwnerMatrixFinite(const D3DMATRIX& matrix) noexcept
    {
        return MatrixFinite(matrix);
    }
    bool R29OwnerInvertMatrix(
        const D3DMATRIX& matrix, D3DMATRIX& inverse) noexcept
    {
        return InvertMatrix(matrix, inverse);
    }
    bool R29OwnerGetInverseProjection(
        const D3DMATRIX& matrix, D3DMATRIX& inverse) noexcept
    {
        return GetInverseProjection(matrix, inverse);
    }

    HRESULT R29OwnerCallRawDrawPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept
    {
        return DrawPrimitiveHook.stdcall<HRESULT>(d, t, s, p);
    }
    HRESULT R29OwnerCallRawDrawIndexedPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, INT b,
        UINT m, UINT n, UINT s, UINT p) noexcept
    {
        return DrawIndexedPrimitiveHook.stdcall<HRESULT>(d,t,b,m,n,s,p);
    }
    HRESULT R29OwnerCallRawDrawPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT p,
        const void* data, UINT st) noexcept
    {
        return DrawPrimitiveUPHook.stdcall<HRESULT>(d,t,p,data,st);
    }
    HRESULT R29OwnerCallRawDrawIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT m,
        UINT n, UINT p, const void* idx, D3DFORMAT f,
        const void* v, UINT st) noexcept
    {
        return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(
            d,t,m,n,p,idx,f,v,st);
    }
    HRESULT R29OwnerCallRawPresent(
        IDirect3DDevice9* d, const RECT* s, const RECT* dst,
        HWND w, const RGNDATA* r) noexcept
    {
        return PresentHook.stdcall<HRESULT>(d,s,dst,w,r);
    }

    IDirect3DDevice9* R29OwnerGameDevice() noexcept
    {
        return Game::D3DDevice_ptr ? *Game::D3DDevice_ptr : nullptr;
    }
    void* R29OwnerPresentTarget() noexcept
    {
        return reinterpret_cast<void*>(&PresentDest);
    }
    void* R29OwnerResetTarget() noexcept
    {
        return reinterpret_cast<void*>(&ResetDest);
    }
    void* R29OwnerDrawPrimitiveTarget() noexcept
    {
        return reinterpret_cast<void*>(&DrawPrimitiveDestR29);
    }
    void* R29OwnerDrawIndexedPrimitiveTarget() noexcept
    {
        return reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR29);
    }
    void* R29OwnerDrawPrimitiveUPTarget() noexcept
    {
        return reinterpret_cast<void*>(&DrawPrimitiveUPDestR29);
    }
    void* R29OwnerDrawIndexedPrimitiveUPTarget() noexcept
    {
        return reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR29);
    }
    bool R29OwnerSetWvpOneRegisterAtATime(
        IDirect3DDevice9* device, const float* constants) noexcept
    {
        return SetWvpOneRegisterAtATime(device, constants);
    }

    // Re-export lower services without relocating physical state/hook ownership.
    bool R29OwnerIsGameDevice(IDirect3DDevice9* device) noexcept
    {
        return IsGameDevice(device);
    }
    bool R29OwnerInternalStereoPassActive() noexcept
    {
        return InternalStereoPass;
    }
    bool R29OwnerStereoBaselineSeeded() noexcept
    {
        return R9StereoBaselineSeeded();
    }
    std::uint64_t R29OwnerMainDepthGeneration() noexcept
    {
        return R9MainDepthGenerationValue();
    }
    bool R29OwnerMainDepthHasStencil() noexcept
    {
        return R9TrackedMainDepthHasStencil();
    }
    void R29OwnerInvalidateRightDepthStencilSync(bool invalidateDepth, bool invalidateStencil) noexcept
    {
        R9InvalidateRightDepthStencilSync(invalidateDepth, invalidateStencil);
    }
    bool R29OwnerRightDepthInSync() noexcept
    {
        return R9IsRightDepthInSync();
    }
    bool R29OwnerRightStencilInSync() noexcept
    {
        return R9IsRightStencilInSync();
    }
    bool R29OwnerAnyAuxRenderTargetActive() noexcept
    {
        return AnyAuxRenderTargetActive();
    }
    bool R29OwnerTryGetTrackedViewport(D3DVIEWPORT9& viewport) noexcept
    {
        return TryGetTrackedViewport(viewport);
    }
    bool R29OwnerOverlayReadyForTransport() noexcept
    {
        return R13OverlayReadyForTransport();
    }
    void R29OwnerNoteSafeAckBackpressure() noexcept
    {
        R13NoteSafeAckBackpressure();
    }
    bool R29OwnerDirectTransportResourcesReady() noexcept
    {
        return DirectTransportResourcesReady;
    }
    bool R29OwnerEnsureDirectTransportResources(IDirect3DDevice9* device) noexcept
    {
        return EnsureDirectTransportResources(device);
    }
    void R29OwnerReleaseDirectAckState() noexcept
    {
        R13ReleaseAckState();
    }
    void R29OwnerReleaseDirectTransportInterop() noexcept
    {
        ReleaseDirectTransportSlots();
        ReleaseDirectInteropProbe();
    }
    void R29OwnerInvalidateEffectStateCache() noexcept
    {
        InvalidateEffectStateCache();
    }
    void R29OwnerInvalidateTrackedRasterShadow() noexcept
    {
        InvalidateTrackedRasterShadow();
    }
    void R29OwnerInvalidateLiveStateSample() noexcept
    {
        InvalidateLiveStateSample();
    }
    bool R29OwnerPrimeTrackedRasterShadow(IDirect3DDevice9* device) noexcept
    {
        return PrimeTrackedRasterShadow(device);
    }
    void R29OwnerSetStereoRecoverySafetyThroughEpoch(std::uint64_t throughEpoch) noexcept
    {
        SetStereoRecoverySafetyThroughEpoch(throughEpoch);
    }
    bool R29OwnerFrameIdAtOrAfter(std::uint32_t candidate, std::uint32_t reference) noexcept
    {
        return FrameIdAtOrAfter(candidate, reference);
    }
    void R29OwnerFailClosedResetBaselineState() noexcept
    {
        FailClosedResetBaselineState();
    }
    void R29OwnerArmStereoRecoverySafety(std::uint64_t extraPresents) noexcept
    {
        ArmStereoRecoverySafety(extraPresents);
    }
    IDirect3DDevice9* R29OwnerInstalledDevice() noexcept
    {
        return StereoInstalledDevice.load(std::memory_order_acquire);
    }

    HRESULT R29OwnerRunRasterReplayGuardCallback(
        IDirect3DDevice9* device, const char* site,
        R29OwnerVoidCallback active, void* activeContext,
        R29OwnerHResultCallback draw, void* drawContext) noexcept
    {
        if (!draw) return E_INVALIDARG;
        R22RasterReplayGuard replay(device, site);
        if (!replay.StateValid()) return draw(drawContext);
        if (active) active(activeContext);
        return draw(drawContext);
    }
    OutRunVR::RuntimeEligibility::InstallState
    R29OwnerLowerPrerequisiteStatus() noexcept
    {
        using State = OutRunVR::RuntimeEligibility::InstallState;
        const auto r22 = R22InstallStatus();
        const auto r13 = R13InstallStatus();
        if (r22 == State::Failed || r13 == R13InstallStatusValue::Failed)
            return State::Failed;
        if (r22 == State::Ready && r13 == R13InstallStatusValue::Ready)
            return State::Ready;
        return State::Pending;
    }

    void R29OwnerNoteDirectTransportRingBackpressure() noexcept
    {
        ++DirectTransportRingBackpressure;
    }
    std::uint64_t R29OwnerDirectTransportRingBackpressureCount() noexcept
    {
        return static_cast<std::uint64_t>(DirectTransportRingBackpressure);
    }
    void R29OwnerSetActiveDirectTransportSlot(std::uint32_t slot) noexcept
    {
        // Exported DirectGPU owner must not publish an invalid ring slot.
        if (slot >= OutRunVR::RenderFrameRingSize)
            return;
        ActiveDirectTransportSlot = slot;
    }
    void R29OwnerMarkDirectTransportSlotPending(
        std::uint32_t slot, std::uint32_t frameId) noexcept
    {
        // Guard R29 independently of the normally bounded R32 caller.
        if (slot >= OutRunVR::RenderFrameRingSize || frameId == 0u)
            return;
        auto& target = DirectTransportSlots[slot];
        target.producerPending = true;
        target.pendingFrameId = frameId;
        target.frameId = frameId;
        target.published = false;
    }
    R29OwnerDirectTransportPublication
    R29OwnerGetDirectTransportSlotPublication(
        std::uint32_t slot) noexcept
    {
        if (slot >= OutRunVR::RenderFrameRingSize)
            return {};
        const auto& candidate = DirectTransportSlots[slot];
        return {candidate.published, candidate.frameId};
    }
    HRESULT R29OwnerPollDirectTransportSlotProducer(
        std::uint32_t slot) noexcept
    {
        if (slot >= OutRunVR::RenderFrameRingSize)
            return D3DERR_INVALIDCALL;
        auto& target = DirectTransportSlots[slot];
        if (!target.producerPending)
            return S_OK;
        const HRESULT ready = target.fence
            ? target.fence->GetData(nullptr, 0, 0) : E_FAIL;
        if (ready == S_OK)
        {
            target.producerPending = false;
            target.pendingFrameId = 0;
            if (!target.published)
                target.frameId = 0;
        }
        return ready;
    }
    void R29OwnerRetireDirectTransportSlotPublication(
        std::uint32_t slot) noexcept
    {
        if (slot >= OutRunVR::RenderFrameRingSize)
            return;
        auto& target = DirectTransportSlots[slot];
        target.frameId = 0;
        target.published = false;
    }
    bool R29OwnerTryGetGpuCompletionSnapshot(
        std::uint32_t completed[OutRunVR::RenderFrameRingSize]) noexcept
    {
        if (!completed)
            return false;
        R13GpuCompletionSnapshot lower{};
        if (!R13TryGetGpuCompletionSnapshot(lower))
            return false;
        for (std::uint32_t i = 0; i < OutRunVR::RenderFrameRingSize; ++i)
            completed[i] = lower.completedFrameId[i];
        return true;
    }
    R29OwnerDirectTransportCopyResult
    R29OwnerCopyDirectTransportEyesAndIssueFence(
        IDirect3DDevice9* device, std::uint32_t index,
        IDirect3DSurface9* left, IDirect3DSurface9* right) noexcept
    {
        if (!device || !left || !right ||
            index >= OutRunVR::RenderFrameRingSize)
            return {D3DERR_INVALIDCALL, true};
        auto& slot = DirectTransportSlots[index];
        if (!slot.leftSurface || !slot.rightSurface || !slot.fence)
            return {D3DERR_INVALIDCALL, true};
        const HRESULT leftCopy = device->StretchRect(
            left, nullptr, slot.leftSurface, nullptr, D3DTEXF_NONE);
        const HRESULT rightCopy = SUCCEEDED(leftCopy)
            ? device->StretchRect(
                right, nullptr, slot.rightSurface, nullptr, D3DTEXF_NONE)
            : leftCopy;
        if (FAILED(leftCopy) || FAILED(rightCopy))
            return {FAILED(leftCopy) ? leftCopy : rightCopy, true};
        return {slot.fence->Issue(D3DISSUE_END), false};
    }
    bool R29OwnerTryGetEffectTelemetrySnapshot(
        R29OwnerEffectTelemetrySnapshot& out) noexcept
    {
        R29EffectTelemetrySnapshot lower{};
        if (!TryGetEffectTelemetrySnapshot(lower))
        {
            // R33 may classify depth-off screen/particle draws before reaching
            // R29's world sync. Warm this cache only with complete R22/R31
            // coverage; uncertain recording/replay keeps R30's live fallback.
            if (!OutRunVR::State::StateBlockTracker::Reliable() ||
                OutRunVR::State::StateBlockTracker::Recording() ||
                InternalStereoPass)
            {
                out = {};
                return false;
            }
            IDirect3DDevice9* const device = R29OwnerGameDevice();
            if (!device || !R29SyncEffectState(device) ||
                !TryGetEffectTelemetrySnapshot(lower))
            {
                out = {};
                return false;
            }
        }
        out.alphaBlend = lower.alphaBlend;
        out.alphaTest = lower.alphaTest;
        out.zWrite = lower.zWrite;
        out.zEnable = lower.zEnable;
        return true;
    }
    bool R29OwnerValidateVerifiedWvp(
        IDirect3DDevice9* device,
        const float* verified, float* live) noexcept
    {
        return device && verified && live &&
            SUCCEEDED(device->GetVertexShaderConstantF(
                OutRunWvpRegister, live, OutRunWvpRegisterCount)) &&
            FloatArrayNear(live, verified, 16, VerifiedWvpEpsilon);
    }

    bool R29OwnerGetR28VerifiedProjection(float outProjection[16],
        std::uint32_t& generation, std::uint32_t& poseSequence) noexcept
    {
        return OutRunVRRenderer::GetR28VerifiedProjection(
            outProjection, generation, poseSequence);
    }
    void R29OwnerInvalidateRendererStateAfterExternalRestore() noexcept
    {
        OutRunVRRenderer::R29InvalidateRendererStateAfterExternalRestore();
    }
    OutRunVR::RuntimeEligibility::InstallState
    R29OwnerRendererInstallStatus() noexcept
    {
        return OutRunVRRenderer::R29RendererState();
    }

    // R84 strict one-owner physical-hook target exports.
    void* R29OwnerResetR22Target() noexcept
    {
        return reinterpret_cast<void*>(&ResetDestR22);
    }
    void* R29OwnerPresentR13Target() noexcept
    {
        return reinterpret_cast<void*>(&PresentDestR13);
    }
    void* R29OwnerDirectTransportR13Target() noexcept
    {
        return reinterpret_cast<void*>(&ResolveDirectTransportR13);
    }
    void* R29OwnerSetRenderStateR29Target() noexcept
    {
        return reinterpret_cast<void*>(&SetRenderStateDestR29);
    }
}