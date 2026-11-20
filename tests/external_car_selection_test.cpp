#include <cassert>
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
    return 0;
}
