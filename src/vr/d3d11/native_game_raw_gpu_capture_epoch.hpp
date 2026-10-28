#pragma once
// One authentic native GPU source capture per D3D9-owned Present epoch.
// Successful GPU Draw is the producer; later Present is only a consumer.
// Does not certify complete source coverage, stereo or gameplay activation.
#include <cstdint>
#include "native_game_raw_gpu_wait.hpp"

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
    // The following game Present can reclaim an orphaned GPU copy only
    // after its D3D11 EVENT completes; never reuse previous-frame pixels.
    [[nodiscard]] bool previous_present_copy(std::uint64_t serial) const noexcept {
        return everQueued_ && lastQueuedSerial_ != serial;
    }
    template <class Probe>
    [[nodiscard]] NativeRawGpuWaitResult retire_previous_copy(
        std::uint64_t serial, bool copyPending, Probe&& probe) noexcept {
        if (!copyPending || !previous_present_copy(serial))
            return NativeRawGpuWaitResult::Pending; // do not poll current frame
        const auto state = probe();
        if (state == NativeRawGpuWaitResult::Complete)
            unconsumed_ = false; // orphaned copy cannot ever be published
        return state;
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
