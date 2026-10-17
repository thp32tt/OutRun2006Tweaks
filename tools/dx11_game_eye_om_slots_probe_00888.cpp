#include "../src/vr/d3d11/native_game_om_slots.hpp"
#include <cassert>
using outrun::vr::dx11::NativeGameOmSlots;
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
}
