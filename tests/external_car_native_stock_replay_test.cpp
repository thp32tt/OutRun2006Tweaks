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
