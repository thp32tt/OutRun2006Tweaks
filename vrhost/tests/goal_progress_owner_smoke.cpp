#include "../../src/vr/game/render_semantics.hpp"
#include <iostream>

using namespace OutRunVR::GameSemantic;

static bool CheckDirectGoal(ProducerToken token)
{
    CurrentScope = RenderScope::SceneEffect;
    CurrentQueueExactScope = RenderScope::WorldBillboard;
    NextDrawScope = RenderScope::ProjectedWorldMarker2D;
    CurrentDirectExactProducer = ProducerToken::RivalMarkerSprani;
    CurrentQueueProjectedMarker = {true, 3.0f, 4.0f, 5.0f};
    {
        ScopedExactProducerSemantic goal(
            RenderScope::ScreenHud, nullptr, true, token);
        if (CurrentScope != RenderScope::ScreenHud ||
            CurrentQueueExactScope != RenderScope::None ||
            NextDrawScope != RenderScope::None ||
            CurrentDirectExactProducer != token ||
            CurrentProjectedMarker() != nullptr ||
            ConsumeForDraw() != RenderScope::ScreenHud)
            return false;
    }
    return CurrentScope == RenderScope::SceneEffect &&
        CurrentQueueExactScope == RenderScope::WorldBillboard &&
        NextDrawScope == RenderScope::ProjectedWorldMarker2D &&
        CurrentDirectExactProducer == ProducerToken::RivalMarkerSprani &&
        CurrentProjectedMarker() != nullptr &&
        CurrentProjectedMarker()->viewX == 3.0f &&
        ConsumeForDraw() == RenderScope::ProjectedWorldMarker2D;
}
int main()
{
    if (!CheckDirectGoal(ProducerToken::ResultProgress) ||
        !CheckDirectGoal(ProducerToken::GoalTime020) ||
        !CheckDirectGoal(ProducerToken::GoalTime150) ||
        // Both exact in-game HUD text families can rasterize immediately
        // during gameplay/GOAL without consuming an earlier world token.
        !CheckDirectGoal(ProducerToken::OutRunHudText) ||
        !CheckDirectGoal(ProducerToken::OutRunHudPeripheralText) ||
        // Original result Sumo_Printf parents 0x975EE/0x97727/0x977FB
        // need the same pending-world isolation and exact direct provenance.
        !CheckDirectGoal(ProducerToken::OutRunStagePrintf)) return 1;
    // Nested GOAL producer cannot hijack the current real world queue.
    SpriteQueueDepth = 1;
    CurrentScope = RenderScope::WorldParticle;
    CurrentQueueExactScope = RenderScope::ProjectedWorldMarker2D;
    CurrentDirectExactProducer = ProducerToken::None;
    NextDrawScope = RenderScope::WorldBillboard;
    CurrentQueueProjectedMarker = {true, 9.0f, 8.0f, 7.0f};
    {
        ScopedExactProducerSemantic nested(
            RenderScope::ScreenHud, nullptr, true, ProducerToken::GoalTime150);
        if (CurrentScope != RenderScope::WorldParticle ||
            CurrentQueueExactScope != RenderScope::ProjectedWorldMarker2D ||
            CurrentDirectExactProducer != ProducerToken::None ||
            NextDrawScope != RenderScope::WorldBillboard ||
            CurrentProjectedMarker()->viewX != 9.0f) return 2;
    }
    if (NextDrawScope != RenderScope::WorldBillboard) return 3;
    std::cout << "GOAL progress/time direct and queue semantic smoke PASS\n";
    return 0;
}
