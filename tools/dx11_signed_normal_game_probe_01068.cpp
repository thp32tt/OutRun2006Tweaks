#include "../src/vr/d3d11/live_game_signed_normal_texture.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <limits>
namespace s = outrun::vr::dx11::live_game_frame::signed_normal_texture;

template<std::size_t Size, std::size_t Native>
bool two_rows(s::Layout layout, const std::array<std::uint8_t, Size>& source,
              std::size_t gamePitch, std::size_t width,
              std::array<std::uint8_t, Native>& native) {
    const auto bytes = width * s::source_bytes_per_texel(layout);
    if (gamePitch < bytes || Size != 2u * gamePitch || Native != 2u * bytes)
        return false;
    for (unsigned y=0; y<2; ++y)
        if (!s::copy_row(source.data()+y*gamePitch,
                         native.data()+y*bytes,
                         static_cast<std::uint32_t>(width), layout))
            return false;
    for (unsigned y=0; y<2; ++y)
        if (std::memcmp(source.data()+y*gamePitch,
                        native.data()+y*bytes, bytes)) return false;
    return true;
}
int main() {
    static_assert(s::source_bytes_per_texel(s::Layout::uv8)==2u);
    static_assert(s::source_bytes_per_texel(s::Layout::uvwq8)==4u);
    static_assert(s::source_bytes_per_texel(s::Layout::uv16)==4u);
    std::uint32_t n{};
    if (s::row_bytes(0u,s::Layout::uv8,n) ||
        s::row_bytes(std::numeric_limits<std::uint32_t>::max(),s::Layout::uv16,n) ||
        s::row_bytes(1u,s::Layout::unsupported,n) ||
        s::copy_row(nullptr,&n,1u,s::Layout::uv8) ||
        s::copy_row(&n,nullptr,1u,s::Layout::uv8) ||
        s::sampleable(s::Layout::uv8,true) ||
        s::from_d3d9_format(62u)!=s::Layout::unsupported) return 1;
    constexpr std::array<std::uint8_t,12> uv8{{0x80,0x7f,0x00,0xff,0xee,0xee,
                                               0x01,0x80,0x7f,0x00,0xdd,0xdd}};
    constexpr std::array<std::uint8_t,20> uvwq8{{0x80,0xff,0x00,0x7f, 0x7f,0x80,0x01,0x00, 0xee,0xee,
                                                 0xff,0x7f,0x80,0x00, 0x00,0x01,0xff,0x80, 0xdd,0xdd}};
    constexpr std::array<std::uint8_t,20> uv16{{0x00,0x80,0xff,0x7f, 0xff,0xff,0x00,0x00,0xee,0xee,
                                                0x01,0x00,0x00,0x80, 0x00,0x00,0xff,0x7f,0xdd,0xdd}};
    std::array<std::uint8_t,8> u{};
    std::array<std::uint8_t,16> q{},v{};
    if (!two_rows( s::Layout::uv8,uv8,6,2,u) ||
        !two_rows(s::Layout::uvwq8,uvwq8,10,2,q) ||
        !two_rows(s::Layout::uv16,uv16,10,2,v)) return 2;
    const std::array<std::uint8_t,2> lastMip{{0x80,0x7f}};
    std::array<std::uint8_t,2> nativeMip{};
    if (!s::copy_row(lastMip.data(),nativeMip.data(),1u,s::Layout::uv8) ||
        lastMip!=nativeMip) return 3;
    std::puts("01068 PASS signed V8U8/Q8W8V8U8/V16U16 normalized native game texture rows");
    return 0;
}