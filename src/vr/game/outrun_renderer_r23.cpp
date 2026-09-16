// R23 renderer eligibility overlay. The R13 semantic classifier remains the
// normal path; this wrapper prevents both head-tracked WVP injection and the
// render-time culling-camera override whenever the common host/baseline gate is
// not eligible.

#include "../runtime_eligibility.hpp"
#include "outrun_renderer_r13.cpp"

namespace OutRunVRRenderer
{
    namespace
    {
        SafetyHookInline R23BeginSceneEligibilityHook{};
        SafetyHookInline R23WvpEligibilityHook{};
        std::atomic<bool> R23WvpEligibilityReady{ false };
        std::uint64_t R23EligibilityBypasses = 0;
        std::uint64_t R23CullingEligibilityBypasses = 0;
        bool R23FirstEligibilityBypassLogged = false;
        bool R23FirstCullingEligibilityBypassLogged = false;

        // Hook application is asynchronous, but base renderer installer threads
        // can start immediately after Hook registration. Close injection during
        // static initialization so there is no base-ready -> R23-apply gap.
        struct R23EarlyRendererFailClosed
        {
            R23EarlyRendererFailClosed() noexcept
            {
                RendererInjectionAllowed.store(false, std::memory_order_release);
            }
        };
        R23EarlyRendererFailClosed R23EarlyRendererFailClosedState{};

        void R23DropIneligibleLatchedPose() noexcept
        {
            RestoreCullingCamera();
            LatchedHeadInverseValid = false;
            LatchedStereo = {};
            LatchedPoseSequence = 0;
            FrameTelemetryFlags &= ~OutRunVR::ClientCullingCameraSynced;
            InvalidateVerifiedWvp();
        }

        HRESULT __stdcall BeginSceneDestR23(IDirect3DDevice9* device)
        {
            const HRESULT result = R23BeginSceneEligibilityHook.stdcall<HRESULT>(device);
            if (SUCCEEDED(result) && IsGameDevice(device) &&
                !OutRunVRStereo::IsInternalStereoPassActive() &&
                !OutRunVR::RuntimeEligibility::MayInjectStereo())
            {
                // Base BeginScene may have latched a fresh HMD pose and applied
                // the culling-camera override before the stereo baseline gate
                // reopened. Restore stock camera state before control returns to
                // the game so culling and visible WVP always use the same policy.
                R23DropIneligibleLatchedPose();
                ++R23CullingEligibilityBypasses;
                if (!R23FirstCullingEligibilityBypassLogged)
                {
                    R23FirstCullingEligibilityBypassLogged = true;
                    spdlog::info(
                        "VR R23: BeginScene culling-camera/head pose held stock until common host-fresh + verified-baseline eligibility is true");
                }
            }
            return result;
        }

        HRESULT __stdcall SetVertexShaderConstantFDestR23(
            IDirect3DDevice9* device, UINT startRegister,
            const float* constantData, UINT vector4fCount)
        {
            if (!R23WvpEligibilityReady.load(std::memory_order_acquire))
            {
                // The wrapper is deliberately armed before R13/base readiness.
                // Keep injection disabled and use R13's trampoline path until the
                // full renderer transaction is ready.
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
                // One authority for host freshness and recovery: keep the stock
                // game matrix, restore any culling-camera override and invalidate
                // verified WVP state so R7 cannot classify a later draw as a
                // head-tracked world draw.
                R23DropIneligibleLatchedPose();
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

            return R23WvpEligibilityHook.stdcall<HRESULT>(
                device, startRegister, constantData, vector4fCount);
        }

        DWORD WINAPI R23RendererInstallThread(void*)
        {
            R23WvpEligibilityReady.store(false, std::memory_order_release);
            RendererInjectionAllowed.store(false, std::memory_order_release);

            // These wrappers target our callback functions, not the D3D device
            // vtable, so install them before waiting for RendererInstallReady.
            // They remain dormant until the lower layers route calls here, which
            // removes the former base-ready -> R23-hook race window.
            R23BeginSceneEligibilityHook = safetyhook::create_inline(
                reinterpret_cast<void*>(&BeginSceneDest), BeginSceneDestR23,
                safetyhook::InlineHook::StartDisabled);
            const bool beginEnabled = R23BeginSceneEligibilityHook &&
                R23BeginSceneEligibilityHook.enable().has_value();
            if (!beginEnabled)
            {
                R23BeginSceneEligibilityHook = {};
                RendererInjectionAllowed.store(false, std::memory_order_release);
                R23DropIneligibleLatchedPose();
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
                RendererInjectionAllowed.store(false, std::memory_order_release);
                R23DropIneligibleLatchedPose();
                spdlog::error(
                    "VR R23: failed to install early WVP eligibility hook; injection disabled while BeginScene culling guard remains active");
                return 0;
            }

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                if (RendererInstallState.load(std::memory_order_acquire) == RendererInstallFailed)
                {
                    RendererInjectionAllowed.store(false, std::memory_order_release);
                    R23DropIneligibleLatchedPose();
                    return 0;
                }

                if (RendererInstallState.load(std::memory_order_acquire) == RendererInstallReady &&
                    R13WvpHookReady.load(std::memory_order_acquire))
                {
                    R23WvpEligibilityReady.store(true, std::memory_order_release);
                    RendererInjectionAllowed.store(true, std::memory_order_release);
                    spdlog::info(
                        "VR R23 RENDERER: early BeginScene/WVP guards armed before base readiness; injection + culling now consume the same 250ms host freshness + recovery-baseline gate");
                    return 0;
                }
                Sleep(25);
            }
            RendererInjectionAllowed.store(false, std::memory_order_release);
            R23DropIneligibleLatchedPose();
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
                RendererInjectionAllowed.store(false, std::memory_order_release);
                R23DropIneligibleLatchedPose();

                HANDLE thread = CreateThread(nullptr, 0, R23RendererInstallThread,
                    nullptr, 0, nullptr);
                if (!thread)
                {
                    RendererInjectionAllowed.store(false, std::memory_order_release);
                    R23DropIneligibleLatchedPose();
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
