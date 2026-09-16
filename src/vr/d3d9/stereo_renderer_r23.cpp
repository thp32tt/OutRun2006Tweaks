// R23 recovery hardening overlay.
//
// R22 already owns scissor preservation, original-game-state full-clear
// classification, common first-seed validation and fail-closed draw callbacks.
// R23 deliberately layers on top of that validated implementation instead of
// installing a second set of render-target/scissor hooks.
//
// The remaining recovery edge is subtle: after a host stall, the common
// RuntimeEligibility gate stays closed until a new safe color/depth baseline is
// observed. R22 correctly blocks stereo draws while the gate is closed, but its
// clear fast-path also bypasses R20. R23 allows ONLY clear callbacks through the
// R20/R22 baseline validator while HostFresh=true and RecoveryPending=true;
// draw callbacks remain blocked until BaselineVerified().

#include "stereo_renderer_r22.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R23ClearR22Hook{};
        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R23InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };
        std::uint64_t R23RecoveryClearPasses = 0;
        bool R23FirstRecoveryClearLogged = false;

        bool R23RecoveryNeedsBaseline() noexcept
        {
            return OutRunVR::RuntimeEligibility::SafetyOverlayReady.load(
                       std::memory_order_acquire) &&
                OutRunVR::RuntimeEligibility::HostFresh.load(
                       std::memory_order_acquire) &&
                OutRunVR::RuntimeEligibility::RecoveryPending.load(
                    std::memory_order_acquire) &&
                !OutRunVR::RuntimeEligibility::StereoAllowed.load(
                    std::memory_order_acquire);
        }

        HRESULT R23RunRecoveryClearThroughBaselinePolicy(
            IDirect3DDevice9* device, DWORD count, const D3DRECT* rects,
            DWORD flags, D3DCOLOR color, float z, DWORD stencil)
        {
            R22ReplayScope replay(device);
            if (!replay.stateValid)
            {
                R22FailClosedReplayState(
                    device, "R23/recovery-clear/scissor-capture");
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

            ++R23RecoveryClearPasses;
            if (!R23FirstRecoveryClearLogged)
            {
                R23FirstRecoveryClearLogged = true;
                spdlog::info(
                    "VR R23: host recovered; clear callbacks may establish a new R22/R20 verified baseline while stereo draws/WVP remain fail-closed");
            }
            return hr;
        }

        HRESULT __stdcall ClearDestR23(IDirect3DDevice9* device, DWORD count,
            const D3DRECT* rects, DWORD flags, D3DCOLOR color, float z,
            DWORD stencil)
        {
            if (IsGameDevice(device) && !InternalStereoPass &&
                R23RecoveryNeedsBaseline())
            {
                return R23RunRecoveryClearThroughBaselinePolicy(
                    device, count, rects, flags, color, z, stencil);
            }

            return R23ClearR22Hook.stdcall<HRESULT>(
                device, count, rects, flags, color, z, stencil);
        }

        DWORD WINAPI R23RecoveryInstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R23InstallState.store(State::Pending, std::memory_order_release);
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                if (R9InstallState.load(std::memory_order_acquire) == R9InstallFailed ||
                    R13InstallState.load(std::memory_order_acquire) == R13InstallFailed ||
                    OutRunVR::RuntimeEligibility::IsFailed(R20InstallState) ||
                    OutRunVR::RuntimeEligibility::IsFailed(R21InstallState) ||
                    OutRunVR::RuntimeEligibility::IsFailed(R22InstallState))
                {
                    R23InstallState.store(State::Failed, std::memory_order_release);
                    OutRunVR::RuntimeEligibility::MarkSafetyOverlayUnavailable();
                    R20StereoEligibilityGate.store(false,
                        std::memory_order_release);
                    spdlog::error(
                        "VR R23: prerequisite overlay FAILED; recovery guard remains fail-closed");
                    return 0;
                }

                if (OutRunVR::RuntimeEligibility::IsReady(R22InstallState))
                {
                    R23ClearR22Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ClearDestR22), ClearDestR23,
                        safetyhook::InlineHook::StartDisabled);
                    const bool enabled = R23ClearR22Hook &&
                        R23ClearR22Hook.enable().has_value();
                    if (!enabled)
                    {
                        R23ClearR22Hook = {};
                        R23InstallState.store(State::Failed, std::memory_order_release);
                        OutRunVR::RuntimeEligibility::MarkSafetyOverlayUnavailable();
                        R20StereoEligibilityGate.store(false,
                            std::memory_order_release);
                        spdlog::error(
                            "VR R23: failed to install recovery-clear baseline guard; stereo remains fail-closed");
                        return 0;
                    }

                    OutRunVR::RuntimeEligibility::MarkSafetyOverlayInstalled();
                    R20StereoEligibilityGate.store(false,
                        std::memory_order_release);
                    R23InstallState.store(State::Ready, std::memory_order_release);
                    spdlog::info(
                        "VR R23 GAME: R22 shadow-state policy retained; recovery-clear-only baseline reopening guard ACTIVE; safety overlay transaction READY");
                    return 0;
                }
                Sleep(25);
            }

            R23InstallState.store(State::Failed, std::memory_order_release);
            OutRunVR::RuntimeEligibility::MarkSafetyOverlayUnavailable();
            R20StereoEligibilityGate.store(false, std::memory_order_release);
            spdlog::error(
                "VR R23: timed out waiting for R22 safety overlay; stereo kept fail-closed");
            return 0;
        }

        class VRRecoveryBaselineR23Hook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRRecoveryBaselineR23";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R23InstallState.store(State::Pending, std::memory_order_release);
                OutRunVR::RuntimeEligibility::MarkSafetyOverlayUnavailable();
                R20StereoEligibilityGate.store(false,
                    std::memory_order_release);

                HANDLE thread = CreateThread(nullptr, 0,
                    R23RecoveryInstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R23InstallState.store(State::Failed, std::memory_order_release);
                    OutRunVR::RuntimeEligibility::MarkSafetyOverlayUnavailable();
                    R20StereoEligibilityGate.store(false,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRRecoveryBaselineR23Hook instance;
        };

        VRRecoveryBaselineR23Hook VRRecoveryBaselineR23Hook::instance;
    }
}
