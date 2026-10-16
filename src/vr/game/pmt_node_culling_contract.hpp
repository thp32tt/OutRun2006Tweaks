#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace OutRunVR::PmtNodeCull
{
    inline constexpr std::uintptr_t RenderNodeVisibleRva = 0x00004B00u;
    inline constexpr std::uintptr_t WalkNodeVisibleCallRva = 0x00005015u;
    inline constexpr std::uintptr_t ResultTestRva = 0x0000501Du;
    inline constexpr std::uintptr_t DisableBranchRva = 0x0000501Fu;

    inline constexpr std::size_t PmtNodeCenterOffset = 0x04u;
    inline constexpr std::size_t PmtNodeRadiusOffset = 0x10u;

    inline constexpr std::array<std::uint8_t, 4> OriginalResultGate{
        0x85, 0xC0, 0x74, 0x72
    };
    inline constexpr std::array<std::uint8_t, 4> DisabledResultGate{
        0x85, 0xC0, 0x90, 0x90
    };

    inline bool ResultGateBytesCompatible(
        const std::uint8_t* bytes, std::size_t count) noexcept
    {
        if (!bytes || count < OriginalResultGate.size())
            return false;
        bool original = true;
        bool disabled = true;
        for (std::size_t i = 0; i < OriginalResultGate.size(); ++i)
        {
            original &= bytes[i] == OriginalResultGate[i];
            disabled &= bytes[i] == DisabledResultGate[i];
        }
        return original || disabled;
    }
}