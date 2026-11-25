// Reject unrelated geometry before the stateful R29 stereo safety query.
#include "../src/vr/game/rank_marker_fixedfn_r62.hpp"
#include <cassert>

int main()
{
    using OutRunVR::RankMarker::ExactR84FixedFnSpritePreflight;
    unsigned cases=0;
    for(unsigned slot=0;slot<16;++slot)
    for(unsigned mask=0;mask<256;++mask) {
        const bool device=mask&1u, triangle=mask&2u, projected=mask&4u;
        const bool marker=mask&8u, hud=mask&16u, pause=mask&32u;
        const bool backbuffer=mask&64u, stable=mask&128u;
        unsigned targetCalls=0, stableCalls=0, monoArms=0;
        const bool admitted=ExactR84FixedFnSpritePreflight(
            device,triangle,projected,marker,hud,pause,
            [&] {++targetCalls; return backbuffer;},
            [&] {++stableCalls; if(!stable)++monoArms; return stable;});
        const bool owned=device && triangle &&
            ((projected && marker) || (!projected && (hud || pause)));
        assert(admitted==(owned && backbuffer && stable));
        assert(targetCalls==(owned?1u:0u));
        assert(stableCalls==((owned && backbuffer)?1u:0u));
        assert(monoArms==((owned && backbuffer && !stable)?1u:0u));
        ++cases;
    }
    assert(cases==4096u);
    unsigned oldChecks=0,newChecks=0;
    const bool oldAdmitted=true && true && ([&]{++oldChecks;return true;})()
        && (false || false || false);
    const bool newAdmitted=ExactR84FixedFnSpritePreflight(
        true,true,false,false,false,false,[]{return true;},
        [&]{++newChecks;return true;});
    assert(!oldAdmitted && !newAdmitted && oldChecks==1u && newChecks==0u);
}
