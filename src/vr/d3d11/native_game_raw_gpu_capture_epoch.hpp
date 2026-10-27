#pragma once
// One authentic native GPU source capture per D3D9-owned Present epoch.
// Successful GPU Draw is the producer; later Present is only a consumer.
// Does not certify complete source coverage, stereo or gameplay activation.
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11 {
class NativeRawGpuCaptureEpoch final {
public:
    [[nodiscard]] bool can_queue(std::uint64_t presentSerial,
                                 bool gpuCopyPending) const noexcept {
        return !gpuCopyPending && lastQueuedSerial_ != presentSerial;
    }
    void queued(std::uint64_t presentSerial) noexcept {
        lastQueuedSerial_ = presentSerial;
        unconsumed_ = true;
    }
    [[nodiscard]] bool consume() noexcept {
        const bool hadCopy = unconsumed_;
        unconsumed_ = false;
        return hadCopy;
    }
    void reset() noexcept {
        lastQueuedSerial_ = (std::numeric_limits<std::uint64_t>::max)();
        unconsumed_ = false;
    }
private:
    std::uint64_t lastQueuedSerial_ = (std::numeric_limits<std::uint64_t>::max)();
    bool unconsumed_ = false;
};
} // namespace outrun::vr::dx11
