#pragma once
// DirectGPU-only transport must reuse the last safe stereo projection when
// a new render frame was deferred. Publishing even a temporary mono frame
// before Present would erase the host's previous valid stereo metadata.
namespace OutRunVR::DirectGpuHold {
inline constexpr bool PublishPrePresentMono(bool stereoRequested,
    bool directTransport, bool directOnlyHold) noexcept {
    return stereoRequested && !directTransport && !directOnlyHold;
}
} // namespace OutRunVR::DirectGpuHold
