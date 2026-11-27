#include "../src/vr/game/external_car_mesh_batch.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
using namespace OutRunVR::DinoSidecar;
static Mesh mesh(const char* name,unsigned material,bool wide=false){
    Mesh m{};m.name=name;m.material=material;m.index32=wide;
    m.vertices={{0,0,0,0,0,1,0,0},{1,0,0,0,0,1,1,0},{0,1,0,0,0,1,0,1}};
    m.indices={0,1,2};return m;
}
int main(){
    Model m{};m.highQuality=true;
    m.meshes={mesh("a",0),mesh("b",0),mesh("EXT_GLASS_FRONT",0),
        mesh("c",0),mesh("speed",0),mesh("d",0),mesh("e",0),mesh("f",1),
        mesh("g",1,true),mesh("h",1,true)};
    DashboardBinding bind{};bind.meshIndex=4;m.dashboardBindings={bind};
    m.vertices=30;m.triangles=10;
    const auto original=m;
    assert(BatchExternalOpaqueMeshes(m)==3);
    assert(m.meshes.size()==7&&m.dashboardBindings[0].meshIndex==3);
    assert(m.meshes[1].name=="EXT_GLASS_FRONT"&&m.meshes[3].name=="speed");
    assert(m.vertices==30&&m.triangles==10);
    unsigned old=0;
    for(const auto& b:m.meshes){
        const unsigned n=static_cast<unsigned>(b.vertices.size()/3);
        for(unsigned j=0;j<n;++j,++old){
            const auto& a=original.meshes[old];
            assert(a.material==b.material&&a.index32==b.index32);
            assert(std::memcmp(b.vertices.data()+3*j,a.vertices.data(),3*sizeof(Vertex))==0);
            for(unsigned k=0;k<3;++k)assert(b.indices[j*3+k]==a.indices[k]+3*j);
        }
    }
    assert(old==10&&BatchExternalOpaqueMeshes(m)==0);
    Model big{};big.highQuality=true;big.meshes={mesh("big",0),mesh("next",0)};
    big.meshes[0].vertices.resize(65534);
    assert(BatchExternalOpaqueMeshes(big)==0);
    Model legacy=original;legacy.highQuality=false;
    assert(BatchExternalOpaqueMeshes(legacy)==0&&legacy.meshes.size()==10);
    Model invalid=original;invalid.dashboardBindings[0].meshIndex=999;
    assert(BatchExternalOpaqueMeshes(invalid)==0&&invalid.meshes.size()==10);
    // Identical vertices from adjacent meshes can share one VB entry;
    // each triangle corner remains bit-identical, including signed zero.
    auto compact=m;const auto before=compact;
    const auto removed=DeduplicateExternalVertices(compact);
    assert(removed==9&&compact.vertices==21&&compact.triangles==10);
    for(unsigned i=0;i<compact.meshes.size();++i){
        const auto& a=before.meshes[i];const auto& b=compact.meshes[i];
        assert(a.indices.size()==b.indices.size()&&a.material==b.material&&
               a.name==b.name&&a.index32==b.index32);
        for(unsigned j=0;j<a.indices.size();++j)
            assert(std::memcmp(&a.vertices[a.indices[j]],&b.vertices[b.indices[j]],sizeof(Vertex))==0);
    }
    assert(compact.dashboardBindings[0].meshIndex==before.dashboardBindings[0].meshIndex);
    assert(DeduplicateExternalVertices(compact)==0);
    Model seam{};seam.highQuality=true;seam.vertices=6;seam.triangles=2;
    auto sm=mesh("seam",0);
    for(unsigned i=0;i<3;++i)sm.vertices.push_back(sm.vertices[i]);
    sm.vertices[3].u=.5f;sm.vertices[4].nx=.5f;sm.vertices[5].x=-0.f;
    sm.indices={0,1,2,3,4,5};seam.meshes.push_back(sm);
    assert(DeduplicateExternalVertices(seam)==0&&seam.vertices==6);
    std::cout<<"EXTERNAL_LOSSLESS_OPAQUE_BATCH_PASS\n";
}
