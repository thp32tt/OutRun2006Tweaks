#include "overlay/f11_responsive_fit.hpp"
#include "overlay/f11_input_routing.hpp"
#include <limits>
using OutRunF11ResponsiveFit::WindowRect;
using OutRunF11ResponsiveFit::ContainWindow;
int main()
{
    // In-bounds dragging never forces window recentering.
    const WindowRect xr{0,0,2496,2688};
    const auto steady=ContainWindow(xr,{450,540,1130,600},2400,2600);
    if (!steady.valid || steady.moved || steady.resized ||
        steady.rect.x!=450 || steady.rect.y!=540) return 1;
    // A dragged-out tab header and mouse hitbox recover on the next frame.
    const auto dragged=ContainWindow(xr,{-300,2530,1130,600},2400,2600);
    if (!dragged.valid || !dragged.moved || dragged.resized ||
        dragged.rect.x!=0 || dragged.rect.y!=2088) return 2;
    // Monitor/Reset transition: size and origin must BOTH recover.
    const auto huge=ContainWindow({240,0,1440,1080},
        {-100,400,2800,1600},1320,960);
    if (!huge.valid || !huge.resized || !huge.moved ||
        huge.rect.width!=1320 || huge.rect.height!=960 ||
        huge.rect.x!=240 || huge.rect.y!=120) return 3;
    const auto wide=ContainWindow({0,0,3440,1440},
        {3000,1000,1130,600},3350,1350);
    if (!wide.valid || wide.resized || !wide.moved ||
        wide.rect.x!=2310 || wide.rect.y!=840) return 4;
    const auto bad=ContainWindow(xr,{
        std::numeric_limits<float>::quiet_NaN(),0,1130,600},2400,2600);
    if (bad.valid || ContainWindow({0,0,0,200},{0,0,50,50},100,100).valid ||
        ContainWindow(xr,{0,0,100,100},0,100).valid ||
        ContainWindow(xr,{0,0,100,100},
            std::numeric_limits<float>::infinity(),100).valid) return 5;
    const auto native=ContainWindow({0,0,640,480},{12,20,400,300},600,440);
    if (!native.valid || native.moved || native.resized) return 6;
    // Real native WndProc event ownership: ImGui may return nonzero for
    // release, focus and Alt shortcuts, but original game/OS must still
    // receive all three. Other consumed ImGui UI input stays in the shell.
    using OutRunF11Input::MustPreserveOriginalWin32Path;
    for (int legacy = 0; legacy <= 1; ++legacy)
        for (int focus = 0; focus <= 1; ++focus)
            for (int system = 0; system <= 1; ++system)
                if (MustPreserveOriginalWin32Path(legacy, focus, system) !=
                    (legacy || focus || system)) return 7;
    if (!OutRunF11Input::ShouldConsumeFromGame(
            true, false, false, true, false, false) ||
        OutRunF11Input::ShouldConsumeFromGame(
            true, false, true, true, false, false) ||
        !OutRunF11Input::ShouldForwardToImGui(
            false, false, true, false, false)) return 8;
    return 0;
}
