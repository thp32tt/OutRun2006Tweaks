#pragma once
// Pure deterministic bounded sampling policy. Diagnostic only: never alters a GPU draw.
#include <cstdint>

namespace OutRunVRStereo::GpuCensusSampling {
    // Historical 1/16 state sample, unchanged on either profile variant.
    inline constexpr bool StateSample(unsigned draw, std::uint64_t frame) noexcept {
        return ((draw + static_cast<unsigned>(frame * 7ull)) & 15u) == 0u;
    }
    // Legacy: nested draw%64 + rotated state%16 => RT/PS only frame%16==0.
    // Opt-in: use the SAME state rotation modulo 64. Every 64th draw becomes
    // eligible on every logical frame, with at most 1/64 candidate probes;
    // no sample is created when the outer state sample is ineligible.
    inline constexpr bool CensusSample(unsigned draw, std::uint64_t frame,
                                       bool dephase) noexcept {
        if (dephase)
            return ((draw + static_cast<unsigned>(frame * 7ull)) & 63u) == 0u;
        return (draw & 63u) == 0u && StateSample(draw, frame);
    }
}
