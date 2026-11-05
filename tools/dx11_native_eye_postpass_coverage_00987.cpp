#include "../src/vr/d3d11/native_game_eye_postpass_coverage.hpp"
#include "../src/vr/d3d11/native_game_stretch_source.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    // Genuine game camera Copy halves cover the *destination* native eye.
    NativeGameEyePostpassCoverage copy;
    copy.record({0u,0u,1920u,1080u});
    assert(!copy.full_eye(3440u,1440u));
    copy.record({1920u,0u,3440u,1080u});
    copy.record({0u,1080u,3440u,1440u});
    assert(copy.full_eye(3440u,1440u));
    // A genuine clipped two-pass Stretch can fill the eye without a
    // synthetic fullscreen draw or borrowing another eye's color.
    const auto left=native_game_stretch_clipped_region(
        1920u,1080u,0u,0u,1920u,1080u,3440u,1440u,
        -80,0,1800,1440);
    const auto right=native_game_stretch_clipped_region(
        1920u,1080u,0u,0u,1920u,1080u,3440u,1440u,
        1800,0,3680,1440);
    assert(left.valid && right.valid);
    NativeGameEyePostpassCoverage stretch;
    stretch.record({left.left,left.top,left.right,left.bottom});
    assert(!stretch.full_eye(3440u,1440u));
    stretch.record({right.left,right.top,right.right,right.bottom});
    assert(stretch.full_eye(3440u,1440u));
    NativeGameEyePostpassCoverage gap;
    gap.record({0u,0u,1719u,1440u});
    gap.record({1720u,0u,3440u,1440u});
    assert(!gap.full_eye(3440u,1440u));
    // Overlaps, invalid regions and a cropped HUD patch do not fill holes.
    gap.record({100u,200u,300u,400u});
    gap.record({3440u,1440u,3440u,1440u});
    assert(!gap.full_eye(3440u,1440u));
    gap.record({1719u,0u,1720u,1440u});
    assert(gap.full_eye(3440u,1440u));
    gap.reset(); // physically full D3D9 Clear erases old postpass history
    assert(!gap.full_eye(3440u,1440u));
    // Saturated disjoint evidence must never invent a full eye.
    NativeGameEyePostpassCoverage saturated;
    for(unsigned i=0;i<40;++i) saturated.record({i*3u,0u,i*3u+1u,2u});
    assert(!saturated.full_eye(120u,2u));
    saturated.record({0u,0u,120u,2u}); // a genuine full overwrite is proof
    assert(saturated.full_eye(120u,2u));
}
