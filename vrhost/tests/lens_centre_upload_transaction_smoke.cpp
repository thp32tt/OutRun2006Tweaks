#include "../../src/vr/game/lens_centre_upload_transaction.hpp"
#include "../../src/vr/d3d9/lens_centre_source_provenance.hpp"
#include <cassert>

int main()
{
    using namespace OutRunVR::LensCentre;
    constexpr UploadSourceStamp original{17, 31, 42, 93, 101, 0x1234, true};
    static_assert(SameSourceAfterNativeUpload(original, original));
    assert(SameSourceAfterNativeUpload(original, original));
    auto nested = original;
    ++nested.uploadGeneration;
    assert(!SameSourceAfterNativeUpload(original, nested));
    // Even a callback which restores the same source scope cannot rewind
    // a newer successful c64 write to the stale outer submission.
    nested = original;
    ++nested.uploadGeneration;
    nested.centreCall = original.centreCall;
    assert(!SameSourceAfterNativeUpload(original, nested));
    auto otherSun = original;
    ++otherSun.centreCall;
    assert(!SameSourceAfterNativeUpload(original, otherSun));
    auto relatch = original;
    ++relatch.pose;
    assert(!SameSourceAfterNativeUpload(original, relatch));
    auto draw = original;
    ++draw.drawSerial;
    assert(!SameSourceAfterNativeUpload(original, draw));
    auto shader = original;
    ++shader.shaderEpoch;
    assert(!SameSourceAfterNativeUpload(original, shader));
    shader = original;
    shader.shader = 0x9876;
    assert(!SameSourceAfterNativeUpload(original, shader));
    auto ring = original;
    ring.exactDirectCentre = false;
    assert(!SameSourceAfterNativeUpload(original, ring));
    auto absent = original;
    absent.uploadGeneration = 0;
    assert(!SameSourceAfterNativeUpload(original, absent));
    // Production R33 must not send C993 to the right eye after an
    // intervening native left Draw changes its exact physical source.
    const StereoDrawSource left{7, 40, 11, 9, 0x100, true};
    assert(SameStereoDrawSource(left, left));
    auto inner = left;
    inner.centreCall = 8;
    assert(!SameStereoDrawSource(left, inner));
    inner = left;
    inner.drawSerial = 41;
    assert(!SameStereoDrawSource(left, inner));
    inner = left;
    inner.shaderEpoch = 12;
    assert(!SameStereoDrawSource(left, inner));
    inner = left;
    inner.shader = 0x200;
    assert(!SameStereoDrawSource(left, inner));
    inner = left;
    inner.poseSequence = 10;
    assert(!SameStereoDrawSource(left, inner));
    inner = left;
    inner.exactDirectCentre = false;
    assert(!SameStereoDrawSource(left, inner));
    inner = left;
    inner.centreCall = 0;
    assert(!SameStereoDrawSource(left, inner));

    // Counterexample: native nested game c64 replacement with an unchanged
    // producer, physical draw, shader and headset pose passes the old guard.
    const RawStereoSource rawOriginal{101, 39, 7, 7, 9, 9, 0x100, 11, true};
    assert(SameStereoDrawSource(left, left));
    assert(SameRawStereoSource(rawOriginal, rawOriginal));
    auto changed = rawOriginal;
    changed.writeSerial++;
    assert(!SameRawStereoSource(rawOriginal, changed));
    changed = rawOriginal;
    changed.writtenDraw++;
    assert(!SameRawStereoSource(rawOriginal, changed));
    changed = rawOriginal;
    changed.writtenCentreCall++;
    assert(!SameRawStereoSource(rawOriginal, changed));
    changed = rawOriginal;
    changed.writtenPoseEpoch++;
    assert(!SameRawStereoSource(rawOriginal, changed));
    changed = rawOriginal;
    changed.shaderEpoch++;
    assert(!SameRawStereoSource(rawOriginal, changed));
    changed = rawOriginal;
    changed.exactDirectRaw = false;
    assert(!SameRawStereoSource(rawOriginal, changed));
    changed = rawOriginal;
    changed.writeSerial = 0;
    assert(!SameRawStereoSource(rawOriginal, changed));
    return 0;
}
