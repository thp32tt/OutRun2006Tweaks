#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace OutRunVR::DinoSidecar {
// Caller owns a successfully locked mip and a bounds-checked DDS source.
// D3D9 may pad rows. Always unlock exactly once, including invalid pitches,
// and propagate an unlock failure instead of exposing uncommitted pixels.
template<class Unlock>
inline bool CopyAndUnlockDdsMip(void* bits, std::ptrdiff_t pitch,
    const std::uint8_t* source, unsigned rows, unsigned rowBytes,
    Unlock&& unlock) noexcept {
    const bool valid = bits && source && rows && rowBytes &&
        pitch >= 0 && static_cast<std::size_t>(pitch) >= rowBytes;
    if (valid) {
        for (unsigned y=0; y<rows; ++y)
            std::memcpy(static_cast<std::uint8_t*>(bits)+
                static_cast<std::size_t>(pitch)*y,
                source+static_cast<std::size_t>(rowBytes)*y,rowBytes);
    }
    const bool unlocked = unlock();
    return valid && unlocked;
}
} // namespace OutRunVR::DinoSidecar
