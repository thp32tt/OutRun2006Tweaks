#include "../src/vr/game/external_car_native_stock_replay.hpp"
#include <cassert>
#include <iostream>
using namespace OutRunVR::DinoSidecar;
int main(){
    unsigned cases=0;
    for(unsigned missing=0;missing<4;++missing)
    for(unsigned invalid=0;invalid<4;++invalid)
    for(unsigned mismatch=0;mismatch<3;++mismatch){
        NativeVehicleStockReplay r{};r.key={1,2,3,4,5,6};
        {
            ScopedNativeVehicleStockReplay owner(r);
            assert(ActiveNativeVehicleStockReplay==&r&&!r.StockOnly());
            for(unsigned group=1;group<=3;++group){
                if(group==missing)continue;
                r.Open(group!=invalid);
                {ScopedNativeVehiclePhysical p(true);
                 if(r.StockOnly()){++r.omitted[0];if(mismatch!=group)++r.omitted[1];}}
                r.Close(true);
            }
        }
        assert(!ActiveNativeVehicleStockReplay);
        assert(r.Ready()==(missing==0&&invalid==0&&mismatch==0));
        ++cases;
    }
    for(int model=0;model<30;++model){
        const auto& profile=NativeModelProfiles[model];
        std::uint32_t layout[0x3e];for(auto& id:layout)id=0xffffffffu;
        for(unsigned group=1;group<=3;++group){
            NativeVehicleStockReplay r{};r.model=model;r.opened=group;r.group=true;
            unsigned field=0;
            for(unsigned part=0;part<32;++part){
                const bool owned=(profile.parts[group-1]&(std::uint32_t{1}<<part))!=0;
                assert(r.OwnsObject(profile.prefix|part)==owned);
                assert(!r.OwnsObject((profile.prefix^0x80000000u)|part));
                if(owned)layout[NativeModelFields[group-1][field++]]=profile.prefix|part;
                ++cases;
            }
            assert(!r.OwnsObject(profile.prefix|0xffffu));
            r.group=false;assert(!r.OwnsObject(profile.prefix));
        }
        assert(NativeModelLayoutMatches(model,layout,0x3e));
        assert(!NativeModelLayoutMatches(model,layout,0x3d));
        const auto original=layout[0xa];layout[0xa]^=0x10000u;
        assert(!NativeModelLayoutMatches(model,layout,0x3e));layout[0xa]=original;
        layout[0xa]=0xffffffffu;assert(!NativeModelLayoutMatches(model,layout,0x3e));
        ++cases;
    }
    assert(!NativeModelProfileFor(-1)&&!NativeModelProfileFor(30));
    for(unsigned count:{0u,1u,3u,256u,257u})for(unsigned index:{0u,1u,2u,255u,256u})
    for(unsigned offset:{0u,1u,59u}){
        const auto address=0x1000u+0x3cu*index+offset;
        assert(NativeQueueEntryInPool(count,256,0x1000,address)==
            (count<=256&&index<count&&offset==0));++cases;
    }
    assert(!NativeQueueEntryInPool(1,256,0x1000,0xfff));
    assert(!NativeQueueEntryInPool(1,257,0x1000,0x1000));
    assert(!NativeQueueEntryInPool(1,256,0,0));
    // Between all three real queue groups, independent native shadow/
    // passenger draws do not enter or invalidate the body transaction.
    {NativeVehicleStockReplay a{};a.key={1,2,3,4,5,6};ScopedNativeVehicleStockReplay owner(a);
     for(unsigned group=0;group<3;++group){
        {ScopedNativeVehiclePhysical unrelated(false);assert(!a.StockOnly()&&!a.failed&&!a.physicalDepth);}
        a.Open(true);
        {ScopedNativeVehiclePhysical ordinary(true);assert(a.StockOnly());++a.omitted[0];++a.omitted[1];}
        {ScopedNativeVehiclePhysical sortedAlpha(true);assert(a.StockOnly());++a.omitted[0];++a.omitted[1];}
        a.Close(true);
     }
     assert(a.Ready()&&a.physicalEntries==6);++cases;}
    NativeVehicleStockReplay r{};r.key={1,2,3,4,5,6};
    {ScopedNativeVehicleStockReplay owner(r);r.Open(true);
     {ScopedNativeVehiclePhysical p(false);assert(!r.StockOnly());}
     r.Close(true);}
    assert(r.failed&&!r.Ready());++cases;
    {NativeVehicleStockReplay a{},b{};ScopedNativeVehicleStockReplay first(a);
     {ScopedNativeVehicleStockReplay nested(b);assert(a.failed&&b.failed);}
     assert(ActiveNativeVehicleStockReplay==&a);}++cases;
    std::cout<<"EXT16_A4_NATIVE_STOCK_REPLAY_PASS "<<cases<<"\n";
}
