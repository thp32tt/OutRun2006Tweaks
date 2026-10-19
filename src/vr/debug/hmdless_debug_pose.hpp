#pragma once
#include <cstdint>

// Renderer-only diagnostic pose selection. No OpenXR runtime, HMD, simulator
// process, IPC write, controller or camera-physics modification is required.
// HMD-less output is an SBS desktop preview, NEVER hardware validation.
namespace OutRunVR::HmdlessDebug
{
    struct PoseStep
    {
        float yawDegrees;
        float pitchDegrees;
        float xMeters;
        float yMeters;
        float zMeters;
    };

    constexpr bool Enabled(int mode) noexcept { return mode >= 1 && mode <= 8; }

    constexpr PoseStep SelectPose(int mode, std::uint32_t elapsedSeconds) noexcept
    {
        // Two seconds per station. The first station is deliberately neutral:
        // renderer recenter establishes a zero-yaw reference before sweeping.
        if (mode == 2)
        {
            switch ((elapsedSeconds / 2u) % 7u)
            {
            case 1: mode = 3; break;
            case 2: mode = 4; break;
            case 3: mode = 5; break;
            case 4: mode = 6; break;
            case 5: mode = 7; break;
            case 6: mode = 8; break;
            default: mode = 1; break;
            }
        }
        switch (mode)
        {
        case 3: return { 30.0f,  0.0f,  0.0f, 0.0f, 0.0f };
        case 4: return {-30.0f,  0.0f,  0.0f, 0.0f, 0.0f };
        case 5: return {  0.0f, 20.0f,  0.0f, 0.0f, 0.0f };
        case 6: return {  0.0f,-20.0f,  0.0f, 0.0f, 0.0f };
        case 7: return {  0.0f,  0.0f,  0.10f,0.0f, 0.0f };
        case 8: return {  0.0f,  0.0f, -0.10f,0.0f, 0.0f };
        default:return {  0.0f,  0.0f,  0.0f, 0.0f, 0.0f };
        }
    }

    // Compile-time positive/negative regressions, both fixed and sweep.
    static_assert(!Enabled(0) && !Enabled(-1) && !Enabled(9));
    static_assert(Enabled(1) && Enabled(2) && Enabled(8));
    static_assert(SelectPose(2, 0).yawDegrees == 0.0f);
    static_assert(SelectPose(2, 2).yawDegrees == 30.0f);
    static_assert(SelectPose(2, 4).yawDegrees == -30.0f);
    static_assert(SelectPose(2, 6).pitchDegrees == 20.0f);
    static_assert(SelectPose(2, 8).pitchDegrees == -20.0f);
    static_assert(SelectPose(2, 10).xMeters == 0.10f);
    static_assert(SelectPose(2, 12).xMeters == -0.10f);
    static_assert(SelectPose(2, 14).yawDegrees == 0.0f);
    static_assert(SelectPose(7, 0).xMeters == 0.10f);
    static_assert(SelectPose(0, 0).xMeters == 0.0f);
}
