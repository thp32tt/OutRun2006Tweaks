#pragma once
#include <cstdint>

namespace outrun::vr::dx11 {
// D3D11 pixel UAV slots and RTVs share one output-merger register namespace.
// Use the highest occupied RTV (including gaps) to select the first legal UAV
// slot. Querying both stages at slot zero when an RTV is bound is invalid.
struct NativeGameOmSlots {
    std::uint32_t rtvCount{};
    std::uint32_t uavStart{};
    std::uint32_t uavCount{};
    static constexpr std::uint32_t kOutputSlots = 8u;

    [[nodiscard]] static constexpr NativeGameOmSlots from_rtv_mask(
        std::uint32_t mask) noexcept {
        std::uint32_t prefix = 0;
        for (std::uint32_t slot = 0; slot < kOutputSlots; ++slot)
            if ((mask & (1u << slot)) != 0u) prefix = slot + 1u;
        return {prefix, prefix, kOutputSlots - prefix};
    }
    [[nodiscard]] constexpr bool valid() const noexcept {
        return rtvCount <= kOutputSlots && uavStart >= rtvCount &&
               uavStart <= kOutputSlots && uavCount <= kOutputSlots-uavStart;
    }
};
static_assert(NativeGameOmSlots::from_rtv_mask(0).uavCount == 8);
static_assert(NativeGameOmSlots::from_rtv_mask(3).uavStart == 2);
static_assert(NativeGameOmSlots::from_rtv_mask(0x81).uavCount == 0);
} // namespace outrun::vr::dx11
