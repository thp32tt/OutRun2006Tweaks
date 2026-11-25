#include <cassert>
#include <cmath>
#include <iostream>
#include "../src/vr/game/external_car_ground.hpp"
#include "../src/vr/game/dino_external_sidecar.hpp"
int main() {
    using OutRunVR::DinoSidecar::ComputeExternalFloorLift;
    float applied=-99.f;
    // Measured 2026-11-16 directly from the real delivered 3-car OVC ZIP.
    assert(ComputeExternalFloorLift(0.22f,-0.16723822f,applied));
    assert(std::fabs(applied-0.22f)<0.00001f);
    assert(ComputeExternalFloorLift(0.22f,-0.33408761f,applied));
    assert(std::fabs(applied-0.36908761f)<0.00002f);
    assert(ComputeExternalFloorLift(0.22f,-0.32695001f,applied));
    assert(std::fabs(applied-0.36195001f)<0.00002f);
    assert(ComputeExternalFloorLift(0.5f,-0.33f,applied));
    assert(std::fabs(applied-0.5f)<0.00002f); // user can lift further
    assert(!ComputeExternalFloorLift(0.22f,-1.9f,applied));
    assert(!ComputeExternalFloorLift(0.22f,0.5f,applied));
    assert(!ComputeExternalFloorLift(NAN,-0.33f,applied));
    assert(!ComputeExternalFloorLift(0.22f,NAN,applied));
    assert(!ComputeExternalFloorLift(100.f,-0.33f,applied));
    using namespace OutRunVR::DinoSidecar;
    for(unsigned slot=0;slot<16;++slot) {
        for(bool index32:{false,true}) {
            Mesh mesh{};
            mesh.index32=index32;
            mesh.vertices={{100.f,-100.f,100.f,0,1,0,0,0},
                           {0.f,-.3f,0.f,0,1,0,0,0},
                           {2.f,0.f,0.f,0,1,0,1,0},
                           {0.f,1.f,2.f,0,1,0,0,1}};
            mesh.indices={1,2,3};
            IndexedMeshBounds bounds{};
            assert(ComputeIndexedMeshBounds(mesh,bounds));
            assert(bounds.low[0]==0.f && bounds.low[1]==-.3f &&
                   bounds.low[2]==0.f && bounds.high[0]==2.f &&
                   bounds.high[1]==1.f && bounds.high[2]==2.f);
            assert(ComputeExternalFloorLift(.22f,bounds.low[1],applied));
            assert(std::fabs(applied-.335f)<.00001f);
            // Old whole-vertex bounds rejected this drawable car and
            // would move a glass centre to x=50 instead of x=1.
            assert(!ComputeExternalFloorLift(.22f,mesh.vertices[0].y,applied));
            assert((bounds.low[0]+bounds.high[0])*.5f==1.f);
            mesh.indices={0,2,3};
            assert(ComputeIndexedMeshBounds(mesh,bounds));
            assert(bounds.low[1]==-100.f && bounds.high[0]==100.f);
            assert(!ComputeExternalFloorLift(.22f,bounds.low[1],applied));
            const auto saved=bounds;
            mesh.indices={1,2,4};
            assert(!ComputeIndexedMeshBounds(mesh,bounds));
            assert(bounds.low==saved.low && bounds.high==saved.high);
            mesh.indices.clear();
            assert(!ComputeIndexedMeshBounds(mesh,bounds));
            mesh.indices={1,2,3};
            mesh.vertices[1].y=NAN;
            assert(!ComputeIndexedMeshBounds(mesh,bounds));
        }
    }
    std::cout<<"OVC_FLOOR_GUARD_PASS F50=0.22 F40=0.369088 288GTO=0.361950\n";
}
