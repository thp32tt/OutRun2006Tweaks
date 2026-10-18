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

    // R84 stage +TIME and GOAL sprite/glyph sources use GAME pixels.
    // Keep the source-to-NDC calculation in double precision: two finite
    // viewport endpoints can overflow float during the *intermediate*
    // (source-origin)*2 step, even when the final binocular pixel is valid.
    // Do not accept NaN/Inf, empty viewports or non-positive optical scale.
    inline bool SourcePixelNdc(
        float sourceX, float sourceY, float viewportX, float viewportY,
        float viewportWidth, float viewportHeight, float hudScale,
        double& nx, double& ny) noexcept
    {
        if (!std::isfinite(sourceX) || !std::isfinite(sourceY) ||
            !std::isfinite(viewportX) || !std::isfinite(viewportY) ||
            !std::isfinite(viewportWidth) || !std::isfinite(viewportHeight) ||
            !std::isfinite(hudScale) || viewportWidth <= 0.0f ||
            viewportHeight <= 0.0f || hudScale <= 0.0f)
            return false;
        const double x = ((static_cast<double>(sourceX) - viewportX) *
            2.0 / viewportWidth - 1.0) * hudScale;
        const double y = (1.0 - (static_cast<double>(sourceY) - viewportY) *
            2.0 / viewportHeight) * hudScale;
        if (!std::isfinite(x) || !std::isfinite(y))
            return false;
        nx = x;
        ny = y;
        return true;
    }

    // One native physical eye. Preserve the caller's previous values when
    // its clip W, matrix, destination float range or source is unprovable.
    inline bool ProjectNdcEye(
        const float clip[16], double nx, double ny,
        float vx, float vy, float vw, float vh,
        float& eyeX, float& eyeY) noexcept
    {
        if (!clip)
            return false;
        const double x = nx * clip[0] + ny * clip[4] + clip[12];
        const double y = nx * clip[1] + ny * clip[5] + clip[13];
        const double w = nx * clip[3] + ny * clip[7] + clip[15];
        if (!std::isfinite(x) || !std::isfinite(y) ||
            !std::isfinite(w) || w <= 1.0e-5)
            return false;
        const double projectedX = static_cast<double>(vx) +
            (x / w + 1.0) * 0.5 * vw;
        const double projectedY = static_cast<double>(vy) +
            (1.0 - y / w) * 0.5 * vh;
        if (!std::isfinite(projectedX) || !std::isfinite(projectedY))
            return false;
        const float outX = static_cast<float>(projectedX);
        const float outY = static_cast<float>(projectedY);
        if (!std::isfinite(outX) || !std::isfinite(outY))
            return false;
        eyeX = outX;
        eyeY = outY;
        return true;
    }

    inline bool ProjectPixel(
        const float clipFromGameNdc[16], float sourceX, float sourceY,
        float viewportX, float viewportY, float viewportWidth,
        float viewportHeight, float hudScale,
        float& eyeX, float& eyeY) noexcept
    {
        double nx = 0.0, ny = 0.0;
        if (!SourcePixelNdc(sourceX, sourceY, viewportX, viewportY,
                viewportWidth, viewportHeight, hudScale, nx, ny))
            return false;
        return ProjectNdcEye(clipFromGameNdc, nx, ny,
            viewportX, viewportY, viewportWidth, viewportHeight,
            eyeX, eyeY);
    }

    // Apply the ESC pause slider AFTER binocular projection, just like the
    // shader-backed option arrows. Never mix a partially adjusted left eye
    // with an unadjusted right eye, or let malformed viewport math publish.
    // All other HUD, GOAL and +TIME paths pass zero and remain unchanged.
    inline bool ApplyPostEyeVerticalShiftPair(
        float shiftPixels, float& leftY, float& rightY) noexcept
    {
        if (!std::isfinite(shiftPixels) ||
            !std::isfinite(leftY) || !std::isfinite(rightY))
            return false;
        const double shiftedLeft =
            static_cast<double>(leftY) + shiftPixels;
        const double shiftedRight =
            static_cast<double>(rightY) + shiftPixels;
        if (!std::isfinite(shiftedLeft) ||
            !std::isfinite(shiftedRight))
            return false;
        const float candidateLeft = static_cast<float>(shiftedLeft);
        const float candidateRight = static_cast<float>(shiftedRight);
        if (!std::isfinite(candidateLeft) ||
            !std::isfinite(candidateRight))
            return false;
        leftY = candidateLeft;
        rightY = candidateRight;
        return true;
    }

    // D3DX +TIME sprite and numeric glyphs, GOAL progress and result text
    // share a source pixel and a latched frame pose across both R84 eyes.
    // Convert pixel -> game NDC ONCE before applying the independently
    // canted eye projections. A failed eye publishes NEITHER output.
    inline bool ProjectPixelPair(
        const float leftClip[16], const float rightClip[16],
        float sourceX, float sourceY,
        float viewportX, float viewportY, float viewportWidth,
        float viewportHeight, float hudScale,
        float& leftX, float& leftY, float& rightX, float& rightY) noexcept
    {
        double nx = 0.0, ny = 0.0;
        if (!leftClip || !rightClip ||
            !SourcePixelNdc(sourceX, sourceY, viewportX, viewportY,
                viewportWidth, viewportHeight, hudScale, nx, ny))
            return false;
        float lx = 0.0f, ly = 0.0f, rx = 0.0f, ry = 0.0f;
        // +TIME's sprite and three numeric print callers must agree on
        // the SAME game NDC and both complete eye projections. Never
        // publish a successful LEFT when RIGHT fails (or vice versa).
        if (!ProjectNdcEye(leftClip, nx, ny, viewportX, viewportY,
                viewportWidth, viewportHeight, lx, ly) ||
            !ProjectNdcEye(rightClip, nx, ny, viewportX, viewportY,
                viewportWidth, viewportHeight, rx, ry))
            return false;
        leftX = lx; leftY = ly; rightX = rx; rightY = ry;
        return true;
    }

    // +TIME's native 2D sprite coordinates are independent of the XR
    // render-target size. Decode in the game's presentation viewport and
    // only THEN map both already-projected eyes to the physical RT viewport.
    // The input and all four outputs are transactional on error.
    inline bool ProjectPixelPairAcrossViewports(
        const float leftClip[16], const float rightClip[16],
        float x, float y, float sx, float sy, float sw, float sh,
        float dx, float dy, float dw, float dh, float scale,
        float& lx, float& ly, float& rx, float& ry) noexcept
    {
        if (!std::isfinite(dx) || !std::isfinite(dy) ||
            !std::isfinite(dw) || !std::isfinite(dh) ||
            dw <= 0.f || dh <= 0.f)
            return false;
        float a, b, c, d;
        if (!ProjectPixelPair(leftClip, rightClip, x, y,
                sx, sy, sw, sh, scale, a, b, c, d))
            return false;
        const double tx = static_cast<double>(dw) / sw;
        const double ty = static_cast<double>(dh) / sh;
        const double result[4]{
            double(dx) + (double(a) - sx) * tx,
            double(dy) + (double(b) - sy) * ty,
            double(dx) + (double(c) - sx) * tx,
            double(dy) + (double(d) - sy) * ty };
        float out[4]{};
        for (unsigned i = 0; i < 4; ++i)
        {
            if (!std::isfinite(result[i]))
                return false;
            out[i] = static_cast<float>(result[i]);
            if (!std::isfinite(out[i]))
                return false;
        }
        lx = out[0]; ly = out[1]; rx = out[2]; ry = out[3];
        return true;
    }
}
