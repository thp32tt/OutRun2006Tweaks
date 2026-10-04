// R34 compatibility readiness observer.
//
// The former R34 Reset/Present/draw detour layer has been folded into the R33
// final dispatcher. R33 now owns the functional install state and replay-health
// synchronization. R34 only preserves the historical async hook/reporting
// surface by observing R33; it owns no D3D9 hooks and no duplicate install
// state.

#include "stereo_renderer_r33.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        DWORD WINAPI R34InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r33 = R33InstallStatus();
                if (r33 == State::Failed)
                {
                    HookManager::ReportAsyncResult(
                        "OpenXRVRStereoR34ResetGuard", false);
                    return 0;
                }

                if (r33 == State::Ready)
                {
                    IDirect3DDevice9* const installedDevice =
                        StereoInstalledDevice.load(std::memory_order_acquire);
                    if (installedDevice)
                        R33SynchronizeResetReplayGuardState(installedDevice);

                    HookManager::ReportAsyncResult(
                        "OpenXRVRStereoR34ResetGuard", true);
                    spdlog::info(
                        "VR R34 OBSERVER: R33 owns ResetEx replay-health/raster readiness; no R34 D3D9 detours or duplicate install state");
                    return 0;
                }
                Sleep(25);
            }

            HookManager::ReportAsyncResult(
                "OpenXRVRStereoR34ResetGuard", false);
            return 0;
        }

        class VRStereoR34ResetGuardHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR34ResetGuard";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(
                    nullptr, 0, R34InstallThread, nullptr, 0, nullptr);
                if (!thread)
                    return false;
                CloseHandle(thread);
                return true;
            }

            static VRStereoR34ResetGuardHook instance;
        };

        VRStereoR34ResetGuardHook VRStereoR34ResetGuardHook::instance;
    }
}
