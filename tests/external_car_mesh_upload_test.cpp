#include "../src/vr/game/external_car_mesh_upload.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>

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
}
