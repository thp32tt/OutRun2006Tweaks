#include "../src/vr/d3d11/native_game_dirty_region.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool crop(std::int64_t left, std::int64_t top,
                    std::int64_t right, std::int64_t bottom,
                    std::int64_t bl, std::int64_t bt,
                    std::int64_t br, std::int64_t bb,
                    std::int64_t rl, std::int64_t rt,
                    std::int64_t rr, std::int64_t rb,
                    std::uint32_t count = 1u, std::uint32_t bytes = 16u) {
    return GameNativeDirtyRegionCoverage::covers_present_crop(
        1920,1080,count,bytes,left,top,right,bottom,
        bl,bt,br,bb,rl,rt,rr,rb);
}
static_assert(crop(0,0,1280,720, 0,0,1280,720, 0,0,1280,720));
static_assert(crop(640,360,1920,1080, 640,360,1920,1080, 640,360,1920,1080));
static_assert(crop(600,0,1920,1080, 600,0,1920,1080, 600,0,1920,1080));
static_assert(!crop(0,0,1920,1080, 0,0,1920,1080, 0,0,1920,1080));
static_assert(!crop(0,0,1280,720, 0,0,1920,1080, 0,0,1280,720));
static_assert(!crop(0,0,1280,720, 0,0,1280,720, 0,0,1279,720));
static_assert(!crop(0,0,1280,720, 0,0,1280,720, 1,0,1280,720));
static_assert(!crop(0,0,1280,720, 0,0,1280,720, 0,0,1280,720,1,15));
static_assert(!crop(0,0,1280,720, 0,0,1280,720, 0,0,1280,720,2,32));
static_assert(!crop(-1,0,1280,720, -1,0,1280,720, -1,0,1280,720));
static_assert(!crop(0,0,1921,720, 0,0,1921,720, 0,0,1921,720));
static_assert(!crop(0,0,0,720, 0,0,0,720, 0,0,0,720));
static_assert(!GameNativeDirtyRegionCoverage::covers_present_crop(
    0,1080,1,16,0,0,100,100,0,0,100,100,0,0,100,100));

constexpr GameNativeDirtyRectangle cropTwo[] = {
    {400,200,1000,800}, {1000,200,1600,800}
};
constexpr GameNativeDirtyRectangle cropFour[] = {
    {400,200,1000,500}, {1000,200,1600,500},
    {400,500,1000,800}, {1000,500,1600,800}
};
constexpr GameNativeDirtyRectangle cropHole[] = {
    {400,200,999,800}, {1000,200,1600,800}
};
constexpr GameNativeDirtyRectangle cropOverlap[] = {
    {400,200,1001,800}, {1000,200,1600,800}
};
constexpr GameNativeDirtyRectangle cropOutside[] = {
    {399,200,1000,800}, {1000,200,1600,800}
};
constexpr bool tiledCrop(const GameNativeDirtyRectangle* rects,
                         std::uint32_t count=2u, std::uint32_t bytes=32u,
                         std::int64_t left=400, std::int64_t top=200,
                         std::int64_t right=1600, std::int64_t bottom=800) {
    return GameNativeDirtyRegionCoverage::covers_partition_crop(
        1920u,1080u,count,bytes,400,200,1600,800,
        left,top,right,bottom,rects);
}
static_assert(tiledCrop(cropTwo));
static_assert(tiledCrop(cropFour,4,64));
static_assert(!tiledCrop(cropHole));
static_assert(!tiledCrop(cropOverlap));
static_assert(!tiledCrop(cropOutside));
static_assert(!tiledCrop(cropTwo,1));
static_assert(!tiledCrop(cropTwo,2,31));
static_assert(!tiledCrop(cropTwo,2,32,0,0,1600,800));
static_assert(!tiledCrop(cropTwo,2,32,400,200,1600,799));
static_assert(!GameNativeDirtyRegionCoverage::covers_partition_crop(
    1920,1080,2,32,0,0,1920,1080,0,0,1920,1080,cropTwo));
static_assert(!GameNativeDirtyRegionCoverage::covers_partition_crop(
    1920,1080,2,32,400,200,1600,800,400,200,1600,800,nullptr));

int main() {
    assert(tiledCrop(cropTwo));
    assert(!tiledCrop(cropHole));
    assert(crop(0,0,1280,720, 0,0,1280,720, 0,0,1280,720));
    assert(!crop(0,0,1280,720, 0,0,1280,720, 0,0,1280,719));
}
