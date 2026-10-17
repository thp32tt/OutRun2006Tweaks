#include "../../src/vr/game/lens_centre_upload_transaction.hpp"
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
    return 0;
}
