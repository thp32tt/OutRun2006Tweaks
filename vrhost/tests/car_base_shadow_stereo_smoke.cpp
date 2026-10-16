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
    const CarShadowStereo::DirectGameWvpOwner source{
        17,17,46,45,0x100,0x100,8,8,
        world,player,false
    };
    if (!CarShadowStereo::OwnsDirectGameWvp(source))
    {
        std::cerr << "R84 direct car shadow original WVP ownership FAIL\n";
        return 2;
    }
    const auto rejected = [&](const auto& changed) {
        return !CarShadowStereo::OwnsDirectGameWvp(changed);
    };
    auto mutation = source;
    mutation.uploadedPoseEpoch = 16;
    if (!rejected(mutation)) return 3;
    mutation = source; mutation.uploadDrawSerial = 44;
    if (!rejected(mutation)) return 4; // stale vehicle / preceding draw
    mutation = source; mutation.nextDrawSerial = 0;
    if (!rejected(mutation)) return 5; // draw serial wrap
    mutation = source; mutation.uploadShader = 0x200;
    if (!rejected(mutation)) return 6;
    mutation = source; mutation.uploadShaderEpoch = 7;
    if (!rejected(mutation)) return 7;
    mutation = source; mutation.uploadScope = RenderScope::ScreenHud;
    if (!rejected(mutation)) return 8;
    mutation = source; mutation.uploadProducer = ProducerToken::LensFlareCentre;
    if (!rejected(mutation)) return 9;
    mutation = source; mutation.uploadedWhileQueued = true;
    if (!rejected(mutation)) return 10;
    mutation = source; mutation.currentPoseEpoch = 0;
    if (!rejected(mutation)) return 11;
    mutation = source; mutation.currentShader = 0;
    if (!rejected(mutation)) return 12;
    mutation = source; mutation.currentShaderEpoch = 0;
    if (!rejected(mutation)) return 13;
    std::cout << "R84 contact shadow eye-owner PASS\n";
    return 0;
}
