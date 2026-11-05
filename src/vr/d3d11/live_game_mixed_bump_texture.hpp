#pragma once
// D3D9 signed U/V + unsigned luminance and computed C normal textures have
// no byte-compatible D3D11 SRV. Decode per LockRect mip into RGBA16_SNORM.
// Reject invalid C/sRGB, preserving original D3D9 game Draw and input.
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
namespace outrun::vr::dx11::live_game_frame::mixed_bump_texture {
enum class Layout : std::uint8_t { unsupported, l6v5u5, x8l8v8u8, cxv8u8 };
[[nodiscard]] constexpr Layout from_d3d9_format(std::uint32_t f) noexcept {
    return f==61u ? Layout::l6v5u5 : f==62u ? Layout::x8l8v8u8 :
           f==117u ? Layout::cxv8u8 : Layout::unsupported;
}
[[nodiscard]] constexpr std::uint32_t source_bytes_per_texel(Layout l) noexcept {
    return l==Layout::l6v5u5 || l==Layout::cxv8u8 ? 2u :
           l==Layout::x8l8v8u8 ? 4u : 0u;
}
[[nodiscard]] constexpr bool sampleable(Layout l,bool srgb) noexcept {
    return !srgb && source_bytes_per_texel(l)!=0u;
}
[[nodiscard]] constexpr bool source_row_bytes(std::uint32_t width,Layout l,
                                             std::uint32_t& bytes) noexcept {
    const auto b=source_bytes_per_texel(l);
    if(!width||!b||width>(std::numeric_limits<std::uint32_t>::max)()/b)return false;
    bytes=width*b;return true;
}
[[nodiscard]] constexpr bool output_row_bytes(std::uint32_t width,
                                             std::uint32_t& bytes) noexcept {
    if(!width||width>(std::numeric_limits<std::uint32_t>::max)()/8u)return false;
    bytes=width*8u;return true;
}
[[nodiscard]] constexpr int signed8(std::uint8_t b) noexcept {
    return b<128u ? static_cast<int>(b) : static_cast<int>(b)-256;
}
[[nodiscard]] constexpr int signed5(unsigned v) noexcept {
    return (v&16u) ? static_cast<int>(v)-32 : static_cast<int>(v);
}
[[nodiscard]] constexpr std::int16_t snorm16(int v,int scale) noexcept {
    return static_cast<std::int16_t>(v<=-scale ? -32768 : v*32767/scale);
}
[[nodiscard]] constexpr std::int16_t unorm16(unsigned v,unsigned max) noexcept {
    return static_cast<std::int16_t>((v*32767u+max/2u)/max);
}
// Caller validates source LockRect pitch and destination GPU upload budget.
// The per-row decoder reads only active pixels, never the source padding.
[[nodiscard]] inline bool unpack_row(const void* source,void* destination,
                                    std::uint32_t width,Layout l) noexcept {
    std::uint32_t srcPitch{},dstPitch{};
    if(!source||!destination||!source_row_bytes(width,l,srcPitch)||
       !output_row_bytes(width,dstPitch))return false;
    const auto* src=static_cast<const std::uint8_t*>(source);
    auto* dst=static_cast<std::uint8_t*>(destination);
    for(std::uint32_t i=0;i<width;++i){
        int u{},v{};
        std::int16_t third{};
        if(l==Layout::l6v5u5){
            const unsigned p=static_cast<unsigned>(src[i*2u])|
                (static_cast<unsigned>(src[i*2u+1u])<<8u);
            u=signed5(p&31u);v=signed5((p>>5u)&31u);
            third=unorm16((p>>10u)&63u,63u);
        }else if(l==Layout::x8l8v8u8){
            u=signed8(src[i*4u]);v=signed8(src[i*4u+1u]);
            third=unorm16(src[i*4u+2u],255u);
        }else if(l==Layout::cxv8u8){
            u=signed8(src[i*2u]);v=signed8(src[i*2u+1u]);
            const double fu=u<=-127 ? -1.0 : static_cast<double>(u)/127.0;
            const double fv=v<=-127 ? -1.0 : static_cast<double>(v)/127.0;
            const double remainder=1.0-fu*fu-fv*fv;
            if(remainder < -1e-10)return false; // no NaN native C component
            third=static_cast<std::int16_t>(std::lround(
                std::sqrt(remainder>0.0?remainder:0.0)*32767.0));
        }else return false;
        const int scale=l==Layout::l6v5u5?15:127;
        const std::array<std::int16_t,4> rgba{
            snorm16(u,scale),snorm16(v,scale),third,32767};
        std::memcpy(dst+static_cast<std::size_t>(i)*8u,rgba.data(),8u);
    }
    return true;
}
static_assert(from_d3d9_format(61u)==Layout::l6v5u5);
static_assert(from_d3d9_format(62u)==Layout::x8l8v8u8);
static_assert(from_d3d9_format(117u)==Layout::cxv8u8);
static_assert(!sampleable(Layout::cxv8u8,true));
static_assert(snorm16(-128,127)==-32768);
} // namespace outrun::vr::dx11::live_game_frame::mixed_bump_texture
