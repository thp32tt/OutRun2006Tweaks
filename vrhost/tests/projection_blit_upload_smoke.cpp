#include "runtime/projection_blit_upload.hpp"
#include <cstdint>
#include <limits>
using namespace OutRunVrProjectionBlit;
// Assert is compiled out for MSVC Release/NDEBUG; keep acceptance executable.
#define EXPECT(condition) do { if (!(condition)) return __LINE__; } while (false)
int main()
{
    Cache left{}, right{};
    const Key sdr{0.5f, 1.f, 0.f, 0.f, 1.f, 0.f};
    EXPECT(left.NeedsUpload(sdr));
    EXPECT(right.NeedsUpload(sdr));
    left.MarkUploaded(sdr);
    EXPECT(!left.NeedsUpload(sdr));
    EXPECT(right.NeedsUpload(sdr)); // separate buffer identity
    const Key secondEye{0.5f, 1.f, 0.5f, 0.f, 1.f, 0.f};
    right.MarkUploaded(secondEye);
    EXPECT(!right.NeedsUpload(secondEye));
    EXPECT(left.NeedsUpload(secondEye));
    EXPECT(right.NeedsUpload(sdr));
    Key changed = sdr;
    changed.uvScaleX = 0.25f; EXPECT(left.NeedsUpload(changed));
    changed = sdr; changed.uvScaleY = 0.75f; EXPECT(left.NeedsUpload(changed));
    changed = sdr; changed.uvOffsetX = 0.1f; EXPECT(left.NeedsUpload(changed));
    changed = sdr; changed.uvOffsetY = 0.1f; EXPECT(left.NeedsUpload(changed));
    changed = sdr; changed.sdrWhiteScale = 2.f; EXPECT(left.NeedsUpload(changed));
    changed = sdr; changed.sourceIsScRgb = 1.f; EXPECT(left.NeedsUpload(changed));
    // On Map failure, do not mark the changed key; next draw must retry.
    EXPECT(!left.NeedsUpload(sdr) && left.NeedsUpload(changed));
    left.MarkUploaded(changed);
    EXPECT(!left.NeedsUpload(changed) && left.NeedsUpload(sdr));
    left.Invalidate(); right.Invalidate();
    EXPECT(left.NeedsUpload(changed) && right.NeedsUpload(secondEye));
    changed = sdr;
    changed.uvOffsetX = std::numeric_limits<float>::quiet_NaN();
    left.MarkUploaded(changed);
    EXPECT(left.NeedsUpload(changed));
    return 0;
}
