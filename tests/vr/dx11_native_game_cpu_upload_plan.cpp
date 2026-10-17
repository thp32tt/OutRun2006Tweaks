#include "../../src/vr/d3d11/native_game_cpu_upload_plan.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr GameNativePresentRegion whole{0,0,3440,1440};
    constexpr GameNativePresentRegion crop{100,40,3300,1380};
    constexpr GameNativePresentRegion dirty{200,60,500,260};
    constexpr GameNativePresentRegion multi{200,60,3100,1320};
    constexpr auto full = NativeGameCpuUploadPlan::select(
        3440,1440,false,false,false,whole,{},{});
    constexpr auto cropped = NativeGameCpuUploadPlan::select(
        3440,1440,true,false,false,crop,{},{});
    constexpr auto partial = NativeGameCpuUploadPlan::select(
        3440,1440,false,true,false,crop,dirty,{});
    constexpr auto grouped = NativeGameCpuUploadPlan::select(
        3440,1440,false,false,true,crop,{},multi);
    static_assert(full.valid && full.region.right == 3440);
    static_assert(cropped.valid && cropped.region.left == 100);
    static_assert(partial.valid && partial.region.right == 500);
    static_assert(grouped.valid && grouped.region.right == 3100);
    assert(!NativeGameCpuUploadPlan::select(
        3440,1440,true,true,false,crop,dirty,{}).valid);
    assert(!NativeGameCpuUploadPlan::select(
        3440,1440,false,true,false,crop,whole,{}).valid);
    assert(!NativeGameCpuUploadPlan::select(
        3440,1440,false,false,true,crop,{},whole).valid);
    assert(!NativeGameCpuUploadPlan::select(
        3440,1440,false,false,false,{0,-1,3440,1440},{},{}).valid);
    // Simulated driver: UpdateSurface writes only a prefix before failing.
    // Replaying the pre-upload GPU snapshot restores all original game pixels,
    // including the gaps in a single multi-dirty bounding upload.
    constexpr unsigned w=12,h=8;
    constexpr GameNativePresentRegion small{1,1,11,7};
    constexpr GameNativePresentRegion unionArea{2,2,9,6};
    constexpr auto selected=NativeGameCpuUploadPlan::select(
        w,h,false,false,true,small,{},unionArea);
    static_assert(selected.valid);
    std::array<unsigned,w*h> pixels{};
    for (unsigned i=0;i<pixels.size();++i) pixels[i]=i+17u;
    const auto original=pixels;
    const auto backup=pixels;
    for (int y=int(selected.region.top); y<selected.region.bottom; ++y)
        for (int x=int(selected.region.left);x<selected.region.right-2;++x)
            pixels[unsigned(y)*w+unsigned(x)]=0xdeadbeefu;
    assert(pixels != original);
    for (int y=int(selected.region.top); y<selected.region.bottom; ++y)
        for (int x=int(selected.region.left);x<selected.region.right;++x)
            pixels[unsigned(y)*w+unsigned(x)]=backup[unsigned(y)*w+unsigned(x)];
    assert(pixels == original);
}
