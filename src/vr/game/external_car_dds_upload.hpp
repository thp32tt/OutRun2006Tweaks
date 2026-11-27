#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace OutRunVR::DinoSidecar {
// Neutral G/B/alpha across ALL mips allows a lossless GPU L8 AO texture.
inline bool IsAoOnlyBgraPixels(const std::uint8_t* source,std::size_t bytes) noexcept {
    if(!source||!bytes||bytes%4u)return false;
    for(std::size_t i=0;i<bytes;i+=4u)
        if(source[i]!=255u||source[i+1]!=255u||source[i+3]!=255u)return false;
    return true;
}
// Caller owns a successfully locked mip and a bounds-checked DDS source.
// D3D9 may pad rows. Always unlock exactly once, including invalid pitches,
// and propagate an unlock failure instead of exposing uncommitted pixels.
template<class Unlock>
inline bool CopyAndUnlockDdsMip(void* bits, std::ptrdiff_t pitch,
    const std::uint8_t* source, unsigned rows, unsigned rowBytes,
    Unlock&& unlock,bool aoLuminance=false) noexcept {
    const unsigned destRow=aoLuminance?rowBytes/4u:rowBytes;
    const bool valid = bits && source && rows && destRow &&
        (!aoLuminance||rowBytes%4u==0u) &&
        pitch >= 0 && static_cast<std::size_t>(pitch) >= destRow;
    if (valid) {
        for (unsigned y=0; y<rows; ++y){
            auto* dst=static_cast<std::uint8_t*>(bits)+static_cast<std::size_t>(pitch)*y;
            const auto* src=source+static_cast<std::size_t>(rowBytes)*y;
            if(aoLuminance){
                for(unsigned x=0;x<destRow;++x)dst[x]=src[4u*x+2u];
            }else std::memcpy(dst,src,rowBytes);
        }
    }
    const bool unlocked = unlock();
    return valid && unlocked;
}
} // namespace OutRunVR::DinoSidecar
