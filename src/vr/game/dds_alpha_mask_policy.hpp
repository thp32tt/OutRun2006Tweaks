#pragma once
#include <cstdint>

// DDS pixel masks describe channel locations; DDPF_ALPHAPIXELS declares
// whether the high byte is meaningful alpha. Some UI replacement DDS files
// retain an A8-shaped mask but advertise RGB only. Those pixels are opaque,
// not alpha-zero sprites; never reinterpret genuine RGBA sprites as XRGB.
namespace OutRunVR::DdsAlphaMask
{
    enum class Rgb32Intent : std::uint8_t
    {
        Unsupported,
        Opaque,
        Alpha
    };

    constexpr Rgb32Intent Classify(std::uint32_t flags,
        std::uint32_t bits, std::uint32_t alphaMask) noexcept
    {
        constexpr std::uint32_t RgbFlag = 0x40u; // DDPF_RGB
        constexpr std::uint32_t AlphaFlag = 0x01u; // DDPF_ALPHAPIXELS
        if (!(flags & RgbFlag) || bits != 32u ||
            (alphaMask != 0u && alphaMask != 0xff000000u))
            return Rgb32Intent::Unsupported;
        if (flags & AlphaFlag)
            return alphaMask == 0xff000000u
                ? Rgb32Intent::Alpha : Rgb32Intent::Unsupported;
        return Rgb32Intent::Opaque;
    }

    static_assert(Classify(0x41u, 32u, 0xff000000u) == Rgb32Intent::Alpha);
    static_assert(Classify(0x40u, 32u, 0xff000000u) == Rgb32Intent::Opaque);
    static_assert(Classify(0x40u, 32u, 0u) == Rgb32Intent::Opaque);
    static_assert(Classify(0x41u, 32u, 0u) == Rgb32Intent::Unsupported);
    static_assert(Classify(0x01u, 32u, 0xff000000u) == Rgb32Intent::Unsupported);
    static_assert(Classify(0x41u, 24u, 0xff000000u) == Rgb32Intent::Unsupported);
}
