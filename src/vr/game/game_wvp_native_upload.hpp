#pragma once
#include <cstddef>
#include <cstdint>

// Normal game WVP injection must survive nested native D3D9 shader-constant
// callbacks. Each in-flight call owns independent rows until its native call
// returns. Keep the common path allocation-free and fail closed on overflow.
namespace OutRunVR::GameWvpNative {
constexpr std::size_t ScratchFrameCount = 4u;
constexpr std::size_t ScratchFloats = 256u * 4u;
struct ScratchBank {
    float rows[ScratchFrameCount][ScratchFloats]{};
    std::size_t depth = 0;
};
class ScopedFrame final {
public:
    explicit ScopedFrame(ScratchBank& bank) noexcept : bank_(bank) {
        if (bank_.depth < ScratchFrameCount) {
            index_ = bank_.depth;
            ++bank_.depth;
            acquired_ = true;
        }
    }
    ~ScopedFrame() {
        if (acquired_)
            --bank_.depth;
    }
    ScopedFrame(const ScopedFrame&) = delete;
    ScopedFrame& operator=(const ScopedFrame&) = delete;
    float* data() const noexcept {
        return acquired_ ? bank_.rows[index_] : nullptr;
    }
private:
    ScratchBank& bank_;
    std::size_t index_ = 0;
    bool acquired_ = false;
};
constexpr bool MayPublishReturnedWvp(bool nativeSucceeded,
    std::uint64_t enteredGeneration, std::uint64_t currentGeneration) noexcept {
    return nativeSucceeded && enteredGeneration != 0 &&
        enteredGeneration == currentGeneration;
}
} // namespace OutRunVR::GameWvpNative
