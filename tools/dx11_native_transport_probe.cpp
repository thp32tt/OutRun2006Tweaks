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
        // Production signal_producer_fence must submit its own EVENT.
        // This helper intentionally does NOT call Flush before polling.
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

    // R178 regression: an acquired slot can already have queued GPU writes
    // even when signal_producer_fence() has not been called. Invalidation must
    // not permit cancellation followed by a new-generation reuse.
    std::uint32_t staleAcquiredSlot = 99;
    require(ring.try_acquire_slot(
                d3d.context, 13, nullptr, staleAcquiredSlot),
            "R178 acquire frame before invalidation");
    const HANDLE staleLeftHandle = ring.shared_handle(staleAcquiredSlot, 0);
    require(staleLeftHandle != nullptr, "R178 original eye handle exists");
    ring.invalidate_lifetime();
    require(!ring.cancel_acquired_slot(staleAcquiredSlot, 13) &&
            ring.slot_state(staleAcquiredSlot) == SharedEyeSlotState::Acquired &&
            ring.slot_frame_id(staleAcquiredSlot) == 13 &&
            ring.shared_handle(staleAcquiredSlot, 0) == staleLeftHandle,
            "R178 invalidated acquired slot cannot be cancelled or recycled");
    require(!ring.bind_lifetime(1001, 2002, 7, 12) &&
            ring.slot_state(staleAcquiredSlot) == SharedEyeSlotState::Acquired,
            "R178 invalidated acquired slot blocks generation retag");

    // R306 integrated stereo transport: render two distinct native D3D11
    // eye targets, copy both into generation-owned shared surfaces, publish
    // only after GPU completion and verify both independent GPU pixel results.
    ring.shutdown();
    require(ring.initialize(
                d3d.device, 64, 64, DXGI_FORMAT_R8G8B8A8_UNORM) &&
            ring.bind_lifetime(1001, 2002, 7, 13),
            "R306 stereo producer generation initialized");

    D3D11_TEXTURE2D_DESC sourceDesc{};
    sourceDesc.Width = 64;
    sourceDesc.Height = 64;
    sourceDesc.MipLevels = 1;
    sourceDesc.ArraySize = 1;
    sourceDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    sourceDesc.SampleDesc.Count = 1;
    sourceDesc.Usage = D3D11_USAGE_DEFAULT;
    sourceDesc.BindFlags = D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* leftSource = nullptr;
    ID3D11Texture2D* rightSource = nullptr;
    ID3D11Texture2D* wrongSizeSource = nullptr;
    ID3D11Texture2D* foreignSource = nullptr;
    ID3D11RenderTargetView* leftView = nullptr;
    ID3D11RenderTargetView* rightView = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &sourceDesc, nullptr, &leftSource)) &&
            SUCCEEDED(d3d.device->CreateTexture2D(
                &sourceDesc, nullptr, &rightSource)) &&
            SUCCEEDED(d3d.device->CreateRenderTargetView(
                leftSource, nullptr, &leftView)) &&
            SUCCEEDED(d3d.device->CreateRenderTargetView(
                rightSource, nullptr, &rightView)),
            "R306 native source eye targets created");
    sourceDesc.Width = 32;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &sourceDesc, nullptr, &wrongSizeSource)),
            "R306 mismatched right eye created");
    sourceDesc.Width = 64;
    require(SUCCEEDED(foreign.device->CreateTexture2D(
                &sourceDesc, nullptr, &foreignSource)),
            "R306 foreign-device source created");

    std::uint32_t stereoSlot = 99;
    require(ring.try_acquire_slot(d3d.context, 20, nullptr, stereoSlot),
            "R306 acquire native game eye frame");
    require(!ring.submit_eye_pair(
                foreign.context, stereoSlot, 20, leftSource, rightSource) &&
            !ring.submit_eye_pair(
                d3d.context, stereoSlot, 20, leftSource, leftSource) &&
            !ring.submit_eye_pair(
                d3d.context, stereoSlot, 20, leftSource, wrongSizeSource) &&
            !ring.submit_eye_pair(
                d3d.context, stereoSlot, 20, leftSource, foreignSource) &&
            ring.slot_state(stereoSlot) == SharedEyeSlotState::Acquired &&
            ring.slot_frame_id(stereoSlot) == 20,
            "R306 invalid stereo inputs fail closed without partial publication");

    const float red[] = {1.f, 0.f, 0.f, 1.f};
    const float blue[] = {0.f, 0.f, 1.f, 1.f};
    d3d.context->ClearRenderTargetView(leftView, red);
    d3d.context->ClearRenderTargetView(rightView, blue);
    require(ring.submit_eye_pair(
                d3d.context, stereoSlot, 20, leftSource, rightSource) &&
            ring.slot_state(stereoSlot) == SharedEyeSlotState::ProducerPending,
            "R306 both native game eyes copied and producer GPU EVENT armed");
    publish_bounded(ring, d3d.context, stereoSlot, 20);
    NativeSharedEyePublication stereoPublication{};
    require(ring.snapshot_published_frame(
                stereoSlot, 20, stereoPublication) &&
            ring.validate_publication_snapshot(stereoPublication) &&
            stereoPublication.left_handle != stereoPublication.right_handle,
            "R306 complete stereo pair is advertised only after GPU fence");

    D3D11_TEXTURE2D_DESC readbackDesc = sourceDesc;
    readbackDesc.Usage = D3D11_USAGE_STAGING;
    readbackDesc.BindFlags = 0;
    readbackDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D* readback = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &readbackDesc, nullptr, &readback)),
            "R306 readback surface");
    for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
    {
        d3d.context->CopyResource(readback, ring.eye(stereoSlot, eyeIndex));
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(d3d.context->Map(
                    readback, 0, D3D11_MAP_READ, 0, &mapped)),
                "R306 GPU native stereo eye readback");
        const auto* pixel = static_cast<const std::uint8_t*>(mapped.pData);
        const bool correct = eyeIndex == 0
            ? pixel[0] == 255 && pixel[1] == 0 && pixel[2] == 0 && pixel[3] == 255
            : pixel[0] == 0 && pixel[1] == 0 && pixel[2] == 255 && pixel[3] == 255;
        d3d.context->Unmap(readback, 0);
        require(correct, "R306 left/right GPU pixel copy identity");
    }
    require(!ring.submit_eye_pair(
                d3d.context, stereoSlot, 20, leftSource, rightSource),
            "R306 published frame cannot be overwritten");
    const auto stereoAck = make_ack(ring.identity(), stereoSlot, 20);
    require(ring.retire_acknowledged(stereoAck) &&
            !ring.validate_publication_snapshot(stereoPublication),
            "R306 exact host ACK releases both eyes and invalidates snapshot");

    readback->Release();
    foreignSource->Release();
    wrongSizeSource->Release();
    rightView->Release();
    leftView->Release();
    rightSource->Release();
    leftSource->Release();
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
