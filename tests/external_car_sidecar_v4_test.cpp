#include "../src/vr/game/dino_external_sidecar.hpp"
#include "../src/vr/game/external_car_selection.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using namespace OutRunVR::DinoSidecar;

static void PutU32(std::vector<std::uint8_t>& b,std::uint32_t v) {
    b.push_back(static_cast<std::uint8_t>(v));
    b.push_back(static_cast<std::uint8_t>(v>>8));
    b.push_back(static_cast<std::uint8_t>(v>>16));
    b.push_back(static_cast<std::uint8_t>(v>>24));
}
static void PutU16(std::vector<std::uint8_t>& b,std::uint16_t v) {
    b.push_back(static_cast<std::uint8_t>(v));
    b.push_back(static_cast<std::uint8_t>(v>>8));
}
static void PutF32(std::vector<std::uint8_t>& b,float v) {
    std::uint32_t bits=0;std::memcpy(&bits,&v,4);PutU32(b,bits);
}
static void Append(std::vector<std::uint8_t>& b,const void* p,std::size_t n) {
    const auto* q=static_cast<const std::uint8_t*>(p);b.insert(b.end(),q,q+n);
}
static void SetU32(std::vector<std::uint8_t>& b,std::size_t off,std::uint32_t v) {
    b[off]=static_cast<std::uint8_t>(v);
    b[off+1]=static_cast<std::uint8_t>(v>>8);
    b[off+2]=static_cast<std::uint8_t>(v>>16);
    b[off+3]=static_cast<std::uint8_t>(v>>24);
}

static std::vector<std::uint8_t> Dds1x1() {
    std::vector<std::uint8_t> d(132,0);
    std::memcpy(d.data(),"DDS ",4);
    SetU32(d,4,124);SetU32(d,8,0x0002100Fu);
    SetU32(d,12,1);SetU32(d,16,1);SetU32(d,20,4);SetU32(d,28,1);
    SetU32(d,76,32);SetU32(d,80,0x41);SetU32(d,84,0);SetU32(d,88,32);
    SetU32(d,92,0x00ff0000u);SetU32(d,96,0x0000ff00u);
    SetU32(d,100,0x000000ffu);SetU32(d,104,0xff000000u);SetU32(d,108,0x401008u);
    d[128]=255;d[129]=255;d[130]=255;d[131]=255;
    return d;
}

static std::vector<std::uint8_t> Dds1x1Dxt5() {
    std::vector<std::uint8_t> d(144,0);
    std::memcpy(d.data(),"DDS ",4);
    SetU32(d,4,124);SetU32(d,8,0x000A1007u);
    SetU32(d,12,1);SetU32(d,16,1);SetU32(d,20,16);SetU32(d,28,1);
    SetU32(d,76,32);SetU32(d,80,0x4);SetU32(d,84,0x35545844u);
    SetU32(d,108,0x401008u);
    return d;
}

static std::vector<std::uint8_t> Make(bool goodAxis=true,
                                      const std::string& name="EXT_OPAQUE_00",
                                      bool maps=false) {
    std::vector<std::uint8_t> payload;
    PutU16(payload,static_cast<std::uint16_t>(name.size()));
    PutU16(payload,0);PutU32(payload,3);PutU32(payload,3);PutU32(payload,4);
    Append(payload,name.data(),name.size());
    const Vertex v[3]{
        {0,0,0,0,1,0,0,0},{1,0,0,0,1,0,1,0},{0,1,0,0,1,0,0,1}
    };
    Append(payload,v,sizeof(v));
    PutU32(payload,0);PutU32(payload,1);PutU32(payload,2);
    const auto dds=Dds1x1();PutU32(payload,static_cast<std::uint32_t>(dds.size()));
    Append(payload,dds.data(),dds.size());
    Append(payload,"OVCPBR3!",8);
    PutF32(payload,0.5f);PutF32(payload,0.f);PutF32(payload,1.f);
    for(unsigned role=0;role<2;++role) {
        PutU32(payload,maps?static_cast<std::uint32_t>(dds.size()):0u);
        if(maps)Append(payload,dds.data(),dds.size());
    }
    Append(payload,"OVCDASH4",8);PutU32(payload,1);
    PutU32(payload,0);PutU32(payload,1);PutU32(payload,0);PutU32(payload,0);
    PutF32(payload,0);PutF32(payload,0);PutF32(payload,0);
    PutF32(payload,0);PutF32(payload,0);PutF32(payload,goodAxis?1.f:0.5f);
    PutF32(payload,0);PutF32(payload,320);
    PutF32(payload,-1);PutF32(payload,1);

    std::vector<std::uint8_t> out;
    Append(out,"OVRCABH4",8);PutU32(out,4);PutU32(out,1);PutU32(out,1);
    PutU32(out,3);PutU32(out,1);
    PutU32(out,static_cast<std::uint32_t>(payload.size()));
    PutU32(out,Crc32(payload.data(),payload.size()));
    Append(out,payload.data(),payload.size());
    return out;
}

