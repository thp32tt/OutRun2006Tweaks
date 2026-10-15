#include "runtime/projection_blit_upload.hpp"
#include "runtime/projection_pair_pipeline.hpp"
#include "runtime/menu_projection_pair.hpp"
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
    // Projection-pair optimization is safe only for successful consecutive
    // left/right eyes at identical nonzero swapchain extents, including Release.
    using OutRunVrProjectionPair::CanReuseCommonPipeline;
    EXPECT(CanReuseCommonPipeline(true, 0, 1, 3440, 1440, 3440, 1440));
    EXPECT(!CanReuseCommonPipeline(false, 0, 1, 3440, 1440, 3440, 1440));
    EXPECT(!CanReuseCommonPipeline(true, 1, 1, 3440, 1440, 3440, 1440));
    EXPECT(!CanReuseCommonPipeline(true, 0, 0, 3440, 1440, 3440, 1440));
    EXPECT(!CanReuseCommonPipeline(true, 0, 1, 3440, 1440, 1920, 1440));
    EXPECT(!CanReuseCommonPipeline(true, 0, 1, 3440, 1440, 3440, 1080));
    EXPECT(!CanReuseCommonPipeline(true, 0, 1, 0, 1440, 0, 1440));
    EXPECT(!CanReuseCommonPipeline(true, 0, 1, 3440, 0, 3440, 0));
    // Adjacent same-extent projection eyes defer only eye-0 resource unbind.
    using OutRunVrProjectionPair::CanDeferFirstEyeUnbind;
    EXPECT(CanDeferFirstEyeUnbind(0, 1, 2064, 2208, 2064, 2208));
    EXPECT(!CanDeferFirstEyeUnbind(1, 0, 2064, 2208, 2064, 2208));
    EXPECT(!CanDeferFirstEyeUnbind(0, 0, 2064, 2208, 2064, 2208));
    EXPECT(!CanDeferFirstEyeUnbind(1, 1, 2064, 2208, 2064, 2208));
    EXPECT(!CanDeferFirstEyeUnbind(0, 2, 2064, 2208, 2064, 2208));
    EXPECT(!CanDeferFirstEyeUnbind(0, 1, 2064, 2208, 1920, 2208));
    EXPECT(!CanDeferFirstEyeUnbind(0, 1, 2064, 2208, 2064, 2048));
    EXPECT(!CanDeferFirstEyeUnbind(0, 1, 0, 2208, 0, 2208));
    EXPECT(!CanDeferFirstEyeUnbind(0, 1, 2064, 0, 2064, 0));
    // R23 LOCAL-fixed menu uses an identical clip and source for both eyes.
    // A failed first submission or discontinuity must not skip rebind/upload.
    using OutRunVrMenuPair::PlanSecondEye;
    EXPECT(PlanSecondEye(true, true, true, 0, 1, 2064, 2208, 2064, 2208).reuseUniformsAndPipeline);
    EXPECT(!PlanSecondEye(false, true, true, 0, 1, 2064, 2208, 2064, 2208).reuseUniformsAndPipeline);
    EXPECT(!PlanSecondEye(true, false, true, 0, 1, 2064, 2208, 2064, 2208).reuseUniformsAndPipeline);
    EXPECT(!PlanSecondEye(true, true, false, 0, 1, 2064, 2208, 2064, 2208).reuseUniformsAndPipeline);
    EXPECT(!PlanSecondEye(true, true, true, 1, 0, 2064, 2208, 2064, 2208).reuseUniformsAndPipeline);
    EXPECT(!PlanSecondEye(true, true, true, 0, 1, 2064, 2208, 2063, 2208).reuseUniformsAndPipeline);
    EXPECT(!PlanSecondEye(true, true, true, 0, 1, 2064, 2208, 2064, 0).reuseUniformsAndPipeline);
    return 0;
}
