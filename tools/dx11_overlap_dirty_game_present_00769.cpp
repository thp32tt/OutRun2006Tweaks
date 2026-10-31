#include "../src/vr/d3d11/native_game_multi_dirty_upload.hpp"
#include "../src/vr/d3d11/native_game_frame_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;

// Menu/vehicle/race Present may contain overlapping partial dirty rectangles.
// Strict complete-coverage proof cannot use overlap as evidence.
constexpr GameNativePresentRegion crop{1,1,5,4};
constexpr GameNativeDirtyRectangle tiles[]{{0,0,4,4},{2,2,6,5}};
constexpr auto strict = GameNativeMultiDirtyUpload::select(
    8,6,crop,2,32,0,0,6,5,tiles);
constexpr auto admitted = GameNativeMultiDirtyUpload::select(
    8,6,crop,2,32,0,0,6,5,tiles,true);
static_assert(!strict.valid);
// A complete overlapping dirty union must continue menu -> vehicle -> race
// native Present; rcBound with an uncovered hole remains D3D9-owned.
constexpr GameNativeDirtyRectangle completeFull[]{{0,0,4,6},{2,0,8,6}};
constexpr GameNativeDirtyRectangle completeCrop[]{{1,1,4,4},{3,1,5,4}};
constexpr GameNativeDirtyRectangle fullGap[]{{0,0,3,6},{5,0,8,6},{2,0,6,2}};
static_assert(GameNativeDirtyRegionCoverage::covers_complete_union(
    8,6,2,32,0,0,8,6,0,0,8,6,completeFull));
static_assert(GameNativeDirtyRegionCoverage::covers_complete_union(
    8,6,2,32,1,1,5,4,1,1,5,4,completeCrop));
static_assert(!GameNativeDirtyRegionCoverage::covers_complete_union(
    8,6,3,48,0,0,8,6,0,0,8,6,fullGap));
static_assert(!GameNativeDirtyRegionCoverage::covers_complete_union(
    8,6,2,16,0,0,8,6,0,0,8,6,completeFull));
static_assert(!GameNativeDirtyRegionCoverage::covers_complete_union(
    8,6,2,32,0,0,8,6,0,0,7,6,completeFull));
static_assert(!GameNativeDirtyRegionCoverage::covers_complete_union(
    8,6,2,32,1,1,5,4,1,1,5,4,completeFull));

static_assert(admitted.valid && admitted.count == 2 &&
    admitted.regions[0].left == 1 && admitted.regions[0].right == 4 &&
    admitted.regions[1].left == 2 && admitted.regions[1].right == 5 &&
    admitted.uploadBounds.left == 1 && admitted.uploadBounds.top == 1 &&
    admitted.uploadBounds.right == 5 && admitted.uploadBounds.bottom == 4);
static_assert(!GameNativeMultiDirtyUpload::select(
    8,6,crop,2,16,0,0,6,5,tiles,true).valid);
static_assert(!GameNativeMultiDirtyUpload::select(
    8,6,crop,2,32,0,0,5,5,tiles,true).valid);
constexpr GameNativeDirtyRectangle invalid[]{{0,0,4,4},{2,2,9,5}};
static_assert(!GameNativeMultiDirtyUpload::select(
    8,6,crop,2,32,0,0,9,5,invalid,true).valid);
static_assert(!GameNativeDirtyRegionCoverage::covers_partition_crop(
    8,6,2,32,1,1,5,4,0,0,6,5,tiles));

int main() {
    constexpr std::uint32_t width=8u,height=6u,sourcePitch=36u;
    constexpr std::int32_t targetPitch=40;
    std::array<std::uint8_t,sourcePitch*height> native{};
    std::array<std::uint8_t,static_cast<std::size_t>(targetPitch)*height> upload{};
    native.fill(0x9a); upload.fill(0x45);
    for(std::uint32_t y=0;y<height;++y)
        for(std::uint32_t x=0;x<width;++x)
            for(std::uint32_t c=0;c<4;++c)
                native[y*sourcePitch+x*4+c]=
                    static_cast<std::uint8_t>(3u+y*17u+x*4u+c);
    for(std::uint32_t i=0;i<admitted.count;++i) {
        const auto& r=admitted.regions[i];
        assert(GameNativeFrameUpload::copy_rect(
            upload.data(),targetPitch,native.data(),sourcePitch,width,height,
            static_cast<std::uint32_t>(r.left),static_cast<std::uint32_t>(r.top),
            static_cast<std::uint32_t>(r.right),static_cast<std::uint32_t>(r.bottom)));
    }
    // One D3D9-backbuffer-seeded SYSTEMMEM snapshot, then native tiles.
    // A failed single UpdateSurface leaves original game pixels untouched.
    std::array<std::uint8_t,static_cast<std::size_t>(targetPitch)*height> original{};
    original.fill(0x45);
    auto output=original;
    assert(output==original);
    for(std::uint32_t y=0;y<height;++y)
        for(std::uint32_t x=0;x<static_cast<std::uint32_t>(targetPitch);++x) {
            const bool touched=(x>=4u&&x<16u&&y>=1u&&y<4u) ||
                               (x>=8u&&x<20u&&y>=2u&&y<4u);
            assert(upload[y*targetPitch+x]==
                (touched?native[y*sourcePitch+x]:static_cast<std::uint8_t>(0x45)));
        }
    // A single bounded UpdateSurface, not multiple partially committed tiles.
    for(std::uint32_t y=static_cast<std::uint32_t>(admitted.uploadBounds.top);
        y<static_cast<std::uint32_t>(admitted.uploadBounds.bottom);++y)
        for(std::uint32_t x=static_cast<std::uint32_t>(admitted.uploadBounds.left)*4u;
            x<static_cast<std::uint32_t>(admitted.uploadBounds.right)*4u;++x)
            output[y*targetPitch+x]=upload[y*targetPitch+x];
    assert(output==upload);
}
