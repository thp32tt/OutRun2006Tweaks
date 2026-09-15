// R13 renderer-pose hardening wrapper. The validated renderer is included in
// this TU; cmake marks outrun_renderer.cpp HEADER_FILE_ONLY.

#include "vr/d3d9/r13_bridge.hpp"
#include "outrun_renderer.cpp"

namespace OutRunVRRenderer
{
    namespace
    {
        SafetyHookInline R13WvpCallbackHook{};
        std::uint64_t R13OffscreenWvpBypasses = 0;
        bool R13FirstOffscreenBypassLogged = false;

        HRESULT __stdcall SetVertexShaderConstantFDestR13(
            IDirect3DDevice9* device, UINT startRegister, const float* constantData, UINT vector4fCount)
        {
            if (IsGameDevice(device) && constantData &&
                !OutRunVRStereo::IsInternalStereoPassActive() &&
                UploadTouchesOutRunWvp(startRegister, vector4fCount) &&
                // Compatibility helper is backed by the centralized R13
                // PassPolicy, so renderer and stereo replay share one class.
                !OutRunVRStereo::IsMainBackbufferPoseInjectionPass())
            {
                // Reflection, shadow and other auxiliary world targets must keep
                // the stock game WVP. Applying the HMD transform here bakes a
                // head-relative view into textures later sampled by both eyes.
                InvalidateVerifiedWvp();
                ++R13OffscreenWvpBypasses;
                if (!R13FirstOffscreenBypassLogged)
                {
                    R13FirstOffscreenBypassLogged = true;
                    spdlog::info(
                        "VR R13: auxiliary/offscreen c64 WVP kept stock; HMD transform is main-backbuffer-only");
                }
                return SetVertexShaderConstantFHook.stdcall<HRESULT>(
                    device, startRegister, constantData, vector4fCount);
            }

            return R13WvpCallbackHook.stdcall<HRESULT>(
                device, startRegister, constantData, vector4fCount);
        }

        DWORD WINAPI R13RendererInstallThread(void*)
        {
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const std::uint32_t rendererState =
                    RendererInstallState.load(std::memory_order_acquire);
                if (rendererState == RendererInstallFailed)
                {
                    RendererInjectionAllowed.store(false, std::memory_order_release);
                    InvalidateVerifiedWvp();
                    spdlog::error(
                        "VR R13: base renderer hook transaction failed; WVP injection remains disabled");
                    return 0;
                }
                if (rendererState == RendererInstallReady)
                {
                    R13WvpCallbackHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&SetVertexShaderConstantFDest),
                        SetVertexShaderConstantFDestR13);
                    if (R13WvpCallbackHook)
                    {
                        spdlog::info(
                            "VR R13: renderer WVP target-classification guard armed via atomic renderer install handoff");
                    }
                    else
                    {
                        // Do not mutate a SafetyHookInline owned by another thread.
                        // The base callback stays installed but becomes a stock-WVP
                        // pass-through through this release/acquire policy flag.
                        RendererInjectionAllowed.store(false, std::memory_order_release);
                        InvalidateVerifiedWvp();
                        spdlog::error(
                            "VR R13: failed to hook renderer c64 callback; WVP injection disabled atomically to fail closed");
                    }
                    return 0;
                }
                Sleep(25);
            }
            RendererInjectionAllowed.store(false, std::memory_order_release);
            InvalidateVerifiedWvp();
            spdlog::warn(
                "VR R13: renderer transaction did not become ready; WVP injection disabled fail-closed");
            return 0;
        }

        class VRRendererR13HardeningHook final : public Hook
        {
        public:
            std::string_view description() override { return "OpenXRVRRendererR13Hardening"; }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(nullptr, 0, R13RendererInstallThread, nullptr, 0, nullptr);
                if (!thread)
                    return false;
                CloseHandle(thread);
                return true;
            }
            static VRRendererR13HardeningHook instance;
        };

        VRRendererR13HardeningHook VRRendererR13HardeningHook::instance;
    }
}
