#pragma once

// Portable row-vector 4x4 homogeneous transform for the exact +TIME
// XYZRHW producer. The R84 caller constructs the finite HUD plane with
// its latched head inverse and both per-eye projection matrices.
#include <cmath>
#include <cstddef>
#include <cstdint>
#include "lens_centre_relative_eye_pose.hpp"

namespace OutRunVR::StageExtensionPlane
{
    // This flag is passed only after R30SeedTouchedXyzrhwVertices validated
    // the same index/mask list and copied exactly those source vertices.
    // Never choose the sparse path for an unseeded, mixed or dense draw.
    constexpr bool CanUseVerifiedTouchedVertices(
        std::uint32_t vertexCount, std::size_t touchedCount,
        bool hasMask, bool hasTouchedList, bool copiedFromTouched) noexcept
    {
        return hasMask && hasTouchedList && copiedFromTouched &&
            touchedCount != 0u && touchedCount <= vertexCount / 4u;
    }
    static_assert(CanUseVerifiedTouchedVertices(128u, 8u, true, true, true),
        "validated sparse +TIME/GOAL indices avoid a full VB-span walk");
    static_assert(!CanUseVerifiedTouchedVertices(128u, 8u, true, true, false),
        "mask-only copy cannot authorize a sparse GPU-eye transform");
    static_assert(!CanUseVerifiedTouchedVertices(128u, 8u, false, true, true),
        "unknown mask cannot prove original referenced coverage");
    static_assert(!CanUseVerifiedTouchedVertices(128u, 8u, true, false, true),
        "no authoritative touched list means the old full walk");
    static_assert(!CanUseVerifiedTouchedVertices(128u, 34u, true, true, true),
        "dense source stays on the verified original path");
    static_assert(!CanUseVerifiedTouchedVertices(0u, 0u, true, true, true),
        "empty or invalid span is never sparsely transformed");

    // Exact +TIME sprites, glyphs and shared GOAL eye-plane use the common
    // head inverse already supplied by R84; keep only HEAD-LOCAL per-eye
    // orientation (OpenXR cant) and relative IPD. Validate both or neither.
    inline bool BuildStageEyePoses(
        const float (&eyeOffsets)[2][3],
        const float (&eyeOrientations)[2][4],
        float worldScale,
        float (&relativeOffsets)[2][3],
        float (&relativeOrientations)[2][4]) noexcept
    {
        return std::isfinite(worldScale) && worldScale > 0.0f &&
            OutRunVR::LensCentre::BuildHeadRelativeEyePose(
                eyeOffsets, eyeOrientations,
                relativeOffsets, relativeOrientations);
    }

    inline bool ProjectPixel(
        const float clipFromGameNdc[16], float sourceX, float sourceY,
        float viewportX, float viewportY, float viewportWidth,
        float viewportHeight, float hudScale,
        float& eyeX, float& eyeY) noexcept
    {
        if (!clipFromGameNdc || !std::isfinite(sourceX) ||
            !std::isfinite(sourceY) || !std::isfinite(viewportX) ||
            !std::isfinite(viewportY) || !std::isfinite(viewportWidth) ||
            !std::isfinite(viewportHeight) || !std::isfinite(hudScale) ||
            viewportWidth <= 0.0f || viewportHeight <= 0.0f ||
            hudScale <= 0.0f)
            return false;
        const float nx = ((sourceX - viewportX) * 2.0f /
                          viewportWidth - 1.0f) * hudScale;
        const float ny = (1.0f - (sourceY - viewportY) * 2.0f /
                          viewportHeight) * hudScale;
        const float x = nx * clipFromGameNdc[0] +
            ny * clipFromGameNdc[4] + clipFromGameNdc[12];
        const float y = nx * clipFromGameNdc[1] +
            ny * clipFromGameNdc[5] + clipFromGameNdc[13];
        const float w = nx * clipFromGameNdc[3] +
            ny * clipFromGameNdc[7] + clipFromGameNdc[15];
        if (!std::isfinite(x) || !std::isfinite(y) ||
            !std::isfinite(w) || w <= 1.0e-5f)
            return false;
        const float newX = viewportX + (x / w + 1.0f) *
            0.5f * viewportWidth;
        const float newY = viewportY + (1.0f - y / w) *
            0.5f * viewportHeight;
        if (!std::isfinite(newX) || !std::isfinite(newY))
            return false;
        eyeX = newX;
        eyeY = newY;
        return true;
    }
}
