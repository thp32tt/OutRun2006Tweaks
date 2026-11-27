#include "../src/vr/game/external_car_dds_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>

int main() {
    using namespace OutRunVR::DinoSidecar;
    const std::array<std::uint8_t,16> ao{255,255,0,255,255,255,42,255,
                                       255,255,128,255,255,255,255,255};
    assert(IsAoOnlyBgraPixels(ao.data(),ao.size()));
    assert(!IsAoOnlyBgraPixels(ao.data(),ao.size()-1));
    assert(!IsAoOnlyBgraPixels(nullptr,ao.size()));
    for(unsigned i=0;i<ao.size();++i)if(i%4!=2){
        auto bad=ao;bad[i]=254;
        assert(!IsAoOnlyBgraPixels(bad.data(),bad.size()));
    }
    for(bool unlockOk:{false,true}){
        std::array<std::uint8_t,8> dst{};
        unsigned unlocks=0;
        assert(CopyAndUnlockDdsMip(dst.data(),4,ao.data(),2,8,
            [&](){++unlocks;return unlockOk;},true)==unlockOk);
        assert(unlocks==1&&(dst==std::array<std::uint8_t,8>{0,42,0,0,128,255,0,0}));
    }
    for(int pitch:{-1,0,1}){
        std::array<std::uint8_t,8> dst{};
        unsigned unlocks=0;
        assert(!CopyAndUnlockDdsMip(dst.data(),pitch,ao.data(),2,8,
            [&](){++unlocks;return true;},true));
        assert(unlocks==1&&(dst==std::array<std::uint8_t,8>{}));
    }
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
