#pragma once
// Portable F11 Win32 forwarding decision. The caller classifies messages
// without creating an ImGui dependency in this tested decision contract.
namespace OutRunF11Input
{
    // The Windows hardware cursor is a separate OS composition plane, not
    // part of the D3D9 game backbuffer replayed to the OpenXR stereo eyes.
    // Rasterize it inside ImGui's draw data only while the F11 shell is
    // visible during VR gameplay. Native desktop and closed F11 keep their
    // original hardware-cursor/game-input ownership.
    constexpr bool ShouldDrawSoftwareCursor(bool f11Visible,
        bool vrGameplay) noexcept
    {
        return f11Visible && vrGameplay;
    }

    static_assert(ShouldDrawSoftwareCursor(true, true),
        "Visible VR F11 must submit a backbuffer cursor to both XR eyes");
    static_assert(!ShouldDrawSoftwareCursor(true, false) &&
                  !ShouldDrawSoftwareCursor(false, true) &&
                  !ShouldDrawSoftwareCursor(false, false),
        "Desktop and closed F11 must not submit the VR cursor");

    constexpr bool ShouldForwardToImGui(bool shellVisible,
        bool bindingDialogVisible, bool legacyF11Key, bool focusTransition,
        bool notificationMouseCapture) noexcept
    {
        return shellVisible || bindingDialogVisible || legacyF11Key ||
            focusTransition || notificationMouseCapture;
    }

    // ImGui's Win32 backend commonly returns zero for keyboard and mouse
    // events even after enqueueing them. Forwarding them to the original
    // WndProc while F11 owns the UI leaks key/click/wheel input into racing.
    // Keep legacy F11 toggles in the original path and never intercept a
    // closed menu's gameplay input. Notification hit targets may own pointer
    // input independently of the F11 shell.
    constexpr bool ShouldConsumeFromGame(bool shellVisible,
        bool bindingDialogVisible, bool legacyF11Key,
        bool keyboardMessage, bool mouseMessage,
        bool notificationMouseCapture) noexcept
    {
        if (legacyF11Key)
            return false;
        const bool interactiveShell = shellVisible || bindingDialogVisible;
        return (interactiveShell && (keyboardMessage || mouseMessage)) ||
            (mouseMessage && notificationMouseCapture);
    }

    static_assert(ShouldConsumeFromGame(true, false, false, true, false, false),
        "F11 keyboard navigation must not reach original gameplay WndProc");
    static_assert(ShouldConsumeFromGame(true, false, false, false, true, false),
        "F11 pointer/wheel UI events must not reach game controls");
    static_assert(ShouldConsumeFromGame(false, true, false, true, false, false),
        "Open binding dialog owns its keyboard editing");
    static_assert(ShouldConsumeFromGame(false, false, false, false, true, true),
        "Clickable notification HUD owns its hovered pointer input");
    static_assert(!ShouldConsumeFromGame(true, false, true, true, false, false),
        "Legacy F11 toggle must reach the original game handler");
    static_assert(!ShouldConsumeFromGame(false, false, false, true, false, false) &&
                  !ShouldConsumeFromGame(false, false, false, false, true, false),
        "Closed F11 must not suppress gameplay controls");
    static_assert(!ShouldConsumeFromGame(true, false, false, false, false, false),
        "Focus and system messages must follow the original WndProc");

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
