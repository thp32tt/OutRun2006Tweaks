// R34 final ResetEx replay health guard.
//
// R33 remains the draw/Reset implementation owner. R34 only adds the final
// compatibility boundary required by the R15 Ex overlay: a successful ResetEx
// is not enough to resume stereo if classic D3D9 state replay was incomplete.
// While that condition is active, every Present keeps the shared eligibility
// state fail-closed so a later baseline cannot accidentally re-enable stereo on
// stale ResetEx state. A later clean Reset clears the block.

#include "stereo_renderer_r33.cpp"

namespace OutRunVRD3D9ExUpgradeR13
{
    bool LastResetStateReplaySucceeded() noexcept;
}

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R34ResetR33Hook{};
        SafetyHookInline R34PresentR33Hook{};
        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R34InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };
        std::atomic<bool> R34ResetReplayBlocked{false};
        std::uint64_t R34ReplayBlocks = 0;
        bool R34FirstReplayBlockLogged = false;

        void R34ForceResetReplayFailClosed(IDirect3DDevice9* device,
            const char* site) noexcept
        {
            if (!device || !IsGameDevice(device))
                return;

            OutRunVR::RuntimeEligibility::SetExternalSafetyBlock(true);
            R22FailClosedEligibility();
            R22ResetBaselineTracking();
            R22ShadowState = {};
            R33InvalidateDepthStencilCache();
            R29ArmMonoSafety();
            RightDepthSynchronized = false;
            RightStencilSynchronized = false;

            if (!R34FirstReplayBlockLogged)
            {
                R34FirstReplayBlockLogged = true;
                spdlog::error(
                    "VR R34 RESET: classic D3D9 state replay is unhealthy at {}; stereo remains fail-closed until a later clean ResetEx replay",
                    site ? site : "unknown");
            }
        }

        HRESULT __stdcall ResetDestR34(IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            const bool gameDevice = IsGameDevice(device);
            const HRESULT hr = R34ResetR33Hook.stdcall<HRESULT>(device, params);

            if (!gameDevice)
                return hr;

            if (!OutRunVRD3D9ExUpgradeR13::IsCompatDevice(device))
            {
                R34ResetReplayBlocked.store(false, std::memory_order_release);
                OutRunVR::RuntimeEligibility::SetExternalSafetyBlock(false);
                return hr;
            }

            const bool healthy = SUCCEEDED(hr) &&
                OutRunVRD3D9ExUpgradeR13::LastResetStateReplaySucceeded();
            R34ResetReplayBlocked.store(!healthy, std::memory_order_release);
            OutRunVR::RuntimeEligibility::SetExternalSafetyBlock(!healthy);
            if (!healthy)
            {
                ++R34ReplayBlocks;
                R34ForceResetReplayFailClosed(device, "Reset");
            }
            return hr;
        }

        HRESULT __stdcall PresentDestR34(IDirect3DDevice9* device,
            const RECT* sourceRect, const RECT* destRect,
            HWND destWindowOverride, const RGNDATA* dirtyRegion)
        {
            const bool blocked = IsGameDevice(device) &&
                R34ResetReplayBlocked.load(std::memory_order_acquire);
            if (blocked)
                R34ForceResetReplayFailClosed(device, "Present/pre");

            const HRESULT hr = R34PresentR33Hook.stdcall<HRESULT>(device,
                sourceRect, destRect, destWindowOverride, dirtyRegion);

            if (blocked)
                R34ForceResetReplayFailClosed(device, "Present/post");
            return hr;
        }

        void R34RollbackHooks() noexcept
        {
            R34PresentR33Hook = {};
            R34ResetR33Hook = {};
        }

        bool R34EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R34ResetR33Hook,
                &R34PresentR33Hook
            };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                    return false;
            }
            return true;
        }

        DWORD WINAPI R34InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R34InstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r33 = R33InstallState.load(std::memory_order_acquire);
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
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R34ResetR33Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR33),
                        ResetDestR34, disabled);
                    R34PresentR33Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&PresentDestR33),
                        PresentDestR34, disabled);

                    if (!R34EnableHooks())
                    {
                        R34RollbackHooks();
                        R34InstallState.store(State::Failed,
                            std::memory_order_release);
                        HookManager::ReportAsyncResult(
                            "OpenXRVRStereoR34ResetGuard", false);
                        spdlog::error(
                            "VR R34: Reset/Present guard transaction failed; R33 remains authoritative");
                        return 0;
                    }

                    IDirect3DDevice9* const installedDevice =
                        StereoInstalledDevice.load(std::memory_order_acquire);
                    if (installedDevice &&
                        OutRunVRD3D9ExUpgradeR13::IsCompatDevice(installedDevice))
                    {
                        const bool healthy =
                            OutRunVRD3D9ExUpgradeR13::LastResetStateReplaySucceeded();
                        R34ResetReplayBlocked.store(!healthy,
                            std::memory_order_release);
                        OutRunVR::RuntimeEligibility::SetExternalSafetyBlock(
                            !healthy);
                        if (!healthy)
                            R34ForceResetReplayFailClosed(
                                installedDevice, "Install/state-sync");
                    }

                    R34InstallState.store(State::Ready,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult(
                        "OpenXRVRStereoR34ResetGuard", true);
                    spdlog::info(
                        "VR R34 RESET GUARD: R15 classic-state replay health now gates post-Reset stereo eligibility");
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
