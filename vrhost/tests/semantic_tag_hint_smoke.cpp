// Portable native test of the exact SpriteNode negative-miss hint.
#include "../../src/vr/game/render_semantics.hpp"
#include <array>
#include <cassert>
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
    assert(definiteMisses > 2800);
    for (int i = 0; i < 64; ++i)
    {
        assert(SpriteNodeSemanticMaybeHasTag(&nodes[i]));
        ProducerToken token = ProducerToken::None;
        assert(PeekSpriteNodeScope(&nodes[i], generic, &token) == hud);
        assert(token == ProducerToken::OutRunHudPeripheralText);
        assert(ConsumeSpriteNodeScope(&nodes[i], generic) == hud);
    }
    assert(SpriteNodeSemanticPublishedCount.load() == 0);

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
    assert(a >= 0 && b >= 0);
    RegisterSpriteNodeScope(&nodes[a], hud);
    RegisterSpriteNodeScope(&nodes[b], RenderScope::WorldBillboard);
    assert(ConsumeSpriteNodeScope(&nodes[a]) == hud);
    assert(SpriteNodeSemanticMaybeHasTag(&nodes[b]));
    assert(PeekSpriteNodeScope(&nodes[b]) == RenderScope::WorldBillboard);
    assert(ConsumeSpriteNodeScope(&nodes[b]) == RenderScope::WorldBillboard);

    // Tags produced after queue cutoff must survive old-tag expiry.
    RegisterSpriteNodeScope(&nodes[300], hud);
    BeginSpriteQueueRender();
    RegisterSpriteNodeScope(&nodes[301], RenderScope::WorldBillboard);
    EndSpriteQueueRender();
    assert(PeekSpriteNodeScope(&nodes[300]) == RenderScope::None);
    assert(SpriteNodeSemanticMaybeHasTag(&nodes[301]));
    assert(ConsumeSpriteNodeScope(&nodes[301]) == RenderScope::WorldBillboard);
    assert(SpriteNodeSemanticPublishedCount.load() == 0);

    // Exhaust the bounded registry to exercise oldest-entry eviction.
    for (int i = 0; i < static_cast<int>(SpriteNodeSemanticCapacity); ++i)
        RegisterSpriteNodeScope(&nodes[i], hud);
    const int evicted = 0;
    RegisterSpriteNodeScope(&nodes[1200], RenderScope::WorldBillboard);
    assert(PeekSpriteNodeScope(&nodes[evicted]) == RenderScope::None);
    assert(SpriteNodeSemanticMaybeHasTag(&nodes[1200]));
    for (int i = 1; i < static_cast<int>(SpriteNodeSemanticCapacity); ++i)
        assert(ConsumeSpriteNodeScope(&nodes[i]) == hud);
    assert(ConsumeSpriteNodeScope(&nodes[1200]) ==
        RenderScope::WorldBillboard);
    assert(SpriteNodeSemanticPublishedCount.load() == 0);
    return 0;
}
