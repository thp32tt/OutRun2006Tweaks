// Standalone portable regression for the packaged R26+HUD central lens source.
#include "../../src/vr/d3d9/lens_centre_source_provenance.hpp"
#include <cassert>
int main()
{
    using namespace OutRunVR::LensCentre;
    const RawWvpEvidence raw{7, 7, 9, 9, 40, 27, 0x100, 0x100, 11, 11, true, true, true};
    assert(OwnsRawWvp(raw));
    auto relatch = raw;
    relatch.currentPoseEpoch = 10;
    assert(!OwnsRawWvp(relatch));
    auto reset = raw;
    reset.writtenPoseEpoch = 0;
    assert(!OwnsRawWvp(reset));
    auto shader = raw;
    shader.shaderEpoch = 12;
    assert(!OwnsRawWvp(shader));
    auto ring = raw;
    ring.exactCentreProducer = false;
    assert(!OwnsRawWvp(ring));
    auto queued = raw;
    queued.noQueue = false;
    assert(!OwnsRawWvp(queued));
    return 0;
}
