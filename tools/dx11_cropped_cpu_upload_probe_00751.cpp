#include "../src/vr/d3d11/native_game_frame_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::live_game_frame::GameNativeFrameUpload;
int main() {
    constexpr std::uint32_t width = 8, height = 6, srcPitch = 40;
    constexpr std::int32_t dstPitch = 36;
    std::array<std::uint8_t, srcPitch * height> src{};
    std::array<std::uint8_t, dstPitch * height> dst{};
    src.fill(0x88); dst.fill(0x5a);
    for (std::uint32_t y = 0; y < height; ++y)
        for (std::uint32_t x = 0; x < width * 4; ++x)
            src[y * srcPitch + x] = static_cast<std::uint8_t>(y * 37 + x);
    // Cropped menu/car/race source must not overwrite surrounding D3D9 image.
    assert(GameNativeFrameUpload::copy_rect(
        dst.data(), dstPitch, src.data(), srcPitch, width, height, 2, 1, 6, 4));
    for (std::uint32_t y = 0; y < height; ++y)
        for (std::uint32_t b = 0; b < static_cast<std::uint32_t>(dstPitch); ++b)
            assert(dst[y * dstPitch + b] ==
                (y >= 1 && y < 4 && b >= 8 && b < 24
                    ? src[y * srcPitch + b] : 0x5a));
    const auto unchanged = dst;
    assert(!GameNativeFrameUpload::copy_rect(
        dst.data(), dstPitch, src.data(), srcPitch, width, height, 2, 1, 9, 4));
    assert(!GameNativeFrameUpload::copy_rect(
        dst.data(), dstPitch, src.data(), srcPitch, width, height, 2, 1, 6, 7));
    assert(!GameNativeFrameUpload::copy_rect(
        dst.data(), dstPitch, src.data(), srcPitch, width, height, 6, 1, 2, 4));
    assert(!GameNativeFrameUpload::copy_rect(
        dst.data(), dstPitch, src.data(), srcPitch, width, height, 2, 4, 6, 4));
    assert(!GameNativeFrameUpload::copy_rect(
        dst.data(), 31, src.data(), srcPitch, width, height, 2, 1, 6, 4));
    assert(!GameNativeFrameUpload::copy_rect(
        dst.data(), dstPitch, src.data(), 31, width, height, 2, 1, 6, 4));
    assert(!GameNativeFrameUpload::copy_rect(
        nullptr, dstPitch, src.data(), srcPitch, width, height, 2, 1, 6, 4));
    assert(!GameNativeFrameUpload::copy_rect(
        dst.data(), dstPitch, src.data(), srcPitch,
        (std::numeric_limits<std::uint32_t>::max)(), height, 2, 1, 6, 4));
    assert(dst == unchanged); // Every reject leaves original game pixels alone.
    assert(GameNativeFrameUpload::copy_rows(
        dst.data(), dstPitch, src.data(), srcPitch, width, height));
    for (std::uint32_t y = 0; y < height; ++y)
        for (std::uint32_t b = 0; b < width * 4; ++b)
            assert(dst[y * dstPitch + b] == src[y * srcPitch + b]);
    return 0;
}
