#include "runtime/projection_blit_upload.hpp"
#include <cassert>
#include <limits>
using namespace OutRunVrProjectionBlit;
int main()
{
    Cache left{}, right{};
    const Key sdr{0.5f, 1.f, 0.f, 0.f, 1.f, 0.f};
    assert(left.NeedsUpload(sdr));
    assert(right.NeedsUpload(sdr));
    left.MarkUploaded(sdr);
    assert(!left.NeedsUpload(sdr));
    assert(right.NeedsUpload(sdr)); // separate buffer identity
    const Key secondEye{0.5f, 1.f, 0.5f, 0.f, 1.f, 0.f};
    right.MarkUploaded(secondEye);
    assert(!right.NeedsUpload(secondEye));
    assert(left.NeedsUpload(secondEye));
    assert(right.NeedsUpload(sdr));
    Key changed = sdr;
    changed.uvScaleX = 0.25f; assert(left.NeedsUpload(changed));
    changed = sdr; changed.uvScaleY = 0.75f; assert(left.NeedsUpload(changed));
    changed = sdr; changed.uvOffsetX = 0.1f; assert(left.NeedsUpload(changed));
    changed = sdr; changed.uvOffsetY = 0.1f; assert(left.NeedsUpload(changed));
    changed = sdr; changed.sdrWhiteScale = 2.f; assert(left.NeedsUpload(changed));
    changed = sdr; changed.sourceIsScRgb = 1.f; assert(left.NeedsUpload(changed));
    // On Map failure, do not mark the changed key; next draw must retry.
    assert(!left.NeedsUpload(sdr) && left.NeedsUpload(changed));
    left.MarkUploaded(changed);
    assert(!left.NeedsUpload(changed) && left.NeedsUpload(sdr));
    left.Invalidate(); right.Invalidate();
    assert(left.NeedsUpload(changed) && right.NeedsUpload(secondEye));
    changed = sdr;
    changed.uvOffsetX = std::numeric_limits<float>::quiet_NaN();
    left.MarkUploaded(changed);
    assert(left.NeedsUpload(changed));
    return 0;
}
