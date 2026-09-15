// R23 renderer eligibility overlay. The R13 semantic classifier remains the
// normal path; this wrapper only prevents head-tracked WVP injection whenever
// the Present-boundary host freshness/baseline state is not eligible.

#include "../runtime_eligibility.hpp"
#include "outrun_renderer_r13.cpp"

namespace OutRunVRRenderer
{
    namespace
    {
        SafetyHookInline R23WvpEligibilityHook{};
        std::atomic<bool> R23WvpEligibilityReady{ false };
        std::uint64_t R23EligibilityBypasses = 0;
        bool R23FirstEligibilityBypassLogged = false;

        HRESULT __stdcall SetVertexShaderConstantFDestR23(
            IDirect3DDevice9* device, UINT startRegister,
            const float* constantData, UINT vector4fCount)
        {
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
                // One authority for host freshness and recovery: keep the stock
                // game matrix and invalidate any previously verified WVP so R7
                // cannot classify a later draw as head-tracked world geometry.
                InvalidateVerifiedWvp();
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
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                if (RendererInstallState.load(std::memory_order_acquire) == RendererInstallFailed)
                    return 0;

                if (RendererInstallState.load(std::memory_order_acquire) == RendererInstallReady &&
                    R13WvpHookReady.load(std::memory_order_acquire))
                {
                    R23WvpEligibilityHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&SetVertexShaderConstantFDestR13),
                        SetVertexShaderConstantFDestR23,
                        safetyhook::InlineHook::StartDisabled);
                    bool enabled = false;
                    if (R23WvpEligibilityHook)
                        enabled = R23WvpEligibilityHook.enable().has_value();
                    if (!enabled)
                    {
                        R23WvpEligibilityHook = {};
                        RendererInjectionAllowed.store(false, std::memory_order_release);
                        InvalidateVerifiedWvp();
                        spdlog::error(
                            "VR R23: failed to install common WVP eligibility hook; injection disabled fail-closed");
                        return 0;
                    }
                    R23WvpEligibilityReady.store(true, std::memory_order_release);
                    spdlog::info(
                        "VR R23 RENDERER: WVP injection now consumes the same 250ms host freshness + recovery-baseline gate as stereo replay");
                    return 0;
                }
                Sleep(25);
            }
            RendererInjectionAllowed.store(false, std::memory_order_release);
            InvalidateVerifiedWvp();
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
                HANDLE thread = CreateThread(nullptr, 0, R23RendererInstallThread,
                    nullptr, 0, nullptr);
                if (!thread)
                {
                    RendererInjectionAllowed.store(false, std::memory_order_release);
                    InvalidateVerifiedWvp();
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
