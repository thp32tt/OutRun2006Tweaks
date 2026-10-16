#include "vr/game/scene_effect_wvp_provenance.hpp"
#include <cassert>
using namespace OutRunVR::GameSemantic;
using namespace OutRunVR::SceneEffectWvp;
int main()
{
    constexpr Evidence direct{RenderScope::SceneEffect,
        RenderScope::SceneEffect, ProducerToken::None, ProducerToken::None,
        false, nullptr, nullptr, 91, 90,
        77, 77, 0x1234, 0x1234, 12, 12, 104, 103};
    static_assert(OwnsOriginalWorldWvp(direct));
    static_assert(!OwnsOriginalWorldWvp(Evidence{
        RenderScope::SceneEffect, RenderScope::WorldParticle,
        ProducerToken::None, ProducerToken::None, false, nullptr, nullptr,
        91, 90, 77, 77, 0x1234, 0x1234, 12, 12, 104, 103}));
    auto check=[](Evidence e, bool expected) {
        assert(OwnsOriginalWorldWvp(e) == expected);
    };
    check(direct,true);
    auto e=direct; e.writtenScope=RenderScope::WorldBillboard;check(e,false);
    e=direct;e.writtenScope=RenderScope::ScreenHud;check(e,false);
    e=direct;e.writtenProducer=ProducerToken::OutRunStagePrintf;check(e,false);
    e=direct;e.currentProducer=ProducerToken::StageExtensionTime;check(e,false);
    e=direct;e.currentPoseEpoch++;check(e,false);
    e=direct;e.writtenShader++;check(e,false);
    e=direct;e.currentShaderEpoch++;check(e,false);
    e=direct;e.writtenDrawSerial=104;check(e,false);
    e=direct;e.writtenDrawSerial=92;check(e,true);
    e=direct;e.writtenDrawSerial=91;check(e,false);
    e=direct;e.currentQueueNode=&e;check(e,false);
    e=direct;e.writtenQueueNode=&e;check(e,false);
    int a=0,b=0;
    e=direct;e.queued=true;e.currentQueueNode=&a;e.writtenQueueNode=&a;
    e.currentQueueEpoch=6;e.writtenQueueEpoch=6;check(e,true);
    e.writtenQueueNode=&b;check(e,false);
    e.writtenQueueNode=&a;e.writtenQueueEpoch=5;check(e,false);
    e.writtenQueueEpoch=6;e.currentQueueEpoch=0;check(e,false);
    e=direct;e.currentQueueEpoch=50;e.writtenQueueEpoch=49;check(e,true);
    return 0;
}
