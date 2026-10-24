#pragma once
#include <cstdint>
// Phase selectors count logical hook Draws, not physical stereo eye Draws.
namespace OutRunVRStereo::GpuCensusPhase {
constexpr bool Legacy(std::uint64_t frame,unsigned draw) noexcept {
    return ((draw+static_cast<unsigned>(frame*7u))&15u)==0u &&
           (draw&63u)==0u;
}
constexpr bool Dephased(std::uint64_t frame,unsigned draw) noexcept {
    return ((draw+static_cast<unsigned>(frame*13u))&63u)==0u;
}
}
