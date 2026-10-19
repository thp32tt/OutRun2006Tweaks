#pragma once
// A Windows borderless mirror WINDOW fit; never a D3D9Ex backbuffer resize
// or optical per-eye transform. Keep internal source/2D menu square pixels.
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace OutRunVRMirrorAspect {
struct Rect {
    int left = 0, top = 0, width = 0, height = 0;
    bool valid = false;
};
inline Rect Fit(int monitorW, int monitorH, int sourceW, int sourceH) noexcept
{
    if (monitorW <= 0 || monitorH <= 0 ||
        sourceW <= 0 || sourceH <= 0)
        return {};
    const double x = static_cast<double>(monitorW) / sourceW;
    const double y = static_cast<double>(monitorH) / sourceH;
    const double scale = (std::min)(x, y);
    if (!std::isfinite(scale) || scale <= 0.0)
        return {};
    const int width = std::clamp(
        static_cast<int>(std::round(sourceW * scale)), 1, monitorW);
    const int height = std::clamp(
        static_cast<int>(std::round(sourceH * scale)), 1, monitorH);
    return {(monitorW - width) / 2, (monitorH - height) / 2,
        width, height, true};
}
} // namespace OutRunVRMirrorAspect
