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
        std::uint64_t R13ScreenSpaceWvpBypasses = 0;
        std::uint64_t R13UnknownProjectionWvpBypasses = 0;
        bool R13FirstOffscreenBypassLogged = false;
        bool R13FirstScreenSpaceBypassLogged = false;
        bool R13FirstUnknownProjectionLogged = false;
        bool R13FirstPerspectiveWorldLogged = false;

        OutRunVR::PassPolicy::RenderSemantic R13CurrentRenderSemantic(
            float& projectionM34, float& projectionM44) noexcept
        {
            projectionM34 = 0.0f;
            projectionM44 = 0.0f;

            const auto targetPolicy = OutRunVRStereo::CurrentPoseInjectionPolicy();
            const bool mainBackbufferPosePass =
                OutRunVRStereo::IsMainBackbufferPoseInjectionPass();

            // Preserve the original R13 cross-TU invariant while consuming the
            // richer centralized policy. The compatibility helper and enum must
            // describe the same pass; disagreement fails closed instead of
            // guessing whether HMD pose injection is safe.
            const bool policySaysMain =
                targetPolicy == OutRunVR::PassPolicy::PoseInjectionPolicy::MainBackbuffer;
            if (mainBackbufferPosePass != policySaysMain)
                return OutRunVR::PassPolicy::RenderSemantic::Unknown;

            if (targetPolicy != OutRunVR::PassPolicy::PoseInjectionPolicy::MainBackbuffer)
            {
                return OutRunVR::PassPolicy::ClassifyRenderSemantic(
                    targetPolicy, OutRunVR::PassPolicy::ProjectionClass::Unknown);
            }

            float projection[16]{};
            auto projectionClass = OutRunVR::PassPolicy::ProjectionClass::Unknown;
            if (GetRendererBaseProjection(projection))
            {
                // D3DMATRIX memory layout: [11] == _34, [15] == _44.
                // OutRun's D3DXMatrixPerspectiveFovRH path normally reports
                // _34=-1/_44=0; orthographic screen-space reports _34=0/_44=1.
                projectionM34 = projection[11];
                projectionM44 = projection[15];
                projectionClass = OutRunVR::PassPolicy::ClassifyProjectionSignature(
                    projectionM34, projectionM44);
            }

            return OutRunVR::PassPolicy::ClassifyRenderSemantic(
                targetPolicy, projectionClass);
        }

        HRESULT __stdcall SetVertexShaderConstantFDestR13(
            IDirect3DDevice9* device, UINT startRegister, const float* constantData, UINT vector4fCount)
        {
            if (IsGameDevice(device) && constantData &&
                !OutRunVRStereo::IsInternalStereoPassActive() &&
                UploadTouchesOutRunWvp(startRegister, vector4fCount))
            {
                float projectionM34 = 0.0f;
                float projectionM44 = 0.0f;
                const auto semantic = R13CurrentRenderSemantic(
                    projectionM34, projectionM44);

                if (!OutRunVR::PassPolicy::AllowsWorldStereo(semantic))
                {
                    // Emulator-inspired fail-closed classification: only a
                    // perspective + main-backbuffer + verified c64 upload may
                    // enter the head-tracked world path. Reflections/shadows,
                    // orthographic HUD/UI, and unknown projections keep stock
                    // game matrices and cannot seed stereo world replay.
                    InvalidateVerifiedWvp();

                    if (semantic == OutRunVR::PassPolicy::RenderSemantic::Auxiliary)
                    {
                        ++R13OffscreenWvpBypasses;
                        if (!R13FirstOffscreenBypassLogged)
                        {
                            R13FirstOffscreenBypassLogged = true;
                            spdlog::info(
                                "VR R13: auxiliary/offscreen c64 WVP kept stock; HMD transform is main-backbuffer-only");
                        }
                    }
                    else if (semantic == OutRunVR::PassPolicy::RenderSemantic::ScreenSpace2D)
                    {
                        ++R13ScreenSpaceWvpBypasses;
                        if (!R13FirstScreenSpaceBypassLogged)
                        {
                            R13FirstScreenSpaceBypassLogged = true;
                            spdlog::info(
                                "VR R13 emulator policy: orthographic/screen-space c64 WVP kept stock; HUD/UI stays zero-disparity (_34={:.3f} _44={:.3f})",
                                projectionM34, projectionM44);
                        }
                    }
                    else
                    {
                        ++R13UnknownProjectionWvpBypasses;
                        if (!R13FirstUnknownProjectionLogged)
                        {
                            R13FirstUnknownProjectionLogged = true;
                            spdlog::warn(
                                "VR R13 emulator policy: unknown main-backbuffer projection kept stock fail-closed (_34={:.3f} _44={:.3f})",
                                projectionM34, projectionM44);
                        }
                    }

                    return SetVertexShaderConstantFHook.stdcall<HRESULT>(
                        device, startRegister, constantData, vector4fCount);
                }

                if (!R13FirstPerspectiveWorldLogged)
                {
                    R13FirstPerspectiveWorldLogged = true;
                    spdlog::info(
                        "VR R13 emulator policy: main-backbuffer perspective class confirmed; c64 remains subject to authoritative WorldView*Projection verification");
                }
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
                            "VR R13: renderer WVP target+projection classification guard armed via atomic renderer install handoff");
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
