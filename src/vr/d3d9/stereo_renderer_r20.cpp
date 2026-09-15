// R20 production stabilization wrapper.
//
// Keep the validated R13/R9 safety stack intact, but fix the bootstrap rule
// that could leave the RenderFrame ring permanently at frameId=0 on OutRun.
// R9 required a *full-screen* main-target color clear on every Present before
// any stereo draw could start. Real OutRun render paths can use a rect/scissored
// main color clear.
//
// The original R20 relaxation was too broad: it could mark a partially-cleared
// mono shadow as complete and could start stereo after depth-writing geometry
// had already diverged between the main and right-eye depth surfaces. This
// version keeps the relaxed color-clear bootstrap only when we can first build
// a complete zero-disparity color baseline for both the right eye and mono
// shadow, and (when depth/stencil is active) when verified full depth/stencil
// clears belong to the current depth generation and have no intervening draw.

#include "stereo_renderer_r13.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R20ClearR9Hook{};
        std::atomic<bool> R20BootstrapReady{false};

        // R21 host-liveness policy toggles this game-local gate. It deliberately
        // does not mutate host-owned SharedPoseState flags.
        std::atomic<bool> R20StereoEligibilityGate{true};

        bool R20FirstRelaxedSeedLogged = false;
        std::uint64_t R20RelaxedSeeds = 0;
        std::uint64_t R20BaselineCopyFailures = 0;
        std::uint64_t R20DepthGateRejects = 0;

        // Track Z and stencil independently. The previous OR-ed flag history
        // could combine two clears separated by a draw and incorrectly treat
        // them as one synchronized depth/stencil baseline.
        std::uint64_t R20DepthClearEpoch = 0;
        std::uint64_t R20DepthClearDrawSerial = 0;
        std::uint64_t R20DepthClearGeneration = 0;
        std::uint64_t R20StencilClearEpoch = 0;
        std::uint64_t R20StencilClearDrawSerial = 0;
        std::uint64_t R20StencilClearGeneration = 0;

        void R20ObserveFullDepthSeed(IDirect3DDevice9* device, DWORD count,
            const D3DRECT* rects, DWORD flags, HRESULT hr) noexcept
        {
            if (FAILED(hr) || !device || !IsGameDevice(device) || InternalStereoPass ||
                !TargetIsBackBuffer() || R9DeferredDepth || !R9CurrentDepthCanMirror() ||
                !R9MonoDepth || R9MonoBackupGap)
                return;

            const DWORD depthFlags = flags & (D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL);
            if (!depthFlags || !ClearCoversStereoBackbuffer(device, count, rects))
                return;

            // R9DrawCalls is intentionally conservative: any intervening draw,
            // including an offscreen draw, prevents relaxed bootstrap. Safety is
            // preferred over availability here until a dedicated main-depth
            // mutation serial replaces this coarse counter.
            if ((depthFlags & D3DCLEAR_ZBUFFER) != 0)
            {
                R20DepthClearEpoch = PresentEpoch;
                R20DepthClearDrawSerial = R9DrawCalls;
                R20DepthClearGeneration = R9MainDepthGeneration;
            }
            if ((depthFlags & D3DCLEAR_STENCIL) != 0)
            {
                R20StencilClearEpoch = PresentEpoch;
                R20StencilClearDrawSerial = R9DrawCalls;
                R20StencilClearGeneration = R9MainDepthGeneration;
            }
        }

        bool R20DepthHistorySafeForRelaxedSeed(IDirect3DDevice9* device) noexcept
        {
            if (!TrackedDepthStencil)
                return true;

            const bool depthSafe =
                R20DepthClearEpoch == PresentEpoch &&
                R20DepthClearDrawSerial == R9DrawCalls &&
                R20DepthClearGeneration == R9MainDepthGeneration &&
                R9MonoDepth != nullptr;

            bool stencilSafe = true;
            if (StencilTestActive(device))
            {
                stencilSafe =
                    R20StencilClearEpoch == PresentEpoch &&
                    R20StencilClearDrawSerial == R9DrawCalls &&
                    R20StencilClearGeneration == R9MainDepthGeneration;
            }

            const bool safe = depthSafe && stencilSafe;
            if (!safe)
                ++R20DepthGateRejects;
            return safe;
        }

        bool R20BuildCompleteColorBaseline(IDirect3DDevice9* device) noexcept
        {
            if (!device || !BackBuffer || !RightEyeSurface || !R9MonoSurface)
                return false;

            InternalPassScope guard;
            const HRESULT rightHr = device->StretchRect(
                BackBuffer, nullptr, RightEyeSurface, nullptr, D3DTEXF_NONE);
            const HRESULT monoHr = SUCCEEDED(rightHr)
                ? device->StretchRect(
                    BackBuffer, nullptr, R9MonoSurface, nullptr, D3DTEXF_NONE)
                : rightHr;
            if (FAILED(rightHr) || FAILED(monoHr))
            {
                ++R20BaselineCopyFailures;
                return false;
            }
            return true;
        }

        HRESULT __stdcall ClearDestR20(IDirect3DDevice9* device, DWORD count,
            const D3DRECT* rects, DWORD flags, D3DCOLOR color, float z,
            DWORD stencil)
        {
            const HRESULT hr = R20ClearR9Hook.stdcall<HRESULT>(
                device, count, rects, flags, color, z, stencil);

            R20ObserveFullDepthSeed(device, count, rects, flags, hr);

            // A stale/dead host is a game-local eligibility decision. R9 may
            // have provisionally seeded from a full clear before this wrapper
            // regains control, so explicitly cancel both seeds. The real game
            // backbuffer remains authoritative and subsequent draws stay mono.
            if (!R20StereoEligibilityGate.load(std::memory_order_acquire))
            {
                R9StereoSeeded = false;
                R9MonoSeeded = false;
                return hr;
            }

            if (FAILED(hr) || !R20BootstrapReady.load(std::memory_order_acquire) ||
                !IsGameDevice(device) || InternalStereoPass ||
                (flags & D3DCLEAR_TARGET) == 0 || R9StereoSeeded)
                return hr;

            // ClearDestR9 has already executed the game clear, mono-shadow
            // clear and legacy eye clear before control returns here.
            if (!StereoWanted() || !TargetIsBackBuffer() || R9DeferredDepth ||
                !R9CurrentDepthCanMirror() || !R9MonoSurface ||
                R9MonoBackupGap || FrameStereoIncomplete ||
                FrameFailureReason != OutRunVR::StereoFailureNone)
                return hr;

            // If depth/stencil exists, each required buffer must have a full
            // clear in this Present, in the current depth generation, with no
            // draw since that clear. Z and stencil may be separate clear calls
            // only when no draw occurs between either clear and this seed.
            if (!R20DepthHistorySafeForRelaxedSeed(device))
                return hr;

            // A rect/scissored color clear alone does not make a newly-created
            // mono RT complete. Snapshot the whole current backbuffer into both
            // the right eye and mono safety shadow first. Any earlier color
            // content becomes zero-disparity rather than missing/uninitialized.
            if (!R20BuildCompleteColorBaseline(device))
            {
                R9MonoBackupGap = true;
                R9Poison(OutRunVR::StereoFailureResourceUnavailable,
                    "R20/bootstrap-color-baseline");
                return hr;
            }

            R9StereoSeeded = true;
            R9MonoSeeded = true;
            R9MonoBackupGap = false;
            ++R20RelaxedSeeds;

            if (TrackedDepthStencil)
            {
                // The verified full clear plus no-intervening-draw gate proves
                // the three depth histories share a baseline. Start a new
                // diagnostic serial epoch instead of double-counting this clear.
                std::uint64_t baseline = std::max(
                    R9MainDepthContentSerial, R9MonoDepthContentSerial);
                if (++baseline == 0)
                    baseline = 1;
                R9MainDepthContentSerial = baseline;
                R9MonoDepthContentSerial = baseline;
                RightDepthSynchronized = true;
                if (StencilTestActive(device))
                    RightStencilSynchronized = true;
            }

            if (!R20FirstRelaxedSeedLogged)
            {
                R20FirstRelaxedSeedLogged = true;
                spdlog::info(
                    "VR R20: relaxed color bootstrap SAFE; complete backbuffer baseline copied to right+mono and per-buffer depth/stencil clear generation/draw-serial gates passed (rectCount={}, flags=0x{:08x})",
                    count, static_cast<unsigned>(flags));
            }
            return hr;
        }

        DWORD WINAPI R20InstallThread(void*)
        {
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const std::uint32_t r9 =
                    R9InstallState.load(std::memory_order_acquire);
                const std::uint32_t r13 =
                    R13InstallState.load(std::memory_order_acquire);

                if (r9 == R9InstallFailed || r13 == R13InstallFailed)
                {
                    spdlog::error(
                        "VR R20: base R9/R13 transaction failed; relaxed bootstrap not installed");
                    return 0;
                }

                if (r9 == R9InstallReady && r13 == R13InstallReady)
                {
                    R20ClearR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ClearDestR9), ClearDestR20);
                    if (!R20ClearR9Hook)
                    {
                        spdlog::error(
                            "VR R20: failed to hook R9 clear bootstrap; base fail-closed policy remains active");
                        return 0;
                    }
                    R20BootstrapReady.store(true, std::memory_order_release);
                    spdlog::info(
                        "VR R20 PRODUCTION: stereo bootstrap overlay ACTIVE; relaxed color seed requires complete right/mono baseline plus current-generation Z/stencil full clears with no intervening draw");
                    return 0;
                }
                Sleep(25);
            }

            spdlog::warn(
                "VR R20: timed out waiting for R9/R13 renderer transaction; bootstrap overlay not installed");
            return 0;
        }

        class VRProductionBootstrapR20Hook : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRProductionBootstrapR20";
            }

            bool validate() override { return true; }

            bool apply() override
            {
                HANDLE thread = CreateThread(
                    nullptr, 0, R20InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    spdlog::error(
                        "VR R20: failed to create bootstrap installer thread: {}",
                        GetLastError());
                    return false;
                }
                CloseHandle(thread);
                return true;
            }

            static VRProductionBootstrapR20Hook instance;
        };

        VRProductionBootstrapR20Hook VRProductionBootstrapR20Hook::instance;
    }
}