int main() {
    static_assert(MaxMaterials==128,"external HQ material budget regression");
    std::string error;Model model;
    Texture compressedTexture;
    auto compressedDds=Dds1x1Dxt5();
    assert(ParseDds(compressedDds.data(),compressedDds.size(),compressedTexture,false));
    assert(compressedTexture.format==TextureFormat::DXT5);
    auto good=Make(true);
    assert(Parse(good.data(),good.size(),model,error));
    assert(model.highQuality && model.pbrEnabled && model.dashboardEnabled);
    assert(model.meshes.size()==1 && model.dashboardBindings.size()==1);
    const auto& b=model.dashboardBindings[0];
    assert(b.meshIndex==0 && b.kind==DashboardKind::SpeedNeedle);
    assert(std::fabs(b.inputMax-320.f)<0.001f);

    auto bad=Make(false);Model rejected;
    assert(!Parse(bad.data(),bad.size(),rejected,error));
    assert(error=="dashboard binding bounds");
    // All sixteen canonical slots: a valid model must parse; identical
    // indices or zero-area positions with recalculated CRC must NOT admit a
    // blank replacement for the corresponding original retail car.
    for(unsigned canonical=0;canonical<30u;++canonical) {
        if(!IsFerrari16CanonicalCarId(static_cast<unsigned char>(canonical)))
            continue;
        const std::string name="EXT_CAR_"+std::to_string(canonical);
        const auto valid=Make(true,name);
        Model accepted;
        assert(Parse(valid.data(),valid.size(),accepted,error));
        assert(accepted.meshes.size()==1 && accepted.meshes[0].name==name);
        const std::size_t vbOff=36u+16u+name.size();
        const std::size_t ibOff=vbOff+3u*sizeof(Vertex);
        // All three DDS roles share ParseDds. Test every canonical slot.
        const auto mapped=Make(true,name,true);
        const std::size_t albedo=ibOff+12u+4u;
        const std::size_t normal=albedo+132u+8u+12u+4u;
        const std::size_t orm=normal+132u+4u;
        struct ResourceCase { unsigned field,value; bool accepted; };
        const ResourceCase cases[]={
            {112u,0u,true},{24u,1u,true},
            {112u,0x200u,false},{112u,0x400u,false},
            {112u,0x8000u,false},{112u,0x200000u,false},
            {8u,0x800000u,false},{24u,2u,false}
        };
        for(const auto offset:{albedo,normal,orm}) {
            for(const auto& c:cases) {
                auto fixture=mapped;
                SetU32(fixture,offset+c.field,c.value);
                SetU32(fixture,32u,Crc32(fixture.data()+36u,fixture.size()-36u));
                Model checked;
                assert(Parse(fixture.data(),fixture.size(),checked,error)==c.accepted);
                if(c.accepted) {
                    assert(checked.pbrMaterials.size()==1);
                    assert(!checked.pbrMaterials[0].normal.dds.empty());
                    assert(!checked.pbrMaterials[0].orm.dds.empty());
                } else assert(error==(offset==albedo?
                    "unsupported dds texture":"unsupported pbr dds texture"));
            }
        }
        auto repeated=valid;
        SetU32(repeated,ibOff+4u,0u);
        SetU32(repeated,ibOff+8u,0u);
        SetU32(repeated,32u,Crc32(repeated.data()+36u,repeated.size()-36u));
        Model rejectedRepeated;
        assert(!Parse(repeated.data(),repeated.size(),rejectedRepeated,error));
        assert(error=="group degenerate geometry");
        auto collapsed=valid;
        // v2.y = 0 => all three vertex positions lie on the X axis.
        SetU32(collapsed,vbOff+2u*sizeof(Vertex)+4u,0u);
        SetU32(collapsed,32u,Crc32(collapsed.data()+36u,collapsed.size()-36u));
        Model rejectedCollapsed;
        assert(!Parse(collapsed.data(),collapsed.size(),rejectedCollapsed,error));
        assert(error=="group degenerate geometry");
        // Match the offline gear-pivot parity fixtures. Native parser
        // already rejects invalid pivots even for visibility-only gears.
        const std::size_t dash=valid.size()-56u;
        for(float pivot : {0.f,-10000.f,10000.f,
                std::numeric_limits<float>::quiet_NaN(),
                std::numeric_limits<float>::infinity(),
                -std::numeric_limits<float>::infinity(),10001.f,-10001.f}) {
            auto gear=valid;
            SetU32(gear,dash+4u,3u);
            SetU32(gear,dash+8u,5u);
            std::uint32_t bits=0;std::memcpy(&bits,&pivot,4);
            SetU32(gear,dash+16u,bits);
            SetU32(gear,32u,Crc32(gear.data()+36u,gear.size()-36u));
            Model gearModel;
            const bool expected=std::isfinite(pivot) && std::fabs(pivot)<=10000.f;
            assert(Parse(gear.data(),gear.size(),gearModel,error)==expected);
            if(expected) {
                const auto& binding=gearModel.dashboardBindings[0];
                assert(DashboardMeshVisible(&binding,SanitizeDashboardTelemetry(0.f,0u,5u)));
                assert(!DashboardMeshVisible(&binding,SanitizeDashboardTelemetry(0.f,0u,4u)));
            } else assert(error=="dashboard binding bounds");
        }
        auto badCrc=valid;
        badCrc[ibOff]^=0x01u;
        Model rejectedCrc;
        assert(!Parse(badCrc.data(),badCrc.size(),rejectedCrc,error));
        assert(error=="sidecar header/CRC");
    }
    std::cout<<"EXTERNAL_SIDECAR_V4_PARSE_PASS\n";
}