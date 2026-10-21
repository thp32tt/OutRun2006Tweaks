#pragma once
// External F11 Dear ImGui is a SCREEN overlay, not a game HUD at -2.50 units.
// Map its original orthographic pixel->NDC projection to the common OpenXR
// angular rectangle. This uses only each eye's FOV, never HMD pose/IPD/world
// c64, so opening F11 cannot move it with the player's head or give it depth.
namespace OutRunVRF11Screen2D
{
    struct TangentBounds
    {
        float left, right, down, up;
    };
    struct EyeAffine
    {
        float scaleX = 1.f, offsetX = 0.f;
        float scaleY = 1.f, offsetY = 0.f;
    };

    // This portable contract is intentionally constexpr: the Windows R84
    // source compile exercises positive/negative geometry in every build.
    constexpr bool Bounded(float f) noexcept
    {
        return f >= -1000.f && f <= 1000.f; // rejects NaN/Inf too
    }
    constexpr float Abs(float f) noexcept { return f < 0.f ? -f : f; }

    constexpr bool Build(const TangentBounds (&fov)[2],
        EyeAffine (&out)[2]) noexcept
    {
        for (int eye = 0; eye != 2; ++eye)
        {
            if (!Bounded(fov[eye].left) || !Bounded(fov[eye].right) ||
                !Bounded(fov[eye].down) || !Bounded(fov[eye].up) ||
                fov[eye].right - fov[eye].left <= 0.05f ||
                fov[eye].up - fov[eye].down <= 0.05f)
                return false;
        }
        // Use the shared visible angular rectangle instead of averaging
        // independently asymmetric eye FOVs. The mean may place F11's
        // outer window beyond one eye's clip volume, which viewport scissor
        // clamping cannot restore. Invalid/empty intersections fail closed.
        const float commonLeft =
            fov[0].left > fov[1].left ? fov[0].left : fov[1].left;
        const float commonRight =
            fov[0].right < fov[1].right ? fov[0].right : fov[1].right;
        const float commonDown =
            fov[0].down > fov[1].down ? fov[0].down : fov[1].down;
        const float commonUp =
            fov[0].up < fov[1].up ? fov[0].up : fov[1].up;
        const float commonWidth = commonRight - commonLeft;
        const float commonHeight = commonUp - commonDown;
        if (!Bounded(commonWidth) || !Bounded(commonHeight) ||
            commonWidth <= 0.05f || commonHeight <= 0.05f)
            return false;

        EyeAffine candidate[2]{};
        for (int eye = 0; eye != 2; ++eye)
        {
            const float width = fov[eye].right - fov[eye].left;
            const float height = fov[eye].up - fov[eye].down;
            candidate[eye].scaleX = commonWidth / width;
            candidate[eye].offsetX =
                (commonLeft + commonRight -
                    fov[eye].left - fov[eye].right) / width;
            candidate[eye].scaleY = commonHeight / height;
            candidate[eye].offsetY =
                (commonDown + commonUp -
                    fov[eye].down - fov[eye].up) / height;
            if (!Bounded(candidate[eye].scaleX) ||
                !Bounded(candidate[eye].scaleY) ||
                !Bounded(candidate[eye].offsetX) ||
                !Bounded(candidate[eye].offsetY) ||
                candidate[eye].scaleX < 0.5f ||
                candidate[eye].scaleX > 1.5f ||
                candidate[eye].scaleY < 0.5f ||
                candidate[eye].scaleY > 1.5f ||
                Abs(candidate[eye].offsetX) > 0.5f ||
                Abs(candidate[eye].offsetY) > 0.5f)
                return false;
        }
        // Publish both eyes together; callers must never draw left only on
        // an invalid or stale right-eye FOV.
        out[0] = candidate[0];
        out[1] = candidate[1];
        return true;
    }

    constexpr bool TestEqualEyes() noexcept
    {
        constexpr TangentBounds bounds[2]{
            {-1.f, 1.f, -1.f, 1.f}, {-1.f, 1.f, -1.f, 1.f}};
        EyeAffine eyes[2]{};
        return Build(bounds, eyes) && eyes[0].scaleX == 1.f &&
            eyes[1].scaleY == 1.f && eyes[0].offsetX == 0.f &&
            eyes[1].offsetY == 0.f;
    }
    constexpr bool TestAsymmetricEyes() noexcept
    {
        constexpr TangentBounds bounds[2]{
            {-1.1f, 0.9f, -0.9f, 1.1f},
            {-0.9f, 1.1f, -1.1f, 0.9f}};
        EyeAffine eyes[2]{};
        return Build(bounds, eyes) &&
            eyes[0].offsetX > 0.f && eyes[1].offsetX < 0.f &&
            eyes[0].offsetY < 0.f && eyes[1].offsetY > 0.f &&
            Abs(eyes[0].scaleX - .9f) < .0001f &&
            Abs(eyes[1].scaleY - .9f) < .0001f;
    }
    constexpr bool TestInvalidRightKeepsBoth() noexcept
    {
        constexpr TangentBounds bounds[2]{
            {-1.f, 1.f, -1.f, 1.f}, {1.f, -1.f, -1.f, 1.f}};
        EyeAffine eyes[2]{{2.f, .25f, 2.f, .25f},
                           {3.f, .35f, 3.f, .35f}};
        return !Build(bounds, eyes) && eyes[0].scaleX == 2.f &&
            eyes[1].scaleX == 3.f;
    }
    constexpr bool TestIntersectionInsideBothEyes() noexcept
    {
        constexpr TangentBounds bounds[2]{
            {-1.1f, 0.9f, -0.9f, 1.1f},
            {-0.9f, 1.1f, -1.1f, 0.9f}};
        EyeAffine eyes[2]{};
        if (!Build(bounds, eyes))
            return false;
        // A normalized ImGui edge stays inside each actual eye's clip.
        for (int eye = 0; eye < 2; ++eye)
        {
            if (eyes[eye].offsetX - eyes[eye].scaleX < -1.0001f ||
                eyes[eye].offsetX + eyes[eye].scaleX > 1.0001f ||
                eyes[eye].offsetY - eyes[eye].scaleY < -1.0001f ||
                eyes[eye].offsetY + eyes[eye].scaleY > 1.0001f)
                return false;
        }
        return true;
    }
    constexpr bool TestDisjointEyesKeepBoth() noexcept
    {
        constexpr TangentBounds bounds[2]{
            {-1.f, -0.1f, -1.f, 1.f}, {0.1f, 1.f, -1.f, 1.f}};
        EyeAffine eyes[2]{{2.f, .25f, 2.f, .25f},
                           {3.f, .35f, 3.f, .35f}};
        return !Build(bounds, eyes) && eyes[0].scaleX == 2.f &&
            eyes[1].scaleX == 3.f;
    }
    static_assert(TestEqualEyes());
    static_assert(TestAsymmetricEyes());
    static_assert(TestInvalidRightKeepsBoth());
    static_assert(TestIntersectionInsideBothEyes());
    static_assert(TestDisjointEyesKeepBoth());
}
