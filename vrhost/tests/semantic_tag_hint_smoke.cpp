// Portable native test of the exact SpriteNode negative-miss hint.
#include "../../src/vr/game/render_semantics.hpp"
#include <array>
#include <cassert>
// Release/NDEBUG tests must still enforce frame-boundary negative cases.
#define EXPECT(x) do { if (!(x)) return __LINE__; } while (false)
#include <thread>
using namespace OutRunVR::GameSemantic;
int main()
{
    std::array<int, 4096> nodes{};
    constexpr auto hud = RenderScope::ScreenHud;
    constexpr auto generic = RenderScope::ScreenOverlay2D;
    std::thread producer([&] {
        for (int i = 0; i < 64; ++i)
            RegisterSpriteNodeScope(&nodes[i], hud,
                ProducerToken::OutRunHudPeripheralText);
    });
    producer.join();
    int definiteMisses = 0;
    for (int i = 64; i < 3064; ++i)
        if (!SpriteNodeSemanticMaybeHasTag(&nodes[i]))
            ++definiteMisses;
    EXPECT(definiteMisses > 2600);
    // Bloom false positives are allowed but never semantic authority:
    // a node with both hint bits set and no exact pointer tag stays generic.
    int falsePositives = 0;
    for (int i = 64; i < 3064; ++i)
    {
        if (!SpriteNodeSemanticMaybeHasTag(&nodes[i]))
            continue;
        ++falsePositives;
        EXPECT(PeekSpriteNodeScope(&nodes[i], generic) == generic);
        EXPECT(ConsumeSpriteNodeScope(&nodes[i], generic) == generic);
    }
    EXPECT(falsePositives > 0);
    for (int i = 0; i < 64; ++i)
    {
        EXPECT(SpriteNodeSemanticMaybeHasTag(&nodes[i]));
        ProducerToken token = ProducerToken::None;
        EXPECT(PeekSpriteNodeScope(&nodes[i], generic, &token) == hud);
        EXPECT(token == ProducerToken::OutRunHudPeripheralText);
        EXPECT(ConsumeSpriteNodeScope(&nodes[i], generic) == hud);
    }
    EXPECT(SpriteNodeSemanticPublishedCount.load() == 0);

    // Two nodes with the same two hint bits must coexist. Removing one
    // never clears another live producer's two bits.
    std::array<int, 256 * 256> first{};
    first.fill(-1);
    int a = -1, b = -1;
    for (int i = 0; i < 4096; ++i)
    {
        const auto bits = SpriteNodeSemanticHintFor(&nodes[i]);
        const unsigned lo = bits.first < bits.second ? bits.first : bits.second;
        const unsigned hi = bits.first < bits.second ? bits.second : bits.first;
        const unsigned pair = lo * 256u + hi;
        if (first[pair] != -1)
        {
            a = first[pair];
            b = i;
            break;
        }
        first[pair] = i;
    }
    EXPECT(a >= 0 && b >= 0);
    RegisterSpriteNodeScope(&nodes[a], hud);
    RegisterSpriteNodeScope(&nodes[b], RenderScope::WorldBillboard);
    EXPECT(ConsumeSpriteNodeScope(&nodes[a]) == hud);
    EXPECT(SpriteNodeSemanticMaybeHasTag(&nodes[b]));
    EXPECT(PeekSpriteNodeScope(&nodes[b]) == RenderScope::WorldBillboard);
    EXPECT(ConsumeSpriteNodeScope(&nodes[b]) == RenderScope::WorldBillboard);

    // Tags produced after queue cutoff must survive old-tag expiry.
    RegisterSpriteNodeScope(&nodes[300], hud);
    BeginSpriteQueueRender();
    RegisterSpriteNodeScope(&nodes[301], RenderScope::WorldBillboard);
    EndSpriteQueueRender();
    // A partial original queue walk may finish before this frame's
    // Present. Its unvisited old tag must still be available to a later
    // priority pass; only the explicit frame fence expires it.
    EXPECT(PeekSpriteNodeScope(&nodes[300]) == hud);
    EndSpriteQueueFrame();
    EXPECT(PeekSpriteNodeScope(&nodes[300]) == RenderScope::None);
    EXPECT(SpriteNodeSemanticMaybeHasTag(&nodes[301]));
    EXPECT(ConsumeSpriteNodeScope(&nodes[301]) == RenderScope::WorldBillboard);
    EXPECT(SpriteNodeSemanticPublishedCount.load() == 0);

    // The render queue snapshots a serial cutoff, but producer registration
    // is shared across threads. Publishing an exact +TIME node AFTER queue
    // Begin must not turn this frame's old pointer into ScreenHud, and Peek
    // (D3DX batch-owner boundary) must agree with physical Consume.
    RegisterSpriteNodeScope(&nodes[1300], hud,
        ProducerToken::OutRunHudPeripheralText);
    BeginSpriteQueueRender();
    RegisterSpriteNodeScope(&nodes[1301], hud,
        ProducerToken::StageExtensionTime);
    ProducerToken peekProducer = ProducerToken::None;
    EXPECT(PeekSpriteNodeScope(&nodes[1301], generic,
        &peekProducer) == generic);
    EXPECT(peekProducer == ProducerToken::None);
    EXPECT(PeekSpriteNodeScope(&nodes[1300], generic) == hud);
    SelectSpriteQueueNode(&nodes[1300]);
    EXPECT(EffectiveScope() == hud);
    EXPECT(CurrentRenderProducerToken() ==
        ProducerToken::OutRunHudPeripheralText);
    SelectSpriteQueueNode(&nodes[1301]);
    EXPECT(EffectiveScope() == generic);
    EXPECT(CurrentRenderProducerToken() == ProducerToken::None);
    EXPECT(CurrentProjectedMarker() == nullptr);
    EndSpriteQueueRender();
    EndSpriteQueueFrame();
    // Future tag and its negative-filter hint survive expiry of the older
    // tags; the SAME exact source is selected when the next walk starts.
    EXPECT(SpriteNodeSemanticMaybeHasTag(&nodes[1301]));
    EXPECT(PeekSpriteNodeScope(&nodes[1301]) == hud);
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&nodes[1301]);
    EXPECT(EffectiveScope() == hud);
    EXPECT(CurrentRenderProducerToken() ==
        ProducerToken::StageExtensionTime);
    EndSpriteQueueRender();
    EndSpriteQueueFrame();
    EXPECT(SpriteNodeSemanticPublishedCount.load() == 0);

    // Same generation rule covers original per-car view-space markers; do
    // not project a next-frame vehicle marker on a previous car or HUD node.
    BeginSpriteQueueRender();
    ProjectedMarkerInfo futureCar{true, 2.5f, 0.3f, 18.0f};
    RegisterSpriteNodeScope(&nodes[1302],
        RenderScope::ProjectedWorldMarker2D,
        ProducerToken::RankMarkerSprani, &futureCar);
    SelectSpriteQueueNode(&nodes[1302]);
    EXPECT(EffectiveScope() == generic);
    EXPECT(CurrentProjectedMarker() == nullptr);
    EndSpriteQueueRender();
    EndSpriteQueueFrame();
    BeginSpriteQueueRender();
    SelectSpriteQueueNode(&nodes[1302]);
    EXPECT(EffectiveScope() == RenderScope::ProjectedWorldMarker2D);
    EXPECT(CurrentProjectedMarker() != nullptr);
    EXPECT(CurrentProjectedMarker()->viewX == 2.5f);
    EXPECT(CurrentRenderProducerToken() ==
        ProducerToken::RankMarkerSprani);
    EndSpriteQueueRender();
    EndSpriteQueueFrame();
    EXPECT(SpriteNodeSemanticPublishedCount.load() == 0);

    // Exhaust the bounded registry to exercise oldest-entry eviction.
    for (int i = 0; i < static_cast<int>(SpriteNodeSemanticCapacity); ++i)
        RegisterSpriteNodeScope(&nodes[i], hud);
    const int evicted = 0;
    RegisterSpriteNodeScope(&nodes[1200], RenderScope::WorldBillboard);
    EXPECT(PeekSpriteNodeScope(&nodes[evicted]) == RenderScope::None);
    EXPECT(SpriteNodeSemanticMaybeHasTag(&nodes[1200]));
    for (int i = 1; i < static_cast<int>(SpriteNodeSemanticCapacity); ++i)
        EXPECT(ConsumeSpriteNodeScope(&nodes[i]) == hud);
    EXPECT(ConsumeSpriteNodeScope(&nodes[1200]) ==
        RenderScope::WorldBillboard);
    EXPECT(SpriteNodeSemanticPublishedCount.load() == 0);
    return 0;
}