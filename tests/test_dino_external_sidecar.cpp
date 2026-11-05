#include "src/vr/game/dino_external_sidecar.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
using namespace OutRunVR::DinoSidecar;
static void set32(std::vector<std::uint8_t>& b,std::size_t o,unsigned v) {
    for(unsigned k=0;k<4;++k)b[o+k]=static_cast<std::uint8_t>(v>>(8*k));
}
static void append16(std::vector<std::uint8_t>& b,unsigned x) {
    b.push_back(static_cast<std::uint8_t>(x));b.push_back(static_cast<std::uint8_t>(x>>8));
}
static void append32(std::vector<std::uint8_t>& b,unsigned x){
    for(unsigned k=0;k<4;++k)b.push_back(static_cast<std::uint8_t>(x>>(k*8)));
}
int main(){
    Gate g{};
    assert(!Eligible(g));
    g={true,true,true,true,true,true,true,false,1};
    assert(Eligible(g));
    g.carKind=0;assert(!Eligible(g));g.carKind=1;
    g.gameplay=false;assert(!Eligible(g));g.gameplay=true;
    g.stateRecording=true;assert(!Eligible(g));g.stateRecording=false;
    g.stereo=false;assert(!Eligible(g));g.stereo=true;
    const std::uint8_t crccheck[]={'1','2','3','4','5','6','7','8','9'};
    assert(Crc32(crccheck,9)==0xcbf43926u);
    std::vector<std::uint8_t> b(36,0);
    const char signature[8]={'O','V','R','C','A','B','1','5'};
    std::memcpy(b.data(),signature,8);
    set32(b,8,1);set32(b,12,Groups);set32(b,16,Materials);
    set32(b,20,Vertices);set32(b,24,Triangles);
    for(unsigned group=0;group<Groups;++group){
        const unsigned vc=group<10?310:300, tc=group<2?558:557;
        const char name[]="LHD_TEST";
        append16(b,8);append16(b,group%Materials);
        append32(b,vc);append32(b,tc*3);
        b.insert(b.end(),name,name+8);
        const Vertex v{0.f,0.f,0.f,0.f,1.f,0.f,.5f,.5f};
        for(unsigned i=0;i<vc;++i){
            const auto* p=reinterpret_cast<const std::uint8_t*>(&v);
            b.insert(b.end(),p,p+sizeof(Vertex));
        }
        for(unsigned i=0;i<tc*3;++i)append16(b,i%vc);
    }
    for(unsigned m=0;m<Materials;++m){
        append32(b,DdsSize);
        const auto start=b.size();b.resize(start+DdsSize,0);
        std::memcpy(b.data()+start,"DDS ",4);
        set32(b,start+4,124);set32(b,start+12,128);
        set32(b,start+16,128);set32(b,start+28,8);set32(b,start+76,32);
        std::memcpy(b.data()+start+84,"DXT1",4);
    }
    set32(b,28,static_cast<unsigned>(b.size()-36));
    set32(b,32,Crc32(b.data()+36,b.size()-36));
    Model model;std::string err;
    assert(Parse(b.data(),b.size(),model,err));
    assert(model.meshes.size()==Groups&&model.meshes[0].vertices.size()==310);
    const auto unchanged=model.meshes.size();
    b[42]^=1;
    assert(!Parse(b.data(),b.size(),model,err) && err=="sidecar header/CRC");
    assert(model.meshes.size()==unchanged); // atomic parse
    b[42]^=1;b[0]^=1;
    assert(!Parse(b.data(),b.size(),model,err) && err=="sidecar signature");
    b[0]^=1;
    assert(!Parse(b.data(),b.size()-1,model,err));
    assert(!Parse(nullptr,0,model,err));
    std::puts("DINO_SIDECAR_70_GROUP_19_DDS_VALIDATION_AND_GATE_PASS");
    return 0;
}
