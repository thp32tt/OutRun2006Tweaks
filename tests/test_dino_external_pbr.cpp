#include "src/vr/game/dino_external_sidecar.hpp"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <vector>
using namespace OutRunVR::DinoSidecar;
static void write32(std::vector<std::uint8_t>& b,std::size_t off,std::uint32_t v){
    for(unsigned i=0;i<4;++i)b[off+i]=std::uint8_t(v>>(8*i));
}
static void add32(std::vector<std::uint8_t>& b,std::uint32_t v){
    for(unsigned i=0;i<4;++i)b.push_back(std::uint8_t(v>>(8*i)));
}
static void add16(std::vector<std::uint8_t>& b,std::uint16_t v){
    b.push_back(std::uint8_t(v));b.push_back(std::uint8_t(v>>8));
}
static void addf(std::vector<std::uint8_t>& b,float f){
    std::uint32_t bits=0;
    std::memcpy(&bits,&f,4);add32(b,bits);
}
static std::vector<std::uint8_t> dds(){
    std::vector<std::uint8_t> b(128+4*4*4,0);
    std::memcpy(b.data(),"DDS ",4);
    write32(b,4,124);write32(b,12,4);write32(b,16,4);
    write32(b,28,1);write32(b,76,32);write32(b,80,0x41);
    write32(b,88,32);write32(b,92,0x00ff0000);
    write32(b,96,0x0000ff00);write32(b,100,0x000000ff);
    write32(b,104,0xff000000);
    return b;
}
static void crc(std::vector<std::uint8_t>& b) {
    write32(b,28,static_cast<std::uint32_t>(b.size()-36));
    write32(b,32,Crc32(b.data()+36,b.size()-36));
}
static std::vector<std::uint8_t> base(){
    std::vector<std::uint8_t> b(36,0);
    std::memcpy(b.data(),"OVRCABH2",8);
    write32(b,8,2);write32(b,12,1);write32(b,16,1);
    write32(b,20,3);write32(b,24,1);
    add16(b,3);add16(b,0);add32(b,3);add32(b,3);add32(b,2);
    b.insert(b.end(),{'P','B','R'});
    const Vertex v[3]{{0,0,0,0,1,0,0,0},{1,0,0,0,1,0,1,0},
                      {0,0,1,0,1,0,0,1}};
    const auto* data=reinterpret_cast<const std::uint8_t*>(v);
    b.insert(b.end(),data,data+sizeof(v));
    add16(b,0);add16(b,1);add16(b,2);
    const auto map=dds();
    add32(b,static_cast<unsigned>(map.size()));
    b.insert(b.end(),map.begin(),map.end());
    crc(b);
    return b;
}
int main(){
    Model model;
    std::string error;
    auto b2=base();
    assert(Parse(b2.data(),b2.size(),model,error));
    assert(!model.pbrEnabled && model.pbrMaterials.empty());
    auto b3=b2;
    std::memcpy(b3.data(),"OVRCABH3",8);
    write32(b3,8,3);
    b3.insert(b3.end(),{'O','V','C','P','B','R','3','!'});
    const std::size_t factorOffset=b3.size();
    addf(b3,.55f);addf(b3,.8f);addf(b3,1.25f);
    const auto map=dds();
    add32(b3,static_cast<unsigned>(map.size()));
    const std::size_t normalOffset=b3.size();
    b3.insert(b3.end(),map.begin(),map.end());
    add32(b3,static_cast<unsigned>(map.size()));
    b3.insert(b3.end(),map.begin(),map.end());
    crc(b3);
    assert(Parse(b3.data(),b3.size(),model,error));
    assert(model.highQuality && model.pbrEnabled && model.pbrMaterials.size()==1);
    const auto& mat=model.pbrMaterials[0];
    assert(std::fabs(mat.roughness-.55f)<1.e-5f);
    assert(std::fabs(mat.metallic-.8f)<1.e-5f);
    assert(std::fabs(mat.normalScale-1.25f)<1.e-5f);
    assert(mat.normal.width==4 && mat.orm.width==4);
    const auto originalMesh=model.meshes[0].vertices.size();
    // Tampered CRC is fail-closed and never replaces the last good model.
    b3[normalOffset+12]^=1;
    assert(!Parse(b3.data(),b3.size(),model,error) &&
           error=="sidecar header/CRC");
    assert(model.pbrEnabled && model.meshes[0].vertices.size()==originalMesh);
    b3[normalOffset+12]^=1;
    // Correct CRC with corrupt DDS must not be accepted.
    b3[normalOffset]='X';crc(b3);
    assert(!Parse(b3.data(),b3.size(),model,error) &&
           error=="unsupported pbr dds texture");
    b3[normalOffset]='D';
    // Reject NaN / invalid roughness after a fresh valid CRC.
    write32(b3,factorOffset,0x7fc00000u);crc(b3);
    assert(!Parse(b3.data(),b3.size(),model,error) &&
           error=="pbr factor bounds");
    assert(model.pbrMaterials.size()==1);
    auto bad=b2;
    std::memcpy(bad.data(),"OVRCABH3",8);
    write32(bad,8,3);crc(bad);
    assert(!Parse(bad.data(),bad.size(),model,error) &&
           error=="pbr extension");
    std::puts("DINO_OVC3_PBR_NORMAL_ORM_CRC_ATOMIC_COMPAT_PASS");
    return 0;
}
