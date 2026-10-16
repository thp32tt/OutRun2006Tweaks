#pragma once

#include <array>
#include <cmath>

namespace OutRunVR::QuestStereoCull
{
    struct EyeSpaceSphere
    {
        float right{};
        float up{};
        float depth{};
    };

    // The eye-space sphere centre is provided independently for each XR eye.
    // Tangents and plane norms are cached once per valid pose/frame rather
    // than recomputing eight tanf calls per visible game object.
    struct Frustum
    {
        float left{}, right{}, down{}, up{};
        float nearZ{}, farZ{};
        float leftNorm{}, rightNorm{}, downNorm{}, upNorm{};
    };

    inline bool Build(float leftAngle, float rightAngle,
        float downAngle, float upAngle, float nearZ, float farZ,
        Frustum& output) noexcept
    {
        Frustum candidate{};
        candidate.left = std::tan(leftAngle);
        candidate.right = std::tan(rightAngle);
        candidate.down = std::tan(downAngle);
        candidate.up = std::tan(upAngle);
        candidate.nearZ = nearZ;
        candidate.farZ = farZ;
        if (!std::isfinite(candidate.left) ||
            !std::isfinite(candidate.right) ||
            !std::isfinite(candidate.down) ||
            !std::isfinite(candidate.up) ||
            !(candidate.left < candidate.right) ||
            !(candidate.down < candidate.up) ||
            !std::isfinite(nearZ) || !std::isfinite(farZ) ||
            !(nearZ > 0.f) || !(farZ > nearZ))
            return false;

        // Use double intermediates in the frustum coefficients: extreme
        // but finite inputs must not silently overflow a normal to Inf.
        const auto normal = [](float t) {
            return std::sqrt(1.0 + double(t) * double(t));
        };
        const double norms[4] = {
            normal(candidate.left), normal(candidate.right),
            normal(candidate.down), normal(candidate.up)};
        for (double n : norms)
            if (!std::isfinite(n) || n > double(3.402823466e38f))
                return false;
        candidate.leftNorm = float(norms[0]);
        candidate.rightNorm = float(norms[1]);
        candidate.downNorm = float(norms[2]);
        candidate.upNorm = float(norms[3]);
        output = candidate;
        return true;
    }

    // Eye local: +right, +up, +depth (forward). Caller must compute real
    // per-eye world->view transform; do not feed original game 2D Sphere*.
    // Fail OPEN on invalid XR input so an invalid pose never deletes a road.
    inline bool Visible(const Frustum& f, EyeSpaceSphere p,
        float radius) noexcept
    {
        if (!std::isfinite(p.right) || !std::isfinite(p.up) ||
            !std::isfinite(p.depth) || !std::isfinite(radius) ||
            radius < 0.f ||
            !(f.left < f.right) || !(f.down < f.up) ||
            !std::isfinite(f.leftNorm) || !std::isfinite(f.rightNorm) ||
            !std::isfinite(f.downNorm) || !std::isfinite(f.upNorm) ||
            !std::isfinite(f.nearZ) || !std::isfinite(f.farZ) ||
            !(f.farZ > f.nearZ))
            return true;

        const double r = double(radius) + 0.1; // Quest culling margin
        const double x = p.right, y = p.up, z = p.depth;
        return z + r >= f.nearZ && z - r <= f.farZ &&
            x - z * f.left >= -r * f.leftNorm &&
            z * f.right - x >= -r * f.rightNorm &&
            y - z * f.down >= -r * f.downNorm &&
            z * f.up - y >= -r * f.upNorm;
    }

    inline bool EitherEyeVisible(const std::array<Frustum, 2>& f,
        const std::array<EyeSpaceSphere, 2>& perEyeCentre,
        float radius) noexcept
    {
        return Visible(f[0], perEyeCentre[0], radius) ||
               Visible(f[1], perEyeCentre[1], radius);
    }
}