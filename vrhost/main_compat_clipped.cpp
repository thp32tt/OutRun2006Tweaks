// Thin compatibility wrapper around main_compat.cpp.
//
// Some OutRun borderless/fullscreen configurations report a client rectangle
// that extends a few pixels across an adjacent monitor. The mono diagnostic
// mirror only needs the portion visible on the monitor selected by
// MonitorFromWindow(), so clamp ClientToScreen() results to that monitor.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

static BOOL WINAPI OutRunClientToScreenClamped(HWND hwnd, LPPOINT point)
{
    if (!::ClientToScreen(hwnd, point))
        return FALSE;

    const HMONITOR monitor = ::MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
    MONITORINFO info{};
    info.cbSize = sizeof(info);
    if (!monitor || !::GetMonitorInfoW(monitor, &info))
        return TRUE;

    if (point->x < info.rcMonitor.left) point->x = info.rcMonitor.left;
    if (point->x > info.rcMonitor.right) point->x = info.rcMonitor.right;
    if (point->y < info.rcMonitor.top) point->y = info.rcMonitor.top;
    if (point->y > info.rcMonitor.bottom) point->y = info.rcMonitor.bottom;
    return TRUE;
}

#define ClientToScreen OutRunClientToScreenClamped
#include "main_compat.cpp"
