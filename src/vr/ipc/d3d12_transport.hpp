#pragma once

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <cstdint>

namespace OutRunVR::D3D12Transport
{
    inline constexpr wchar_t MappingName[] = L"Local\\OutRunVRD3D12Transport.v1";
    inline constexpr std::uint32_t Magic = 0x32315256u; // "VR12"
    inline constexpr std::uint32_t Version = 1;
    inline constexpr std::uint32_t RingSize = 4;
    inline constexpr std::uint32_t NameChars = 96;

#pragma pack(push, 4)
    struct Slot
    {
        volatile LONG sequence = 0;
        std::uint32_t frameId = 0;
        std::uint32_t poseSequence = 0;
        std::uint32_t generation = 0;
        std::uint32_t fenceValueLow = 0;
        std::uint32_t fenceValueHigh = 0;
        wchar_t leftResourceName[NameChars]{};
        wchar_t rightResourceName[NameChars]{};
    };

    struct SharedState
    {
        std::uint32_t magic = Magic;
        std::uint32_t version = Version;
        std::uint32_t structSize = 0;
        std::uint32_t ringSize = RingSize;

        volatile LONG producerSequence = 0;
        std::uint32_t clientPid = 0;
        std::uint32_t generation = 0;
        std::uint32_t adapterLuidLow = 0;
        std::uint32_t adapterLuidHigh = 0;
        std::uint32_t width = 0;
        std::uint32_t height = 0;
        std::uint32_t format = 0;
        std::uint32_t viewInstancingTier = 0;
        wchar_t producerFenceName[NameChars]{};

        volatile LONG hostSequence = 0;
        std::uint32_t hostPid = 0;
        std::uint32_t hostHeartbeatLow = 0;
        std::uint32_t hostHeartbeatHigh = 0;
        std::uint32_t hostConsumedFrameId = 0;
        std::uint32_t hostAdapterLuidLow = 0;
        std::uint32_t hostAdapterLuidHigh = 0;

        volatile LONG publishSequence = 0;
        std::uint32_t latestSlot = 0;
        std::uint32_t latestFrameId = 0;
        Slot slots[RingSize]{};
    };
#pragma pack(pop)

    inline std::uint64_t Join64(std::uint32_t low, std::uint32_t high) noexcept
    {
        return static_cast<std::uint64_t>(low) |
            (static_cast<std::uint64_t>(high) << 32);
    }

    inline void Split64(std::uint64_t value,
        std::uint32_t& low, std::uint32_t& high) noexcept
    {
        low = static_cast<std::uint32_t>(value & 0xffffffffull);
        high = static_cast<std::uint32_t>(value >> 32);
    }

    inline bool FrameAtOrAfter(std::uint32_t candidate,
        std::uint32_t reference) noexcept
    {
        return reference == 0 ||
            static_cast<std::int32_t>(candidate - reference) >= 0;
    }
}
