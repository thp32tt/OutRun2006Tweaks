// R23 renderer eligibility overlay. The R13 semantic classifier remains the
// normal path; this wrapper prevents head-tracked WVP injection and render-time
// culling-camera override until the common game-side baseline gate is eligible.
//
// R27 narrows R13's old alpha-state heuristic: a c64 upload that is already
// proven to be the main-backbuffer perspective world path is allowed to reach
// the authoritative WVP verifier regardless of alpha/cull state. Confirmed
// orthographic UI and auxiliary passes still stay stock. R27 also publishes F10
// to the host from every game BeginScene, including menus/theater mode.
//
// Recovery uses a separate pose-warmup phase. During that phase BeginScene may
// latch a fresh host pose for the upcoming authoritative clear, but the stock
// camera and stock c64 values remain on screen. The x86 recovery coordinator can
// then open stereo at a safe full clear without reusing the previous frame pose.

#include "../runtime_eligibility.hpp"
#include "../ipc/recenter_request.hpp"
#include "outrun_renderer_r13.cpp"

namespace OutRunVRRenderer
{
    namespace
    {
        SafetyHookInline R23BeginSceneEligibilityHook{};
        SafetyHookInline R23WvpEligibilityHook{};
        std::atomic<bool> R23WvpEligibilityReady{ false };
        std::atomic<bool> R23RenderThreadCleanupRequested{ true };
        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R23RendererInstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };
        std::uint64_t R23EligibilityBypasses = 0;
        std::uint64_t R23CullingEligibilityBypasses = 0;
        std::uint64_t R23WarmupPosePreserves = 0;
        std::uint64_t R27PerspectiveEffectWorldUploads = 0;
        bool R23FirstEligibilityBypassLogged = false;
        bool R23FirstCullingEligibilityBypassLogged = false;
        bool R23FirstWarmupPoseLogged = false;
        bool R27FirstPerspectiveEffectWorldLogged = false;
        bool R27HostRecenterWasDown = false;

        struct R23EarlyRendererFailClosed
        {
            R23EarlyRendererFailClosed() noexcept
            {
                RendererInjectionAllowed.store(false, std::memory_order_release);
                R23RenderThreadCleanupRequested.store(true, std::memory_order_release);
            }
        };
        R23EarlyRendererFailClosed R23EarlyRendererFailClosedState{};

        void R23DropIneligibleLatchedPoseOnRenderThread() noexcept
        {
            RestoreCullingCamera();
            LatchedHeadInverseValid = false;
            LatchedStereo = {};
            LatchedPoseSequence = 0;
            FrameTelemetryFlags &= ~OutRunVR::ClientCullingCameraSynced;
            InvalidateVerifiedWvp();
        }

        void R23KeepWarmupPoseStockOnRenderThread() noexcept
        {
            // LatchFramePose may have temporarily applied the culling camera.
            // Recovery warmup keeps the immutable pose packet but never exposes
            // its camera/WVP transform to the monoscopic game frame.
            RestoreCullingCamera();
            FrameTelemetryFlags &= ~OutRunVR::ClientCullingCameraSynced;
            FrameTelemetryFlags &= ~OutRunVR::ClientRendererPoseInjected;
            FrameTelemetryFlags &= ~OutRunVR::ClientPoseApplied;
            InvalidateVerifiedWvp();
            ++R23WarmupPosePreserves;
            if (!R23FirstWarmupPoseLogged)
            {
                R23FirstWarmupPoseLogged = true;
                spdlog::info(
                    "VR R23/R25 RENDERER: recovery pose warmup latched a fresh pose while stock camera/WVP remain authoritative");
            }
        }

        void R23RequestFailClosedCleanup() noexcept
        {
            RendererInjectionAllowed.store(false, std::memory_order_release);
            R23WvpEligibilityReady.store(false, std::memory_order_release);
            R23RenderThreadCleanupRequested.store(true, std::memory_order_release);
        }

        void R23ServiceRenderThreadCleanup() noexcept
        {
            if (R23RenderThreadCleanupRequested.exchange(false,
                    std::memory_order_acq_rel))
            {
                R23DropIneligibleLatchedPoseOnRenderThread();
            }
        }

