#include "../src/vr/d3d11/native_game_frame_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::live_game_frame::GameNativeFrameUpload;

int main() {
    // Menu/car/race D3D11 staging and D3D9 upload pitches can differ.
    std::array<std::uint8_t, 60> src{}, dst{};
    src.fill(0xaa);
    dst.fill(0x5a);
    for (std::size_t y = 0; y != 3; ++y)
        for (std::size_t x = 0; x != 12; ++x)
            src[y * 20 + x] = static_cast<std::uint8_t>(y * 12 + x);
    assert(GameNativeFrameUpload::copy_rows(dst.data(), 18, src.data(), 20, 3, 3));
    for (std::size_t y = 0; y != 3; ++y) {
        for (std::size_t x = 0; x != 12; ++x)
            assert(dst[y * 18 + x] == src[y * 20 + x]);
        for (std::size_t x = 12; x != 18; ++x)
            assert(dst[y * 18 + x] == 0x5a);
    }
    const auto before = dst;
    assert(!GameNativeFrameUpload::copy_rows(nullptr, 18, src.data(), 20, 3, 3));
    assert(!GameNativeFrameUpload::copy_rows(dst.data(), 18, nullptr, 20, 3, 3));
    assert(!GameNativeFrameUpload::copy_rows(dst.data(), 18, src.data(), 11, 3, 3));
    assert(!GameNativeFrameUpload::copy_rows(dst.data(), 11, src.data(), 20, 3, 3));
    assert(!GameNativeFrameUpload::copy_rows(dst.data(), -18, src.data(), 20, 3, 3));
    assert(!GameNativeFrameUpload::copy_rows(dst.data(), 18, src.data(), 20, 0, 3));
    assert(!GameNativeFrameUpload::copy_rows(dst.data(), 18, src.data(), 20, 3, 0));
    assert(!GameNativeFrameUpload::copy_rows(dst.data(), 18, src.data(), 20,
                                             (std::numeric_limits<std::uint32_t>::max)(), 3));
    assert(dst == before); // All rejects preserve the original D3D9 pixels.
    return 0;
}
