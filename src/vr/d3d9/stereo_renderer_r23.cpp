// R23 render-state hardening overlay.
//
// The validated R21->R20->R13->R9->R7 implementation stays intact. This final
// game-side TU fixes render-target state that D3D9 may reset when internal mono
// and right-eye targets are bound, and prevents a scissored game clear from
// being misclassified as the first full-frame seed.

#include "stereo_renderer_r21.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R23SetRenderTargetTrampolineHook{};
        SafetyHookInline R23ClearR20Hook{};
        std::atomic<bool> R23StateGuardReady{ false };

        struct ReplayClipState
        {
            bool active = false;
            bool valid = false;
            IDirect3DSurface9* gameTarget = nullptr;
            D3DVIEWPORT9 viewport{};
            RECT scissor{};
            DWORD scissorEnabled = FALSE;
        };

        thread_local ReplayClipState R23ReplayClip{};
        std::uint64_t R23ClipCaptureFailures = 0;
        std::uint64_t R23ClipRestoreFailures = 0;
        std::uint64_t R23ScissoredLegacySeedsRejected = 0;
        bool R23FirstClipLogged = false;

        bool R23CaptureClipState(IDirect3DDevice9* device,
            ReplayClipState& state) noexcept
        {
            state.valid = false;
            if (!device || FAILED(device->GetViewport(&state.viewport)) ||
                FAILED(device->GetRenderState(
                    D3DRS_SCISSORTESTENABLE, &state.scissorEnabled)) ||
                FAILED(device->GetScissorRect(&state.scissor)))
            {
                ++R23ClipCaptureFailures;
                return false;
            }
            state.valid = true;
            return true;
        }

        bool R23ApplyClipState(IDirect3DDevice9* device,
            const ReplayClipState& state) noexcept
        {
            if (!device || !state.valid)
                return false;
            const HRESULT viewportHr = device->SetViewport(&state.viewport);
            const HRESULT scissorHr = device->SetScissorRect(&state.scissor);
            const HRESULT enableHr = device->SetRenderState(
                D3DRS_SCISSORTESTENABLE, state.scissorEnabled);
            if (FAILED(viewportHr) || FAILED(scissorHr) || FAILED(enableHr))
            {
                ++R23ClipRestoreFailures;
                return false;
            }
            return true;
        }

        bool R23ScissorRestrictsBackbuffer(IDirect3DDevice9* device) noexcept
        {
            if (!device || !BackBufferDesc.Width || !BackBufferDesc.Height)
                return true; // fail closed when classification state is unknown
            DWORD enabled = FALSE;
            if (FAILED(device->GetRenderState(D3DRS_SCISSORTESTENABLE, &enabled)))
                return true;
            if (!enabled)
                return false;
            RECT rect{};
            if (FAILED(device->GetScissorRect(&rect)))
                return true;
            return rect.left > 0 || rect.top > 0 ||
                rect.right < static_cast<LONG>(BackBufferDesc.Width) ||
                rect.bottom < static_cast<LONG>(BackBufferDesc.Height);
        }

        HRESULT __stdcall SetRenderTargetTrampolineDestR23(
            IDirect3DDevice9* device, DWORD index, IDirect3DSurface9* surface)
        {
            const bool enteringReplay = InternalStereoPass && index == 0 &&
                (surface == R9MonoSurface || surface == RightEyeSurface) &&
                !R23ReplayClip.active;

            if (enteringReplay)
            {
                R23ReplayClip = {};
                R23ReplayClip.active = true;
                R23ReplayClip.gameTarget = TrackedRenderTarget;
                if (!R23CaptureClipState(device, R23ReplayClip))
                    R9Poison(OutRunVR::StereoFailureViewportUnavailable,
                        "R23/scissor-capture");
            }

            const bool restoringReplay = R23ReplayClip.active && index == 0 &&
                surface == R23ReplayClip.gameTarget;

            const HRESULT hr = R23SetRenderTargetTrampolineHook.stdcall<HRESULT>(
                device, index, surface);

            if (SUCCEEDED(hr) && (enteringReplay || restoringReplay) &&
                R23ReplayClip.valid)
            {
                if (!R23ApplyClipState(device, R23ReplayClip))
                    R9Poison(OutRunVR::StereoFailureViewportUnavailable,
                        "R23/scissor-restore");
                else if (!R23FirstClipLogged)
                {
                    R23FirstClipLogged = true;
                    spdlog::info(
                        "VR R23: viewport + scissor rectangle + SCISSORTESTENABLE preserved across internal mono/right-eye render-target switches");
                }
            }

            if (restoringReplay || FAILED(hr))
                R23ReplayClip = {};
            return hr;
        }

        HRESULT __stdcall ClearDestR23(IDirect3DDevice9* device, DWORD count,
            const D3DRECT* rects, DWORD flags, D3DCOLOR color, float z,
            DWORD stencil)
        {
            const bool gameMain = IsGameDevice(device) && !InternalStereoPass &&
                TargetIsBackBuffer();
            const bool scissorRestricted = gameMain &&
                R23ScissorRestrictsBackbuffer(device);
            const bool seededBefore = R9StereoSeeded;
            const bool depthSyncBefore = RightDepthSynchronized;
            const bool stencilSyncBefore = RightStencilSynchronized;
            const auto relaxedBefore = R20RelaxedSeeds;

            const auto oldDepthEpoch = R20DepthClearEpoch;
            const auto oldDepthDraw = R20DepthClearDrawSerial;
            const auto oldDepthGeneration = R20DepthClearGeneration;
            const auto oldStencilEpoch = R20StencilClearEpoch;
            const auto oldStencilDraw = R20StencilClearDrawSerial;
            const auto oldStencilGeneration = R20StencilClearGeneration;

            const HRESULT hr = R23ClearR20Hook.stdcall<HRESULT>(
                device, count, rects, flags, color, z, stencil);

            if (!scissorRestricted || FAILED(hr))
                return hr;

            // R7/R9 ClearCoversStereoBackbuffer historically considered only
            // viewport+clear rectangles. Restore the pre-call full-clear records
            // so a scissored clear cannot manufacture a new full depth baseline.
            if ((flags & D3DCLEAR_ZBUFFER) != 0)
            {
                R20DepthClearEpoch = oldDepthEpoch;
                R20DepthClearDrawSerial = oldDepthDraw;
                R20DepthClearGeneration = oldDepthGeneration;
            }
            if ((flags & D3DCLEAR_STENCIL) != 0)
            {
                R20StencilClearEpoch = oldStencilEpoch;
                R20StencilClearDrawSerial = oldStencilDraw;
                R20StencilClearGeneration = oldStencilGeneration;
            }

            const bool relaxedAccepted = R20RelaxedSeeds != relaxedBefore;
            if (!seededBefore && R9StereoSeeded && !relaxedAccepted)
            {
                // This was R9's legacy full-clear promotion, not R20's explicit
                // relaxed baseline-copy path. Reject it because the original game
                // clip state proves the clear was not actually full-frame.
                ++R23ScissoredLegacySeedsRejected;
                R20CancelInitialSeed(device);
            }

            // A scissored clear applied equally to already-synchronized eyes may
            // preserve a previous true state, but it may not upgrade false->true.
            if (!relaxedAccepted)
            {
                if (!depthSyncBefore)
                    RightDepthSynchronized = false;
                if (!stencilSyncBefore)
                    RightStencilSynchronized = false;
            }
            return hr;
        }

        DWORD WINAPI R23StateInstallThread(void*)
        {
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                if (R9InstallState.load(std::memory_order_acquire) == R9InstallFailed ||
                    R13InstallState.load(std::memory_order_acquire) == R13InstallFailed)
                    return 0;

                if (R9InstallState.load(std::memory_order_acquire) == R9InstallReady &&
                    R13InstallState.load(std::memory_order_acquire) == R13InstallReady &&
                    R20BootstrapReady.load(std::memory_order_acquire) &&
                    R21PresentGuardReady.load(std::memory_order_acquire) &&
                    SetRenderTargetHook && SetRenderTargetHook.trampoline())
                {
                    R23SetRenderTargetTrampolineHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(SetRenderTargetHook.trampoline().address()),
                        SetRenderTargetTrampolineDestR23);
                    R23ClearR20Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ClearDestR20), ClearDestR23);
                    if (!R23SetRenderTargetTrampolineHook || !R23ClearR20Hook)
                    {
                        R23SetRenderTargetTrampolineHook = {};
                        R23ClearR20Hook = {};
                        spdlog::error(
                            "VR R23: failed to install scissor/bootstrap state guards; stereo remains fail-closed until corrected");
                        OutRunVR::RuntimeEligibility::FailClosed();
                        R20StereoEligibilityGate.store(false, std::memory_order_release);
                        return 0;
                    }
                    R23StateGuardReady.store(true, std::memory_order_release);
                    spdlog::info(
                        "VR R23 GAME: scissor-preserving target replay + original-game-state first-seed classifier ACTIVE");
                    return 0;
                }
                Sleep(25);
            }
            spdlog::error("VR R23: timed out installing render-state guards");
            OutRunVR::RuntimeEligibility::FailClosed();
            return 0;
        }

        class VRRenderStateHardeningR23Hook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRRenderStateHardeningR23";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(nullptr, 0, R23StateInstallThread,
                    nullptr, 0, nullptr);
                if (!thread)
                {
                    OutRunVR::RuntimeEligibility::FailClosed();
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRRenderStateHardeningR23Hook instance;
        };

        VRRenderStateHardeningR23Hook VRRenderStateHardeningR23Hook::instance;
    }
}
