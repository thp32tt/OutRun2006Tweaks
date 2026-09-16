#include "hook_mgr.hpp"

Hook::Hook()
{
    HookManager::RegisterHook(this);
}

void HookManager::ApplyHooks()
{
    for (const auto& hook : hooks())
    {
        hook->declare_settings();

        hook->is_active_.store(false, std::memory_order_release);
        hook->has_error_.store(false, std::memory_order_release);
        if (hook->validate())
        {
            const bool active = hook->apply();
            hook->is_active_.store(active, std::memory_order_release);
            hook->has_error_.store(!active, std::memory_order_release);

            const auto desc = hook->description();
            if (!desc.empty())
            {
                spdlog::log(active ? spdlog::level::info : spdlog::level::err,
                    "{}: apply {}", desc, active ? "successful" : "failed");
            }
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
        hook->is_active_.store(active, std::memory_order_release);
        hook->has_error_.store(!active, std::memory_order_release);
        spdlog::log(active ? spdlog::level::info : spdlog::level::err,
            "{}: async installer {}", description,
            active ? "ready" : "failed");
        return;
    }
}
