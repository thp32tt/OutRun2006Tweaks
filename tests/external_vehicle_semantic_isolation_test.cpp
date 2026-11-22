#include "../src/vr/game/render_semantics.hpp"
#include <cassert>
using namespace OutRunVR::GameSemantic;
int main() {
    int originalNode=123;
    CurrentScope=RenderScope::ScreenHud;
    NextDrawScope=RenderScope::ScreenHud;
    SpriteQueueDepth=1;
    CurrentSpriteQueueNode=&originalNode;
    SpriteQueueNodeEpoch=27;
    CurrentSpriteQueueProducer=ProducerToken::RankMarkerSprani;
    CurrentQueueProjectedMarker.valid=true;
    assert(QueueRenderActive());
    assert(CurrentProjectedMarker()!=nullptr);
    {
        ScopedExternalVehicleSemantic scope;
        assert(EffectiveScope()==RenderScope::WorldBillboard);
        assert(ConsumeForDraw()==RenderScope::WorldBillboard);
        assert(NextDrawScope==RenderScope::ScreenHud);
        assert(!QueueRenderActive());
        assert(CurrentRenderProducerToken()==ProducerToken::None);
        assert(CurrentQueueProducerToken()==ProducerToken::None);
        assert(CurrentQueueNode()==nullptr);
        assert(CurrentQueueNodeEpoch()==0);
        assert(CurrentProjectedMarker()==nullptr);
        auto physical=CapturePhysicalDrawCommand();
        assert(physical.scope==RenderScope::WorldBillboard);
        assert(physical.producer==ProducerToken::None);
        assert(!physical.queued && physical.queueNode==nullptr);
        assert(physical.queueEpoch==0);
        assert(!physical.NeedsScreenStereoOrOriginal());
    }
    assert(ExternalVehicleSemanticDepth==0);
    assert(QueueRenderActive());
    assert(CurrentSpriteQueueNode==&originalNode);
    assert(CurrentQueueNodeEpoch()==27);
    assert(CurrentRenderProducerToken()==ProducerToken::RankMarkerSprani);
    assert(CurrentProjectedMarker()!=nullptr);
    assert(NextDrawScope==RenderScope::ScreenHud);
    assert(CurrentScope==RenderScope::ScreenHud);
    SpriteQueueDepth=0;
    CurrentSpriteQueueNode=nullptr;
    CurrentQueueProjectedMarker.valid=false;
    CurrentSpriteQueueProducer=ProducerToken::None;
    CurrentScope=RenderScope::None;
    NextDrawScope=RenderScope::None;
}
