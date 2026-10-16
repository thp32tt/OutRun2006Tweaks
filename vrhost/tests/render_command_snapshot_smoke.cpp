#include "vr/game/render_semantics.hpp"
using namespace OutRunVR::GameSemantic;
int main()
{
    CurrentScope=RenderScope::SceneEffect;
    CurrentQueueExactScope=RenderScope::None;
    CurrentDirectExactProducer=ProducerToken::None;
    auto generic=CapturePhysicalDrawCommand();
    if(generic.scope!=RenderScope::SceneEffect || generic.queued ||
       generic.queueNode || generic.IsDirectWorldLensCentre() ||
       generic.IsSourceProvenHud())return 1;

    // A directly generated stage/GOAL HUD command survives the original
    // source callback and can be reinstated at the D3DX GPU Flush boundary.
    {
        ScopedExactProducerSemantic stage(
            RenderScope::ScreenHud,nullptr,true,
            ProducerToken::StageExtensionTime);
        auto cmd=CapturePhysicalDrawCommand();
        if(cmd.queued || cmd.queueNode ||
           cmd.scope!=RenderScope::ScreenHud ||
           cmd.producer!=ProducerToken::StageExtensionTime ||
           !cmd.IsSourceProvenHud())return 2;
    }
    if(CapturePhysicalDrawCommand().producer!=ProducerToken::None)
        return 3;

    // A live queued WorldBillboard must win over any nested direct HUD.
    int marker=0;
    RegisterSpriteNodeScope(&marker,RenderScope::WorldBillboard,
        ProducerToken::RivalMarkerSprani);
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&marker);
    const auto queued=CapturePhysicalDrawCommand();
    if(!queued.queued || queued.queueNode!=&marker ||
       queued.queueEpoch==0 ||
       queued.scope!=RenderScope::WorldBillboard ||
       queued.producer!=ProducerToken::RivalMarkerSprani ||
       queued.IsSourceProvenHud())return 4;
    {
        ScopedExactProducerSemantic direct(
            RenderScope::ScreenHud,nullptr,true,
            ProducerToken::StageExtensionTime);
        const auto inside=CapturePhysicalDrawCommand();
        if(!inside.queued || inside.queueNode!=&marker ||
            inside.producer!=ProducerToken::RivalMarkerSprani)
            return 5;
    }
    EndSpriteQueueRender();
    if(CapturePhysicalDrawCommand().queued ||
       CapturePhysicalDrawCommand().queueNode != nullptr)
        return 6;
    // The exact D3A5→C993 owner must remain direct, never promoted by
    // generic screen HUD or queued caller-derived source information.
    CurrentScope=RenderScope::WorldBillboard;
    {
        ScopedExactLensCentreGpuDraw lens(true);
        auto cmd=CapturePhysicalDrawCommand();
        if(!cmd.IsDirectWorldLensCentre() ||
           cmd.IsSourceProvenHud() || cmd.queueNode) return 7;
    }
    if(CapturePhysicalDrawCommand().IsDirectWorldLensCentre())
        return 8;
    return 0;
}
