#include "vr/game/car_base_shadow_stereo.hpp"
#include <iostream>
using namespace OutRunVR;
int main()
{
    using GameSemantic::ProducerToken;
    using GameSemantic::RenderScope;
    constexpr auto player = ProducerToken::CarBaseShadow;
    constexpr auto world = RenderScope::WorldParticle;
    const auto eligible = [](ProducerToken p, RenderScope scope,
        bool queue, bool wvp, bool off, bool write, bool stencil, bool flat) {
        return CarShadowStereo::CanUseSpatialShadow(
            p, scope, queue, wvp, off, write, stencil, flat);
    };
    if (!eligible(player,world,false,true,true,false,false,false) ||
        eligible(player,world,true,true,true,false,false,false) ||
        eligible(player,world,false,false,true,false,false,false) ||
        eligible(player,world,false,true,true,true,false,false) ||
        eligible(player,world,false,true,true,false,true,false) ||
        eligible(player,world,false,true,true,false,false,true) ||
        eligible(player,world,false,true,false,false,false,false) ||
        eligible(player,RenderScope::ScreenHud,false,true,true,false,false,false) ||
        eligible(ProducerToken::LensFlareCentre,world,false,true,true,false,false,false) ||
        eligible(ProducerToken::None,world,false,true,true,false,false,false))
    {
        std::cerr << "R84 contact shadow eye-owner FAIL\n";
        return 1;
    }
    std::cout << "R84 contact shadow eye-owner PASS\n";
    return 0;
}
