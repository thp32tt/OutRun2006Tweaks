#include "src/vr/game/dino_external_sidecar.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
using namespace OutRunVR::DinoSidecar;
static void wr32(std::vector<std::uint8_t>& b,std::size_t o,std::uint32_t v) {
    for(unsigned i=0;i<4;++i)b[o+i]=std::uint8_t(v>>(8*i));
}
static void put16(std::vector<std::uint8_t>& b,std::uint32_t v) {
    b.push_back(std::uint8_t(v));b.push_back(std::uint8_t(v>>8));
}
static void put32(std::vector<std::uint8_t>& b,std::uint32_t v){
    for(unsigned i=0;i<4;++i)b.push_back(std::uint8_t(v>>(8*i)));
}
static std::vector<std::uint8_t> dds(unsigned dimension,bool compressed) {
    std::vector<std::uint8_t> b(128);
    std::memcpy(b.data(),"DDS ",4);
    wr32(b,4,124);wr32(b,12,dimension);wr32(b,16,dimension);
    wr32(b,76,32);
    const unsigned mip=dimension==1024?11u:12u;
    wr32(b,28,mip);
    if(compressed){wr32(b,80,4);std::memcpy(b.data()+84,"DXT5",4);}
    else {wr32(b,80,0x41);wr32(b,88,32);wr32(b,92,0x00ff0000);
          wr32(b,96,0x0000ff00);wr32(b,100,0x000000ff);
          wr32(b,104,0xff000000);}
    for(unsigned d=dimension;d;d>>=1) {
        const std::size_t bytes=compressed?
            std::size_t((d+3u)/4u)*((d+3u)/4u)*16u:
            std::size_t(d)*d*4u;
        b.insert(b.end(),bytes,0x35);
    }
    return b;
}
int main(){
    std::vector<std::uint8_t> b(36,0);
    std::memcpy(b.data(),"OVRCABH2",8);
    wr32(b,8,2);wr32(b,12,157);wr32(b,16,2);
    wr32(b,20,65536+156*3);wr32(b,24,157);
    for(unsigned g=0;g<157;++g) {
        const unsigned n=g==0?65536:3;
        const unsigned idxBytes=g==0?4:2;
        const char name[]="HQ_DINO";
        put16(b,7);put16(b,g%2);put32(b,n);put32(b,3);
        put32(b,idxBytes);
        b.insert(b.end(),name,name+7);
        const Vertex v{0.f,.1f,.2f,0.f,1.f,0.f,.3f,.4f};
        const auto* src=reinterpret_cast<const std::uint8_t*>(&v);
        for(unsigned i=0;i<n;++i)b.insert(b.end(),src,src+sizeof(Vertex));
        if(idxBytes==4){put32(b,0);put32(b,1);put32(b,65535);}
        else {put16(b,0);put16(b,1);put16(b,2);}
    }
    const auto texture0=dds(1024,false);
    const auto texture1=dds(2048,true);
    for(const auto* p:{&texture0,&texture1}) {
        put32(b,static_cast<unsigned>(p->size()));
        b.insert(b.end(),p->begin(),p->end());
    }
    wr32(b,28,static_cast<unsigned>(b.size()-36));
    wr32(b,32,Crc32(b.data()+36,b.size()-36));
    Model model;std::string error;
    assert(Parse(b.data(),b.size(),model,error));
    assert(model.highQuality && model.meshes.size()==157 && model.textures.size()==2);
    assert(model.meshes[0].index32 && model.meshes[0].indices[2]==65535);
    assert(!model.meshes[1].index32);
    assert(model.textures[0].width==1024 &&
           model.textures[0].format==TextureFormat::ARGB32 &&
           model.textures[0].mips==11);
    assert(model.textures[1].width==2048 &&
           model.textures[1].format==TextureFormat::DXT5 &&
           model.textures[1].mips==12);
    // CRC failure must not overwrite the last successfully parsed model.
    const auto kept=model.meshes.size();
    b[150]^=0x10;
    assert(!Parse(b.data(),b.size(),model,error) && error=="sidecar header/CRC");
    assert(model.meshes.size()==kept);
    b[150]^=0x10;
    // CRC-correct, but out-of-range 32-bit triangle index must be rejected.
    // First 16-byte record + 7 byte name + 65536*32 vertex bytes.
    const std::size_t badIndex=36+16+7+65536u*32u+8u;
    wr32(b,badIndex,65536u);
    wr32(b,32,Crc32(b.data()+36,b.size()-36));
    assert(!Parse(b.data(),b.size(),model,error) &&
           error=="index outside vertex group");
    std::puts("DINO_OVC2_157_GROUP_1024_ARGB_2048_DXT5_INDEX32_PASS");
    return 0;
}
