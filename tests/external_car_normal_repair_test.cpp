#include "../src/vr/game/external_car_normal_repair.hpp"
#include <cassert>
#include <cmath>
using namespace OutRunVR::DinoSidecar;
static Model triangle(bool pbr=true) {
    Model m{};m.pbrEnabled=pbr;
    Mesh mesh{};
    mesh.vertices={{0,0,0,0,0,0,0,0},
                   {1,0,0,0,0,0,1,0},
                   {0,1,0,0,0,0,0,1}};
    mesh.indices={0,1,2};
    m.meshes.push_back(mesh);
    return m;
}
int main(){
    auto model=triangle();
    auto r=RepairExternalModelNormals(model);
    assert(r.repaired==3 && r.unresolved==0);
    for(const auto& v:model.meshes[0].vertices) {
        assert(v.nx==0 && v.ny==0 && v.nz==1);
    }
    assert(model.meshes[0].vertices[1].u==1); // UV invariant
    assert(model.meshes[0].indices[2]==2); // winding invariant
    assert(RepairExternalModelNormals(model).repaired==0); // idempotent
    auto legacy=triangle(false);
    r=RepairExternalModelNormals(legacy);
    assert(r.repaired==0 && legacy.meshes[0].vertices[0].nz==0);
    auto reversed=triangle();
    reversed.meshes[0].indices={0,2,1};
    r=RepairExternalModelNormals(reversed);
    assert(r.repaired==3 && reversed.meshes[0].vertices[2].nz==-1);
    auto mixed=triangle();
    mixed.meshes[0].vertices[0].nx=1; // keep a genuine imported normal
    r=RepairExternalModelNormals(mixed);
    assert(r.repaired==2 && mixed.meshes[0].vertices[0].nx==1);
    auto degenerate=triangle();
    degenerate.meshes[0].vertices[2].x=2;
    degenerate.meshes[0].vertices[2].y=0;
    r=RepairExternalModelNormals(degenerate);
    assert(r.repaired==0 && r.unresolved==3);
}
