// R34 compatibility readiness observer.
//
// The former R34 Reset/Present/draw detour layer has been folded into the R33
// final dispatcher. R33 owns the functional install state, initial replay-health
// synchronization, and terminal Ready/Failed publication. R34 preserves only
// the historical HookManager status surface; it owns no D3D9 hooks, duplicate
// install state, polling loop, or worker thread.

#include "stereo_renderer_r33.cpp"

namespace OutRunVRStereo
{
    namespace
    {
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
                using State = OutRunVR::RuntimeEligibility::InstallState;
                const auto r33 = R33InstallStatus();
                if (r33 == State::Failed)
                    return false;

                if (r33 == State::Ready)
                {
                    spdlog::info(
                        "VR R34 OBSERVER: R33 already owns ready replay-health/raster state; no R34 worker or D3D9 detours");
                }
                else
                {
                    spdlog::info(
                        "VR R34 OBSERVER: R33 install pending; R33 owns terminal compatibility status publication with no R34 polling worker");
                }
                return true;
            }

            static VRStereoR34ResetGuardHook instance;
        };

        VRStereoR34ResetGuardHook VRStereoR34ResetGuardHook::instance;
    }
}
