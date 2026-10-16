#include "vr/game/scene_effect_wvp_provenance.hpp"
#include <cstdint>
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
    auto check=[](Evidence e, bool expected) noexcept {
        return OwnsOriginalWorldWvp(e) == expected;
    };
    if (!check(direct,true)) return 1;
    auto e=direct; e.writtenScope=RenderScope::WorldBillboard;if (!check(e,false)) return 2;
    e=direct;e.writtenScope=RenderScope::ScreenHud;if (!check(e,false)) return 3;
    e=direct;e.writtenProducer=ProducerToken::OutRunStagePrintf;if (!check(e,false)) return 4;
    e=direct;e.currentProducer=ProducerToken::StageExtensionTime;if (!check(e,false)) return 5;
    e=direct;e.currentPoseEpoch++;if (!check(e,false)) return 6;
    e=direct;e.writtenShader++;if (!check(e,false)) return 7;
    e=direct;e.currentShaderEpoch++;if (!check(e,false)) return 8;
    e=direct;e.writtenDrawSerial=104;if (!check(e,false)) return 9;
    e=direct;e.writtenDrawSerial=92;if (!check(e,true)) return 10;
    e=direct;e.writtenDrawSerial=91;if (!check(e,false)) return 11;
    e=direct;e.currentQueueNode=&e;if (!check(e,false)) return 12;
    e=direct;e.writtenQueueNode=&e;if (!check(e,false)) return 13;
    int a=0,b=0;
    e=direct;e.queued=true;e.currentQueueNode=&a;e.writtenQueueNode=&a;
    e.currentQueueEpoch=6;e.writtenQueueEpoch=6;if (!check(e,true)) return 14;
    e.writtenQueueNode=&b;if (!check(e,false)) return 15;
    e.writtenQueueNode=&a;e.writtenQueueEpoch=5;if (!check(e,false)) return 16;
    e.writtenQueueEpoch=6;e.currentQueueEpoch=0;if (!check(e,false)) return 17;
    e=direct;e.currentQueueEpoch=50;e.writtenQueueEpoch=49;if (!check(e,true)) return 18;
    return 0;
}
