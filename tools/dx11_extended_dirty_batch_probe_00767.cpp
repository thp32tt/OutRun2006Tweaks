#include "../src/vr/d3d11/native_game_multi_dirty_upload.hpp"
#include "../src/vr/d3d11/native_game_frame_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;

// Four columns x eight rows of genuine game Present rectangles (32 total).
// Previously the ninth region rejected an otherwise complete native frame.
constexpr std::array<GameNativeDirtyRectangle, 32> wholeTiles = [] {
    std::array<GameNativeDirtyRectangle, 32> out{};
    for (std::uint32_t y = 0; y < 8; ++y)
        for (std::uint32_t x = 0; x < 4; ++x)
            out[y * 4u + x] = {2 * x, y, 2 * x + 2, y + 1};
    return out;
}();
constexpr GameNativePresentRegion whole{0, 0, 8, 8};
constexpr bool wholeAdmitted = GameNativeDirtyRegionCoverage::covers_partition(
    8, 8, 32, 32 * 16, 0, 0, 8, 8, wholeTiles.data());
static_assert(wholeAdmitted, "full-game 32-tile native repaint must be admitted");
constexpr auto wholeSelection = GameNativeMultiDirtyUpload::select(
    8, 8, whole, 32, 32 * 16, 0, 0, 8, 8, wholeTiles.data());
static_assert(wholeSelection.valid && wholeSelection.count == 32 &&
    wholeSelection.uploadBounds.left == 0 && wholeSelection.uploadBounds.right == 8 &&
    wholeSelection.uploadBounds.top == 0 && wholeSelection.uploadBounds.bottom == 8);

// A 30-tile vehicle/menu source crop keeps every pixel outside its source
// rectangle D3D9-owned; one source-rectangle upload must not replace those.
constexpr std::array<GameNativeDirtyRectangle, 30> cropTiles = [] {
    std::array<GameNativeDirtyRectangle, 30> out{};
    for (std::uint32_t y = 0; y < 5; ++y)
        for (std::uint32_t x = 0; x < 6; ++x)
            out[y * 6u + x] = {x + 1, y + 1, x + 2, y + 2};
    return out;
}();
constexpr GameNativePresentRegion crop{1, 1, 7, 6};
static_assert(GameNativeDirtyRegionCoverage::covers_partition_crop(
    8, 8, 30, 30 * 16, 1, 1, 7, 6, 1, 1, 7, 6, cropTiles.data()));
constexpr auto cropSelection = GameNativeMultiDirtyUpload::select(
    8, 8, crop, 30, 30 * 16, 1, 1, 7, 6, cropTiles.data());
static_assert(cropSelection.valid && cropSelection.count == 30 &&
    cropSelection.uploadBounds.left == 1 && cropSelection.uploadBounds.top == 1 &&
    cropSelection.uploadBounds.right == 7 && cropSelection.uploadBounds.bottom == 6);

constexpr auto overlapped = [] {
    auto out = wholeTiles;
    out[2] = out[1];
    return out;
}();
static_assert(!GameNativeDirtyRegionCoverage::covers_partition(
    8, 8, 32, 512, 0, 0, 8, 8, overlapped.data()));
static_assert(!GameNativeMultiDirtyUpload::select(
    8, 8, whole, 32, 512, 0, 0, 8, 8, overlapped.data()).valid);
static_assert(!GameNativeDirtyRegionCoverage::covers_partition(
    8, 8, 32, 31 * 16, 0, 0, 8, 8, wholeTiles.data()));
static_assert(!GameNativeMultiDirtyUpload::select(
    8, 8, whole, 32, 31 * 16, 0, 0, 8, 8, wholeTiles.data()).valid);
static_assert(!GameNativeMultiDirtyUpload::select(
    8, 8, whole, 33, 33 * 16, 0, 0, 8, 8, wholeTiles.data()).valid);
static_assert(!GameNativeDirtyRegionCoverage::covers_partition_crop(
    8, 8, 29, 29 * 16, 1, 1, 7, 6, 1, 1, 7, 6, cropTiles.data()),
    "missing source crop tile may never certify full visible native coverage");

int main() {
    constexpr std::uint32_t w = 8, h = 8, srcPitch = 40;
    constexpr std::int32_t dstPitch = 48;
    std::array<std::uint8_t, srcPitch * h> native{};
    for (std::uint32_t y = 0; y < h; ++y)
        for (std::uint32_t x = 0; x < w; ++x)
            for (std::uint32_t channel = 0; channel < 4; ++channel)
                native[y * srcPitch + x * 4 + channel] =
                    static_cast<std::uint8_t>(y * 21 + x * 4 + channel);
    for (const auto& selection : {wholeSelection, cropSelection}) {
        std::array<std::uint8_t, dstPitch * h> upload{};
        upload.fill(0x5a); // Current original D3D9 backbuffer seed.
        for (std::uint32_t i = 0; i < selection.count; ++i) {
            const auto& r = selection.regions[i];
            assert(GameNativeFrameUpload::copy_rect(
                upload.data(), dstPitch, native.data(), srcPitch, w, h,
                static_cast<std::uint32_t>(r.left), static_cast<std::uint32_t>(r.top),
                static_cast<std::uint32_t>(r.right), static_cast<std::uint32_t>(r.bottom)));
        }
        // One UpdateSurface of the bounded source RECT cannot corrupt a hole,
        // a separate crop or the D3D9 pitch padding.
        for (std::uint32_t y = 0; y < h; ++y)
            for (std::uint32_t x = 0; x < static_cast<std::uint32_t>(dstPitch); ++x) {
                const bool inBounds = x < w * 4u;
                const bool inCrop = selection.count == 32 ||
                    (y >= 1u && y < 6u && x >= 4u && x < 28u);
                assert(upload[y * dstPitch + x] ==
                    (inBounds && inCrop
                        ? native[y * srcPitch + x]
                        : static_cast<std::uint8_t>(0x5a)));
            }
    }
}
