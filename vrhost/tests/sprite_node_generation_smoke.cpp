#include "vr/game/render_semantics.hpp"
#include <thread>
using namespace OutRunVR::GameSemantic;
int main()
{
    int node=0, sibling=0;
    RegisterSpriteNodeScope(&node,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime);
    BeginSpriteQueueRender();
    const auto oldCutoff=SpriteQueueSemanticCutoff;
    std::thread next([&] {
        RegisterSpriteNodeScope(&node,RenderScope::WorldBillboard,
            ProducerToken::RivalMarkerSprani);
        // Re-registering the SAME future generation updates only future,
        // not the old stage-owner tag being drained on this thread.
        RegisterSpriteNodeScope(&node,RenderScope::ProjectedWorldMarker2D,
            ProducerToken::RankMarkerSprani);
    });
    next.join();
    if(SpriteNodeSemanticCount != 2 ||
        SpriteNodeSemanticActiveQueueCutoff != oldCutoff)return 1;
    ProducerToken producer=ProducerToken::None;
    if(PeekSpriteNodeScope(&node,RenderScope::None,&producer) !=
            RenderScope::ScreenHud ||
       producer != ProducerToken::StageExtensionTime)return 2;
    SelectSpriteQueueNode(&node);
    if(CurrentQueueProducerToken()!=ProducerToken::StageExtensionTime ||
       CurrentScope!=RenderScope::ScreenHud)return 3;
    EndSpriteQueueRender();
    if(SpriteNodeSemanticCount!=1 ||
        SpriteNodeSemanticActiveQueueCutoff!=0 ||
        !SpriteNodeSemanticMaybeHasTag(&node))return 4;
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&node);
    if(CurrentQueueProducerToken()!=ProducerToken::RankMarkerSprani ||
       CurrentScope!=RenderScope::ProjectedWorldMarker2D)return 5;
    EndSpriteQueueRender();
    if(SpriteNodeSemanticCount || SpriteNodeSemanticMaybeHasTag(&node))return 6;

    // Ordinary repeated writes to a node with no live queue should retain
    // the original one-record-per-pointer fast path.
    RegisterSpriteNodeScope(&sibling,RenderScope::ScreenHud,
        ProducerToken::DispRankFirst);
    RegisterSpriteNodeScope(&sibling,RenderScope::ScreenHud,
        ProducerToken::DispRankClipSprite);
    if(SpriteNodeSemanticCount!=1)return 7;
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&sibling);
    if(CurrentQueueProducerToken()!=ProducerToken::DispRankClipSprite)return 8;
    EndSpriteQueueRender();

    // Force saturation with all 560 slots snapshotted. A cross-thread
    // next-frame producer must not replace the still-valid original tag.
    int slots[SpriteNodeSemanticCapacity]{};
    for(std::size_t i=0;i<SpriteNodeSemanticCapacity;++i)
        RegisterSpriteNodeScope(&slots[i],RenderScope::ScreenHud,
            ProducerToken::StageExtensionTime);
    if(SpriteNodeSemanticCount!=SpriteNodeSemanticCapacity)return 9;
    BeginSpriteQueueRender();
    std::thread overflow([&]{
        RegisterSpriteNodeScope(&slots[0],RenderScope::WorldBillboard,
            ProducerToken::RivalMarkerSprani);
    });
    overflow.join();
    if(SpriteNodeSemanticProtectedDrops.load()!=1 ||
       SpriteNodeSemanticCount!=SpriteNodeSemanticCapacity)return 10;
    SelectSpriteQueueNode(&slots[0]);
    if(CurrentQueueProducerToken()!=ProducerToken::StageExtensionTime)return 11;
    EndSpriteQueueRender();
    if(SpriteNodeSemanticCount != 0)return 12;
    return 0;
}