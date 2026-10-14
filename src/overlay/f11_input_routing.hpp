#pragma once
// Portable F11 Win32 forwarding decision. The caller classifies messages
// without creating an ImGui dependency in this tested decision contract.
namespace OutRunF11Input
{
    constexpr bool ShouldForwardToImGui(bool shellVisible,
        bool bindingDialogVisible, bool legacyF11Key, bool focusTransition,
        bool notificationMouseCapture) noexcept
    {
        return shellVisible || bindingDialogVisible || legacyF11Key ||
            focusTransition || notificationMouseCapture;
    }

    static_assert(!ShouldForwardToImGui(false, false, false, false, false),
        "Closed F11 must not intercept gameplay mouse/keyboard input");
    static_assert(ShouldForwardToImGui(true, false, false, false, false),
        "Open F11 must accept pointer and navigation");
    static_assert(ShouldForwardToImGui(false, true, false, false, false),
        "Binding dialog remains interactive");
    static_assert(ShouldForwardToImGui(false, false, true, false, false),
        "Legacy key release must open F11 from a closed frame");
    static_assert(ShouldForwardToImGui(false, false, false, true, false),
        "Focus loss must clear queued ImGui input");
    static_assert(ShouldForwardToImGui(false, false, false, false, true),
        "Interactive notification HUD remains clickable without F11");
}
