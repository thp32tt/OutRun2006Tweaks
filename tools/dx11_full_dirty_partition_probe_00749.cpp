#include "../src/vr/d3d11/native_game_dirty_region.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
constexpr GameNativeDirtyRectangle horizontal[] = {{0,0,1920,540},{0,540,1920,1080}};
constexpr GameNativeDirtyRectangle vertical[] = {{0,0,960,1080},{960,0,1920,1080}};
constexpr GameNativeDirtyRectangle quadrants[] = {{0,0,960,540},{960,0,1920,540},{0,540,960,1080},{960,540,1920,1080}};
constexpr GameNativeDirtyRectangle hole[] = {{0,0,1920,540},{0,541,1920,1080}};
constexpr GameNativeDirtyRectangle overlap[] = {{0,0,1920,600},{0,500,1920,1080}};
constexpr GameNativeDirtyRectangle overflow[] = {{-1,0,960,1080},{960,0,1920,1080}};
constexpr bool check(const GameNativeDirtyRectangle* parts, std::uint32_t count,
                     std::uint32_t bytes, std::int64_t right=1920) {
    return GameNativeDirtyRegionCoverage::covers_partition(
        1920,1080,count,bytes,0,0,right,1080,parts);
}
static_assert(check(horizontal,2,32));
static_assert(check(vertical,2,32));
static_assert(check(quadrants,4,64));
static_assert(!check(hole,2,32));
static_assert(!check(overlap,2,32));
static_assert(!check(overflow,2,32));
static_assert(!check(horizontal,2,31));
static_assert(!check(horizontal,2,32,1919));
static_assert(!check(horizontal,9,144));
static_assert(!check(nullptr,2,32));
static_assert(!GameNativeDirtyRegionCoverage::covers_partition(
    0,1080,2,32,0,0,0,1080,horizontal));
static_assert(!GameNativeDirtyRegionCoverage::covers_partition(
    (std::numeric_limits<std::uint32_t>::max)(),1080,2,32,
    0,0,4294967295LL,1080,horizontal));
int main() { assert(check(horizontal,2,64)); assert(!check(hole,2,32)); }
