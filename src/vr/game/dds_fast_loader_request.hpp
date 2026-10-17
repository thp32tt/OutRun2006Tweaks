#pragma once
// The replacement DDS fast uploader copies existing file levels in one exact
// GPU format. Requests needing D3DX conversion or mipmap generation must use
// the original D3DX trampoline rather than silently return another texture.
#include <cstdint>
namespace OutRunVR::DdsFastLoad
{
    constexpr bool RequestedMipCountSupported(
        std::uint32_t requested, std::uint32_t available,
        std::uint32_t automatic) noexcept
    {
        return requested == automatic ||
            (requested > 0u && requested <= available);
    }

    constexpr bool RequestedFormatSupported(
        std::uint32_t requested, std::uint32_t resolved,
        std::uint32_t automatic, std::uint32_t fromFile) noexcept
    {
        return requested == automatic || requested == fromFile ||
            requested == resolved;
    }
}
