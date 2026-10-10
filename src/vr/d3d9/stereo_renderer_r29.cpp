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
#include "../state/state_block_tracker.hpp"
#include "vr/game/render_semantics.hpp"
namespace OutRunVRRenderer
{
    void R29InvalidateRawWvpGeneration() noexcept;
    void R29InvalidateRendererStateAfterExternalRestore() noexcept;
    OutRunVR::RuntimeEligibility::InstallState R29RendererState() noexcept;
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
            bool valid = false;
            std::uint64_t presentEpoch = 0;
            std::uint64_t drawSerial = 0;
            std::uint64_t applyGeneration = 0;
        };

        thread_local R29EffectState R29Effect{};
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
            if (!OutRunVR::State::StateBlockTracker::Reliable())
                return false;
            if (R29Effect.applyGeneration !=
                OutRunVR::State::StateBlockTracker::ApplyGeneration())
                return false;
            return R29Effect.valid &&
                R29Effect.presentEpoch == PresentEpoch &&
                TopLevelDrawSerial() >= R29Effect.drawSerial &&
                TopLevelDrawSerial() - R29Effect.drawSerial < 64;
        }

        void R29ArmMonoSafety(std::uint64_t extraPresents = 2) noexcept
        {
            const std::uint64_t target = PresentEpoch + extraPresents;
            if (target > R29MonoSafetyThroughEpoch)
                R29MonoSafetyThroughEpoch = target;
        }

        bool R29SyncEffectState(IDirect3DDevice9* device) noexcept
        {
            if (!device)
                return false;

            // Age alone cannot prove safety after an untracked Apply.
            if (R29EffectCacheCurrent())
                return true;

            const auto applyGenerationBefore =
                OutRunVR::State::StateBlockTracker::ApplyGeneration();
            DWORD alphaBlend = FALSE;
            DWORD alphaTest = FALSE;
            DWORD zWrite = TRUE;
            DWORD zEnable = D3DZB_TRUE;
            DWORD cullMode = D3DCULL_CCW;
            if (FAILED(device->GetRenderState(
                    D3DRS_ALPHABLENDENABLE, &alphaBlend)) ||
                FAILED(device->GetRenderState(
                    D3DRS_ALPHATESTENABLE, &alphaTest)) ||
                FAILED(device->GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)) ||
                FAILED(device->GetRenderState(D3DRS_ZENABLE, &zEnable)) ||
                FAILED(device->GetRenderState(D3DRS_CULLMODE, &cullMode)))
            {
                R29Effect.valid = false;
                return false;
            }
            // A concurrent Apply between five independent live reads can
            // produce a torn policy. Let existing conservative R13 handle it.
            if (OutRunVR::State::StateBlockTracker::ApplyGeneration() !=
                applyGenerationBefore)
            {
                R29Effect.valid = false;
                return false;
            }

            R29Effect.alphaBlend = alphaBlend;
            R29Effect.alphaTest = alphaTest;
            R29Effect.zWrite = zWrite;
            R29Effect.zEnable = zEnable;
            R29Effect.cullMode = cullMode;
            R29Effect.valid = true;
            R29Effect.presentEpoch = PresentEpoch;
            R29Effect.drawSerial = TopLevelDrawSerial();
            R29Effect.applyGeneration = applyGenerationBefore;
            ++R29EffectStateSyncs;
            return true;
        }

        bool R29FragileEffectCached(IDirect3DDevice9* device,
            bool& fragile) noexcept
        {
            fragile = true;
            if (!R29SyncEffectState(device))
                return false;

            const auto policy = OutRunVR::PassPolicy::ClassifyEffectStereo(
                R29Effect.alphaBlend != FALSE,
                R29Effect.alphaTest != FALSE,
                R29Effect.zWrite != FALSE,
                R29Effect.zEnable != D3DZB_FALSE,
                R29Effect.cullMode == D3DCULL_NONE);
            fragile = !OutRunVR::PassPolicy::AllowsEffectWorldStereo(policy);
            return true;
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

            if (LeftDrawMayWriteDepth(device) ||
                LeftDrawMayWriteStencil(device))
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

#if defined(OUTRUN_VR_R29_R28_CLASSIFICATION_COMPARE)
            // C1/C2 world-correctness path.
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
            if (R28CanRebindVerifiedWorld(
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
#endif

            bool fragile = true;
            if (!R29FragileEffectCached(device, fragile))
            {
                ++R29SafetyFallbackDraws;
                return legacyR13Draw();
            }

            const auto semanticScope = OutRunVR::GameSemantic::EffectiveScope();
            if (OutRunVR::GameSemantic::ForceZeroDisparity(semanticScope))
            {
                // Exact original-game post-process ownership beats a generic
                // perspective-looking signature, but only after all stable
                // main-backbuffer/depth safety gates above have passed.
                fragile = true;
            }
            else if (OutRunVR::GameSemantic::CorroboratesWorld(semanticScope) &&
                R27ShouldBypassLegacyZeroDisparity(device))
            {
                // Particle/attached-world semantics are corroborating evidence,
                // never sole authority: the proven R27 WVP gate must agree.
                fragile = false;
                ++R29FragileWorldRetries;
            }

            // R29 originally forced every depth-disabled two-sided alpha draw
            // to zero disparity here. That is too broad for OutRun: smoke,
            // skid/decal billboards and the white floating position glyphs can
            // be alpha/depth-disabled while still carrying the verified world
            // WVP. Let the proven R27 gate try the unmasked R7 classifier first.
            // If the WVP is not actually verified, R7 still fails closed to
            // NonWorld/stock constants, so screen HUD remains safe.
            if (fragile && R27ShouldBypassLegacyZeroDisparity(device))
            {
                fragile = false;
                ++R29FragileWorldRetries;
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

            // A setter cannot revalidate OTHER fields cached before Apply.
            if (R29Effect.valid &&
                R29Effect.applyGeneration !=
                    OutRunVR::State::StateBlockTracker::ApplyGeneration())
                R29Effect.valid = false;

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
            default:
                return hr;
            }

            // If the cache has already been live-synchronized, tracked setters
            // keep it authoritative without any draw-time D3D getter.
            if (R29Effect.valid)
            {
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

    bool R29OwnerTryGetDirectTransportIdentity(
        R29OwnerTransportIdentity& out) noexcept
    {
        out = {};
        if (!SharedState || !DirectInteropVerified)
            return false;
        out.hostPid = SharedState->hostPid;
        out.hostAdapterLuidLow = SharedState->hostAdapterLuidLow;
        out.hostAdapterLuidHigh = SharedState->hostAdapterLuidHigh;
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
        return LeftDrawMayWriteDepth(device);
    }

    bool R29OwnerLeftDrawMayWriteStencil(IDirect3DDevice9* device) noexcept
    {
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
        ActiveDirectTransportSlot = slot;
    }
    void R29OwnerMarkDirectTransportSlotPending(
        std::uint32_t slot, std::uint32_t frameId) noexcept
    {
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
            out = {};
            return false;
        }
        out.alphaBlend = lower.alphaBlend;
        out.alphaTest = lower.alphaTest;
        out.zWrite = lower.zWrite;
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