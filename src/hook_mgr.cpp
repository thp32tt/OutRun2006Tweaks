#include "hook_mgr.hpp"
#include "plugin.hpp"

#include <cstdlib>
#include <cstring>


namespace
{
    // All VR-specific hooks, including those in the shared hooks_*.cpp files,
    // must be skipped when VR is disabled for this process.
    constexpr bool IsVrHookDescription(std::string_view description) noexcept
    {
        return description.starts_with("OpenXRVR") ||
            description.starts_with("OpenXVRR") ||
            description.starts_with("VR");
    }

    static_assert(IsVrHookDescription("OpenXRVRD3D9ExUpgrade"));
    static_assert(IsVrHookDescription("VRDriverSeatRenderTest"));
    static_assert(IsVrHookDescription("VRDriverSeatVehicleScaleRenderHook"));
    static_assert(IsVrHookDescription("VRLensFlareProjected2D"));
    static_assert(IsVrHookDescription("VRHudQueueSemanticBridge"));
    static_assert(!IsVrHookDescription("UIScaling"));

    bool VrHooksEnabledForProcess() noexcept
    {
        const char* forceDisabled = std::getenv("OUTRUN_VR_FORCE_DISABLED");
        if (forceDisabled && *forceDisabled &&
            (std::strcmp(forceDisabled, "1") == 0 ||
             _stricmp(forceDisabled, "true") == 0 ||
             _stricmp(forceDisabled, "on") == 0))
        {
            return false;
        }
        return Settings::VREnabled.get();
    }
}

Hook::Hook()
{
    HookManager::RegisterHook(this);
}

void HookManager::ApplyHooks()
{
    for (const auto& hook : hooks())
    {
        hook->declare_settings();

        // A validation failure is a failed installation, not an idle hook.
        // Reset stale async state before attempting a fresh installation.
        hook->is_active_.store(false, std::memory_order_release);
        hook->has_error_.store(false, std::memory_order_release);

        const auto desc = hook->description();
        if (IsVrHookDescription(desc) && !VrHooksEnabledForProcess())
        {
            if (!desc.empty())
                spdlog::info("{}: skipped because VR is disabled for this process", desc);
            continue;
        }

        if (!hook->validate())
        {
            hook->publish_status(false);
            if (!desc.empty())
                spdlog::error("{}: validation failed; hook not installed", desc);
            continue;
        }

        const bool active = hook->apply();
        hook->publish_status(active);
        if (!desc.empty())
        {
            spdlog::log(active ? spdlog::level::info : spdlog::level::err,
                "{}: apply {}", desc, active ? "successful" : "failed");
        }
    }
}

void HookManager::ReportAsyncResult(std::string_view description, bool active)
{
    if (description.empty())
        return;

    for (Hook* hook : hooks())
    {
        if (!hook || hook->description() != description)
            continue;
        hook->publish_status(active);
        spdlog::log(active ? spdlog::level::info : spdlog::level::err,
            "{}: async installer {}", description,
            active ? "ready" : "failed");
        return;
    }
}
