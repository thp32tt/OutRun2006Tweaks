#include "../src/vr/game/external_car_dds_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>

int main() {
    using OutRunVR::DinoSidecar::CopyAndUnlockDdsMip;
    const std::array<std::uint8_t,8> src{1,2,3,4,5,6,7,8};
    for (bool unlockOk : {false,true}) {
        std::array<std::uint8_t,12> dst{};
        unsigned unlocks=0, published=0;
        if (CopyAndUnlockDdsMip(dst.data(),6,src.data(),2,4,
                [&]() noexcept {++unlocks;return unlockOk;})) ++published;
        assert(unlocks==1 && published==(unlockOk?1u:0u));
        assert((dst==std::array<std::uint8_t,12>{1,2,3,4,0,0,5,6,7,8,0,0}));
    }
    for (int pitch : {-1,0,3,6}) {
        for (bool nullBits : {false,true}) {
            if (pitch==6 && !nullBits) continue;
            std::array<std::uint8_t,12> dst{};
            unsigned unlocks=0;
            assert(!CopyAndUnlockDdsMip(nullBits?nullptr:dst.data(),pitch,
                src.data(),2,4,[&]() noexcept {++unlocks;return true;}));
            assert(unlocks==1);
            assert((dst==std::array<std::uint8_t,12>{}));
        }
    }
}
