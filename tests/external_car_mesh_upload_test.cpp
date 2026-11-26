#include "../src/vr/game/external_car_mesh_upload.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <initializer_list>

struct Buffer {
    bool lockOk=true, nullData=false, unlockOk=true;
    unsigned locks=0, copies=0, unlocks=0;
    std::uint32_t value=0;
    bool upload(std::uint32_t input) {
        return OutRunVR::DinoSidecar::UploadExternalMeshBuffer(
            [&](void** out) noexcept {
                ++locks;
                *out=nullData?nullptr:&value;
                return lockOk;
            },
            [&](void* data) noexcept {
                ++copies;
                std::memcpy(data,&input,sizeof(input));
            },
            [&]() noexcept {++unlocks;return unlockOk;});
    }
};

int main() {
    // All combinations for each of the vertex and index buffers.
    // The index upload may not run after a rejected vertex upload.
    for(unsigned v=0;v<8;++v)for(unsigned i=0;i<8;++i) {
        Buffer vb{bool(v&1),bool(v&2),bool(v&4)};
        Buffer ib{bool(i&1),bool(i&2),bool(i&4)};
        const bool vGood=vb.lockOk && !vb.nullData && vb.unlockOk;
        const bool iGood=ib.lockOk && !ib.nullData && ib.unlockOk;
        const bool published=vb.upload(123u) && ib.upload(456u);
        assert(published==(vGood && iGood));
        assert(vb.locks==1u);
        assert(vb.unlocks==unsigned(vb.lockOk));
        assert(vb.copies==unsigned(vb.lockOk && !vb.nullData));
        assert(vb.value==(vb.copies?123u:0u));
        assert(ib.locks==unsigned(vGood));
        assert(ib.unlocks==unsigned(vGood && ib.lockOk));
        assert(ib.copies==unsigned(vGood && ib.lockOk && !ib.nullData));
        assert(ib.value==(ib.copies?456u:0u));
    }
    // Actual upload helper: reset before Lock, inside Lock/Copy/Unlock.
    for(unsigned fault=0;fault<5;++fault){
        bool current=fault!=1;
        unsigned locks=0,copies=0,unlocks=0;
        std::uint32_t data=0;
        const bool ok=OutRunVR::DinoSidecar::UploadExternalMeshBuffer(
            [&](void** p){++locks;*p=&data;if(fault==2)current=false;return true;},
            [&](void* p){++copies;*static_cast<std::uint32_t*>(p)=5;if(fault==3)current=false;},
            [&](){++unlocks;if(fault==4)current=false;return true;},
            [&](){return current;});
        assert(ok==(fault==0));
        assert(locks==unsigned(fault!=1)&&unlocks==locks);
        assert(copies==unsigned(fault==0||fault==3||fault==4));
    }
    struct Resource {unsigned releases=0;void Release(){++releases;}};
    for(bool current:{false,true}){
        Resource resource;Resource* pending=&resource;Resource* published=nullptr;
        assert(OutRunVR::DinoSidecar::PublishExternalGpuResource(pending,
            [&](){return current;},[&](auto* p){published=p;})==current);
        assert(!pending&&resource.releases==unsigned(!current));
        assert(published==(current?&resource:nullptr));
    }
}
