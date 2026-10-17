// Native portable R84 gameplay ScreenHud source-ownership regression.
// Run without a D3D9 game device; the Windows game TU uses this same predicate.
#include "../../src/vr/d3d9/hud_original_wvp_provenance.hpp"
#define CHECK(v) do { if (!(v)) return __LINE__; } while (false)

int main()
{
    using namespace OutRunVR::GameSemantic;
    using namespace OutRunVR::HudOriginalWvp;
    Provenance direct = DirectHud;
    CHECK(OwnsProducer(direct));
    direct.writtenScope = RenderScope::WorldBillboard;
    CHECK(!OwnsProducer(direct));
    direct = DirectHud;
    direct.currentScope = RenderScope::ScreenOverlay2D;
    CHECK(!OwnsProducer(direct));
    direct = DirectHud;
    direct.writtenProducer = ProducerToken::StageExtensionTime;
    CHECK(!OwnsProducer(direct));
    direct = DirectHud;
    direct.currentProducer = ProducerToken::None;
    CHECK(!OwnsProducer(direct));
    direct = DirectHud;
    int one = 1, two = 2;
    direct.queueActive = true;
    direct.currentNode = &one;
    direct.writtenNode = &one;
    direct.currentNodeEpoch = 12;
    direct.writtenNodeEpoch = 12;
    CHECK(OwnsProducer(direct));
    direct.writtenNode = &two;
    CHECK(!OwnsProducer(direct)); // other glyph with same shader/prod
    direct.writtenNode = &one;
    direct.writtenNodeEpoch = 11;
    CHECK(!OwnsProducer(direct)); // replayed stale queue node
    direct.writtenNodeEpoch = 12;
    direct.currentNodeEpoch = 0;
    CHECK(!OwnsProducer(direct)); // unlatched frame queue
    direct.currentNodeEpoch = 12;
    direct.currentNode = nullptr;
    CHECK(!OwnsProducer(direct)); // no active owned node
    direct.currentNode = &one;
    direct.queueActive = false;
    CHECK(!OwnsProducer(direct)); // queued source cannot become direct
    direct = DirectHud;
    CHECK(OwnsProducer(direct));  // direct E8/ScreenHud unaffected

    // One thousand R26 -> R84 callback-ownership comparisons: each case
    // varies producer, node, queue generation, exact screen scope and
    // whether a shader has merely retained an unrelated WVP.
    // The *only* admitted generic overlay is a complete live same-node
    // raw original. Other variants must never inherit the prior road eye.
    int admitted = 0, rejected = 0;
    for (int i = 0; i < 1000; ++i)
    {
        Provenance p{
            RenderScope::ScreenOverlay2D,
            RenderScope::ScreenOverlay2D,
            ProducerToken::None, ProducerToken::None,
            true, &one, &one,
            static_cast<std::uint64_t>(i + 1),
            static_cast<std::uint64_t>(i + 1)
        };
        switch (i % 10)
        {
            case 1: p.writtenNode = &two; break;   // older SpriteNode c64
            case 2: --p.writtenNodeEpoch; break;  // previous queue generation
            case 3: p.currentScope = RenderScope::ScreenHud; break;
            case 4: p.writtenScope = RenderScope::WorldBillboard; break;
            case 5: p.currentProducer = ProducerToken::OutRunHudText; break;
            case 6: p.writtenProducer = ProducerToken::DispRankFirst; break;
            case 7: p.queueActive = false; break;
            case 8: p.currentNode = nullptr; break;
            case 9: p.currentNodeEpoch = 0; break;
            default: break;
        }
        const bool good = (i % 10 == 0);
        CHECK(OwnsGenericQueuedOverlay(p) == good);
        CHECK(!OwnsProducer(p)); // unknown queue ≠ exact ScreenHud
        if (good) ++admitted; else ++rejected;
    }
    CHECK(admitted == 100 && rejected == 900);
    return 0;
}
