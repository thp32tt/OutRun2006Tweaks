// R20 production stabilization wrapper.
//
// Keep the validated R13/R9 safety stack intact, but fix the bootstrap rule
// that could leave the RenderFrame ring permanently at frameId=0 on OutRun.
// R9 required a *full-screen* main-target color clear on every Present before
// any stereo draw could start. Real OutRun render paths can use a rect/scissored
// main color clear, so the safety shadow and both eyes were cleared identically
// but R9 still refused to mark the frame seeded.
//
// R20 accepts that already-replayed main-target color clear as a safe seed when
// all of the existing R9 safety conditions are still true: exact main depth,
// mono shadow available, no mono gap, no frame poison, and successful clear.
// MRT/occlusion/depth fail-closed behavior remains owned by R13/R9 unchanged.

#include "stereo_renderer_r13.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R20ClearR9Hook{};
        std::atomic<bool> R20BootstrapReady{false};
        bool R20FirstRelaxedSeedLogged = false;
        std::uint64_t R20RelaxedSeeds = 0;

        HRESULT __stdcall ClearDestR20(IDirect3DDevice9* device, DWORD count,
            const D3DRECT* rects, DWORD flags, D3DCOLOR color, float z,
            DWORD stencil)
        {
            const HRESULT hr = R20ClearR9Hook.stdcall<HRESULT>(
                device, count, rects, flags, color, z, stencil);

            if (FAILED(hr) || !R20BootstrapReady.load(std::memory_order_acquire) ||
                !IsGameDevice(device) || InternalStereoPass ||
                (flags & D3DCLEAR_TARGET) == 0 || R9StereoSeeded)
                return hr;

            // ClearDestR9 has already executed the game clear, the mono-shadow
            // clear and the legacy stereo clear before control returns here.
            // Promote only that successfully mirrored main-target clear.
            if (!StereoWanted() || !TargetIsBackBuffer() || R9DeferredDepth ||
                !R9CurrentDepthCanMirror() || !R9MonoSurface ||
                R9MonoBackupGap || FrameStereoIncomplete ||
                FrameFailureReason != OutRunVR::StereoFailureNone)
                return hr;

            R9StereoSeeded = true;
            R9MonoSeeded = true;
            R9MonoBackupGap = false;
            ++R20RelaxedSeeds;

            // Both main and mono depth/stencil received the same clear through
            // the existing R9 paths, so keep their history serials aligned.
            if ((flags & (D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL)) != 0)
            {
                ++R9MainDepthContentSerial;
                R9MonoDepthContentSerial = R9MainDepthContentSerial;
            }

            if (!R20FirstRelaxedSeedLogged)
            {
                R20FirstRelaxedSeedLogged = true;
                spdlog::info(
                    "VR R20: main-target color clear accepted as stereo bootstrap; full-screen-only R9 gate relaxed safely (rectCount={}, flags=0x{:08x})",
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
                        "VR R20 PRODUCTION: stereo bootstrap overlay ACTIVE; matched main-target color clear may seed R9 while mono/depth/MRT/occlusion safety remains enforced");
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
