#include "vr/game/render_semantics.hpp"
using namespace OutRunVR::GameSemantic;
int main()
{
    CurrentScope=RenderScope::SceneEffect;
    CurrentQueueExactScope=RenderScope::None;
    CurrentDirectExactProducer=ProducerToken::None;
    auto generic=CapturePhysicalDrawCommand();
    if(generic.scope!=RenderScope::SceneEffect || generic.queued ||
       generic.queueNode || !generic.CanUseGenericXyzrhwStereo() ||
       generic.IsDirectWorldLensCentre() ||
       generic.IsSourceProvenHud())return 1;

    // A directly generated stage/GOAL HUD command survives the original
    // source callback and can be reinstated at the D3DX GPU Flush boundary.
    {
        ScopedExactProducerSemantic stage(
            RenderScope::ScreenHud,nullptr,true,
            ProducerToken::StageExtensionTime);
        auto cmd=CapturePhysicalDrawCommand();
        if(cmd.queued || cmd.queueNode ||
           !cmd.CanUseGenericXyzrhwStereo() ||
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
    CurrentLensCentreCallEpoch=41;
    {
        ScopedExactLensCentreGpuDraw lens(true);
        auto cmd=CapturePhysicalDrawCommand();
        if(!cmd.IsDirectWorldLensCentre() ||
           cmd.CanUseGenericXyzrhwStereo() ||
           cmd.IsSourceProvenHud() || cmd.queueNode ||
           cmd.lensCentreCallEpoch!=41) return 7;
        // A later nested source mutation must not rewrite the already captured
        // physical primitive identity.
        CurrentLensCentreCallEpoch=42;
        if(cmd.lensCentreCallEpoch!=41) return 8;
    }
    CurrentLensCentreCallEpoch=0;
    if(CapturePhysicalDrawCommand().IsDirectWorldLensCentre() ||
       CapturePhysicalDrawCommand().lensCentreCallEpoch!=0)
        return 9;
    {
        // Producer/scope alone are insufficient: without a D3A5 call epoch
        // there is no source-owned central sun to reproject.
        ScopedExactLensCentreGpuDraw lens(true);
        if(CapturePhysicalDrawCommand().IsDirectWorldLensCentre())
            return 10;
    }
    // Quest-inspired separation of source commands from the physical
    // shadow draw: only a *direct* player car world particle may use
    // native world WVP. A queued sprite with the same token is not proof.
    {
        ScopedExactProducerSemantic shadow(
            RenderScope::WorldParticle,nullptr,true,
            ProducerToken::CarBaseShadow);
        const auto cmd=CapturePhysicalDrawCommand();
        if (!cmd.IsDirectCarBaseShadow() || cmd.IsSourceProvenHud() ||
            cmd.IsDirectWorldLensCentre())return 11;
    }
    if(CapturePhysicalDrawCommand().IsDirectCarBaseShadow())
        return 12;
    int other=0;
    RegisterSpriteNodeScope(&other,RenderScope::WorldParticle,
        ProducerToken::CarBaseShadow);
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&other);
    if(CapturePhysicalDrawCommand().IsDirectCarBaseShadow())
        return 13;
    EndSpriteQueueRender();

    // R84 physical GPU dispatch: if R30 cannot prove the finite HUD eye
    // plane, none of these exact source owners may borrow R31's cached road
    // world WVP. Both direct D3DX Flush and tagged SpriteNode draws are
    // tested, including GOAL progress and B9200's source-proven glyphs.
    const ProducerToken results[]{
        ProducerToken::StageExtensionTime,
        ProducerToken::GoalTime020,
        ProducerToken::GoalTime150,
        ProducerToken::ResultProgress,
        ProducerToken::OutRunStagePrintf,
        ProducerToken::ResultTextB9200
    };
    for (auto producer : results)
    {
        CurrentScope=RenderScope::SceneEffect;
        {
            ScopedExactProducerSemantic owner(
                RenderScope::ScreenHud, nullptr, true, producer);
            const auto c=CapturePhysicalDrawCommand();
            if (c.queued || !c.IsExactFiniteResultHud() ||
                !c.IsSourceProvenHud() || c.IsDirectWorldLensCentre())
                return 12;
        }
        int glyph=0;
        RegisterSpriteNodeScope(&glyph,RenderScope::ScreenHud,producer);
        BeginSpriteQueueRender();
        SelectSpriteQueueNode(&glyph);
        const auto c=CapturePhysicalDrawCommand();
        if (!c.queued || c.queueNode!=&glyph || c.queueEpoch==0 ||
            !c.IsExactFiniteResultHud()) return 13;
        EndSpriteQueueRender();
    }
    // Unknown or wrong-scope tokens, rank markers, world shadows and the
    // original D3A5 sun retain their existing world/marking routes.
    CurrentScope=RenderScope::ScreenHud;
    {
        ScopedExactProducerSemantic notAResult(
            RenderScope::ScreenHud,nullptr,true,
            ProducerToken::DispRankFirst);
        if(CapturePhysicalDrawCommand().IsExactFiniteResultHud())
            return 14;
    }
    {
        ScopedExactProducerSemantic foreign(
            RenderScope::WorldBillboard,nullptr,true,
            ProducerToken::StageExtensionTime);
        if(CapturePhysicalDrawCommand().IsExactFiniteResultHud())
            return 15;
    }
    {
        ScopedExactProducerSemantic generic(
            RenderScope::ScreenOverlay2D,nullptr,true,
            ProducerToken::ResultProgress);
        if(CapturePhysicalDrawCommand().IsExactFiniteResultHud())
            return 16;
    }
    CurrentScope=RenderScope::WorldBillboard;
    {
        ScopedExactLensCentreGpuDraw lens(true);
        if(CapturePhysicalDrawCommand().IsExactFiniteResultHud())
            return 17;
    }
    CurrentScope=RenderScope::SceneEffect;
    if(CapturePhysicalDrawCommand().IsExactFiniteResultHud())
        return 18;
    // R84 physical R33::ConsumeForDraw used to eat TIME RECORD's pending
    // one-shot when the independent exact +TIME queue rendered first. The
    // queued draw looked correctly tagged to R30, but the *next* original
    // TIME RECORD glyph silently lost its ScreenHud scope. Check both GPU
    // commands, not just the immediate queue classification.
    CurrentScope = RenderScope::SceneEffect;
    NextDrawScope = RenderScope::None;
    ArmNextDraw(RenderScope::ScreenHud);
    int extensionNode = 0;
    RegisterSpriteNodeScope(&extensionNode, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime);
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&extensionNode);
    if (ConsumeForDraw() != RenderScope::ScreenHud ||
        NextDrawScope != RenderScope::ScreenHud ||
        !CapturePhysicalDrawCommand().IsExactFiniteResultHud()) return 19;
    EndSpriteQueueRender();
    if (ConsumeForDraw() != RenderScope::ScreenHud ||
        NextDrawScope != RenderScope::None) return 20;

    // A physical projected-car glyph must preserve its own world anchor
    // and leave any previously armed unrelated direct text owner intact.
    ArmNextDraw(RenderScope::ScreenHud);
    int rankNode = 0;
    ProjectedMarkerInfo rankAnchor{true, 0.25f, -0.5f, 19.0f};
    RegisterSpriteNodeScope(&rankNode,
        RenderScope::ProjectedWorldMarker2D,
        ProducerToken::RankMarkerSprani, &rankAnchor);
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&rankNode);
    if (ConsumeForDraw() != RenderScope::ProjectedWorldMarker2D ||
        NextDrawScope != RenderScope::ScreenHud ||
        CapturePhysicalDrawCommand().scope !=
            RenderScope::ProjectedWorldMarker2D ||
        !CurrentProjectedMarker()) return 21;
    EndSpriteQueueRender();
    if (ConsumeForDraw() != RenderScope::ScreenHud) return 22;

    // No exact SpriteNode tag: preserve original one-shot behavior for
    // unclassified native clips and unchanged TIME RECORD call patterns.
    ArmNextDraw(RenderScope::ScreenHud);
    int genericNode = 0;
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&genericNode);
    if (ConsumeForDraw() != RenderScope::ScreenHud ||
        NextDrawScope != RenderScope::None) return 23;
    EndSpriteQueueRender();

    // External F11 must neither consume the game token nor acquire its HUD.
    ArmNextDraw(RenderScope::ScreenHud);
    {
        ScopedExternalOverlaySemantic overlay(RenderScope::ScreenOverlay2D);
        if (ConsumeForDraw() != RenderScope::ScreenOverlay2D ||
            NextDrawScope != RenderScope::ScreenHud) return 24;
    }
    if (ConsumeForDraw() != RenderScope::ScreenHud ||
        NextDrawScope != RenderScope::None) return 25;
    return 0;
}
