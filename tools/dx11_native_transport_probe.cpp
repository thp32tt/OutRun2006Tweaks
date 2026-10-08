#include <Windows.h>

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <type_traits>

#include <d3d11.h>

#include "vr/d3d11/native_shared_eye_ring.hpp"

namespace
{
    using outrun::vr::dx11::NativeSharedEyePublication;
    using outrun::vr::dx11::NativeSharedEyeRing;
    using outrun::vr::dx11::SharedEyeSlotState;
    using OutRunVR::Core::FrameAck;
    using OutRunVR::Core::TransportIdentity;

    using ConsumerAckSignature =
        void (OutRunVR::Core::IFrameConsumer::*)(const FrameAck&) noexcept;
    static_assert(
        std::is_same_v<
            decltype(&OutRunVR::Core::IFrameConsumer::acknowledge),
            ConsumerAckSignature>,
        "R117 consumer ACK contract must carry exact FrameAck identity");

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R116 native transport probe failure: "
                      << message << '\n';
            std::exit(1);
        }
    }

    struct DevicePair
    {
        ID3D11Device* device{};
        ID3D11DeviceContext* context{};
    };

    DevicePair create_warp_device()
    {
        const D3D_FEATURE_LEVEL requested[] = {
            D3D_FEATURE_LEVEL_11_0,
            D3D_FEATURE_LEVEL_10_1,
            D3D_FEATURE_LEVEL_10_0,
        };

        DevicePair out{};
        D3D_FEATURE_LEVEL created = D3D_FEATURE_LEVEL_9_1;
        const HRESULT hr = D3D11CreateDevice(
            nullptr,
            D3D_DRIVER_TYPE_WARP,
            nullptr,
            0,
            requested,
            static_cast<UINT>(std::size(requested)),
            D3D11_SDK_VERSION,
            &out.device,
            &created,
            &out.context);
        require(SUCCEEDED(hr) && out.device && out.context,
                "WARP device/context creation");
        require(created >= D3D_FEATURE_LEVEL_10_0,
                "WARP feature level");
        return out;
    }

    FrameAck make_ack(
        const TransportIdentity& identity,
        std::uint32_t slot,
        std::uint64_t frameId)
    {
        FrameAck ack{};
        ack.producerPid = identity.producerPid;
        ack.consumerPid = identity.consumerPid;
        ack.runGeneration = identity.runGeneration;
        ack.generation = identity.generation;
        ack.slot = slot;
        ack.frameId = frameId;
        return ack;
    }

    void publish_bounded(
        NativeSharedEyeRing& ring,
        ID3D11DeviceContext* context,
        std::uint32_t slot,
        std::uint64_t frameId)
    {
        context->Flush();
        for (int attempt = 0; attempt < 2000; ++attempt)
        {
            if (ring.publish_if_fence_complete(context, slot, frameId))
                return;
            require(!ring.synchronization_faulted(),
                    "producer EVENT query fault");
            require(
                ring.slot_state(slot) == SharedEyeSlotState::ProducerPending,
                "pending slot changed state before publish");
            Sleep(1);
        }
        require(false, "producer EVENT did not complete within bounded wait");
    }
}

