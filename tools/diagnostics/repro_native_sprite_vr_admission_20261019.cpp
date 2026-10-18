#include "../../src/vr/game/direct_sprite_source_provenance.hpp"
#include <cassert>
int main()
{
    using namespace OutRunVR::DirectSpriteSource;
    using OutRunVR::GameSemantic::RenderScope;
    using OutRunVR::GameSemantic::ProducerToken;
    const Snapshot hud{RenderScope::ScreenHud,
        ProducerToken::DispRankFirst, false, false, 99};
    assert(TestNativeDirectVrAdmission());
    assert(CanAdmitNativeDirectNodeTags(true, true, hud, hud));
    assert(!CanAdmitNativeDirectNodeTags(false, true, hud, hud));
    assert(!CanAdmitNativeDirectNodeTags(true, false, hud, hud));
    auto modified = hud;
    modified.queueActive = true;
    assert(!CanAdmitNativeDirectNodeTags(true, true, hud, modified));
    modified = hud;
    modified.externalOverlay = true;
    assert(!CanAdmitNativeDirectNodeTags(true, true, modified, hud));
    modified = hud;
    modified.producer = ProducerToken::ResultProgress;
    assert(!CanAdmitNativeDirectNodeTags(true, true, hud, modified));
    modified = hud;
    modified.registrationSerial++;
    assert(CanAdmitNativeDirectNodeTags(true, true, hud, modified));
    const Snapshot unknown{RenderScope::None,
        ProducerToken::None, false, false, 5};
    assert(CanAdmitNativeDirectNodeTags(true, true, unknown, unknown));
    assert(ProvenScreenHudProducer(RenderScope::ScreenHud,
        unknown, unknown) == ProducerToken::None);
}
