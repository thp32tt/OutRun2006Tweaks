// Genuine full/cropped native GPU tile output is not lost just because
// D3D9 supplied an explicit, verified dirty region for the same source crop.
#include "../src/vr/d3d11/native_game_raw_present_coverage.hpp"
#include <cassert>
using outrun::vr::dx11::native_raw_preview_present_coverage;
constexpr bool kSafeRawPresentCoverage =
    native_raw_preview_present_coverage(false, false, false, false) &&
    native_raw_preview_present_coverage(true, true, false, false) &&
    native_raw_preview_present_coverage(true, false, true, false) &&
    native_raw_preview_present_coverage(true, false, false, true) &&
    !native_raw_preview_present_coverage(true, false, false, false) &&
    !native_raw_preview_present_coverage(true, false, false, false);
static_assert(kSafeRawPresentCoverage,
              "unproven D3D9 dirty source crops must not publish RAW tiles");
int main() { assert(kSafeRawPresentCoverage); }
