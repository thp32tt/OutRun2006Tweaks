#pragma once
// Source-owned pre/post D3D11 GPU color readback token. An aborted or
// mismatched native Draw may never donate a BEFORE snapshot to another Draw.
#include <cstdint>
namespace outrun::vr::dx11 {
class NativeRawDrawPair final {
public:
    void reset() noexcept {
        armed_ = false; presentSerial_ = 0u; color_ = nullptr;
    }
    void arm(std::uint64_t presentSerial, const void* nativeColor) noexcept {
        presentSerial_ = presentSerial;
        color_ = nativeColor;
        armed_ = nativeColor != nullptr;
    }
    [[nodiscard]] bool consume(std::uint64_t presentSerial,
                               const void* nativeColor) noexcept {
        const bool matched = armed_ && color_ == nativeColor &&
            presentSerial_ == presentSerial;
        reset(); // A mismatched source Draw always invalidates the pair.
        return matched;
    }
    [[nodiscard]] bool armed() const noexcept { return armed_; }
private:
    std::uint64_t presentSerial_ = 0u;
    const void* color_ = nullptr;
    bool armed_ = false;
};
} // namespace outrun::vr::dx11
