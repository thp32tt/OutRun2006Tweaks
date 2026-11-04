#pragma once
// Independent OutRun 2006 v15 cockpit sidecar; never accesses PMT memory.
#include <array>
#include <cstdint>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>
#include <utility>
namespace OutRunVR::DinoSidecar {
constexpr unsigned Groups=70, Materials=19, Vertices=21100, Triangles=38992;
constexpr unsigned DdsSize=11136;
struct Vertex {float x,y,z,nx,ny,nz,u,v;};
static_assert(sizeof(Vertex)==32,"Dino sidecar vertex ABI");
struct Mesh {
    std::string name;
    unsigned material=0;
    std::vector<Vertex> vertices;
    std::vector<std::uint16_t> indices;
};
struct Model {
    std::vector<Mesh> meshes;
    // Keep 19x11 KiB on the heap, not twice on the original x86 game's
    // render-hook stack (Parse result + EnsureLoaded temporary).
    std::vector<std::array<std::uint8_t,DdsSize>> dds;
};
inline unsigned U32(const std::uint8_t* a) noexcept {
    return unsigned(a[0])|(unsigned(a[1])<<8)|(unsigned(a[2])<<16)|(unsigned(a[3])<<24);
}
inline unsigned U16(const std::uint8_t* a) noexcept {return unsigned(a[0])|(unsigned(a[1])<<8);}
inline bool Bounds(std::size_t pos,std::size_t len,std::size_t size) noexcept {
    return pos<=size && len<=size-pos;
}
inline unsigned Crc32(const std::uint8_t* data,std::size_t n) noexcept {
    unsigned crc=0xffffffffu;
    for(std::size_t i=0;i<n;++i){
        crc^=data[i];
        for(int k=0;k<8;++k) crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));
    }
    return ~crc;
}
inline bool Parse(const std::uint8_t* data,std::size_t size,Model& output,std::string& error){
    const auto fail=[&](const char* why){error=why;return false;};
    if(!data||size<36||size>8u*1024u*1024u) return fail("sidecar file size");
    const char magic[8]={'O','V','R','C','A','B','1','5'};
    if(std::memcmp(data,magic,8))return fail("sidecar signature");
    if(U32(data+8)!=1||U32(data+12)!=Groups||U32(data+16)!=Materials||
       U32(data+20)!=Vertices||U32(data+24)!=Triangles||
       U32(data+28)!=size-36||U32(data+32)!=Crc32(data+36,size-36))
        return fail("sidecar header/CRC");
    Model result;
    result.meshes.reserve(Groups);
    std::size_t p=36;
    std::uint64_t nv=0,nt=0;
    for(unsigned i=0;i<Groups;++i){
        if(!Bounds(p,12,size))return fail("group header");
        const auto nameLen=U16(data+p),material=U16(data+p+2);
        const auto vertices=U32(data+p+4),indices=U32(data+p+8);
        p+=12;
        if(!nameLen||nameLen>256||material>=Materials||vertices<3||
           vertices>8000||indices<3||indices>40000||indices%3)
            return fail("group bounds");
        const std::size_t bytes=nameLen+std::size_t(vertices)*32+std::size_t(indices)*2;
        if(!Bounds(p,bytes,size))return fail("group data");
        Mesh mesh;
        mesh.name.assign(reinterpret_cast<const char*>(data+p),nameLen);
        if(mesh.name.compare(0,3,"LHD")||mesh.name.find('\0')!=std::string::npos)
            return fail("group identity");
        mesh.material=material;p+=nameLen;
        mesh.vertices.resize(vertices);
        std::memcpy(mesh.vertices.data(),data+p,std::size_t(vertices)*32);
        p+=std::size_t(vertices)*32;
        for(const auto& v:mesh.vertices){
            const float values[]={v.x,v.y,v.z,v.nx,v.ny,v.nz,v.u,v.v};
            for(float f:values)if(!std::isfinite(f)||std::fabs(f)>10000.f)
                return fail("nonfinite vertex");
        }
        mesh.indices.resize(indices);
        for(unsigned j=0;j<indices;++j){
            const auto k=U16(data+p+j*2);
            if(k>=vertices)return fail("index outside vertex group");
            mesh.indices[j]=static_cast<std::uint16_t>(k);
        }
        p+=std::size_t(indices)*2;
        nv+=vertices;nt+=indices/3;
        result.meshes.push_back(std::move(mesh));
    }
    if(nv!=Vertices||nt!=Triangles)return fail("model total");
    result.dds.resize(Materials);
    for(unsigned i=0;i<Materials;++i){
        if(!Bounds(p,4,size))return fail("dds length");
        const auto len=U32(data+p);p+=4;
        if(len!=DdsSize||!Bounds(p,len,size))return fail("dds bounds");
        const auto* d=data+p;
        if(std::memcmp(d,"DDS ",4)||U32(d+4)!=124||
           U32(d+12)!=128||U32(d+16)!=128||
           U32(d+28)!=8||std::memcmp(d+84,"DXT1",4))
            return fail("unsupported dds texture");
        std::memcpy(result.dds[i].data(),d,DdsSize);
        p+=len;
    }
    if(p!=size)return fail("trailing sidecar data");
    output=std::move(result);
    error.clear();
    return true;
}
struct Gate {
    bool optIn=false,vr=false,seat=false,gameplay=false,stereo=false;
    bool playerDraw=false,deviceReady=false,stateRecording=false;
    unsigned char carKind=255;
};
inline bool Eligible(const Gate& g) noexcept {
    return g.optIn&&g.vr&&g.seat&&g.gameplay&&g.stereo&&g.playerDraw&&
           g.deviceReady&&!g.stateRecording&&g.carKind==1;
}
} // OutRunVR::DinoSidecar
