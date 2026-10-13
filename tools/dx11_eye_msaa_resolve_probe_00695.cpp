// Portable native game stereo eye transfer (copy vs MSAA resolve).
#include "../src/vr/d3d11/native_game_eye_pair_sources.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
using outrun::vr::dx11::NativeGameEyeTransfer;
using outrun::vr::dx11::native_game_eye_transfer;
constexpr bool accepts() {
    using T=NativeGameEyeTransfer;
    return native_game_eye_transfer(1,0,1,0,false)==T::Copy &&
           native_game_eye_transfer(1,0,1,0,true)==T::Copy &&
           native_game_eye_transfer(2,0,2,0,true)==T::Resolve &&
           native_game_eye_transfer(4,3,4,3,true)==T::Resolve &&
           native_game_eye_transfer(8,0,8,0,true)==T::Resolve &&
           native_game_eye_transfer(0,0,0,0,true)==T::Reject &&
           native_game_eye_transfer(1,0,4,0,true)==T::Reject &&
           native_game_eye_transfer(4,0,4,1,true)==T::Reject &&
           native_game_eye_transfer(4,0,4,0,false)==T::Reject &&
           native_game_eye_transfer(1,1,1,1,true)==T::Reject;
}
static_assert(accepts(), "Stereo eye single-sample Copy / MSAA Resolve acceptance");
int main() {
    if (!accepts()) return 1;
    constexpr std::array<std::uint32_t,4> samples{1,2,4,8};
    for(auto count:samples) {
        for (auto quality: {0u,1u}) {
            const auto route=native_game_eye_transfer(
                count,quality,count,quality,true);
            if (route != (count==1
                    ? (quality==0 ? NativeGameEyeTransfer::Copy : NativeGameEyeTransfer::Reject)
                    : NativeGameEyeTransfer::Resolve)) return 2;
        }
    }
    std::puts("00695 PASS: native stereo copy or per-eye MSAA Resolve; mismatched samples/quality/format reject");
}
