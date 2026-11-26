#include "../src/vr/game/external_car_isolated_transaction.hpp"
#include <cassert>
#include <iostream>
using namespace OutRunVR::DinoSidecar;
int main(){
    unsigned cases=0;
    IsolatedVehicleKey key{1,0,9,4,7,123};
    assert(key.Same(key));auto wrong=key;wrong.pose++;assert(!key.Same(wrong));
    // Both eyes must run, and an incomplete/dirty first eye vetoes the second.
    for(unsigned fail=0;fail<3;++fail)for(unsigned dirty=0;dirty<2;++dirty)
    for(unsigned retire=0;retire<3;++retire){
        bool current=true;unsigned calls=0;
        const auto r=StageWholeIsolatedVehicle([&](){return current;},[&](unsigned eye){
            assert(eye==calls++);if(retire==eye+1)current=false;
            return fail==eye+1?(dirty?IsolatedStageResult::DirtyRestore:IsolatedStageResult::Unavailable):IsolatedStageResult::Complete;
        });
        const bool complete=fail==0&&retire==0;
        assert((r==IsolatedStageResult::Complete)==complete);
        assert(calls==((fail==1||retire==1)?1u:2u));++cases;
    }
    // Actual transfer algorithm: the unpublished pair is always all-stock
    // or all-candidate before fence; no mixed pair ever gets a fence.
    for(unsigned admit=0;admit<2;++admit)
    for(unsigned fail=0;fail<5;++fail)
    for(unsigned retire=0;retire<6;++retire)
    for(unsigned revoke=0;revoke<4;++revoke)
    for(unsigned fenceFail=0;fenceFail<2;++fenceFail){
        bool owner=true,candidate=bool(admit);unsigned calls=0,fences=0;
        unsigned pixels[2]{0,0};
        const auto r=TransferIsolatedPair([&](){return owner;},[&](){return candidate;},
            [&](bool external,unsigned eye){
                assert(owner);++calls;
                if(calls==retire)owner=false;
                if(calls==revoke)candidate=false;
                if(calls==fail)return false;
                pixels[eye]=external?2u:1u;return true;
            },[&](){
                assert(owner&&pixels[0]&&pixels[0]==pixels[1]);++fences;
                return !fenceFail;
            });
        if(r==IsolatedPairTransfer::Candidate||r==IsolatedPairTransfer::Stock){
            assert(fences==1&&pixels[0]==pixels[1]);
            assert(pixels[0]==(r==IsolatedPairTransfer::Candidate?2u:1u));
        }else if(r==IsolatedPairTransfer::FenceFailed)assert(fences==1);
        else assert(fences==0);
        ++cases;
    }
    std::cout<<"ISOLATED_WHOLE_VEHICLE_PAIR_PASS "<<cases<<"\n";
}
