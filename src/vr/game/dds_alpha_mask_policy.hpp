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


    // 16-bit selector/menu surfaces can be 5:6:5, 5:5:5 or 4:4:4:4.
    // The highest source bit/nibble is *not* transparency merely because
    // the DDS writer left an alpha-shaped mask in an RGB-only descriptor.
    // Preserve opaque 5:5:5 as X1, genuine declared 1-bit alpha as A1,
    // and require declared alpha for 4:4:4:4; ambiguous opaque 4:4:4
    // deliberately uses native D3DX instead of manufacturing transparency.
    enum class Rgb16Intent : std::uint8_t
    {
        Unsupported, Rgb565, Opaque555, Alpha1555, Alpha4444
    };

    constexpr Rgb16Intent Classify16(std::uint32_t flags,
        std::uint32_t bits, std::uint32_t red, std::uint32_t green,
        std::uint32_t blue, std::uint32_t alpha) noexcept
    {
        constexpr std::uint32_t RgbFlag = 0x40u;
        constexpr std::uint32_t AlphaFlag = 0x01u;
        constexpr std::uint32_t FourCcFlag = 0x04u;
        if (!(flags & RgbFlag) || (flags & FourCcFlag) || bits != 16u)
            return Rgb16Intent::Unsupported;
        const bool declaredAlpha = (flags & AlphaFlag) != 0u;
        if (red == 0xf800u && green == 0x07e0u &&
            blue == 0x001fu && alpha == 0u && !declaredAlpha)
            return Rgb16Intent::Rgb565;
        if (red == 0x7c00u && green == 0x03e0u &&
            blue == 0x001fu && (alpha == 0u || alpha == 0x8000u))
        {
            if (!declaredAlpha)
                return Rgb16Intent::Opaque555;
            return alpha == 0x8000u
                ? Rgb16Intent::Alpha1555 : Rgb16Intent::Unsupported;
        }
        if (red == 0x0f00u && green == 0x00f0u &&
            blue == 0x000fu && alpha == 0xf000u && declaredAlpha)
            return Rgb16Intent::Alpha4444;
        return Rgb16Intent::Unsupported;
    }

    static_assert(Classify16(0x40u, 16, 0x7c00, 0x03e0, 0x001f, 0x8000) ==
        Rgb16Intent::Opaque555);
    static_assert(Classify16(0x41u, 16, 0x7c00, 0x03e0, 0x001f, 0x8000) ==
        Rgb16Intent::Alpha1555);
    static_assert(Classify16(0x41u, 16, 0x0f00, 0x00f0, 0x000f, 0xf000) ==
        Rgb16Intent::Alpha4444);
    static_assert(Classify16(0x40u, 16, 0x0f00, 0x00f0, 0x000f, 0xf000) ==
        Rgb16Intent::Unsupported);
    static_assert(Classify16(0x40u, 16, 0xf800, 0x07e0, 0x001f, 0) ==
        Rgb16Intent::Rgb565);
    static_assert(Classify16(0x41u, 16, 0xf800, 0x07e0, 0x001f, 0) ==
        Rgb16Intent::Unsupported);

    static_assert(Classify(0x41u, 32u, 0xff000000u) == Rgb32Intent::Alpha);
    static_assert(Classify(0x40u, 32u, 0xff000000u) == Rgb32Intent::Opaque);
    static_assert(Classify(0x40u, 32u, 0u) == Rgb32Intent::Opaque);
    static_assert(Classify(0x41u, 32u, 0u) == Rgb32Intent::Unsupported);
    static_assert(Classify(0x01u, 32u, 0xff000000u) == Rgb32Intent::Unsupported);
    static_assert(Classify(0x41u, 24u, 0xff000000u) == Rgb32Intent::Unsupported);
}
