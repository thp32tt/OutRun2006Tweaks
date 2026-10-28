#pragma once
// One authentic native GPU source capture per D3D9-owned Present epoch.
// Successful GPU Draw is the producer; later Present is only a consumer.
// Does not certify complete source coverage, stereo or gameplay activation.
#include <cstdint>

namespace outrun::vr::dx11 {
class NativeRawGpuCaptureEpoch final {
public:
    [[nodiscard]] bool can_queue(std::uint64_t presentSerial,
                                 bool gpuCopyPending) const noexcept {
        return !gpuCopyPending &&
            (!everQueued_ || lastQueuedSerial_ != presentSerial);
    }
    void queued(std::uint64_t presentSerial) noexcept {
        lastQueuedSerial_ = presentSerial;
        everQueued_ = true;
        unconsumed_ = true;
    }
    // A GPU capture is valid only for its exact original game's Present
    // serial. Late GPU completion can retire staging but cannot publish it.
    [[nodiscard]] bool consume_for_present(std::uint64_t presentingSerial) noexcept {
        const bool matched = unconsumed_ && lastQueuedSerial_ == presentingSerial;
        unconsumed_ = false;
        return matched;
    }
    [[nodiscard]] bool consume() noexcept {
        const bool hadCopy = unconsumed_;
        unconsumed_ = false;
        return hadCopy;
    }
    void reset() noexcept {
        lastQueuedSerial_ = 0u;
        everQueued_ = false;
        unconsumed_ = false;
    }
private:
    std::uint64_t lastQueuedSerial_ = 0u;
    bool everQueued_ = false;
    bool unconsumed_ = false;
};
} // namespace outrun::vr::dx11
