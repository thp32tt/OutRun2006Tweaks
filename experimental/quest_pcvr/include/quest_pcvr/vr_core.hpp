#pragma once
#include <array>
#include <cstdint>

// New, independent portable behavior model informed by observed Quest VR semantics.
// No copied Android code, APK resources, rendering hooks, or OpenXR dependencies.
namespace quest_pcvr {
struct Vec3 { float x{}, y{}, z{}; };
struct Quaternion { float x{}, y{}, z{}, w{1.f}; };
struct Pose { Vec3 position{}; Quaternion orientation{}; };
struct Fov { float left{}, right{}, down{}, up{}; }; // OpenXR angular FOV, radians
struct EyeView { Pose pose{}; Fov fov{}; };
struct StereoViews {
    std::array<EyeView, 2> eyes{};
    float near_plane{0.05f};
    float far_plane{1000.f};
};

enum class Visibility : std::uint8_t { Culled, Visible, Unknown };
// The +0.1 world-unit expansion is a provisional Quest-observed behavior, NOT calibrated
// for a Windows game's world units. Only enable for PC after scale/camera A/B tests.
Visibility sphere_in_stereo(const StereoViews& view, Vec3 world_center,
                            float radius, float radius_margin = 0.1f) noexcept;
// Fail open for untrusted bounds/camera: never make scenery disappear on an unknown test.
bool should_render(Visibility result) noexcept;

struct EyeImageStamp {
    std::uint64_t generation{};
    std::uint64_t frame_id{};
    std::uint64_t pose_sample_id{};
    std::uint64_t target_identity{}; // unique session + swapchain + image resource identity
};
struct FrameSubmission {
    std::uint64_t generation{};
    std::uint64_t frame_id{};
    std::uint64_t pose_sample_id{};
    std::int64_t predicted_display_time_ns{};
    std::array<EyeImageStamp, 2> eyes{};
};
// Fail closed for GPU resource ownership: stale/one-eye/aliased resources are rejected.
bool valid_stereo_submission(const FrameSubmission& frame) noexcept;
}
