#include <cassert>
#include <initializer_list>
#include <cwchar>
#include "../src/vr/game/external_car_selection.hpp"
using namespace OutRunVR::DinoSidecar;
int main() {
    for (int requested=0; requested<30; ++requested) {
        for (int observed=0; observed<30; ++observed) {
            const bool expected=CanonicalFerrariExternalCarId(
                    static_cast<unsigned char>(requested)) ==
                CanonicalFerrariExternalCarId(
                    static_cast<unsigned char>(observed));
            assert(MatchesFerrariSelection(
                static_cast<unsigned char>(observed),requested)==expected);
        }
    }
    for(int observed=0; observed<30; ++observed)
        assert(MatchesFerrariSelection(
            static_cast<unsigned char>(observed),-1));
    for(int selected : {-100,-2,30,255}) 
        for(int observed=0;observed<30;++observed)
            assert(!MatchesFerrariSelection(
                static_cast<unsigned char>(observed),selected));
    assert(!MatchesFerrariSelection(30u,-1));
    assert(!MatchesFerrariSelection(255u,5));
    assert(MatchesFerrariSelection(5u,20));  // tuned alias -> base
    assert(MatchesFerrariSelection(20u,5));
    for(unsigned id=0;id<256;++id){
        const auto* suffix=LegacyFerrariCarSuffix(static_cast<unsigned char>(id));
        if(id==2||id==17)assert(suffix&&std::wcscmp(suffix,L"F50_External_Test.ovc")==0);
        else if(id==7||id==22)assert(suffix&&std::wcscmp(suffix,L"ExternalCars\\288gto.ovc")==0);
        else if(id==11||id==26)assert(suffix&&std::wcscmp(suffix,L"ExternalCars\\f40.ovc")==0);
        else assert(!suffix);
    }
    return 0;
}
