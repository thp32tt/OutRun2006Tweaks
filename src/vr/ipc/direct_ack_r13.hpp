#pragma once

#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace OutRunVR::R13
{
    inline constexpr wchar_t DirectGpuAckName[] = L"Local\\OutRun2006Tweaks.VR.R13.DirectGpuAck";
    inline constexpr std::uint32_t DirectGpuAckMagic = 0x334B4341u; // 'ACK3'
    inline constexpr std::uint32_t DirectGpuAckVersion = 1;
    inline constexpr std::uint32_t DirectGpuAckRingSize = 4;
    // Reuse reserved storage without changing the 48-byte IPC ABI. The host
    // stamps the complete Frame.v2 game-run identity that produced each ACK
    // batch so a restarted or overlapping game process rejects stale completions.
    inline constexpr std::uint32_t DirectGpuAckRunGenerationIndex = 0;
    inline constexpr std::uint32_t DirectGpuAckGamePidIndex = 1;

#pragma pack(push, 4)
    struct DirectGpuAckState
    {
        std::uint32_t magic{DirectGpuAckMagic};
        std::uint32_t version{DirectGpuAckVersion};
        std::uint32_t structSize{sizeof(DirectGpuAckState)};
        volatile std::uint32_t sequence{};
        std::uint32_t hostPid{};
        std::uint32_t transportGeneration{};
        std::uint32_t completedFrameId[DirectGpuAckRingSize]{};
        std::uint32_t reserved[2]{};
    };
#pragma pack(pop)

    static_assert(sizeof(DirectGpuAckState) == 48);
    static_assert(std::is_standard_layout_v<DirectGpuAckState>);
    static_assert(std::is_trivially_copyable_v<DirectGpuAckState>);
}
