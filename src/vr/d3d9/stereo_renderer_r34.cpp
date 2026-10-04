// R34 compatibility readiness ledger.
//
// The former R34 Reset/Present/draw detour layer has been folded into the R33
// final dispatcher. R34 remains only as a durable install/readiness checkpoint
// for the R15 ResetEx replay-health dependency. It installs no D3D9 hooks.
//
// Keeping the readiness object preserves the historical async hook/reporting
// contract while removing six physical inline detours from the runtime chain.

#include "stereo_renderer_r33.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R34InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        DWORD WINAPI R34InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R34InstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r33 = R33InstallStatus();
                if (r33 == State::Failed)
                {
                    R34InstallState.store(State::Failed,
                        std::memory_order_release);
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

                    R34InstallState.store(State::Ready,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult(
                        "OpenXRVRStereoR34ResetGuard", true);
                    spdlog::info(
                        "VR R34 READY: ResetEx replay-health/raster responsibilities are folded into the R33 final physical dispatcher; no R34 D3D9 detours installed");
                    return 0;
                }
                Sleep(25);
            }

            R34InstallState.store(State::Failed, std::memory_order_release);
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
                {
                    R34InstallState.store(
                        OutRunVR::RuntimeEligibility::InstallState::Failed,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }

            static VRStereoR34ResetGuardHook instance;
        };

        VRStereoR34ResetGuardHook VRStereoR34ResetGuardHook::instance;
    }
}
