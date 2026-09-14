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
        bool R13FirstAckMappingLogged = false;

        HANDLE R13AckMapping = nullptr;
        const OutRunVR::R13::DirectGpuAckState* R13AckState = nullptr;

        bool R13EnsureAckState() noexcept
        {
            if (R13AckState &&
                R13AckState->magic == OutRunVR::R13::DirectGpuAckMagic &&
                R13AckState->version == OutRunVR::R13::DirectGpuAckVersion &&
                R13AckState->structSize == sizeof(OutRunVR::R13::DirectGpuAckState))
                return true;

            if (R13AckState)
            {
                UnmapViewOfFile(R13AckState);
                R13AckState = nullptr;
            }
            if (R13AckMapping)
            {
                CloseHandle(R13AckMapping);
                R13AckMapping = nullptr;
            }

            R13AckMapping = OpenFileMappingW(
                FILE_MAP_READ, FALSE, OutRunVR::R13::DirectGpuAckName);
            if (!R13AckMapping)
                return false;

            R13AckState = static_cast<const OutRunVR::R13::DirectGpuAckState*>(MapViewOfFile(
                R13AckMapping, FILE_MAP_READ, 0, 0,
                sizeof(OutRunVR::R13::DirectGpuAckState)));
            if (!R13AckState)
            {
                CloseHandle(R13AckMapping);
                R13AckMapping = nullptr;
                return false;
            }

            if (R13AckState->magic != OutRunVR::R13::DirectGpuAckMagic ||
                R13AckState->version != OutRunVR::R13::DirectGpuAckVersion ||
                R13AckState->structSize != sizeof(OutRunVR::R13::DirectGpuAckState))
            {
                UnmapViewOfFile(R13AckState);
                R13AckState = nullptr;
                CloseHandle(R13AckMapping);
                R13AckMapping = nullptr;
                return false;
            }

            if (!R13FirstAckMappingLogged)
            {
                R13FirstAckMappingLogged = true;
                spdlog::info(
                    "VR D3D9Ex R13: dedicated per-slot GPU-consumer ACK mapping opened; legacy pose reserved fields remain untouched");
            }
            return true;
        }

        bool R13ReadGpuCompletedFrame(std::uint32_t slotIndex,
            std::uint32_t& completedFrame) noexcept
        {
            completedFrame = 0;
            if (slotIndex >= OutRunVR::RenderFrameRingSize || !R13EnsureAckState())
                return false;

            for (int attempt = 0; attempt < 4; ++attempt)
            {
                const std::uint32_t before = R13AckState->sequence;
                if (before & 1u)
                    continue;
                MemoryBarrier();

                OutRunVR::R13::DirectGpuAckState snapshot{};
                std::memcpy(&snapshot, R13AckState, sizeof(snapshot));

                MemoryBarrier();
                const std::uint32_t after = R13AckState->sequence;
                if (before != after || (after & 1u))
                    continue;

                if (snapshot.magic != OutRunVR::R13::DirectGpuAckMagic ||
                    snapshot.version != OutRunVR::R13::DirectGpuAckVersion ||
                    snapshot.structSize != sizeof(snapshot) ||
                    !snapshot.hostPid || !SharedState ||
                    snapshot.hostPid != SharedState->hostPid ||
                    snapshot.transportGeneration != DirectTransportGeneration)
                    return false;

                completedFrame = snapshot.completedFrameId[slotIndex];
                return true;
            }
            return false;
        }

        bool ResolveDirectTransportR13(IDirect3DDevice9* device, std::uint32_t frameId)
        {
            if (frameId && SharedState)
            {
                const std::uint32_t slotIndex =
                    (frameId - 1u) % OutRunVR::RenderFrameRingSize;
                const auto& slot = DirectTransportSlots[slotIndex];
                if (slot.frameId)
                {
                    std::uint32_t gpuCompleted = 0;
                    const bool ackValid = R13ReadGpuCompletedFrame(slotIndex, gpuCompleted);
                    if (!ackValid || !FrameIdAtOrAfter(gpuCompleted, slot.frameId))
                    {
                        ++R13SafeAckBackpressure;
                        ++DirectTransportRingBackpressure;
                        if (!R13FirstSafeAckBlockLogged)
                        {
                            R13FirstSafeAckBlockLogged = true;
                            spdlog::info(
                                "VR D3D9Ex R13: GPU-completion direct-ring backpressure active; slot={} slotFrame={} gpuCompleted={} ackValid={} generation={}",
                                slotIndex, slot.frameId, gpuCompleted, ackValid ? 1 : 0,
                                DirectTransportGeneration);
                        }
                        return false;
                    }
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

        HRESULT __stdcall ResetDestR13(IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            if (!IsGameDevice(device) ||
                !OutRunVRD3D9ExUpgradeR13::IsCompatDevice(device))
                return R13ResetR9Hook.stdcall<HRESULT>(device, params);

            // A single authoritative reset path: do the renderer/R9 teardown
            // once, then call ResetEx directly. This avoids stacking a second
            // inline detour on IDirect3DDevice9::Reset.
            OutRunVRD3D9ExUpgradeR13::DisarmLegacyResetHook();
            R13ResetCommonPre(device);

            HRESULT hr = D3DERR_INVALIDCALL;
            if (!OutRunVRD3D9ExUpgradeR13::ResetCompatDevice(device, params, hr))
            {
                spdlog::error(
                    "VR D3D9Ex R13: compat device lost ResetEx ownership unexpectedly; refusing competing Reset chain");
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
                if (R9ResetCallbackHook && Game::D3DDevice_ptr &&
                    *Game::D3DDevice_ptr)
                {
                    R13ResetR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR9), ResetDestR13);
                    R13ResolveDirectHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResolveDirectTransport),
                        ResolveDirectTransportR13);
                    if (R13ResetR9Hook && R13ResolveDirectHook)
                    {
                        spdlog::info(
                            "VR R13: stereo hardening ACTIVE; single ResetEx owner + GPU-completion direct-ring backpressure");
                    }
                    else
                    {
                        spdlog::error(
                            "VR R13: failed to install reset/direct-transport hardening hooks");
                    }
                    return 0;
                }
                Sleep(25);
            }
            spdlog::warn(
                "VR R13: R9 callback policy did not become ready; hardening overlay not installed");
            return 0;
        }

        class VRStereoR13HardeningHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR13Hardening";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(
                    nullptr, 0, R13StereoInstallThread, nullptr, 0, nullptr);
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
        return TargetIsBackBuffer() && !AnyAuxRenderTargetActive() &&
            !InternalStereoPass;
    }
}
