#pragma once

#include "vr/core/frame_types.hpp"
#include "vr/core/transport.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace OutRunVR::IpcV3
{
    inline constexpr std::uint32_t ProtocolVersion = 3;
    inline constexpr std::uint32_t RingSize = 4;
    using WireHandle = std::uint64_t;

    inline constexpr wchar_t HostStateName[] = L"Local\\OutRun2006Tweaks.VR.v3.HostState";
    inline constexpr wchar_t ClientStateName[] = L"Local\\OutRun2006Tweaks.VR.v3.ClientState";
    inline constexpr wchar_t FrameRingName[] = L"Local\\OutRun2006Tweaks.VR.v3.FrameRing";
    inline constexpr wchar_t AckStateName[] = L"Local\\OutRun2006Tweaks.VR.v3.AckState";

    inline constexpr std::uint32_t HostMagic = 0x3348524Fu;   // ORH3
    inline constexpr std::uint32_t ClientMagic = 0x3343524Fu; // ORC3
    inline constexpr std::uint32_t FrameMagic = 0x3346524Fu;  // ORF3
    inline constexpr std::uint32_t AckMagic = 0x3341524Fu;    // ORA3

#pragma pack(push, 4)
    struct WireFov
    {
        float angleLeft{};
        float angleRight{};
        float angleUp{};
        float angleDown{};
    };

    struct WireEyeView
    {
        float orientation[4]{};
        float positionMeters[3]{};
        float reserved{};
        WireFov fov{};
    };

    // Single writer: x64 host. Single reader: x86 game.
    struct HostState
    {
        std::uint32_t magic{HostMagic};
        std::uint32_t version{ProtocolVersion};
        std::uint32_t structSize{sizeof(HostState)};
        volatile std::uint32_t sequence{};
        std::uint32_t hostPid{};
        std::uint32_t flags{};
        std::uint32_t referenceSpaceGeneration{};
        std::uint32_t directTransportGeneration{};
        std::uint64_t poseId{};
        std::int64_t predictedDisplayTime{};
        std::int64_t sampleQpc{};
        float headOrientation[4]{};
        float headPositionMeters[3]{};
        std::uint32_t recommendedWidth[2]{};
        std::uint32_t recommendedHeight[2]{};
        std::uint32_t adapterLuidLow{};
        std::int32_t adapterLuidHigh{};
        WireEyeView eyes[2]{};
        char runtimeName[64]{};
    };

    // Single writer: x86 game. Single reader: x64 host.
    struct ClientState
    {
        std::uint32_t magic{ClientMagic};
        std::uint32_t version{ProtocolVersion};
        std::uint32_t structSize{sizeof(ClientState)};
        volatile std::uint32_t sequence{};
        std::uint32_t clientPid{};
        std::uint32_t flags{};
        std::uint32_t presentationMode{};
        std::uint32_t gameState{};
        std::uint32_t stereoState{};
        std::uint32_t lastFailure{};
        std::uint32_t adapterLuidLow{};
        std::int32_t adapterLuidHigh{};
        std::uint32_t interopProbeGeneration{};
        std::uint32_t interopProbeToken{};
        WireHandle interopProbeHandle{};
        std::uint32_t backbufferWidth{};
        std::uint32_t backbufferHeight{};
        std::uint64_t lastPresentedFrameId{};
        std::uint64_t lastRenderedPoseId{};
    };

    struct FrameDescriptor
    {
        std::uint64_t frameId{};
        std::uint64_t renderPoseId{};
        std::int64_t presentQpc{};
        std::uint32_t presentationMode{};
        std::uint32_t flags{};
        std::uint32_t failureReason{};
        std::uint32_t transportKind{};
        std::uint32_t transportGeneration{};
        std::uint32_t transportSlot{};
        std::uint32_t width{};
        std::uint32_t height{};
        std::uint32_t format{};
        WireHandle leftHandle{};
        WireHandle rightHandle{};
        WireEyeView renderedEyes[2]{};
    };

    // Single producer: x86 game. Single consumer: x64 host.
    struct FrameRing
    {
        std::uint32_t magic{FrameMagic};
        std::uint32_t version{ProtocolVersion};
        std::uint32_t structSize{sizeof(FrameRing)};
        std::uint32_t slotCount{RingSize};
        volatile std::uint32_t publishSequence{};
        volatile std::uint32_t latestSlot{};
        std::uint32_t producerPid{};
        std::uint32_t generation{};
        FrameDescriptor slots[RingSize]{};
    };

    // Single writer: x64 host. Single reader: x86 game.
    struct AckState
    {
        std::uint32_t magic{AckMagic};
        std::uint32_t version{ProtocolVersion};
        std::uint32_t structSize{sizeof(AckState)};
        volatile std::uint32_t sequence{};
        std::uint32_t consumerPid{};
        std::uint32_t acceptedProbeGeneration{};
        std::uint32_t acceptedProbeToken{};
        std::uint32_t transportGeneration{};
        std::uint64_t consumedFrameId{};
        std::uint32_t consumedSlot{};
        std::uint32_t flags{};
    };
#pragma pack(pop)

    static_assert(sizeof(WireHandle) == 8);
    static_assert(sizeof(WireFov) == 16);
    static_assert(sizeof(WireEyeView) == 48);
    static_assert(std::is_standard_layout_v<HostState>);
    static_assert(std::is_standard_layout_v<ClientState>);
    static_assert(std::is_standard_layout_v<FrameDescriptor>);
    static_assert(std::is_standard_layout_v<FrameRing>);
    static_assert(std::is_standard_layout_v<AckState>);
}
