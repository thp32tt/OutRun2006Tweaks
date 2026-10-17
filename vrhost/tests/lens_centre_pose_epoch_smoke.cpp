// Standalone portable regression for the packaged R26+HUD central lens source.
#include "../../src/vr/d3d9/lens_centre_source_provenance.hpp"
#include "../../src/vr/game/lens_centre_partial_wvp.hpp"
#include <cassert>
int main()
{
    using namespace OutRunVR::LensCentre;
    assert(SplitUploadCompletesOwnedWvp());
    assert(RejectsMixedAndFailedUploads());
    assert(RejectsCrossDrawAndOverlappingPartialWvp());
    assert(CommittedFullAcceptsOwnedPartialRows());
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

    // The first physical C993 left Draw is allowed to submit to the
    // right eye only when native reentrant callbacks left its exact
    // centre producer, shader, pose and physical draw unchanged.
    const StereoDrawSource left{7, 40, 11, 9, 0x100, true};
    assert(SameStereoDrawSource(left, left));
    auto changedCentre = left;
    changedCentre.centreCall++;
    assert(!SameStereoDrawSource(left, changedCentre));
    auto nestedDraw = left;
    nestedDraw.drawSerial++;
    assert(!SameStereoDrawSource(left, nestedDraw));
    auto newPose = left;
    newPose.poseSequence++;
    assert(!SameStereoDrawSource(left, newPose));
    auto newShader = left;
    newShader.shaderEpoch++;
    assert(!SameStereoDrawSource(left, newShader));
    newShader = left;
    newShader.shader = 0x200;
    assert(!SameStereoDrawSource(left, newShader));
    auto outerDisc = left;
    outerDisc.exactDirectCentre = false;
    assert(!SameStereoDrawSource(left, outerDisc));
    auto noSource = left;
    noSource.centreCall = 0;
    assert(!SameStereoDrawSource(noSource, left));
    // Untagged, queued, other effect, or an epoch reset cannot pass this
    // physical binocular owner. The original mono draw still runs once.
    noSource = left;
    noSource.shaderEpoch = 0;
    assert(!SameStereoDrawSource(noSource, left));

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
    // The early R33 raster bypass has no proof of binocular eligibility.
    // C993 alone must avoid the R29 cached-WVP/road fallback there; a ready
    // C993 is still allowed to reach the exact stereo path, and unrelated
    // world/halo draws keep their historical routing.
    assert(PreserveOriginalBeforeRasterResync(true, false));
    assert(!PreserveOriginalBeforeRasterResync(true, true));
    assert(!PreserveOriginalBeforeRasterResync(false, false));
    assert(!PreserveOriginalBeforeRasterResync(false, true));
    // Ordinary shader world draw path and CABE outer effect remain unchanged.
    assert(SelectWorldRoute(false, false) ==
        WorldRoute::HistoricalWorld);
    return 0;
}
