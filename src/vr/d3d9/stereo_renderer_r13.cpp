// R13 hardening wrapper.  The validated R9 renderer remains source-of-truth;
// cmake marks stereo_renderer.cpp HEADER_FILE_ONLY and compiles this TU.

#include "r13_bridge.hpp"
#include "stereo_renderer.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R13ResetR9Hook{};
        SafetyHookInline R13ResolveDirectHook{};
        std::uint64_t R13SafeAckBackpressure = 0;
        bool R13FirstSafeAckBlockLogged = false;

        std::uint32_t R13ReadGpuCompletedFrame() noexcept
        {
            if (!SharedState)
                return 0;
            return static_cast<std::uint32_t>(InterlockedCompareExchange(
                reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVRR13::HostDirectGpuCompletedFrameIndex]),
                0, 0));
        }

        bool ResolveDirectTransportR13(IDirect3DDevice9* device, std::uint32_t frameId)
        {
            if (frameId && SharedState)
            {
                const std::uint32_t slotIndex = (frameId - 1u) % OutRunVR::RenderFrameRingSize;
                const auto& slot = DirectTransportSlots[slotIndex];
                const std::uint32_t gpuCompleted = R13ReadGpuCompletedFrame();
                if (slot.frameId && !FrameIdAtOrAfter(gpuCompleted, slot.frameId))
                {
                    ++R13SafeAckBackpressure;
                    ++DirectTransportRingBackpressure;
                    if (!R13FirstSafeAckBlockLogged)
                    {
                        R13FirstSafeAckBlockLogged = true;
                        spdlog::info(
                            "VR D3D9Ex R13: direct ring reuse blocked until D3D11 GPU-consumer completion ack; slotFrame={} gpuCompleted={}",
                            slot.frameId, gpuCompleted);
                    }
                    return false;
                }
            }
            return R13ResolveDirectHook.call<bool>(device, frameId);
        }

        void R13ResetCommonPre(IDirect3DDevice9* device)
        {
            R9ReleaseMonoResources();
            R9ReleaseDepthIdentity();
            R9StereoSeeded = false;
            R9MonoSeeded = false;
            R9MonoBackupGap = false;
            R9ExpectMainDepthAfterReset = true;

            OutRunVRRenderer::NotifyGameReset();
            ReleaseStereoResources();
            AuxRenderTargetActive = {};
            ActiveOcclusionQueries.store(0, std::memory_order_release);
            CurrentVertexShaderIdentity.store(0, std::memory_order_release);
            VertexShaderSerial.store(0, std::memory_order_release);
            LastStereoWanted = false;
            RightStencilSynchronized = true;
            FramePoseMismatchLogged = false;
            FirstMainDepthReuseLogged = false;
            FirstMainClearLogged = false;
            FirstDepthBootstrapLogged = false;
            PresentEpoch = 1;
            LastMainDepthClearEpoch = 0;
            LastMainDepthClearFlags = 0;
            LastMainDepthClearZ = 1.0f;
            LastMainDepthClearStencil = 0;
            LastMainDepthClearDesc = {};
            LastBeginSceneCountAtPresent = OutRunVRRenderer::GetBeginSceneCallCount();
            FrameStereoIncomplete = false;
            FrameFailureReason = OutRunVR::StereoFailureNone;
            FrameStereoMetadata = {};
            PublishStereoState(OutRunVR::StereoDisabled, false, 0, 0);
            PublishRenderFrame(OutRunVR::StereoDisabled, 0, 0, 0,
                OutRunVR::StereoFailureNone, nullptr);
        }

        HRESULT __stdcall ResetDestR13(IDirect3DDevice9* device, D3DPRESENT_PARAMETERS* params)
        {
            if (!IsGameDevice(device) || !OutRunVRD3D9ExUpgradeR13::IsCompatDevice(device))
                return R13ResetR9Hook.stdcall<HRESULT>(device, params);

            // A single authoritative reset path: do the renderer/R9 teardown
            // once, then call ResetEx directly.  This avoids stacking a second
            // inline detour on the same IDirect3DDevice9::Reset implementation.
            OutRunVRD3D9ExUpgradeR13::DisarmLegacyResetHook();
            R13ResetCommonPre(device);

            HRESULT hr = D3DERR_INVALIDCALL;
            if (!OutRunVRD3D9ExUpgradeR13::ResetCompatDevice(device, params, hr))
            {
                spdlog::error("VR D3D9Ex R13: compat device lost ResetEx ownership unexpectedly; refusing to call competing Reset chain");
                return D3DERR_INVALIDCALL;
            }

            if (SUCCEEDED(hr))
            {
                EnsureStereoResources(device);
                if (TrackedDepthStencil)
                {
                    R9CaptureMainDepth(TrackedDepthStencil, "r13-resetex-complete");
                    R9ExpectMainDepthAfterReset = false;
                }
            }
            return hr;
        }

        DWORD WINAPI R13StereoInstallThread(void*)
        {
            for (int attempt = 0; attempt < 1200; ++attempt)
            {
                if (R9ResetCallbackHook && Game::D3DDevice_ptr && *Game::D3DDevice_ptr)
                {
                    R13ResetR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR9), ResetDestR13);
                    R13ResolveDirectHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResolveDirectTransport), ResolveDirectTransportR13);
                    if (R13ResetR9Hook && R13ResolveDirectHook)
                    {
                        spdlog::info(
                            "VR R13: stereo hardening ACTIVE; single ResetEx owner + GPU-completion direct-ring backpressure");
                    }
                    else
                    {
                        spdlog::error("VR R13: failed to install reset/direct-transport hardening hooks");
                    }
                    return 0;
                }
                Sleep(25);
            }
            spdlog::warn("VR R13: R9 callback policy did not become ready; hardening overlay not installed");
            return 0;
        }

        class VRStereoR13HardeningHook final : public Hook
        {
        public:
            std::string_view description() override { return "OpenXRVRStereoR13Hardening"; }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(nullptr, 0, R13StereoInstallThread, nullptr, 0, nullptr);
                if (!thread)
                    return false;
                CloseHandle(thread);
                return true;
            }
            static VRStereoR13HardeningHook instance;
        };

        VRStereoR13HardeningHook VRStereoR13HardeningHook::instance;
    }

    bool IsMainBackbufferPoseInjectionPass() noexcept
    {
        return TargetIsBackBuffer() && !AnyAuxRenderTargetActive() && !InternalStereoPass;
    }
}
