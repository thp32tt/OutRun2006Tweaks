#include "../src/vr/d3d11/native_game_om_slots.hpp"
#include "../src/vr/d3d11/native_game_postpass_replay.hpp"
#include <cassert>
using outrun::vr::dx11::NativeGameOmSlots;
using outrun::vr::dx11::native_game_postpass_mip_extent;
using outrun::vr::dx11::native_game_postpass_source_box;
int main() {
    for (unsigned mask = 0; mask < 256; ++mask) {
        const auto slots = NativeGameOmSlots::from_rtv_mask(mask);
        assert(slots.valid());
        assert(slots.uavStart == slots.rtvCount);
        assert(slots.uavCount + slots.rtvCount == 8);
        for (unsigned i = 0; i < 8; ++i)
            if ((mask & (1u << i)) != 0u) assert(i < slots.uavStart);
    }
    const auto noRt = NativeGameOmSlots::from_rtv_mask(0);
    const auto twoRt = NativeGameOmSlots::from_rtv_mask(3);
    const auto sparseRt = NativeGameOmSlots::from_rtv_mask(0b00010001);
    const auto allRt = NativeGameOmSlots::from_rtv_mask(255);
    assert(noRt.rtvCount == 0 && noRt.uavCount == 8);
    assert(twoRt.rtvCount == 2 && twoRt.uavCount == 6);
    assert(sparseRt.rtvCount == 5 && sparseRt.uavCount == 3);
    assert(allRt.rtvCount == 8 && allRt.uavCount == 0);
    // Independent left/right camera slices in a mipmapped 16x8 source:
    // mip one is 8x4, and an oversized late-eye box fails *before* GPU work.
    constexpr auto left = native_game_postpass_mip_extent(16u,8u,4u,1u,2u,0u,1u);
    constexpr auto right = native_game_postpass_mip_extent(16u,8u,4u,1u,2u,1u,1u);
    static_assert(left.valid && right.valid && left.width == 8u && left.height == 4u);
    static_assert(native_game_postpass_source_box(16u,8u,4u,1u,2u,0u,1u,0u,0u,8u,4u).valid);
    static_assert(native_game_postpass_source_box(16u,8u,4u,1u,2u,1u,1u,2u,1u,8u,4u).valid);
    static_assert(!native_game_postpass_source_box(16u,8u,4u,1u,2u,1u,1u,0u,0u,16u,8u).valid);
    static_assert(!native_game_postpass_source_box(16u,8u,4u,1u,2u,1u,1u,2u,1u,9u,4u).valid);
    static_assert(!native_game_postpass_mip_extent(16u,8u,4u,1u,2u,2u,1u).valid);
    static_assert(!native_game_postpass_mip_extent(16u,8u,4u,4u,2u,0u,1u).valid);
    static_assert(!native_game_postpass_mip_extent(16u,8u,2u,0u,2u,1u,4u).valid);
    static_assert(!native_game_postpass_mip_extent(16u,8u,1u,0u,1u,0u,0u).valid);
    assert(left.width == right.width && left.height == right.height);
}
