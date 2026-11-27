#include "../src/vr/game/external_car_dds_upload.hpp"
#include "../src/vr/game/external_car_texture_alias.hpp"
#include <array>
#include <cassert>
#include <cstdint>

int main() {
    using namespace OutRunVR::DinoSidecar;
    Model model{};
    Texture tx{};tx.width=4;tx.height=4;tx.mips=2;tx.dds={1,2,3,4,5,6};
    auto different=tx;different.dds.back()=9;
    auto extent=tx;extent.width=8;
    auto format=tx;format.format=TextureFormat::DXT5;
    model.textures={tx,tx,different,tx,extent,format};
    model.pbrMaterials.resize(6);
    model.pbrMaterials[0].normal=tx;model.pbrMaterials[2].normal=tx;
    model.pbrMaterials[0].orm=tx;model.pbrMaterials[3].orm=tx;
    const auto plan=BuildExternalTextureAliasPlan(model);
    assert((plan.albedo==std::vector<unsigned>{0,0,2,0,4,5}));
    assert((plan.normal==std::vector<unsigned>{0,1,0,3,4,5}));
    assert((plan.orm==std::vector<unsigned>{0,1,2,0,4,5}));
    int resource=5,other=7;
    std::vector<int*> owners{&resource,nullptr,&other,nullptr,nullptr,nullptr};
    assert(ResolveExternalTexture(owners,plan.albedo,3)==&resource);
    assert(ResolveExternalTexture(owners,plan.albedo,2)==&other);
    assert(!ResolveExternalTexture(owners,plan.albedo,6));
    auto invalid=plan.albedo;invalid[3]=1;
    assert(!ResolveExternalTexture(owners,invalid,3));
    owners.clear();
    assert(!ResolveExternalTexture(owners,plan.albedo,1));
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