int main()
{
    DevicePair d3d = create_warp_device();
    DevicePair foreign = create_warp_device();

    NativeSharedEyeRing ring;
    require(!ring.ready() && !ring.activation_ready(),
            "ring must start dormant");
    require(
        ring.initialize(
            d3d.device, 64, 64, DXGI_FORMAT_R8G8B8A8_UNORM),
        "shared-eye ring initialize");
    require(ring.ready() && !ring.activation_ready(),
            "resource allocation alone must not activate transport");

    require(!ring.bind_lifetime(0, 2002, 7, 9),
            "zero producer PID must fail closed");

    const TransportIdentity generationA{1001, 2002, 7, 9};
    require(
        ring.bind_lifetime(
            generationA.producerPid,
            generationA.consumerPid,
            generationA.runGeneration,
            generationA.generation),
        "bind initial lifetime identity");
    require(ring.activation_ready() && ring.identity() == generationA,
            "exact lifetime identity activates dormant ring");

    std::uint32_t slot = 99;
    std::uint32_t rejectedSlot = 99;
    require(!ring.try_acquire_slot(foreign.context, 1, nullptr, rejectedSlot) &&
            rejectedSlot == OutRunVR::RenderFrameRingSize &&
            ring.all_slots_idle() && !ring.synchronization_faulted(),
            "foreign-device context cannot acquire a producer slot");
    require(ring.try_acquire_slot(d3d.context, 1, nullptr, slot),
            "acquire first frame");
    require(slot < OutRunVR::RenderFrameRingSize &&
            ring.slot_state(slot) == SharedEyeSlotState::Acquired &&
            ring.slot_frame_id(slot) == 1,
            "acquired slot identity");
    rejectedSlot = 99;
    require(!ring.try_acquire_slot(d3d.context, 1, nullptr, rejectedSlot) &&
            rejectedSlot == OutRunVR::RenderFrameRingSize &&
            ring.slot_state(slot) == SharedEyeSlotState::Acquired &&
            ring.slot_frame_id(slot) == 1,
            "duplicate acquired frame must retain its sole slot owner");
    require(
        !ring.bind_lifetime(1001, 2002, 7, 10),
        "in-flight allocation must reject generation retag");
    require(!ring.cancel_acquired_slot(slot, 2),
            "wrong frame cannot cancel acquired slot");
    require(ring.cancel_acquired_slot(slot, 1) && ring.all_slots_idle(),
            "exact frame cancellation returns slot to idle");

    const TransportIdentity generationB{1001, 2002, 7, 10};
    require(
        ring.bind_lifetime(
            generationB.producerPid,
            generationB.consumerPid,
            generationB.runGeneration,
            generationB.generation),
        "idle ring may bind next transport generation");
    require(ring.identity() == generationB,
            "new transport generation committed");

    slot = 99;
    require(ring.try_acquire_slot(d3d.context, 5, nullptr, slot),
            "acquire published-frame candidate");
    require(!ring.signal_producer_fence(foreign.context, slot, 5) &&
            ring.slot_state(slot) == SharedEyeSlotState::Acquired &&
            !ring.synchronization_faulted(),
            "foreign-device context cannot signal producer EVENT");
    require(ring.signal_producer_fence(d3d.context, slot, 5),
            "signal producer EVENT after eye work");
    rejectedSlot = 99;
    require(!ring.try_acquire_slot(d3d.context, 5, nullptr, rejectedSlot) &&
            rejectedSlot == OutRunVR::RenderFrameRingSize &&
            ring.slot_state(slot) == SharedEyeSlotState::ProducerPending &&
            ring.slot_frame_id(slot) == 5,
            "duplicate pending frame cannot acquire a second slot");
    require(!ring.publish_if_fence_complete(foreign.context, slot, 5) &&
            ring.slot_state(slot) == SharedEyeSlotState::ProducerPending &&
            !ring.synchronization_faulted(),
            "foreign-device context cannot publish producer EVENT");
    rejectedSlot = 99;
    require(!ring.try_acquire_slot(foreign.context, 6, nullptr, rejectedSlot) &&
            rejectedSlot == OutRunVR::RenderFrameRingSize &&
            ring.slot_state(slot) == SharedEyeSlotState::ProducerPending &&
            !ring.synchronization_faulted(),
            "foreign-device context cannot recycle pending producer fence");
    require(ring.slot_state(slot) == SharedEyeSlotState::ProducerPending,
            "signal transitions acquired slot to producer-pending");
    publish_bounded(ring, d3d.context, slot, 5);
    require(ring.slot_state(slot) == SharedEyeSlotState::Published,
            "completed EVENT publishes slot");
    rejectedSlot = 99;
    require(!ring.try_acquire_slot(d3d.context, 5, nullptr, rejectedSlot) &&
            rejectedSlot == OutRunVR::RenderFrameRingSize &&
            ring.slot_state(slot) == SharedEyeSlotState::Published &&
            ring.slot_frame_id(slot) == 5,
            "duplicate published frame cannot acquire a second slot");

    NativeSharedEyePublication publication{};
    require(ring.snapshot_published_frame(slot, 5, publication),
            "published frame must produce exact handoff snapshot");
    require(publication.identity == generationB &&
            publication.slot == slot &&
            publication.frame_id == 5 &&
            publication.left_handle == ring.shared_handle(slot, 0) &&
            publication.right_handle == ring.shared_handle(slot, 1) &&
            publication.width == 64 &&
            publication.height == 64 &&
            publication.format == DXGI_FORMAT_R8G8B8A8_UNORM,
            "published handoff snapshot identity and resources");
    require(ring.validate_publication_snapshot(publication),
            "fresh published handoff snapshot validates");
    NativeSharedEyePublication wrongFramePublication{};
    require(!ring.snapshot_published_frame(slot, 4, wrongFramePublication),
            "wrong frame cannot snapshot published handles");

    auto staleGenerationAck = make_ack(generationA, slot, 5);
    require(!ring.retire_acknowledged(staleGenerationAck) &&
            ring.slot_state(slot) == SharedEyeSlotState::Published,
            "stale generation ACK cannot retire published slot");

    auto wrongProducerAck = make_ack(generationB, slot, 5);
    wrongProducerAck.producerPid ^= 1u;
    require(!ring.retire_acknowledged(wrongProducerAck) &&
            ring.slot_state(slot) == SharedEyeSlotState::Published,
            "wrong process identity ACK cannot retire slot");

    auto staleFrameAck = make_ack(generationB, slot, 4);
    require(!ring.retire_acknowledged(staleFrameAck) &&
            ring.slot_state(slot) == SharedEyeSlotState::Published,
            "older frame ACK cannot retire newer publication");

    auto exactAck = make_ack(generationB, slot, 5);
    require(ring.retire_acknowledged(exactAck) &&
            ring.slot_state(slot) == SharedEyeSlotState::Free &&
            ring.slot_frame_id(slot) == 0,
            "exact identity/frame ACK retires publication");
    require(!ring.validate_publication_snapshot(publication),
            "ACK retirement invalidates published handoff snapshot");
    std::uint32_t recycledSlot = 99;
    require(ring.try_acquire_slot(d3d.context, 5, nullptr, recycledSlot) &&
            ring.cancel_acquired_slot(recycledSlot, 5) &&
            ring.all_slots_idle(),
            "ACK retirement permits frame-id reuse without stale ownership");

    slot = 99;
    require(ring.try_acquire_slot(d3d.context, 9, nullptr, slot),
            "acquire cumulative-ACK candidate");
    require(ring.signal_producer_fence(d3d.context, slot, 9),
            "signal second producer EVENT");
    publish_bounded(ring, d3d.context, slot, 9);
    auto cumulativeAck = make_ack(generationB, slot, 10);
    require(ring.retire_acknowledged(cumulativeAck) &&
            ring.all_slots_idle(),
            "same-generation cumulative ACK may release older frame");

    slot = 99;
    require(ring.try_acquire_slot(d3d.context, 12, nullptr, slot),
            "acquire invalidation candidate");
    require(ring.signal_producer_fence(d3d.context, slot, 12),
            "signal invalidation candidate EVENT");
    publish_bounded(ring, d3d.context, slot, 12);
    NativeSharedEyePublication invalidationPublication{};
    require(ring.snapshot_published_frame(
                slot, 12, invalidationPublication) &&
            ring.validate_publication_snapshot(invalidationPublication),
            "pre-invalidation published snapshot must validate");
    auto generationBAck = make_ack(generationB, slot, 12);
    ring.invalidate_lifetime();
    require(!ring.activation_ready(),
            "lifetime invalidation disables activation");
    require(!ring.validate_publication_snapshot(invalidationPublication),
            "lifetime invalidation rejects stale handoff snapshot");
    require(!ring.retire_acknowledged(generationBAck) &&
            ring.slot_state(slot) == SharedEyeSlotState::Published,
            "invalidated lifetime cannot manufacture retirement");
    require(!ring.bind_lifetime(1001, 2002, 7, 11),
            "busy invalidated allocation requires hard retirement");

    ring.shutdown();
    require(!ring.ready() && !ring.activation_ready() &&
            ring.all_slots_idle(),
            "shutdown hard-retires old generation resources");

    require(
        ring.initialize(
            d3d.device, 64, 64, DXGI_FORMAT_R8G8B8A8_UNORM),
        "reinitialize fresh ring after hard retirement");
    require(ring.bind_lifetime(1001, 2002, 7, 11) &&
            ring.activation_ready(),
            "fresh allocation accepts next generation");

    ring.shutdown();
    foreign.context->Release();
    foreign.device->Release();
    d3d.context->Release();
    d3d.device->Release();

    std::cout << "DX11 native shared-eye context ownership: PASS\n";
    std::cout << "DX11 native shared-eye transport behavior R116: PASS\n";
    std::cout << "DX11 native shared-eye publication handoff R118: PASS\n";
    return 0;
}
