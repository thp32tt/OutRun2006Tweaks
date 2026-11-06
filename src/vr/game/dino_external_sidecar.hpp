#pragma once
// OutRun VR native-PMT-free cockpit sidecars.
// V1 128px BC1, V2 HQ DDS and V3 optional tangent-space normal/ORM PBR maps.
// All offsets and counts are validated before GPU allocation.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace OutRunVR::DinoSidecar {
constexpr unsigned Groups=70, Materials=19, Vertices=21100, Triangles=38992;
constexpr unsigned DdsSize=11136;
constexpr std::size_t MaxSidecarBytes=128u*1024u*1024u;
constexpr std::size_t MaxGpuPayloadBytes=112u*1024u*1024u;
constexpr unsigned MaxGroups=512,MaxMaterials=64,MaxVertices=1000000,MaxTriangles=2000000;
enum class TextureFormat : std::uint8_t { DXT1,DXT5,ARGB32 };
struct Vertex {float x,y,z,nx,ny,nz,u,v;};
static_assert(sizeof(Vertex)==32,"Dino fixed function vertex stride");
struct Mesh {
    std::string name;
    unsigned material=0;
    std::vector<Vertex> vertices;
    std::vector<std::uint32_t> indices;
    bool index32=false;
};
struct Texture {
    std::vector<std::uint8_t> dds;
    unsigned width=0,height=0,mips=0;
    TextureFormat format=TextureFormat::DXT1;
};
// V3 OVC material data; ORM = occlusion(R), roughness(G), metallic(B).
// DDS maps are optional and are validated using the same bounded parser as albedo.
struct PbrMaterial {
    Texture normal,orm;
    float roughness=0.75f,metallic=0.04f,normalScale=1.0f;
};
struct Model {
    std::vector<Mesh> meshes;
    std::vector<Texture> textures;
    std::vector<PbrMaterial> pbrMaterials;
    unsigned vertices=0,triangles=0;
    bool highQuality=false,pbrEnabled=false;
};
inline unsigned U32(const std::uint8_t* p) noexcept {
    return unsigned(p[0])|(unsigned(p[1])<<8)|(unsigned(p[2])<<16)|(unsigned(p[3])<<24);
}
inline unsigned U16(const std::uint8_t* p) noexcept {return unsigned(p[0])|(unsigned(p[1])<<8);}
inline float F32(const std::uint8_t* p) noexcept {
    const std::uint32_t bits=U32(p);
    float value=0;
    std::memcpy(&value,&bits,sizeof(value));
    return value;
}
inline bool Bounds(std::size_t p,std::size_t n,std::size_t limit) noexcept {
    return p<=limit && n<=limit-p;
}
inline unsigned Crc32(const std::uint8_t* p,std::size_t size) noexcept {
    unsigned c=0xffffffffu;
    for(std::size_t i=0;i<size;++i){
        c^=p[i];
        for(unsigned j=0;j<8;++j)c=(c>>1)^(0xedb88320u&(0u-(c&1u)));
    }
    return ~c;
}
inline bool ParseDds(const std::uint8_t* d,std::size_t size,Texture& out,bool legacy) {
    if(!d || size<128 || std::memcmp(d,"DDS ",4)!=0 ||
       U32(d+4)!=124 || U32(d+76)!=32 || U32(d+12)==0 || U32(d+16)==0)
        return false;
    const unsigned width=U32(d+16),height=U32(d+12);
    if(width>2048 || height>2048 ||
       (width&(width-1))!=0 || (height&(height-1))!=0)
        return false;
    const unsigned mip=U32(d+28);
    const unsigned maxDim=width>height?width:height;
    unsigned fullMips=1;
    for(unsigned dim=maxDim;dim>1;dim>>=1)++fullMips;
    if(!mip || mip>fullMips)return false;
    TextureFormat format;
    unsigned blockBytes=0;
    if(U32(d+84)==0x31545844u) {format=TextureFormat::DXT1;blockBytes=8;}
    else if(U32(d+84)==0x35545844u) {format=TextureFormat::DXT5;blockBytes=16;}
    else if(U32(d+84)==0 && U32(d+88)==32 &&
            U32(d+92)==0x00ff0000u && U32(d+96)==0x0000ff00u &&
            U32(d+100)==0x000000ffu && U32(d+104)==0xff000000u) {
        format=TextureFormat::ARGB32;
    } else return false;
    std::size_t need=128;
    for(unsigned level=0;level<mip;++level) {
        const unsigned w=(width>>level)?(width>>level):1u;
        const unsigned h=(height>>level)?(height>>level):1u;
        const std::size_t rows=blockBytes ? ((h+3u)/4u? (h+3u)/4u:1u) : h;
        const std::size_t pitch=blockBytes ?
             std::size_t(((w+3u)/4u)?(w+3u)/4u:1u)*blockBytes : std::size_t(w)*4u;
        if(!Bounds(need,rows*pitch,size))return false;
        need+=rows*pitch;
    }
    // V1's experimental DDS contains 72 trailing padding bytes.
    // Do not accept padding in V2; unknown bytes could hide corrupt mip data.
    if((!legacy && need!=size) || (legacy && (size!=DdsSize || need!=128u+10936u ||
                                               width!=128 || height!=128 || mip!=8 ||
                                               format!=TextureFormat::DXT1)))
        return false;
    out.width=width;out.height=height;out.mips=mip;out.format=format;
    out.dds.assign(d,d+size);
    return true;
}
inline bool Parse(const std::uint8_t* d,std::size_t size,Model& out,std::string& error) {
    const auto fail=[&](const char* message){error=message;return false;};
    if(!d || size<36 || size>MaxSidecarBytes)return fail("sidecar file size");
    const bool legacy=std::memcmp(d,"OVRCAB15",8)==0;
    const bool v2=std::memcmp(d,"OVRCABH2",8)==0;
    const bool v3=std::memcmp(d,"OVRCABH3",8)==0;
    if(!legacy && !v2 && !v3)return fail("sidecar signature");
    const unsigned version=U32(d+8),groups=U32(d+12),materials=U32(d+16);
    const unsigned vertices=U32(d+20),triangles=U32(d+24);
    if(version!=(legacy?1u:(v2?2u:3u)) || groups==0 || materials==0 ||
       groups>MaxGroups || materials>MaxMaterials ||
       vertices>MaxVertices || triangles>MaxTriangles ||
       (legacy && (groups!=Groups || materials!=Materials ||
                    vertices!=Vertices || triangles!=Triangles)) ||
       U32(d+28)!=size-36 || U32(d+32)!=Crc32(d+36,size-36))
        return fail("sidecar header/CRC");
    Model parsed;
    parsed.highQuality=!legacy;
    parsed.pbrEnabled=v3;
    parsed.meshes.reserve(groups);
    std::size_t pos=36,bytesGpu=0;
    std::uint64_t nv=0,nt=0;
    for(unsigned g=0;g<groups;++g) {
        const unsigned headBytes=legacy?12u:16u;
        if(!Bounds(pos,headBytes,size))return fail("group header");
        const unsigned nameLen=U16(d+pos),mat=U16(d+pos+2);
        const unsigned n=U32(d+pos+4),ic=U32(d+pos+8);
        const unsigned indexWidth=legacy?2u:U32(d+pos+12);
        pos+=headBytes;
        if(nameLen==0 || nameLen>256 || mat>=materials ||
           n<3 || n>MaxVertices || ic<3 || ic%3!=0 ||
           ic>MaxTriangles*3u || (indexWidth!=2 && indexWidth!=4) ||
           (indexWidth==2 && n>65535u))
            return fail("group bounds");
        const std::size_t vb=std::size_t(n)*sizeof(Vertex);
        const std::size_t ib=std::size_t(ic)*indexWidth;
        if(!Bounds(pos,std::size_t(nameLen)+vb+ib,size))
            return fail("group data");
        if(bytesGpu+vb+ib>MaxGpuPayloadBytes)return fail("sidecar GPU budget");
        bytesGpu+=vb+ib;
        Mesh mesh;
        mesh.name.assign(reinterpret_cast<const char*>(d+pos),nameLen);
        if(mesh.name.empty() || mesh.name.find('\0')!=std::string::npos ||
           (legacy && mesh.name.compare(0,3,"LHD")!=0))
            return fail("group identity");
        mesh.material=mat;mesh.index32=indexWidth==4;
        pos+=nameLen;
        mesh.vertices.resize(n);
        std::memcpy(mesh.vertices.data(),d+pos,vb);
        pos+=vb;
        for(const auto& vertex:mesh.vertices){
            for(float f:{vertex.x,vertex.y,vertex.z,vertex.nx,vertex.ny,
                         vertex.nz,vertex.u,vertex.v})
                if(!std::isfinite(f)||std::fabs(f)>10000.f)
                    return fail("nonfinite vertex");
        }
        mesh.indices.resize(ic);
        for(unsigned i=0;i<ic;++i) {
            const unsigned idx=indexWidth==4?U32(d+pos+std::size_t(i)*4u):
                                               U16(d+pos+std::size_t(i)*2u);
            if(idx>=n)return fail("index outside vertex group");
            mesh.indices[i]=idx;
        }
        pos+=ib;
        nv+=n;nt+=ic/3u;
        if(nv>vertices||nt>triangles)return fail("model total");
        parsed.meshes.push_back(std::move(mesh));
    }
    if(nv!=vertices || nt!=triangles)return fail("model total");
    parsed.textures.reserve(materials);
    for(unsigned i=0;i<materials;++i) {
        if(!Bounds(pos,4,size))return fail("dds length");
        const unsigned len=U32(d+pos);pos+=4;
        if(len<128 || !Bounds(pos,len,size) ||
           bytesGpu+len>MaxGpuPayloadBytes)return fail("dds bounds/budget");
        Texture texture;
        if(!ParseDds(d+pos,len,texture,legacy))return fail("unsupported dds texture");
        bytesGpu+=len;
        parsed.textures.push_back(std::move(texture));
        pos+=len;
    }
    if(v3) {
        constexpr char pbrMagic[]="OVCPBR3!";
        if(!Bounds(pos,8,size) || std::memcmp(d+pos,pbrMagic,8)!=0)
            return fail("pbr extension");
        pos+=8;
        parsed.pbrMaterials.reserve(materials);
        for(unsigned i=0;i<materials;++i) {
            if(!Bounds(pos,12,size))return fail("pbr material factors");
            PbrMaterial mat;
            mat.roughness=F32(d+pos);
            mat.metallic=F32(d+pos+4);
            mat.normalScale=F32(d+pos+8);
            pos+=12;
            if(!std::isfinite(mat.roughness) || mat.roughness<0.04f ||
               mat.roughness>1.0f || !std::isfinite(mat.metallic) ||
               mat.metallic<0.f || mat.metallic>1.f ||
               !std::isfinite(mat.normalScale) || mat.normalScale<0.f ||
               mat.normalScale>2.f)return fail("pbr factor bounds");
            for(Texture* map:{&mat.normal,&mat.orm}) {
                if(!Bounds(pos,4,size))return fail("pbr map length");
                const unsigned len=U32(d+pos);pos+=4;
                if(!len)continue;
                if(len<128 || !Bounds(pos,len,size) ||
                   bytesGpu+len>MaxGpuPayloadBytes)
                    return fail("pbr map bounds/budget");
                if(!ParseDds(d+pos,len,*map,false))
                    return fail("unsupported pbr dds texture");
                bytesGpu+=len;
                pos+=len;
            }
            parsed.pbrMaterials.push_back(std::move(mat));
        }
    }
    if(pos!=size)return fail("trailing sidecar data");
    parsed.vertices=vertices;parsed.triangles=triangles;
    out=std::move(parsed);
    error.clear();
    return true;
}
// Portable failure policy: a failed x86 D3D9Ex allocation is retried only
// after device Reset or an actual different device. No per-frame OOM storm.
struct GpuRetryPolicy {
    std::uintptr_t rejectedDevice=0;
    bool CanAttempt(const void* device) const noexcept {
        return device &&
            reinterpret_cast<std::uintptr_t>(device)!=rejectedDevice;
    }
    void NoteFailure(const void* device) noexcept {
        rejectedDevice=reinterpret_cast<std::uintptr_t>(device);
    }
    void OnReset() noexcept {rejectedDevice=0;}
};
struct Gate {
    bool optIn=false,vr=false,seat=false,gameplay=false,stereo=false;
    bool playerDraw=false,deviceReady=false,stateRecording=false;
    unsigned char carKind=255;
};
inline bool Eligible(const Gate& g) noexcept {
    return g.optIn&&g.vr&&g.seat&&g.gameplay&&g.stereo&&g.playerDraw&&
           g.deviceReady&&!g.stateRecording&&g.carKind==1;
}
} // namespace OutRunVR::DinoSidecar