        void R27PublishHostRecenterIfPressed() noexcept
        {
            const bool down = (GetAsyncKeyState(VK_F10) & 0x8000) != 0;
            const bool pressed = down && !R27HostRecenterWasDown;
            R27HostRecenterWasDown = down;
            if (!pressed)
                return;

            const LONG requestId = OutRunVR::RecenterIpc::SharedChannel().Publish();
            if (requestId != 0)
            {
                spdlog::info(
                    "VR R27 recenter: F10 game->host request published requestId={} pid={} presentation={}",
                    requestId, GetCurrentProcessId(),
                    static_cast<unsigned>(CurrentPresentationMode()));
            }
            else
            {
                spdlog::warn(
                    "VR R27 recenter: F10 pressed but game->host request mapping is unavailable");
            }
        }

        HRESULT __stdcall BeginSceneDestR23(IDirect3DDevice9* device)
        {
            // Do this before the gameplay eligibility branch. Menus render
            // BeginScene too, so F10 can re-anchor the host theater even though
            // LatchFramePose intentionally skips gameplay tracking there.
            if (IsGameDevice(device) && !OutRunVRStereo::IsInternalStereoPassActive())
                R27PublishHostRecenterIfPressed();

            R23ServiceRenderThreadCleanup();
            const HRESULT result = R23BeginSceneEligibilityHook.stdcall<HRESULT>(device);
            if (SUCCEEDED(result) && IsGameDevice(device) &&
                !OutRunVRStereo::IsInternalStereoPassActive() &&
                !OutRunVR::RuntimeEligibility::MayInjectStereo())
            {
                if (OutRunVR::RuntimeEligibility::PoseWarmupAllowed())
                    R23KeepWarmupPoseStockOnRenderThread();
                else
                    R23DropIneligibleLatchedPoseOnRenderThread();

                ++R23CullingEligibilityBypasses;
                if (!R23FirstCullingEligibilityBypassLogged)
                {
                    R23FirstCullingEligibilityBypassLogged = true;
                    spdlog::info(
                        "VR R23: BeginScene culling-camera/head transform held stock until common host-fresh + verified-baseline eligibility is true");
                }
            }
            return result;
        }

        HRESULT __stdcall SetVertexShaderConstantFDestR23(
            IDirect3DDevice9* device, UINT startRegister,
            const float* constantData, UINT vector4fCount)
        {
            R23ServiceRenderThreadCleanup();
            if (!R23WvpEligibilityReady.load(std::memory_order_acquire))
            {
                if (R23WvpEligibilityHook)
                    return R23WvpEligibilityHook.stdcall<HRESULT>(
                        device, startRegister, constantData, vector4fCount);
                return SetVertexShaderConstantFHook.stdcall<HRESULT>(
                    device, startRegister, constantData, vector4fCount);
            }

            const bool candidateWvp = IsGameDevice(device) && constantData &&
                !OutRunVRStereo::IsInternalStereoPassActive() &&
                UploadTouchesOutRunWvp(startRegister, vector4fCount);

            if (candidateWvp && !OutRunVR::RuntimeEligibility::MayInjectStereo())
            {
                if (OutRunVR::RuntimeEligibility::PoseWarmupAllowed())
                    R23KeepWarmupPoseStockOnRenderThread();
                else
                    R23DropIneligibleLatchedPoseOnRenderThread();

                ++R23EligibilityBypasses;
                if (!R23FirstEligibilityBypassLogged)
                {
                    R23FirstEligibilityBypassLogged = true;
                    spdlog::info(
                        "VR R23: c64 WVP head injection held stock until common host-fresh + verified-baseline eligibility is true");
                }
                return SetVertexShaderConstantFHook.stdcall<HRESULT>(
                    device, startRegister, constantData, vector4fCount);
            }

            if (candidateWvp && OutRunVR::RuntimeEligibility::MayInjectStereo())
            {
                float projectionM34 = 0.0f;
                float projectionM44 = 0.0f;
                const auto semantic = R13CurrentRenderSemantic(
                    projectionM34, projectionM44);
                if (OutRunVR::PassPolicy::AllowsWorldStereo(semantic))
                {
                    // R13's alpha/cull-only ZeroDisparity heuristic mixed two
                    // camera spaces: opaque world geometry used the HMD eye WVP
                    // while projected shadows/billboards retained the stock WVP.
                    // Once the target+projection classifier proves this is the
                    // perspective world pass, let the authoritative base c64
                    // verifier decide. Orthographic HUD and auxiliary passes
                    // still flow through R13 and remain stock.
                    ++R27PerspectiveEffectWorldUploads;
                    if (!R27FirstPerspectiveEffectWorldLogged)
                    {
                        R27FirstPerspectiveEffectWorldLogged = true;
                        spdlog::info(
                            "VR R27 EFFECT: main-backbuffer perspective c64 now follows the verified per-eye world WVP regardless of alpha/cull state; orthographic HUD and auxiliary passes remain stock");
                    }
                    return R13WvpCallbackHook.stdcall<HRESULT>(
                        device, startRegister, constantData, vector4fCount);
                }
            }

            return R23WvpEligibilityHook.stdcall<HRESULT>(
                device, startRegister, constantData, vector4fCount);
        }

