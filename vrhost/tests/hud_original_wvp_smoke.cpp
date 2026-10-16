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
    return 0;
}
