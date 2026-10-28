#pragma once
// One authentic native GPU source capture per D3D9-owned Present epoch.
// Successful GPU Draw is the producer; later Present is only a consumer.
// Does not certify complete source coverage, stereo or gameplay activation.
#include <cstdint>
#include "native_game_raw_gpu_wait.hpp"

namespace outrun::vr::dx11 {
// Only an authenticated live game device clearing its own canonical color
// backbuffer may supersede RAW GPU pixels. RECT count/coverage is deliberately
// not required: a clipped TARGET Clear after the native Draw can replace any
// pixels in the sampled tile. An offscreen or foreign Clear cannot do so.
[[nodiscard]] constexpr bool native_raw_source_color_clear_matches(
    std::uintptr_t capturedDevice, std::uintptr_t clearingDevice,
    std::uintptr_t target, std::uintptr_t backbuffer,
    std::uint32_t targetWidth, std::uint32_t targetHeight,
    std::uint32_t backWidth, std::uint32_t backHeight) noexcept {
    return capturedDevice != 0u && capturedDevice == clearingDevice &&
           target != 0u && target == backbuffer &&
           targetWidth != 0u && targetHeight != 0u &&
           targetWidth == backWidth && targetHeight == backHeight;
}
// SOURCE writes other than Clear (successful ColorFill/StretchRect/UpdateSurface)
// supersede a queued native RGB tile under the same canonical backbuffer identity.
// A failed or empty operation has no source pixels to supersede.
[[nodiscard]] constexpr bool native_raw_source_color_write_matches(
    bool succeeded, bool nonempty,
    std::uintptr_t capturedDevice, std::uintptr_t writingDevice,
    std::uintptr_t target, std::uintptr_t backbuffer,
    std::uint32_t targetWidth, std::uint32_t targetHeight,
    std::uint32_t backWidth, std::uint32_t backHeight) noexcept {
    return succeeded && nonempty &&
        native_raw_source_color_clear_matches(
            capturedDevice, writingDevice, target, backbuffer,
            targetWidth, targetHeight, backWidth, backHeight);
}
// A native GPU BEFORE/AFTER pair samples only this bounded source tile.
// Authentic D3D9 rectangular color writes elsewhere in the game's canonical
// backbuffer do not erase pixels INSIDE the captured tile. Unknown, excessive
// or malformed source regions remain conservatively overlapping.
struct NativeRawSourcePixelRect {
    std::int64_t left, top, right, bottom;
};
[[nodiscard]] constexpr bool native_raw_source_write_overlaps_tile(
    std::uint32_t tileLeft, std::uint32_t tileTop,
    std::uint32_t tileRight, std::uint32_t tileBottom,
    const NativeRawSourcePixelRect* writes,
    std::uint32_t count) noexcept {
    if (tileRight <= tileLeft || tileBottom <= tileTop ||
        !writes || count == 0u || count > 32u) return true;
    for (std::uint32_t i = 0u; i < count; ++i) {
        const auto& r = writes[i];
        if (r.left < 0 || r.top < 0 ||
            r.right <= r.left || r.bottom <= r.top) return true;
        if (r.left < static_cast<std::int64_t>(tileRight) &&
            r.right > static_cast<std::int64_t>(tileLeft) &&
            r.top < static_cast<std::int64_t>(tileBottom) &&
            r.bottom > static_cast<std::int64_t>(tileTop))
            return true;
    }
    return false;
}
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
        invalidatedByClear_ = false;
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
    // A successful canonical TARGET Clear (whole or clipped) supersedes a
    // native Draw's sampled pixels inside the SAME D3D9 Present.
    // Retain the in-flight GPU staging fence.
    [[nodiscard]] bool invalidate_for_full_source_clear(
        bool gpuCopyPending) noexcept {
        const bool discarded = everQueued_ && unconsumed_;
        unconsumed_ = false;
        invalidatedByClear_ = gpuCopyPending && everQueued_;
        if (!gpuCopyPending) everQueued_ = false;
        return discarded;
    }
    [[nodiscard]] bool invalidated_for_full_source_clear() const noexcept {
        return invalidatedByClear_;
    }
    // Only event completion permits a fresh source-owned GPU capture after
    // a whole Clear. Never map or display superseded pre-Clear pixels.
    template <class Probe>
    [[nodiscard]] NativeRawGpuWaitResult retire_invalidated_source_clear(
        bool gpuCopyPending, Probe&& probe) noexcept {
        if (!invalidatedByClear_ || !gpuCopyPending)
            return NativeRawGpuWaitResult::Pending;
        const auto state = probe();
        if (state == NativeRawGpuWaitResult::Complete) {
            everQueued_ = false;
            unconsumed_ = false;
            invalidatedByClear_ = false;
        }
        return state;
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
    // A completed, RGB-inert source Draw can release its staging pair BEFORE
    // Present, allowing a later real Draw from the same source frame to be
    // captured. A pending fence or any true RGB delta forbids replacement.
    [[nodiscard]] bool retire_same_present_zero_rgb(
        std::uint64_t serial, bool copyPending, bool gpuComplete,
        bool rgbChanged) noexcept {
        if (!copyPending || !gpuComplete || rgbChanged || !unconsumed_ ||
            !everQueued_ || lastQueuedSerial_ != serial) return false;
        unconsumed_ = false;
        everQueued_ = false; // permit a fresh GPU pair for this serial only
        return true;
    }
    void reset() noexcept {
        lastQueuedSerial_ = 0u;
        everQueued_ = false;
        unconsumed_ = false;
        invalidatedByClear_ = false;
    }
private:
    std::uint64_t lastQueuedSerial_ = 0u;
    bool everQueued_ = false;
    bool unconsumed_ = false;
    bool invalidatedByClear_ = false;
};
} // namespace outrun::vr::dx11
