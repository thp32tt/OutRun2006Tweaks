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
    for(int model:{2,17,5})for(unsigned group=1;group<=3;++group){
        NativeVehicleStockReplay r{};r.model=model;r.opened=group;r.group=true;
        const auto prefix=model==2?0x30000u:0x1500000u;
        const unsigned part=group==1?0x11u:group==2?0u:1u;
        assert(r.OwnsObject(prefix|part)==(model!=5));
        assert(!r.OwnsObject(0x570008u));
        assert(!r.OwnsObject(prefix|0xffffu));++cases;
    }
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
