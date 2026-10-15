#pragma once
// Native R84 Calc3D2D exact vehicle/rival rank marker eye-space mapping.
// Pure math for portable positive/negative regressions.
#include <cmath>
namespace OutRunVR::RankMarker
{
    struct StereoNdcShift
    {
        float baseX = 0.0f, baseY = 0.0f;
        float deltaX[2]{}, deltaY[2]{};
    };
    inline bool RemapScreenPoint(
        float sourceX, float sourceY, float viewportX, float viewportY,
        float viewportW, float viewportH, float markerScale,
        const StereoNdcShift& shift, int eye, float& outX, float& outY) noexcept
    {
        if (eye < 0 || eye > 1 || viewportW <= 0.0f || viewportH <= 0.0f ||
            !std::isfinite(sourceX) || !std::isfinite(sourceY) ||
            !std::isfinite(viewportX) || !std::isfinite(viewportY) ||
            !std::isfinite(viewportW) || !std::isfinite(viewportH) ||
            !std::isfinite(markerScale) ||
            markerScale <= 0.0f || markerScale > 2.0f ||
            !std::isfinite(shift.baseX) || !std::isfinite(shift.baseY) ||
            !std::isfinite(shift.deltaX[eye]) ||
            !std::isfinite(shift.deltaY[eye]))
            return false;
        const float ndcX = ((sourceX - viewportX) / viewportW) * 2.0f - 1.0f;
        const float ndcY = 1.0f - ((sourceY - viewportY) / viewportH) * 2.0f;
        const float mappedX = markerScale * ndcX + shift.deltaX[eye] +
            (1.0f - markerScale) * shift.baseX;
        const float mappedY = markerScale * ndcY + shift.deltaY[eye] +
            (1.0f - markerScale) * shift.baseY;
        outX = viewportX + (mappedX + 1.0f) * viewportW * 0.5f;
        outY = viewportY + (1.0f - mappedY) * viewportH * 0.5f;
        return std::isfinite(outX) && std::isfinite(outY);
    }
}
