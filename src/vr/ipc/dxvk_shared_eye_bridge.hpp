#pragma once

#include <cstddef>
#include <cstdint>

#include "vr/ipc/protocol.hpp"

namespace OutRunVR::DxvkSharedEyeBridge
{
    inline constexpr wchar_t MemoryName[] =
        L"Local\\OutRun2006Tweaks.VR.DxvkSharedEye.v1";
    inline constexpr std::uint32_t Magic = 0x4258444Fu; // 'ODXB'
    inline constexpr std::uint32_t Version = 1;
    inline constexpr std::uint32_t DxgiB8G8R8A8Unorm = 87;

    enum Flags : std::uint32_t
    {
        HostAlive = 1u << 0,
        ResourcesReady = 1u << 1,
    };

#pragma pack(push, 4)
    struct Slot
    {
        std::uint64_t leftHandle;
        std::uint64_t rightHandle;
    };

    struct State
    {
        std::uint32_t magic;
        std::uint32_t version;
        std::uint32_t structSize;
        volatile std::uint32_t sequence;
        volatile std::uint32_t hostPid;
        volatile std::uint32_t flags;
        std::uint32_t generation;
        std::uint32_t width;
        std::uint32_t height;
        std::uint32_t format;
        Slot slots[OutRunVR::RenderFrameRingSize];
        std::uint32_t reserved[8];
    };
#pragma pack(pop)

    static_assert(sizeof(Slot) == 16);
    static_assert(offsetof(State, slots) == 40);
    static_assert(sizeof(State) == 136);
}
