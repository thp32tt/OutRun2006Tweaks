#include "../../src/vr/game/quest_cockpit_v2_glass_hook.hpp"
#include <cassert>
#include <cmath>
using namespace OutRunVR::QuestCockpitV2::Glass;
int main(){
    // Keep normal diffusion/blend flags when stripping ONLY glass reflect.
    constexpr std::uint32_t mode5=(5u<<19)|0x5101u|0x40000000u;
    constexpr std::uint32_t mode4=(4u<<19)|0x5401u;
    constexpr std::uint32_t normal=(3u<<19)|0x5101u;
    static_assert((RemoveGlassReflectionFlags(mode5)&(15u<<19))==0u);
    static_assert((RemoveGlassReflectionFlags(mode4)&(15u<<19))==0u);
    static_assert((RemoveGlassReflectionFlags(normal)&(15u<<19))==(3u<<19));
    static_assert((RemoveGlassReflectionFlags(mode5)&0x5100u)==0x5100u);
    static_assert((RemoveGlassReflectionFlags(mode4)&1u)==0);
    static_assert(RemoveGlassReflectionLayer(0x8au|0x003fe000u)==0x003fe000u);
    static_assert(RemoveGlassReflectionLayer(0x1u)==0x1u);
    float normalColour[18]{};
    for(unsigned i=0;i<18;++i)normalColour[i]=1.f;
    SuppressGlassReflectionColours(normalColour,false);
    for(unsigned i=0;i<8;++i)assert(normalColour[i]==1.f);
    for(unsigned i=8;i<16;++i)assert(normalColour[i]==0.f);
    assert(normalColour[16]==1.f&&normalColour[17]==1.f);
    SuppressGlassReflectionColours(normalColour,true);
    for(unsigned i=0;i<16;++i)assert(normalColour[i]==0.f);
    assert(normalColour[16]==1.f&&normalColour[17]==-1.f);
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