        DWORD WINAPI R23RendererInstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R23RendererInstallState.store(State::Pending, std::memory_order_release);
            R23RequestFailClosedCleanup();

            R23BeginSceneEligibilityHook = safetyhook::create_inline(
                reinterpret_cast<void*>(&BeginSceneDest), BeginSceneDestR23,
                safetyhook::InlineHook::StartDisabled);
            const bool beginEnabled = R23BeginSceneEligibilityHook &&
                R23BeginSceneEligibilityHook.enable().has_value();
            if (!beginEnabled)
            {
                R23BeginSceneEligibilityHook = {};
                R23RendererInstallState.store(State::Failed, std::memory_order_release);
                R23RequestFailClosedCleanup();
                HookManager::ReportAsyncResult(
                    "OpenXRVRRendererR23Eligibility", false);
                spdlog::error(
                    "VR R23: failed to install early BeginScene culling eligibility hook; renderer injection disabled fail-closed");
                return 0;
            }

            R23WvpEligibilityHook = safetyhook::create_inline(
                reinterpret_cast<void*>(&SetVertexShaderConstantFDestR13),
                SetVertexShaderConstantFDestR23,
                safetyhook::InlineHook::StartDisabled);
            const bool wvpEnabled = R23WvpEligibilityHook &&
                R23WvpEligibilityHook.enable().has_value();
            if (!wvpEnabled)
            {
                R23WvpEligibilityHook = {};
                R23RendererInstallState.store(State::Failed, std::memory_order_release);
                R23RequestFailClosedCleanup();
                HookManager::ReportAsyncResult(
                    "OpenXRVRRendererR23Eligibility", false);
                spdlog::error(
                    "VR R23: failed to install early WVP eligibility hook; injection disabled while BeginScene culling guard remains active");
                return 0;
            }

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                if (RendererInstallState.load(std::memory_order_acquire) == RendererInstallFailed)
                {
                    R23RendererInstallState.store(State::Failed, std::memory_order_release);
                    R23RequestFailClosedCleanup();
                    HookManager::ReportAsyncResult(
                        "OpenXRVRRendererR23Eligibility", false);
                    return 0;
                }

                if (RendererInstallState.load(std::memory_order_acquire) == RendererInstallReady &&
                    R13WvpHookReady.load(std::memory_order_acquire))
                {
                    R23WvpEligibilityReady.store(true, std::memory_order_release);
                    RendererInjectionAllowed.store(true, std::memory_order_release);
                    R23RendererInstallState.store(State::Ready, std::memory_order_release);
                    HookManager::ReportAsyncResult(
                        "OpenXRVRRendererR23Eligibility", true);
                    spdlog::info(
                        "VR R23 RENDERER: BeginScene/WVP guards READY; recovery pose warmup is stock-visible and stereo injection still requires the authoritative baseline gate; R27 world-effect correction active");
                    return 0;
                }
                Sleep(25);
            }
            R23RendererInstallState.store(State::Failed, std::memory_order_release);
            R23RequestFailClosedCleanup();
            HookManager::ReportAsyncResult(
                "OpenXRVRRendererR23Eligibility", false);
            spdlog::error(
                "VR R23 RENDERER: timed out waiting for base/R13 renderer transaction; injection remains fail-closed");
            return 0;
        }

        class VRRendererR23EligibilityHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRRendererR23Eligibility";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R23RendererInstallState.store(State::Pending, std::memory_order_release);
                R23RequestFailClosedCleanup();

                HANDLE thread = CreateThread(nullptr, 0, R23RendererInstallThread,
                    nullptr, 0, nullptr);
                if (!thread)
                {
                    R23RendererInstallState.store(State::Failed, std::memory_order_release);
                    R23RequestFailClosedCleanup();
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRRendererR23EligibilityHook instance;
        };

        VRRendererR23EligibilityHook VRRendererR23EligibilityHook::instance;
    }
}
