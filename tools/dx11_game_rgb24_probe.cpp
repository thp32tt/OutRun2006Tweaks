#include "../src/vr/d3d11/live_game_rgb24_texture.hpp"
#include <array>
#include <cassert>
#include <algorithm>
using namespace outrun::vr::dx11::live_game_frame::rgb24_texture;
int main() {
static_assert(source_bytes_per_texel()==3u && upload_bytes_per_texel()==4u);
std::array<unsigned char,12> src{1,32,224,10,102,176,254,2,49,90,90,90};
std::array<unsigned char,16> dst{}; dst.fill(119); unpack_row(src.data(),dst.data(),3u);
assert((dst==std::array<unsigned char,16>{1,32,224,255,10,102,176,255,254,2,49,255,119,119,119,119}));
dst.fill(119); unpack_row(src.data(),dst.data(),1u);
assert((dst==std::array<unsigned char,16>{1,32,224,255,119,119,119,119,119,119,119,119,119,119,119,119}));
dst.fill(119); unpack_row(src.data(),dst.data(),0u);
assert(std::all_of(dst.begin(),dst.end(),[](auto b){return b==119;}));
std::array<unsigned char,4> mip{18,52,86,171}; unpack_row(mip.data(),dst.data(),1u);
assert(dst[0]==18 && dst[1]==52 && dst[2]==86 && dst[3]==255);
}
