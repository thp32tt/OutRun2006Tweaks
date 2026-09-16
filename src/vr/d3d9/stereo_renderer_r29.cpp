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

namespace OutRunVRRenderer
{
    void R29InvalidateRawWvpGeneration() noexcept;
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
            DWORD cullMode = D3DCULL_CCW;
            bool valid = false;
            std::uint64_t presentEpoch = 0;
            std::uint64_t drawSerial = 0;
        };

        thread_local R29EffectState R29Effect{};
        std::uint64_t R29StableTwoEyeDraws = 0;
        std::uint64_t R29ZeroDisparityTwoEyeDraws = 0;
        std::uint64_t R29SafetyFallbackDraws = 0;
        std::uint64_t R29EffectStateSyncs = 0;
        std::uint64_t R29MonoSafetyThroughEpoch = 2;
        bool R29FirstStableLogged = false;
        bool R29FirstZeroDisparityLogged = false;
        bool R29FirstSafetyFallbackLogged = false;

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

            // SetRenderState updates the cache synchronously. One live refresh
            // per Present plus a sparse 64-draw bound covers StateBlock::Apply,
            // which can bypass the setter hook, without four getters per draw.
            if (R29Effect.valid && R29Effect.presentEpoch == PresentEpoch &&
                R23GameDrawSerial >= R29Effect.drawSerial &&
                R23GameDrawSerial - R29Effect.drawSerial < 64)
                return true;

            DWORD alphaBlend = FALSE;
            DWORD alphaTest = FALSE;
            DWORD zWrite = TRUE;
            DWORD cullMode = D3DCULL_CCW;
            if (FAILED(device->GetRenderState(
                    D3DRS_ALPHABLENDENABLE, &alphaBlend)) ||
                FAILED(device->GetRenderState(
                    D3DRS_ALPHATESTENABLE, &alphaTest)) ||
                FAILED(device->GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)) ||
                FAILED(device->GetRenderState(D3DRS_CULLMODE, &cullMode)))
            {
                R29Effect.valid = false;
                return false;
            }

            R29Effect.alphaBlend = alphaBlend;
            R29Effect.alphaTest = alphaTest;
            R29Effect.zWrite = zWrite;
            R29Effect.cullMode = cullMode;
            R29Effect.valid = true;
            R29Effect.presentEpoch = PresentEpoch;
            R29Effect.drawSerial = R23GameDrawSerial;
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
            ++R9DrawCalls;

            // This frame intentionally does not maintain a complete independent
            // mono history. R9 must therefore never restore a stale/incomplete
            // safety RT if a later hazard poisons the same Present.
            R9MonoBackupGap = true;

            if (LeftDrawMayWriteDepth(device) ||
                LeftDrawMayWriteStencil(device))
                ++R9MainDepthContentSerial;

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
                        "VR R29 EFFECT: fragile alpha/billboard/shadow draw uses stock-WVP zero disparity in LEFT+RIGHT only; R27/R28 world promotion disabled");
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

            bool fragile = true;
            if (!R29FragileEffectCached(device, fragile))
            {
                ++R29SafetyFallbackDraws;
                return legacyR13Draw();
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
                R29Effect.drawSerial = R23GameDrawSerial;
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
                if (r26 == State::Failed)
                {
                    R29StereoInstallState.store(State::Failed,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR29", false);
                    spdlog::error(
                        "VR R29 STEREO: R26 prerequisite failed; R26/R28 remains active");
                    return 0;
                }

                if (r26 == State::Ready)
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
                "VR R29 STEREO: timed out waiting for R26; R26/R28 remains active");
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
}
