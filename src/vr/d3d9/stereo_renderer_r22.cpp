// R22 pre-hardware-test hardening overlay.
//
// Keeps the R21/R20/R13/R9 implementation intact while closing review gaps
// that are easiest to enforce at the final game-side callback boundary:
//   * preserve the game's viewport/scissor state across internal replay;
//   * shadow viewport/scissor state instead of querying D3D9 on every draw;
//   * validate every first stereo seed against one depth/stencil baseline;
//   * make the R21 game-local host-liveness gate authoritative;
//   * after D3D9 Reset, require a new host-fresh verified baseline;
//   * install every overlay hook disabled-first and publish READY only after the
//     complete callback transaction is enabled.

#include "stereo_renderer_r21.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        constexpr std::size_t R22SetViewportVtableIndex = 47;
        constexpr std::size_t R22SetRenderStateVtableIndex = 57;
        constexpr std::size_t R22SetScissorRectVtableIndex = 75;

        SafetyHookInline R22SetViewportHook{};
        SafetyHookInline R22SetRenderStateHook{};
        SafetyHookInline R22SetScissorRectHook{};
        SafetyHookInline R22ResetR13Hook{};
        SafetyHookInline R22ClearR20Hook{};
        SafetyHookInline R22DrawPrimitiveR9Hook{};
        SafetyHookInline R22DrawIndexedPrimitiveR9Hook{};
        SafetyHookInline R22DrawPrimitiveUPR9Hook{};
        SafetyHookInline R22DrawIndexedPrimitiveUPR9Hook{};
        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R22InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        struct R22ScissorSnapshot
        {
            RECT rect{};
            DWORD enabled = FALSE;
            D3DVIEWPORT9 viewport{};
            bool viewportValid = false;
            bool rectValid = false;
            bool enableValid = false;

            bool Valid() const noexcept
            {
                return viewportValid && rectValid && enableValid;
            }
        };

        thread_local R22ScissorSnapshot R22GameScissor{};
        thread_local R22ScissorSnapshot R22ShadowState{};
        thread_local std::uint32_t R22InternalReplayDepth = 0;

        std::uint64_t R22DepthClearEpoch = 0;
        std::uint64_t R22DepthClearDrawSerial = 0;
        std::uint64_t R22DepthClearGeneration = 0;
        std::uint64_t R22StencilClearEpoch = 0;
        std::uint64_t R22StencilClearDrawSerial = 0;
        std::uint64_t R22StencilClearGeneration = 0;
        std::uint64_t R22RejectedInitialSeeds = 0;
        std::uint64_t R22ReplayStateCaptureFailures = 0;
        std::uint64_t R22ReplayStateGetterFallbacks = 0;
        bool R22FirstSeedRejectLogged = false;
        bool R22FirstReplayStateCaptureFailureLogged = false;

        void R22FailClosedEligibility() noexcept
        {
            OutRunVR::RuntimeEligibility::FailClosed();
            R20StereoEligibilityGate.store(false, std::memory_order_release);
            R9StereoSeeded = false;
            R9MonoSeeded = false;
        }

        void R22ResetBaselineTracking() noexcept
        {
            R20DepthClearEpoch = 0;
            R20DepthClearDrawSerial = 0;
            R20DepthClearGeneration = 0;
            R20StencilClearEpoch = 0;
            R20StencilClearDrawSerial = 0;
            R20StencilClearGeneration = 0;
            R22DepthClearEpoch = 0;
            R22DepthClearDrawSerial = 0;
            R22DepthClearGeneration = 0;
            R22StencilClearEpoch = 0;
            R22StencilClearDrawSerial = 0;
            R22StencilClearGeneration = 0;
        }

        bool R22CaptureGameScissor(IDirect3DDevice9* device,
            R22ScissorSnapshot& out) noexcept
        {
            out = {};
            if (!device || FAILED(device->GetViewport(&out.viewport)) ||
                FAILED(device->GetScissorRect(&out.rect)) ||
                FAILED(device->GetRenderState(D3DRS_SCISSORTESTENABLE, &out.enabled)))
                return false;
            out.viewportValid = out.rectValid = out.enableValid = true;
            return true;
        }

        bool R22PrimeShadowState(IDirect3DDevice9* device) noexcept
        {
            R22ScissorSnapshot captured{};
            if (!R22CaptureGameScissor(device, captured))
            {
                R22ShadowState = {};
                return false;
            }
            R22ShadowState = captured;
            return true;
        }

        bool R22SnapshotShadowedGameState(IDirect3DDevice9* device,
            R22ScissorSnapshot& out) noexcept
        {
            if (R22ShadowState.Valid())
            {
                out = R22ShadowState;
                return true;
            }
            ++R22ReplayStateGetterFallbacks;
            if (!R22CaptureGameScissor(device, out))
                return false;
            R22ShadowState = out;
            return true;
        }

        bool R22ApplyGameScissor(IDirect3DDevice9* device,
            const R22ScissorSnapshot& state) noexcept
        {
            if (!device || !state.Valid())
                return false;
            bool ok = true;
            if (FAILED(device->SetScissorRect(&state.rect)))
                ok = false;
            if (FAILED(device->SetRenderState(
                    D3DRS_SCISSORTESTENABLE, state.enabled)))
                ok = false;
            return ok;
        }

        struct R22ReplayScope
        {
            IDirect3DDevice9* device = nullptr;
            bool outer = false;
            bool stateValid = false;

            explicit R22ReplayScope(IDirect3DDevice9* d) noexcept : device(d)
            {
                outer = R22InternalReplayDepth++ == 0;
                if (outer)
                    stateValid = R22SnapshotShadowedGameState(device, R22GameScissor);
                else
                    stateValid = R22GameScissor.Valid();
            }

            ~R22ReplayScope()
            {
                if (R22InternalReplayDepth)
                    --R22InternalReplayDepth;
                if (outer)
                {
                    if (R22GameScissor.Valid() &&
                        !R22ApplyGameScissor(device, R22GameScissor))
                    {
                        R20CancelInitialSeed(device);
                        R9MonoBackupGap = true;
                        NoteRestoreFailure("R22 final scissor restore");
                    }
                    R22GameScissor = {};
                }
            }
        };

        void R22FailClosedReplayState(IDirect3DDevice9* device,
            const char* site) noexcept
        {
            ++R22ReplayStateCaptureFailures;
            R20CancelInitialSeed(device);
            R9MonoBackupGap = true;
            R9Poison(OutRunVR::StereoFailureViewportUnavailable, site);
            if (!R22FirstReplayStateCaptureFailureLogged)
            {
                R22FirstReplayStateCaptureFailureLogged = true;
                spdlog::warn(
                    "VR R22 FAIL-CLOSED: unable to capture viewport/scissor state; stereo replay disabled until a new verified baseline");
            }
        }

        HRESULT __stdcall SetViewportDestR22(IDirect3DDevice9* device,
            const D3DVIEWPORT9* viewport)
        {
            const HRESULT hr = R22SetViewportHook.stdcall<HRESULT>(device, viewport);
            if (SUCCEEDED(hr) && IsGameDevice(device))
            {
                if (!InternalStereoPass && viewport)
                {
                    R22ShadowState.viewport = *viewport;
                    R22ShadowState.viewportValid = true;
                }
                else if (InternalStereoPass && R22InternalReplayDepth &&
                    R22GameScissor.Valid() && !R22ApplyGameScissor(device, R22GameScissor))
                {
                    NoteRestoreFailure("R22 scissor replay");
                }
            }
            return hr;
        }

        HRESULT __stdcall SetScissorRectDestR22(IDirect3DDevice9* device,
            const RECT* rect)
        {
            const HRESULT hr = R22SetScissorRectHook.stdcall<HRESULT>(device, rect);
            if (SUCCEEDED(hr) && IsGameDevice(device) && !InternalStereoPass && rect)
            {
                R22ShadowState.rect = *rect;
                R22ShadowState.rectValid = true;
            }
            return hr;
        }

        HRESULT __stdcall SetRenderStateDestR22(IDirect3DDevice9* device,
            D3DRENDERSTATETYPE state, DWORD value)
        {
            const HRESULT hr = R22SetRenderStateHook.stdcall<HRESULT>(device, state, value);
            if (SUCCEEDED(hr) && IsGameDevice(device) && !InternalStereoPass &&
                state == D3DRS_SCISSORTESTENABLE)
            {
                R22ShadowState.enabled = value;
                R22ShadowState.enableValid = true;
            }
            return hr;
        }

        bool R22RectCoversBackbuffer(const RECT& r) noexcept
        {
            return r.left <= 0 && r.top <= 0 &&
                r.right >= static_cast<LONG>(BackBufferDesc.Width) &&
                r.bottom >= static_cast<LONG>(BackBufferDesc.Height);
        }

        bool R22GameClearCoversBackbuffer(DWORD count,
            const D3DRECT* rects, const R22ScissorSnapshot& state) noexcept
        {
            if (!state.Valid() || !BackBufferDesc.Width || !BackBufferDesc.Height)
                return false;
            if (state.viewport.X != 0 || state.viewport.Y != 0 ||
                state.viewport.Width != BackBufferDesc.Width ||
                state.viewport.Height != BackBufferDesc.Height)
                return false;
            if (state.enabled && !R22RectCoversBackbuffer(state.rect))
                return false;
            if (count == 0)
                return true;
            if (!rects)
                return false;
            for (DWORD i = 0; i < count; ++i)
            {
                const auto& r = rects[i];
                if (r.x1 <= 0 && r.y1 <= 0 &&
                    r.x2 >= static_cast<LONG>(BackBufferDesc.Width) &&
                    r.y2 >= static_cast<LONG>(BackBufferDesc.Height))
                    return true;
            }
            return false;
        }

        void R22ObserveDepthBaseline(bool gameMainTarget, bool fullGameClear,
            DWORD flags, HRESULT hr) noexcept
        {
            if (FAILED(hr) || !gameMainTarget || !fullGameClear ||
                R9DeferredDepth || !R9CurrentDepthCanMirror() ||
                !R9MonoDepth || R9MonoBackupGap)
                return;

            if ((flags & D3DCLEAR_ZBUFFER) != 0)
            {
                R22DepthClearEpoch = PresentEpoch;
                R22DepthClearDrawSerial = R9DrawCalls;
                R22DepthClearGeneration = R9MainDepthGeneration;
            }
            if ((flags & D3DCLEAR_STENCIL) != 0)
            {
                R22StencilClearEpoch = PresentEpoch;
                R22StencilClearDrawSerial = R9DrawCalls;
                R22StencilClearGeneration = R9MainDepthGeneration;
            }
        }

        bool R22InitialDepthBaselineSafe(IDirect3DDevice9* device) noexcept
        {
            if (!TrackedDepthStencil)
                return true;
            const bool depthSafe =
                R22DepthClearEpoch == PresentEpoch &&
                R22DepthClearDrawSerial == R9DrawCalls &&
                R22DepthClearGeneration == R9MainDepthGeneration &&
                R9MonoDepth != nullptr;
            if (!depthSafe)
                return false;
            if (!StencilTestActive(device))
                return true;
            return R22StencilClearEpoch == PresentEpoch &&
                R22StencilClearDrawSerial == R9DrawCalls &&
                R22StencilClearGeneration == R9MainDepthGeneration;
        }

        void R22CancelUnsafeFirstSeed(IDirect3DDevice9* device,
            bool seededBefore, bool fullGameClear) noexcept
        {
            if (seededBefore || !R9StereoSeeded)
                return;
            if (fullGameClear && R22InitialDepthBaselineSafe(device))
                return;

            R20CancelInitialSeed(device);
            ++R22RejectedInitialSeeds;
            if (!R22FirstSeedRejectLogged)
            {
                R22FirstSeedRejectLogged = true;
                spdlog::warn(
                    "VR R22: initial stereo seed rejected; common WVP/stereo eligibility rolled back because game-state full-clear/scissor or depth-stencil baseline was not synchronized");
            }
        }

        bool R22StereoCallbacksEligible() noexcept
        {
            return R20StereoEligibilityGate.load(std::memory_order_acquire);
        }

        HRESULT __stdcall ResetDestR22(IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            const bool gameDevice = IsGameDevice(device);
            if (gameDevice)
            {
                R22FailClosedEligibility();
                R22ResetBaselineTracking();
                R22ShadowState = {};
                spdlog::info(
                    "VR R22 RESET: common eligibility closed; waiting for a new host-fresh verified color/depth baseline");
            }
            const HRESULT hr = R22ResetR13Hook.stdcall<HRESULT>(device, params);
            if (gameDevice && SUCCEEDED(hr))
                R22PrimeShadowState(device);
            return hr;
        }

        HRESULT __stdcall ClearDestR22(IDirect3DDevice9* device, DWORD count,
            const D3DRECT* rects, DWORD flags, D3DCOLOR color, float z,
            DWORD stencil)
        {
            if (!IsGameDevice(device) || InternalStereoPass)
                return R22ClearR20Hook.stdcall<HRESULT>(
                    device, count, rects, flags, color, z, stencil);

            if (!R22StereoCallbacksEligible())
                return ClearHook.stdcall<HRESULT>(
                    device, count, rects, flags, color, z, stencil);

            R22ReplayScope replay(device);
            if (!replay.stateValid)
            {
                R22FailClosedReplayState(device, "R22/Clear/scissor-capture");
                return ClearHook.stdcall<HRESULT>(
                    device, count, rects, flags, color, z, stencil);
            }

            const bool mainBefore = TargetIsBackBuffer();
            const bool seedBefore = R9StereoSeeded;
            const bool depthSyncBefore = RightDepthSynchronized;
            const bool stencilSyncBefore = RightStencilSynchronized;
            const bool fullGameClear = R22GameClearCoversBackbuffer(
                count, rects, R22GameScissor);

            const HRESULT hr = R22ClearR20Hook.stdcall<HRESULT>(
                device, count, rects, flags, color, z, stencil);

            R22ObserveDepthBaseline(mainBefore, fullGameClear, flags, hr);

            if (SUCCEEDED(hr) && mainBefore && !fullGameClear)
            {
                if ((flags & D3DCLEAR_ZBUFFER) != 0)
                    RightDepthSynchronized = depthSyncBefore;
                if ((flags & D3DCLEAR_STENCIL) != 0)
                    RightStencilSynchronized = stencilSyncBefore;
            }

            R22CancelUnsafeFirstSeed(device, seedBefore, fullGameClear);
            return hr;
        }

        HRESULT __stdcall DrawPrimitiveDestR22(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            if (!IsGameDevice(device) || InternalStereoPass)
                return R22DrawPrimitiveR9Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            if (!R22StereoCallbacksEligible())
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            R22ReplayScope replay(device);
            if (!replay.stateValid)
            {
                R22FailClosedReplayState(device, "R22/DrawPrimitive/scissor-capture");
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            }
            return R22DrawPrimitiveR9Hook.stdcall<HRESULT>(
                device, type, startVertex, primitiveCount);
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR22(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, INT baseVertexIndex, UINT minVertexIndex,
            UINT numVertices, UINT startIndex, UINT primitiveCount)
        {
            if (!IsGameDevice(device) || InternalStereoPass)
                return R22DrawIndexedPrimitiveR9Hook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            if (!R22StereoCallbacksEligible())
                return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            R22ReplayScope replay(device);
            if (!replay.stateValid)
            {
                R22FailClosedReplayState(device,
                    "R22/DrawIndexedPrimitive/scissor-capture");
                return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            }
            return R22DrawIndexedPrimitiveR9Hook.stdcall<HRESULT>(device, type,
                baseVertexIndex, minVertexIndex, numVertices, startIndex,
                primitiveCount);
        }

        HRESULT __stdcall DrawPrimitiveUPDestR22(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT primitiveCount, const void* data,
            UINT stride)
        {
            if (!IsGameDevice(device) || InternalStereoPass)
                return R22DrawPrimitiveUPR9Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            if (!R22StereoCallbacksEligible())
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            R22ReplayScope replay(device);
            if (!replay.stateValid)
            {
                R22FailClosedReplayState(device,
                    "R22/DrawPrimitiveUP/scissor-capture");
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            }
            return R22DrawPrimitiveUPR9Hook.stdcall<HRESULT>(
                device, type, primitiveCount, data, stride);
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR22(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT minVertexIndex, UINT numVertices,
            UINT primitiveCount, const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            if (!IsGameDevice(device) || InternalStereoPass)
                return R22DrawIndexedPrimitiveUPR9Hook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            if (!R22StereoCallbacksEligible())
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            R22ReplayScope replay(device);
            if (!replay.stateValid)
            {
                R22FailClosedReplayState(device,
                    "R22/DrawIndexedPrimitiveUP/scissor-capture");
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            }
            return R22DrawIndexedPrimitiveUPR9Hook.stdcall<HRESULT>(device, type,
                minVertexIndex, numVertices, primitiveCount, indexData,
                indexFormat, vertexData, stride);
        }

        void R22RollbackHooks() noexcept
        {
            R22SetViewportHook = {};
            R22SetRenderStateHook = {};
            R22SetScissorRectHook = {};
            R22ResetR13Hook = {};
            R22ClearR20Hook = {};
            R22DrawPrimitiveR9Hook = {};
            R22DrawIndexedPrimitiveR9Hook = {};
            R22DrawPrimitiveUPR9Hook = {};
            R22DrawIndexedPrimitiveUPR9Hook = {};
        }

        bool R22EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R22SetViewportHook, &R22SetRenderStateHook, &R22SetScissorRectHook,
                &R22ResetR13Hook, &R22ClearR20Hook, &R22DrawPrimitiveR9Hook,
                &R22DrawIndexedPrimitiveR9Hook, &R22DrawPrimitiveUPR9Hook,
                &R22DrawIndexedPrimitiveUPR9Hook
            };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                    return false;
            }
            return true;
        }

        DWORD WINAPI R22InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R22InstallState.store(State::Pending, std::memory_order_release);
            R22FailClosedEligibility();

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                if (R9InstallState.load(std::memory_order_acquire) == R9InstallFailed ||
                    R13InstallState.load(std::memory_order_acquire) == R13InstallFailed ||
                    OutRunVR::RuntimeEligibility::IsFailed(R20InstallState) ||
                    OutRunVR::RuntimeEligibility::IsFailed(R21InstallState))
                {
                    R22InstallState.store(State::Failed, std::memory_order_release);
                    spdlog::error(
                        "VR R22: prerequisite hook transaction failed; safety overlay remains fail-closed");
                    return 0;
                }
                if (R9InstallState.load(std::memory_order_acquire) == R9InstallReady &&
                    R13InstallState.load(std::memory_order_acquire) == R13InstallReady &&
                    OutRunVR::RuntimeEligibility::IsReady(R20InstallState) &&
                    OutRunVR::RuntimeEligibility::IsReady(R21InstallState))
                {
                    IDirect3DDevice9* device =
                        StereoInstalledDevice.load(std::memory_order_acquire);
                    if (!device)
                    {
                        R22InstallState.store(State::Failed, std::memory_order_release);
                        spdlog::error(
                            "VR R22: installed game device unavailable; safety overlay remains fail-closed");
                        return 0;
                    }
                    void** vtable = *reinterpret_cast<void***>(device);
                    if (!vtable)
                    {
                        R22InstallState.store(State::Failed, std::memory_order_release);
                        spdlog::error(
                            "VR R22: game device vtable unavailable; safety overlay remains fail-closed");
                        return 0;
                    }

                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R22SetViewportHook = safetyhook::create_inline(
                        vtable[R22SetViewportVtableIndex], SetViewportDestR22, disabled);
                    R22SetRenderStateHook = safetyhook::create_inline(
                        vtable[R22SetRenderStateVtableIndex], SetRenderStateDestR22, disabled);
                    R22SetScissorRectHook = safetyhook::create_inline(
                        vtable[R22SetScissorRectVtableIndex], SetScissorRectDestR22, disabled);
                    R22ResetR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR13), ResetDestR22, disabled);
                    R22ClearR20Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ClearDestR20), ClearDestR22, disabled);
                    R22DrawPrimitiveR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR9), DrawPrimitiveDestR22, disabled);
                    R22DrawIndexedPrimitiveR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR9), DrawIndexedPrimitiveDestR22, disabled);
                    R22DrawPrimitiveUPR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR9), DrawPrimitiveUPDestR22, disabled);
                    R22DrawIndexedPrimitiveUPR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR9), DrawIndexedPrimitiveUPDestR22, disabled);

                    if (!R22SetViewportHook || !R22SetRenderStateHook ||
                        !R22SetScissorRectHook || !R22ResetR13Hook ||
                        !R22ClearR20Hook || !R22DrawPrimitiveR9Hook ||
                        !R22DrawIndexedPrimitiveR9Hook ||
                        !R22DrawPrimitiveUPR9Hook || !R22DrawIndexedPrimitiveUPR9Hook ||
                        !R22EnableHooks())
                    {
                        R22RollbackHooks();
                        R22FailClosedEligibility();
                        R22InstallState.store(State::Failed, std::memory_order_release);
                        spdlog::error(
                            "VR R22: disabled-first reset/state/bootstrap hook transaction failed closed");
                        return 0;
                    }

                    R22PrimeShadowState(device);
                    R22InstallState.store(State::Ready, std::memory_order_release);
                    spdlog::info(
                        "VR R22 GAME: shadow-tracked viewport/scissor replay + common initial depth baseline + R21 eligibility gate ACTIVE");
                    spdlog::info(
                        "VR R22 REVIEW: disabled-first transaction READY; per-draw GetViewport/GetScissorRect/GetRenderState eliminated after initial state prime");
                    return 0;
                }
                Sleep(25);
            }
            R22FailClosedEligibility();
            R22InstallState.store(State::Failed, std::memory_order_release);
            spdlog::error(
                "VR R22: timed out waiting for prerequisite hook transactions; safety overlay FAILED closed");
            return 0;
        }

        class VRR22SafetyOverlayHook : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRSafetyOverlayR22";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R22InstallState.store(State::Pending, std::memory_order_release);
                HANDLE thread = CreateThread(
                    nullptr, 0, R22InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R22FailClosedEligibility();
                    R22InstallState.store(State::Failed, std::memory_order_release);
                    spdlog::error(
                        "VR R22: failed to create safety-overlay installer thread; eligibility remains fail-closed: {}",
                        GetLastError());
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRR22SafetyOverlayHook instance;
        };

        VRR22SafetyOverlayHook VRR22SafetyOverlayHook::instance;
    }
}
