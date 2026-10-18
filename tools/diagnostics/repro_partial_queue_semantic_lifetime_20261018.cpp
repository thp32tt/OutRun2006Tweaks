// Read-only diagnostic: reproduce a queue lifetime gap in R84 semantics.
// Build (GCC/Clang): c++ -std=c++20 -O0 -pthread -Isrc
//   tools/diagnostics/repro_partial_queue_semantic_lifetime_20261018.cpp -o /tmp/queue-repro
// Modes: --expect-broken passes on confirmed old behavior; --expect-fixed
// should FAIL before the repair and PASS after a complete, reviewed repair.
// Does not hook the game, mutate any game executable or allocate GPU resources.
#include "vr/game/render_semantics.hpp"
#include <cstdio>
#include <cstring>
#include <thread>
using namespace OutRunVR::GameSemantic;

int main(int argc, char** argv)
{
    int normalA=0, normalB=0;
    RegisterSpriteNodeScope(&normalA, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime);
    RegisterSpriteNodeScope(&normalB,
        RenderScope::ProjectedWorldMarker2D,
        ProducerToken::RankMarkerSprani);
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&normalA);
    const bool controlA = CurrentQueueProducerToken() ==
        ProducerToken::StageExtensionTime;
    SelectSpriteQueueNode(&normalB);
    const bool controlB = CurrentQueueProducerToken() ==
        ProducerToken::RankMarkerSprani;
    EndSpriteQueueRender();
    EndSpriteQueueFrame();
    if (!controlA || !controlB)
    {
        std::puts("CONTROL_SINGLE_WALK=FAILED");
        return 3;
    }
    std::puts("CONTROL_SINGLE_WALK=PASSED");

    int first=0, later=0;
    RegisterSpriteNodeScope(&first, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime);
    RegisterSpriteNodeScope(&later,
        RenderScope::ProjectedWorldMarker2D,
        ProducerToken::RankMarkerSprani);

    // Original EXE: 0x00449050 stage 8 conditionally calls 0x004C50A0;
    // that helper calls 0x0042D710(0, 5 or 7) when enabled.
    // The main frame path then calls the same queue renderer again.
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&first);
    const bool firstOk = CurrentQueueProducerToken() ==
        ProducerToken::StageExtensionTime;
    EndSpriteQueueRender();

    const bool laterTagStillAvailable =
        PeekSpriteNodeScope(&later) ==
        RenderScope::ProjectedWorldMarker2D;
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&later);
    const bool laterOwnerSurvived =
        CurrentQueueProducerToken() ==
        ProducerToken::RankMarkerSprani &&
        CurrentScope == RenderScope::ProjectedWorldMarker2D;
    EndSpriteQueueRender();
    EndSpriteQueueFrame();
    const bool noOldTagAfterFrame =
        !SpriteNodeSemanticMaybeHasTag(&later) &&
        PeekSpriteNodeScope(&later) == RenderScope::None;

    // If no later full walk occurs, the end-of-frame fence must remove
    // abandoned old tags rather than leaking them into the next frame.
    int abandoned=0, visited=0;
    RegisterSpriteNodeScope(&visited, RenderScope::ScreenHud,
        ProducerToken::DispRankFirst);
    RegisterSpriteNodeScope(&abandoned, RenderScope::WorldBillboard,
        ProducerToken::RivalMarkerSprani);
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&visited);
    EndSpriteQueueRender();
    const bool abandonedSurvivesPartial =
        PeekSpriteNodeScope(&abandoned) == RenderScope::WorldBillboard;
    EndSpriteQueueFrame();
    const bool abandonedClearedAtPresent =
        !SpriteNodeSemanticMaybeHasTag(&abandoned);

    // A future generation of the SAME physical node can arrive on another
    // producer thread during the current queue walk. Never consume it with
    // the old priority walk or discard it at the current frame's Present.
    int reused=0;
    RegisterSpriteNodeScope(&reused, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime);
    BeginSpriteQueueRender();
    std::thread future([&] {
        RegisterSpriteNodeScope(&reused,
            RenderScope::ProjectedWorldMarker2D,
            ProducerToken::RankMarkerSprani);
    });
    future.join();
    SelectSpriteQueueNode(&reused);
    const bool oldConsumed =
        CurrentQueueProducerToken() == ProducerToken::StageExtensionTime;
    EndSpriteQueueRender();
    EndSpriteQueueFrame();
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&reused);
    const bool nextGenerationPreserved =
        CurrentQueueProducerToken() == ProducerToken::RankMarkerSprani;
    EndSpriteQueueRender();
    EndSpriteQueueFrame();

    // Reset or device-loss invalidates the entire original ring even
    // without a final canonical queue visit.
    int resetNode=0;
    RegisterSpriteNodeScope(&resetNode, RenderScope::ScreenHud,
        ProducerToken::GoalTime020);
    BeginSpriteQueueRender();
    EndSpriteQueueRender();
    EndSpriteQueueFrame(true);
    const bool resetClearsTag =
        !SpriteNodeSemanticMaybeHasTag(&resetNode) &&
        SpriteNodeSemanticCount == 0;

    const bool preserved =
        firstOk && laterTagStillAvailable && laterOwnerSurvived &&
        noOldTagAfterFrame && abandonedSurvivesPartial &&
        abandonedClearedAtPresent && oldConsumed &&
        nextGenerationPreserved && resetClearsTag;
    std::printf("CASE=PARTIAL_THEN_FULL initial=%u after_partial=%u final=%u\n",
        unsigned(firstOk), unsigned(laterTagStillAvailable),
        unsigned(laterOwnerSurvived));
    std::printf("UNVISITED_PRODUCER_PRESERVED=%s\n",
        preserved ? "YES" : "NO");
    std::printf("FRAME_FENCE=%u NEXT_GENERATION=%u RESET=%u\n",
        unsigned(abandonedClearedAtPresent),
        unsigned(nextGenerationPreserved), unsigned(resetClearsTag));
    if (argc > 1 && std::strcmp(argv[1], "--expect-fixed") == 0)
        return preserved ? 0 : 42;
    if (argc > 1 && std::strcmp(argv[1], "--expect-broken") == 0)
        return preserved ? 42 : 0;
    return 0;
}