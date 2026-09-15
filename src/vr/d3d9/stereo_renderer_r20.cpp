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
// shadow, and (when depth/stencil is active) when a verified full depth/stencil
// clear occurred in this Present with no intervening draws.

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

        std::uint64_t R20DepthSeedEpoch = 0;
        std::uint64_t R20DrawCallsAtDepthSeed = 0;
        DWORD R20DepthSeedFlags = 0;

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

            if (R20DepthSeedEpoch != PresentEpoch)
            {
                R20DepthSeedEpoch = PresentEpoch;
                R20DepthSeedFlags = 0;
            }
            R20DepthSeedFlags |= depthFlags;
            R20DrawCallsAtDepthSeed = R9DrawCalls;
        }

        bool R20DepthHistorySafeForRelaxedSeed(IDirect3DDevice9* device) noexcept
        {
            if (!TrackedDepthStencil)
                return true;

            DWORD required = D3DCLEAR_ZBUFFER;
            if (StencilTestActive(device))
                required |= D3DCLEAR_STENCIL;

            const bool safe = R20DepthSeedEpoch == PresentEpoch &&
                (R20DepthSeedFlags & required) == required &&
                R20DrawCallsAtDepthSeed == R9DrawCalls &&
                R9MonoDepth != nullptr;
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

            // If depth/stencil exists, a full clear must have synchronized the
            // main/right/mono depth history after the last pre-seed draw. This
            // preserves R9's no-mid-frame-depth-divergence invariant.
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
                    "VR R20: relaxed color bootstrap SAFE; complete backbuffer baseline copied to right+mono and depth/stencil full-clear/no-intervening-draw gate passed (rectCount={}, flags=0x{:08x})",
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
                        "VR R20 PRODUCTION: stereo bootstrap overlay ACTIVE; relaxed color seed requires complete right/mono baseline plus full depth/stencil clear with no intervening draws");
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
