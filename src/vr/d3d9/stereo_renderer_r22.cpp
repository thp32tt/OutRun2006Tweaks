// R22 pre-hardware-test hardening overlay.
//
// Keeps the R21/R20/R13/R9 implementation intact while closing review gaps
// that are easiest to enforce at the final game-side callback boundary:
//   * preserve the game's scissor state across internal mono/right-eye RT swaps;
//   * validate every first stereo seed (full-clear and relaxed) against one
//     common game-state depth/stencil baseline;
//   * make the R21 game-local host-liveness gate authoritative for clear/draw
//     callbacks so stale host flags cannot keep stereo work alive;
//   * after D3D9 Reset, require a new host-fresh verified baseline before WVP or
//     stereo replay may resume;
//   * if replay state cannot be captured or the overlay cannot install, fail
//     closed instead of attempting stereo with unknown viewport/scissor state.

#include "stereo_renderer_r21.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        constexpr std::size_t R22SetViewportVtableIndex = 47;

        SafetyHookInline R22SetViewportHook{};
        SafetyHookInline R22ResetR13Hook{};
        SafetyHookInline R22ClearR20Hook{};
        SafetyHookInline R22DrawPrimitiveR9Hook{};
        SafetyHookInline R22DrawIndexedPrimitiveR9Hook{};
        SafetyHookInline R22DrawPrimitiveUPR9Hook{};
        SafetyHookInline R22DrawIndexedPrimitiveUPR9Hook{};
        std::atomic<bool> R22InstallReady{false};

        struct R22ScissorSnapshot
        {
            RECT rect{};
            DWORD enabled = FALSE;
            D3DVIEWPORT9 viewport{};
            bool valid = false;
        };

        thread_local R22ScissorSnapshot R22GameScissor{};
        thread_local std::uint32_t R22InternalReplayDepth = 0;

        std::uint64_t R22DepthClearEpoch = 0;
        std::uint64_t R22DepthClearDrawSerial = 0;
        std::uint64_t R22DepthClearGeneration = 0;
        std::uint64_t R22StencilClearEpoch = 0;
        std::uint64_t R22StencilClearDrawSerial = 0;
        std::uint64_t R22StencilClearGeneration = 0;
        std::uint64_t R22RejectedInitialSeeds = 0;
        std::uint64_t R22ReplayStateCaptureFailures = 0;
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
            out.valid = true;
            return true;
        }

        bool R22ApplyGameScissor(IDirect3DDevice9* device,
            const R22ScissorSnapshot& state) noexcept
        {
            if (!device || !state.valid)
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
                    stateValid = R22CaptureGameScissor(device, R22GameScissor);
                else
                    stateValid = R22GameScissor.valid;
            }

            ~R22ReplayScope()
            {
                if (R22InternalReplayDepth)
                    --R22InternalReplayDepth;
                if (outer)
                {
                    if (R22GameScissor.valid)
                        R22ApplyGameScissor(device, R22GameScissor);
                    R22GameScissor = {};
                }
            }
        };

        void R22FailClosedReplayState(IDirect3DDevice9* device,
            const char* site) noexcept
        {
            ++R22ReplayStateCaptureFailures;
            // Do not allow a draw/clear with unknown replay state to leave the
            // common WVP/stereo gate open. The current callback executes exactly
            // once on the real game target; recovery requires a later verified
            // baseline before stereo is allowed again.
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
            if (SUCCEEDED(hr) && IsGameDevice(device) && InternalStereoPass &&
                R22InternalReplayDepth && R22GameScissor.valid)
            {
                if (!R22ApplyGameScissor(device, R22GameScissor))
                    NoteRestoreFailure("R22 scissor replay");
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
            if (!state.valid || !BackBufferDesc.Width || !BackBufferDesc.Height)
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

            // R20 may already have promoted RuntimeEligibility after its older
            // viewport/rect-only classifier. Roll back the entire common state,
            // not just the R9 seed bits, so WVP injection cannot remain enabled
            // after R22 proves the real scissored game clear was unsafe.
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
            if (IsGameDevice(device))
            {
                // Reset invalidates every render-target/depth baseline. Even if
                // the host remains fresh, do not carry a pre-Reset eligibility
                // decision into the new device state.
                R22FailClosedEligibility();
                R22ResetBaselineTracking();
                spdlog::info(
                    "VR R22 RESET: common eligibility closed; waiting for a new host-fresh verified color/depth baseline");
            }
            return R22ResetR13Hook.stdcall<HRESULT>(device, params);
        }

        HRESULT __stdcall ClearDestR22(IDirect3DDevice9* device, DWORD count,
            const D3DRECT* rects, DWORD flags, D3DCOLOR color, float z,
            DWORD stencil)
        {
            if (!IsGameDevice(device) || InternalStereoPass)
                return R22ClearR20Hook.stdcall<HRESULT>(
                    device, count, rects, flags, color, z, stencil);

            // R21's Present-boundary freshness decision is authoritative for the
            // entire next game frame. When closed, bypass every stereo replay and
            // execute only the game's real clear.
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

            // Legacy full-clear classifiers did not include the pre-replay
            // scissor state. Undo any synchronization promotion they made for a
            // clear that was only partial in the real game state.
            if (SUCCEEDED(hr) && mainBefore && !fullGameClear)
            {
                if ((flags & D3DCLEAR_ZBUFFER) != 0)
                    RightDepthSynchronized = depthSyncBefore;
                if ((flags & D3DCLEAR_STENCIL) != 0)
                    RightStencilSynchronized = stencilSyncBefore;
            }

            // Applies equally to the R9 full-color bootstrap and R20 relaxed
            // bootstrap because this wrapper runs after both have completed.
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

        DWORD WINAPI R22InstallThread(void*)
        {
            // Until every R22 callback is installed transactionally, no earlier
            // layer may reopen WVP/stereo eligibility on its own.
            R22InstallReady.store(false, std::memory_order_release);
            R22FailClosedEligibility();

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                if (R9InstallState.load(std::memory_order_acquire) == R9InstallFailed ||
                    R13InstallState.load(std::memory_order_acquire) == R13InstallFailed)
                {
                    spdlog::error(
                        "VR R22: base R9/R13 transaction failed; safety overlay remains fail-closed");
                    return 0;
                }
                if (R9InstallState.load(std::memory_order_acquire) == R9InstallReady &&
                    R13InstallState.load(std::memory_order_acquire) == R13InstallReady &&
                    R20BootstrapReady.load(std::memory_order_acquire) &&
                    R21PresentGuardReady.load(std::memory_order_acquire))
                {
                    IDirect3DDevice9* device =
                        StereoInstalledDevice.load(std::memory_order_acquire);
                    if (!device)
                    {
                        spdlog::error(
                            "VR R22: installed game device unavailable; safety overlay remains fail-closed");
                        return 0;
                    }
                    void** vtable = *reinterpret_cast<void***>(device);
                    if (!vtable)
                    {
                        spdlog::error(
                            "VR R22: game device vtable unavailable; safety overlay remains fail-closed");
                        return 0;
                    }

                    R22SetViewportHook = safetyhook::create_inline(
                        vtable[R22SetViewportVtableIndex], SetViewportDestR22);
                    R22ResetR13Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR13), ResetDestR22);
                    R22ClearR20Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ClearDestR20), ClearDestR22);
                    R22DrawPrimitiveR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR9),
                        DrawPrimitiveDestR22);
                    R22DrawIndexedPrimitiveR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR9),
                        DrawIndexedPrimitiveDestR22);
                    R22DrawPrimitiveUPR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR9),
                        DrawPrimitiveUPDestR22);
                    R22DrawIndexedPrimitiveUPR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR9),
                        DrawIndexedPrimitiveUPDestR22);

                    if (!R22SetViewportHook || !R22ResetR13Hook ||
                        !R22ClearR20Hook || !R22DrawPrimitiveR9Hook ||
                        !R22DrawIndexedPrimitiveR9Hook ||
                        !R22DrawPrimitiveUPR9Hook ||
                        !R22DrawIndexedPrimitiveUPR9Hook)
                    {
                        R22SetViewportHook = {};
                        R22ResetR13Hook = {};
                        R22ClearR20Hook = {};
                        R22DrawPrimitiveR9Hook = {};
                        R22DrawIndexedPrimitiveR9Hook = {};
                        R22DrawPrimitiveUPR9Hook = {};
                        R22DrawIndexedPrimitiveUPR9Hook = {};
                        R22FailClosedEligibility();
                        spdlog::error(
                            "VR R22: reset/scissor/bootstrap hardening hook transaction failed closed");
                        return 0;
                    }

                    R22InstallReady.store(true, std::memory_order_release);
                    spdlog::info(
                        "VR R22 GAME: scissor-preserving mono/right replay + common initial depth baseline + R21 eligibility gate ACTIVE");
                    spdlog::info(
                        "VR R22 REVIEW: Reset recovery gate + unsafe-seed common rollback + replay-state capture fail-closed ACTIVE");
                    return 0;
                }
                Sleep(25);
            }
            R22FailClosedEligibility();
            spdlog::error(
                "VR R22: timed out waiting for prerequisite hook transactions; safety overlay remains fail-closed");
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
                HANDLE thread = CreateThread(
                    nullptr, 0, R22InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R22FailClosedEligibility();
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
