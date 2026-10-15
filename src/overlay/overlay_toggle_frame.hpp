#pragma once

// Poll once per EndScene before the F11 font atlas is chosen. Both the atlas
// and the later ImGui/cursor draw must consume the same visibility transition.
struct OverlayToggleFrame
{
    struct Decision { bool toggle; bool visible; };
    bool previousBoundHeld = false;

    Decision poll(bool boundHeld, bool legacyReleased, bool newInput,
                  bool bindingDialog, bool visible) noexcept
    {
        const bool edge = boundHeld && !previousBoundHeld;
        previousBoundHeld = boundHeld;
        const bool legacyEdge = !newInput && !bindingDialog && legacyReleased;
        const bool toggle = edge || legacyEdge;
        return { toggle, toggle ? !visible : visible };
    }
};
