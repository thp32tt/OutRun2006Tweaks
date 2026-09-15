// R13 hardening wrapper. The validated R9 renderer remains source-of-truth;
// cmake marks stereo_renderer.cpp HEADER_FILE_ONLY and compiles this TU.
//
// Review hardening added here keeps unsafe MRT/occlusion transitions single-
// execution: once such a main-backbuffer draw appears after stereo has started,
// the rest of that Present is rendered only into the already-seeded mono safety
// shadow and restored before Present. This avoids replaying side-effecting MRT
// or query draws while still producing a complete mono fallback.

#include "r13_bridge.hpp"
#include "stereo_renderer.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R13ResetR9Hook{};
        SafetyHookInline R13ResolveDirectHook{};
        SafetyHookInline R13PresentR9Hook{};
        SafetyHookInline R13DrawPrimitiveR9Hook{};
        SafetyHookInline R13DrawIndexedPrimitiveR9Hook{};
        SafetyHookInline R13DrawPrimitiveUPR9Hook{};
        SafetyHookInline R13DrawIndexedPrimitiveUPR9Hook{};

        std::uint64_t R13SafeAckBackpressure = 0;
        bool R13FirstSafeAckBlockLogged = false;
        bool R13FirstAckMappingLogged = false;
        bool R13ForceMonoShadow = false;
        std::uint64_t R13UnsafeTransitionFrames = 0;
        bool R13FirstUnsafeTransitionLogged = false;

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
            R13ForceMonoShadow = false;
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

        template <typename DrawCall>
        HRESULT R13DrawMonoShadowOnce(IDirect3DDevice9* device,
            DrawCall&& actualDraw, const char* site)
        {
            IDirect3DSurface9* savedRt = nullptr;
            IDirect3DSurface9* savedDepth = nullptr;
            D3DVIEWPORT9 savedViewport{};
            if (!R9BindMonoTarget(device, savedRt, savedDepth, savedViewport))
            {
                R9MonoBackupGap = true;
                R9Poison(OutRunVR::StereoFailureResourceUnavailable, site);
                return actualDraw();
            }

            const bool mayWriteDepth = LeftDrawMayWriteDepth(device);
            const bool mayWriteStencil = LeftDrawMayWriteStencil(device);
            const HRESULT hr = actualDraw();
            const bool restoreOk =
                R9RestoreGameTarget(device, savedRt, savedDepth, savedViewport);
            if (FAILED(hr) || !restoreOk)
            {
                R9MonoBackupGap = true;
                R9Poison(OutRunVR::StereoFailureRestoreFailed, site, hr);
                return hr;
            }
            ++R9MonoBackupDraws;
            if (mayWriteDepth || mayWriteStencil)
                ++R9MonoDepthContentSerial;
            return hr;
        }

        template <typename ActualDraw, typename LegacyDraw>
        HRESULT R13GuardedDraw(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, LegacyDraw&& legacyDraw, const char* site)
        {
            if (!IsGameDevice(device) || InternalStereoPass)
                return legacyDraw();

            const bool mainTarget = TargetIsBackBuffer();
            if (R13ForceMonoShadow && mainTarget)
                return R13DrawMonoShadowOnce(device, actualDraw, site);

            const bool unsafeMrt = mainTarget && AnyAuxRenderTargetActive();
            const bool unsafeOcclusion = mainTarget &&
                ActiveOcclusionQueries.load(std::memory_order_acquire) > 0;
            if (StereoWanted() && R9StereoSeeded &&
                (unsafeMrt || unsafeOcclusion))
            {
                const auto reason = unsafeMrt
                    ? OutRunVR::StereoFailureMrtActive
                    : OutRunVR::StereoFailureOcclusionQueryActive;
                R9Poison(reason, site);
                ++R13UnsafeTransitionFrames;

                if (R9MonoSeeded && !R9MonoBackupGap &&
                    R9CurrentDepthCanMirror())
                {
                    R13ForceMonoShadow = true;
                    if (!R13FirstUnsafeTransitionLogged)
                    {
                        R13FirstUnsafeTransitionLogged = true;
                        spdlog::info(
                            "VR R13 review hardening: unsafe MRT/occlusion transition switches the remainder of the Present to single-execution mono shadow; no duplicate query/MRT side effects");
                    }
                    return R13DrawMonoShadowOnce(device, actualDraw, site);
                }

                // If the independent mono history is unavailable, do not replay
                // a side-effecting draw. Continue the real target once and mark
                // the shadow unusable for Present restoration.
                R9MonoBackupGap = true;
                return actualDraw();
            }

            return legacyDraw();
        }

        HRESULT __stdcall DrawPrimitiveDestR13(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto legacy = [&]() {
                return R13DrawPrimitiveR9Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R13GuardedDraw(device, actual, legacy, "R13/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR13(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, INT baseVertexIndex, UINT minVertexIndex,
            UINT numVertices, UINT startIndex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            auto legacy = [&]() {
                return R13DrawIndexedPrimitiveR9Hook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            return R13GuardedDraw(
                device, actual, legacy, "R13/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR13(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT primitiveCount, const void* data, UINT stride)
        {
            auto actual = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto legacy = [&]() {
                return R13DrawPrimitiveUPR9Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R13GuardedDraw(device, actual, legacy, "R13/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR13(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT minVertexIndex, UINT numVertices,
            UINT primitiveCount, const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            auto legacy = [&]() {
                return R13DrawIndexedPrimitiveUPR9Hook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            return R13GuardedDraw(
                device, actual, legacy, "R13/DrawIndexedPrimitiveUP");
        }

        HRESULT __stdcall PresentDestR13(IDirect3DDevice9* device,
            const RECT* sourceRect, const RECT* destRect,
            HWND destWindowOverride, const RGNDATA* dirtyRegion)
        {
            const HRESULT hr = R13PresentR9Hook.stdcall<HRESULT>(device,
                sourceRect, destRect, destWindowOverride, dirtyRegion);
            if (IsGameDevice(device))
                R13ForceMonoShadow = false;
            return hr;
        }

        void R13RollbackOverlayHooks() noexcept
        {
            R13ResetR9Hook = {};
            R13ResolveDirectHook = {};
            R13PresentR9Hook = {};
            R13DrawPrimitiveR9Hook = {};
            R13DrawIndexedPrimitiveR9Hook = {};
            R13DrawPrimitiveUPR9Hook = {};
            R13DrawIndexedPrimitiveUPR9Hook = {};
        }

        void R13RollbackPartialR9Policy() noexcept
        {
            R9ResetCallbackHook = {};
            R9PresentCallbackHook = {};
            R9SetRenderTargetCallbackHook = {};
            R9SetDepthCallbackHook = {};
            R9ClearCallbackHook = {};
            R9DrawPrimitiveCallbackHook = {};
            R9DrawIndexedPrimitiveCallbackHook = {};
            R9DrawPrimitiveUPCallbackHook = {};
            R9DrawIndexedPrimitiveUPCallbackHook = {};
        }

        bool R13R9PolicyComplete() noexcept
        {
            return R9ResetCallbackHook && R9PresentCallbackHook &&
                R9SetRenderTargetCallbackHook && R9SetDepthCallbackHook &&
                R9ClearCallbackHook && R9DrawPrimitiveCallbackHook &&
                R9DrawIndexedPrimitiveCallbackHook && R9DrawPrimitiveUPCallbackHook &&
                R9DrawIndexedPrimitiveUPCallbackHook;
        }

        DWORD WINAPI R13StereoInstallThread(void*)
        {
            for (int attempt = 0; attempt < 1200; ++attempt)
            {
                if (R13R9PolicyComplete() && Game::D3DDevice_ptr &&
                    *Game::D3DDevice_ptr)
                {
                    R13ResetR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR9), ResetDestR13);
                    R13ResolveDirectHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResolveDirectTransport),
                        ResolveDirectTransportR13);
                    R13PresentR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&PresentDestR9), PresentDestR13);
                    R13DrawPrimitiveR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR9),
                        DrawPrimitiveDestR13);
                    R13DrawIndexedPrimitiveR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR9),
                        DrawIndexedPrimitiveDestR13);
                    R13DrawPrimitiveUPR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR9),
                        DrawPrimitiveUPDestR13);
                    R13DrawIndexedPrimitiveUPR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR9),
                        DrawIndexedPrimitiveUPDestR13);

                    if (R13ResetR9Hook && R13ResolveDirectHook &&
                        R13PresentR9Hook && R13DrawPrimitiveR9Hook &&
                        R13DrawIndexedPrimitiveR9Hook && R13DrawPrimitiveUPR9Hook &&
                        R13DrawIndexedPrimitiveUPR9Hook)
                    {
                        spdlog::info(
                            "VR R13: stereo hardening ACTIVE; single ResetEx owner + GPU-completion direct-ring backpressure + single-execution MRT/occlusion fallback");
                    }
                    else
                    {
                        R13RollbackOverlayHooks();
                        spdlog::error(
                            "VR R13: overlay hook installation was partial; all R13 overlay hooks rolled back");
                    }
                    return 0;
                }
                Sleep(25);
            }

            if (R9ResetCallbackHook || R9PresentCallbackHook ||
                R9SetRenderTargetCallbackHook || R9SetDepthCallbackHook ||
                R9ClearCallbackHook || R9DrawPrimitiveCallbackHook ||
                R9DrawIndexedPrimitiveCallbackHook || R9DrawPrimitiveUPCallbackHook ||
                R9DrawIndexedPrimitiveUPCallbackHook)
            {
                R13RollbackPartialR9Policy();
                spdlog::error(
                    "VR R13: R9 callback policy was only partially installed; partial policy rolled back to fail closed");
            }
            else
            {
                spdlog::warn(
                    "VR R13: R9 callback policy did not become ready; hardening overlay not installed");
            }
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
