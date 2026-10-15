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

    // The whole centre draw is exclusive: both source-owned and unknown
    // C993 c64 bypass the earlier road-shader and R28 world rebind owner.
    assert(SelectWorldRoute(true, OwnsRawWvp(raw)) ==
        WorldRoute::ExactCentreStereo);
    assert(SelectWorldRoute(true, OwnsRawWvp(relatch)) ==
        WorldRoute::PreserveOriginal);
    assert(SelectWorldRoute(true, OwnsRawWvp(shader)) ==
        WorldRoute::PreserveOriginal);
    assert(SelectWorldRoute(true, OwnsRawWvp(ring)) ==
        WorldRoute::PreserveOriginal);
    assert(SelectWorldRoute(true, OwnsRawWvp(queued)) ==
        WorldRoute::PreserveOriginal);
    // R84 renderer upper-dispatch fallback: original only when the exact
    // central sun has no R30 proof or R33 did not handle binocular draw.
    assert(PreserveOriginalAtUpperDispatch(true, false, false));
    assert(PreserveOriginalAtUpperDispatch(true, true, false));
    assert(!PreserveOriginalAtUpperDispatch(true, true, true));
    assert(!PreserveOriginalAtUpperDispatch(false, false, false));
    assert(!PreserveOriginalAtUpperDispatch(false, true, false));
    // Ordinary shader world draw path and CABE outer effect remain unchanged.
    assert(SelectWorldRoute(false, false) ==
        WorldRoute::HistoricalWorld);
    return 0;
}
