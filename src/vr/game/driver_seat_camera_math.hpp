#pragma once

#include <cmath>
#include <cstdint>

namespace OutRunVR::DriverSeatCamera
{
    struct Vec3
    {
        float x{};
        float y{};
        float z{};
    };

    // Pure game-camera-space translation: never alters the native camera state.
    // Keep the established camera-relative right-axis convention for current
    // DriverSeatRight presets. Invalid camera poses/INI values fail closed.
    inline bool ComputeTranslation(Vec3 position, Vec3 look,
        float forward, float right, float up, Vec3& translation) noexcept
    {
        if (!std::isfinite(position.x) || !std::isfinite(position.y) ||
            !std::isfinite(position.z) || !std::isfinite(look.x) ||
            !std::isfinite(look.y) || !std::isfinite(look.z) ||
            !std::isfinite(forward) || !std::isfinite(right) ||
            !std::isfinite(up))
            return false;

        float fx = look.x - position.x;
        float fy = look.y - position.y;
        float fz = look.z - position.z;
        const float forwardLength = std::sqrt(fx * fx + fy * fy + fz * fz);
        if (!std::isfinite(forwardLength) || forwardLength < 1.0e-5f)
            return false;
        fx /= forwardLength;
        fy /= forwardLength;
        fz /= forwardLength;

        // Forward x world-up preserves the existing PCVR offset sign.
        // A vertical pole has no stable right axis. Fail closed rather than
        // hiding the driver with a mismatched camera.
        float rx = -fz;
        float rz = fx;
        const float rightLength = std::sqrt(rx * rx + rz * rz);
        if (!std::isfinite(rightLength) || rightLength < 1.0e-5f)
            return false;
        rx /= rightLength;
        rz /= rightLength;
        const float ux = -rz * fy;
        const float uy = rz * fx - rx * fz;
        const float uz = rx * fy;
        const Vec3 proposed{
            fx * forward + rx * right + ux * up,
            fy * forward + uy * up,
            fz * forward + rz * right + uz * up
        };
        if (!std::isfinite(proposed.x) || !std::isfinite(proposed.y) ||
            !std::isfinite(proposed.z))
            return false;
        translation = proposed;
        return true;
    }

    // The final absolute seat camera must also be finite. A finite native
    // position plus finite offset can overflow after arithmetic, leaving a
    // corrupted view matrix even though the camera passed delta validation.
    inline bool ComputeTranslatedCamera(Vec3 position, Vec3 look,
        float forward, float right, float up,
        Vec3& newPosition, Vec3& newLook) noexcept
    {
        Vec3 delta{};
        if (!ComputeTranslation(position, look, forward, right, up, delta))
            return false;
        const Vec3 p{position.x + delta.x, position.y + delta.y,
                     position.z + delta.z};
        const Vec3 q{look.x + delta.x, look.y + delta.y,
                     look.z + delta.z};
        if (!std::isfinite(p.x) || !std::isfinite(p.y) ||
            !std::isfinite(p.z) || !std::isfinite(q.x) ||
            !std::isfinite(q.y) || !std::isfinite(q.z))
            return false;
        newPosition = p;
        newLook = q;
        return true;
    }

    // Validate the actual user-selected depth plane before native 6DoF
    // cockpit and SceneEffect projection. std::clamp does not sanitize NaN.
    inline float SafeNearPlane(float requested, float minimum,
        float maximum, float fallback = 0.10f) noexcept
    {
        if (!std::isfinite(requested) || !std::isfinite(minimum) ||
            !std::isfinite(maximum) || !std::isfinite(fallback) ||
            !(minimum > 0.f) || !(maximum >= minimum))
            return 0.10f;
        const float boundedFallback = fallback < minimum ? minimum :
            (fallback > maximum ? maximum : fallback);
        if (!(requested > 0.f))
            return boundedFallback;
        return requested < minimum ? minimum :
            (requested > maximum ? maximum : requested);
    }

    // Canonical EXE RVA 0x84A40 uses camera+0x340 and +0x344 as
    // native mode-transition counters. Mode +0x34A may already equal the
    // selected bumper view while the original transition is still pending.
    // The independent legacy +0x364 timer check is retained below.
    inline bool NativeViewTransitionSettled(std::uint16_t switchTicks,
        std::uint16_t delayedSwitchTicks) noexcept
    {
        return switchTicks == 0 && delayedSwitchTicks == 0;
    }

    // The native +0x340/+0x344 counters are useful while ENTERING a camera
    // mode, but runtime evidence shows they can pulse again after the selected
    // bumper/in-car mode is already stable. Treating every pulse as a hard
    // per-frame veto alternates the synthetic seat view with the stock camera,
    // which appears as repeated zoom-in/zoom-out. Require one fully settled
    // sample to arm the selected mode, then keep that mode armed while the
    // authoritative legacy mode/timer/gameplay gate stays unchanged.
    // Any real mode/timer/gameplay transition clears the latch and requires a
    // new settled sample before the seat camera is re-enabled.
    inline bool StableNativeViewEligible(bool enabled, bool gameplayActive,
        float transitionTime, int nativeMode, int selectedMode,
        std::uint16_t switchTicks, std::uint16_t delayedSwitchTicks,
        bool& settledLatch) noexcept
    {
        const bool baseEligible =
            enabled && gameplayActive && nativeMode == selectedMode &&
            std::isfinite(transitionTime) && transitionTime == 0.0f;
        if (!baseEligible)
        {
            settledLatch = false;
            return false;
        }

        if (!settledLatch)
            settledLatch =
                NativeViewTransitionSettled(switchTicks, delayedSwitchTicks);
        return settledLatch;
    }

    // Separate the original game's camera-mode/transition gate from the
    // choice of mathematical pose basis. In a vertical loop the smoothed
    // native view has no horizontal right vector, although matrix_B0 still
    // supplies a valid car forward/up basis. Rejecting based on a *legacy*
    // basis before trying the car basis makes the cockpit disappear.
    inline bool NativeCameraModeEligible(bool enabled, bool gameplayActive,
        float transitionTime, int nativeMode, int selectedMode) noexcept
    {
        return enabled && gameplayActive && nativeMode == selectedMode &&
            std::isfinite(transitionTime) && transitionTime == 0.0f;
    }

    // Scope contract: cockpit near-plane, player-car model, driver suppression
    // and camera displacement must agree for the *same* native camera frame.
    // Re-evaluate after mode switches; never reuse a cached eligibility bit.
    inline bool CameraAndBodyEligible(
        bool enabled, bool gameplayActive, float transitionTime,
        int nativeMode, int selectedMode, Vec3 position, Vec3 look,
        float forward, float right, float up) noexcept
    {
        if (!NativeCameraModeEligible(enabled, gameplayActive, transitionTime,
                nativeMode, selectedMode))
            return false;
        Vec3 newPosition{}, newLook{};
        return ComputeTranslatedCamera(position, look, forward, right, up,
            newPosition, newLook);
    }

}