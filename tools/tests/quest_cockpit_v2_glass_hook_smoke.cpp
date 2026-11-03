#include "../../src/vr/game/quest_cockpit_v2_glass_hook.hpp"
#include <cassert>
#include <cmath>
using namespace OutRunVR::QuestCockpitV2::Glass;
int main(){
    assert(GlassDiffuse(.3f,.3f,.3f,.55f));
    assert(GlassDiffuse(.3f,.3f,.3f,.425f));
    assert(!GlassDiffuse(.3f,.3f,.3f,.50f));
    assert(!GlassDiffuse(.3f,.3f,.3f,1.f));
    assert(!GlassDiffuse(1.f,1.f,1.f,.55f));
    assert(!GlassDiffuse(.3f,.31f,.3f,.55f));
    assert(!GlassDiffuse(.3f,.3f,.3f,NAN));
    assert(std::fabs(AlphaFromBrightness(0)-.9f)<1e-6f);
    assert(std::fabs(AlphaFromBrightness(50)-.5f)<1e-6f);
    assert(std::fabs(AlphaFromBrightness(75)-.3f)<1e-6f);
    assert(std::fabs(AlphaFromBrightness(100)-.1f)<1e-6f);
    assert(!Admit(true,true,true,true,true,true,true,false,true,true,true,true));
    assert(!Admit(true,true,true,true,true,true,false,true,true,true,true,true));
    assert(!Admit(true,true,true,true,true,true,true,true,false,true,true,true));
    assert(!Admit(true,true,true,true,true,true,true,true,true,true,true,false));
    assert(Admit(true,true,true,true,true,true,true,true,true,true,true,true));
}
