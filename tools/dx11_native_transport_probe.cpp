#include <Windows.h>

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <type_traits>

#include <d3d11.h>
#include <d3dcompiler.h>

#include "vr/d3d11/native_shared_eye_ring.hpp"
#include "vr/d3d11/native_game_stereo_submission.hpp"

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
    require(!ring.try_acquire_slot(d3d.context, 5, nullptr, recycledSlot) &&
            recycledSlot == OutRunVR::RenderFrameRingSize && ring.all_slots_idle(),
            "retired frame ID cannot be replayed in a transport lifetime");
    auto futureAck = make_ack(generationB, slot, 6);
    require(!ring.try_acquire_slot(d3d.context, 6, &futureAck, recycledSlot) &&
            ring.all_slots_idle(),
            "future cumulative ACK cannot retire a new eye pair");
    require(ring.try_acquire_slot(d3d.context, 6, nullptr, recycledSlot) &&
            ring.cancel_acquired_slot(recycledSlot, 6) && ring.all_slots_idle(),
            "new frame ID still permits input-safe cancellation");

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
    require(!ring.try_acquire_slot(d3d.context, 10, nullptr, rejectedSlot) &&
            !ring.try_acquire_slot(d3d.context, 9, nullptr, rejectedSlot),
            "cumulative ACK high watermark rejects old or already ACKed frame");
    require(ring.try_acquire_slot(d3d.context, 11, nullptr, recycledSlot) &&
            ring.cancel_acquired_slot(recycledSlot, 11),
            "frame newer than cumulative ACK can be reserved and cancelled");

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
    // Emulate the x64 OpenXR host on a second D3D11 WARP device. Reading
    // the producer's resource directly would not prove shared-handle transport.
    ID3D11Texture2D* hostEyes[2]{};
    ID3D11Texture2D* hostReadback = nullptr;
    require(SUCCEEDED(foreign.device->CreateTexture2D(
                &readbackDesc, nullptr, &hostReadback)),
            "R306 independent host GPU readback surface");
    const HANDLE hostHandles[] = {
        stereoPublication.left_handle, stereoPublication.right_handle};
    for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
    {
        require(SUCCEEDED(foreign.device->OpenSharedResource(
                    hostHandles[eyeIndex], __uuidof(ID3D11Texture2D),
                    reinterpret_cast<void**>(&hostEyes[eyeIndex]))) &&
                hostEyes[eyeIndex],
                "R306 host opens published native producer eye handle");
        foreign.context->CopyResource(hostReadback, hostEyes[eyeIndex]);
        D3D11_MAPPED_SUBRESOURCE hostMapped{};
        require(SUCCEEDED(foreign.context->Map(
                    hostReadback, 0, D3D11_MAP_READ, 0, &hostMapped)),
                "R306 host reads independent shared eye GPU pixels");
        const auto* px = static_cast<const std::uint8_t*>(hostMapped.pData);
        const bool match = eyeIndex == 0
            ? px[0] == 255 && px[1] == 0 && px[2] == 0 && px[3] == 255
            : px[0] == 0 && px[1] == 0 && px[2] == 255 && px[3] == 255;
        foreign.context->Unmap(hostReadback, 0);
        require(match, "R306 foreign host shared handle preserves both eye colors");
    }
    hostReadback->Release();
    hostEyes[1]->Release();
    hostEyes[0]->Release();

    require(!ring.submit_eye_pair(
                d3d.context, stereoSlot, 20, leftSource, rightSource),
            "R306 published frame cannot be overwritten");
    const auto stereoAck = make_ack(ring.identity(), stereoSlot, 20);
    require(ring.retire_acknowledged(stereoAck) &&
            !ring.validate_publication_snapshot(stereoPublication),
            "R306 exact host ACK releases both eyes and invalidates snapshot");

    // 00695 live native eye producer: WARP-resolve two different game-created
    // 4xMSAA color buffers into the pre-existing single-sample host eye ring.
    // Prove that source sample mismatch does not enqueue a half-resolved frame.
    D3D11_TEXTURE2D_DESC msaaDesc = sourceDesc;
    msaaDesc.SampleDesc.Count = 4;
    msaaDesc.SampleDesc.Quality = 0;
    UINT msaaQualities = 0;
    UINT resolveSupport = 0;
    require(SUCCEEDED(d3d.device->CheckMultisampleQualityLevels(
                sourceDesc.Format, 4, &msaaQualities)) && msaaQualities > 0 &&
            SUCCEEDED(d3d.device->CheckFormatSupport(
                sourceDesc.Format, &resolveSupport)) &&
            (resolveSupport & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) != 0,
            "00695 WARP native game 4x eye format can resolve");
    ID3D11Texture2D* msaaLeft = nullptr;
    ID3D11Texture2D* msaaRight = nullptr;
    ID3D11RenderTargetView* msaaLeftView = nullptr;
    ID3D11RenderTargetView* msaaRightView = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &msaaDesc, nullptr, &msaaLeft)) &&
            SUCCEEDED(d3d.device->CreateTexture2D(
                &msaaDesc, nullptr, &msaaRight)) &&
            SUCCEEDED(d3d.device->CreateRenderTargetView(
                msaaLeft, nullptr, &msaaLeftView)) &&
            SUCCEEDED(d3d.device->CreateRenderTargetView(
                msaaRight, nullptr, &msaaRightView)),
            "00695 local game 4x stereo targets created");
    const float green[] = {0.f, 1.f, 0.f, 1.f};
    const float magenta[] = {1.f, 0.f, 1.f, 1.f};
    d3d.context->ClearRenderTargetView(msaaLeftView, green);
    d3d.context->ClearRenderTargetView(msaaRightView, magenta);
    std::uint32_t msaaSlot = 99;
    require(ring.try_acquire_slot(d3d.context, 21, nullptr, msaaSlot) &&
            !ring.submit_eye_pair(
                d3d.context, msaaSlot, 21, msaaLeft, rightSource) &&
            ring.slot_state(msaaSlot) == SharedEyeSlotState::Acquired &&
            ring.slot_frame_id(msaaSlot) == 21,
            "00695 mixed sample stereo pair must fail before GPU Resolve");
    require(ring.submit_eye_pair(
                d3d.context, msaaSlot, 21, msaaLeft, msaaRight) &&
            ring.slot_state(msaaSlot) == SharedEyeSlotState::ProducerPending,
            "00695 both 4x game eyes submitted for native DX11 MSAA Resolve");
    publish_bounded(ring, d3d.context, msaaSlot, 21);
    NativeSharedEyePublication msaaPublication{};
    require(ring.snapshot_published_frame(msaaSlot, 21, msaaPublication) &&
            ring.validate_publication_snapshot(msaaPublication),
            "00695 MSAA eye pair has one complete producer EVENT and exact publication");
    for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
    {
        d3d.context->CopyResource(readback, ring.eye(msaaSlot, eyeIndex));
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(d3d.context->Map(
                    readback, 0, D3D11_MAP_READ, 0, &mapped)),
                "00695 GPU MSAA resolved eye readback");
        const auto* p = static_cast<const std::uint8_t*>(mapped.pData);
        const bool match = eyeIndex == 0
            ? p[0] == 0 && p[1] == 255 && p[2] == 0 && p[3] == 255
            : p[0] == 255 && p[1] == 0 && p[2] == 255 && p[3] == 255;
        d3d.context->Unmap(readback, 0);
        require(match, "00695 left/right game eye GPU MSAA Resolve color identity");
    }
    // The native host must consume the resolved single-sample texture,
    // not the producer's game MSAA resource.
    ID3D11Texture2D* hostMsaaReadback = nullptr;
    require(SUCCEEDED(foreign.device->CreateTexture2D(
                &readbackDesc, nullptr, &hostMsaaReadback)),
            "00695 independent host resolved-eye staging");
    for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
    {
        ID3D11Texture2D* hostResolvedEye = nullptr;
        const HANDLE handle = eyeIndex == 0
            ? msaaPublication.left_handle : msaaPublication.right_handle;
        require(SUCCEEDED(foreign.device->OpenSharedResource(
                    handle, __uuidof(ID3D11Texture2D),
                    reinterpret_cast<void**>(&hostResolvedEye))) && hostResolvedEye,
                "00695 host opened published resolved MSAA eye handle");
        foreign.context->CopyResource(hostMsaaReadback, hostResolvedEye);
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(foreign.context->Map(
                    hostMsaaReadback, 0, D3D11_MAP_READ, 0, &mapped)),
                "00695 independent OpenXR host GPU resolved color");
        const auto* p = static_cast<const std::uint8_t*>(mapped.pData);
        const bool match = eyeIndex == 0
            ? p[0] == 0 && p[1] == 255 && p[2] == 0 && p[3] == 255
            : p[0] == 255 && p[1] == 0 && p[2] == 255 && p[3] == 255;
        foreign.context->Unmap(hostMsaaReadback, 0);
        hostResolvedEye->Release();
        require(match, "00695 foreign host sees both independent resolved game eyes");
    }
    hostMsaaReadback->Release();
    require(ring.retire_acknowledged(
                make_ack(ring.identity(), msaaSlot, 21)) &&
            !ring.validate_publication_snapshot(msaaPublication),
            "00695 exact ACK releases GPU-resolved stereo frame");
    msaaRightView->Release();
    msaaLeftView->Release();
    msaaRight->Release();
    msaaLeft->Release();

    // 00812: real native Draw recorders can render directly to two ring RTs.
    // This is a distinct per-eye GPU producer path, not duplicated mono,
    // and uses the same completion fence + host-visible shared handles.
    const auto nativeDraw = [](
        void* user, ID3D11DeviceContext* context,
        ID3D11RenderTargetView* left, ID3D11RenderTargetView* right) noexcept -> bool
    {
        if (!user || !context || !left || !right || left == right)
            return false;
        const auto* colors = static_cast<const float (*)[4]>(user);
        context->ClearRenderTargetView(left, colors[0]);
        context->ClearRenderTargetView(right, colors[1]);
        return true;
    };
    const float nativeEyeColors[2][4] = {
        {0.f, 1.f, 1.f, 1.f}, // left cyan
        {1.f, 1.f, 0.f, 1.f}  // right yellow
    };
    std::uint32_t directSlot = 99;
    require(ring.try_acquire_slot(d3d.context, 22, nullptr, directSlot) &&
            !ring.render_eye_pair(
                foreign.context, directSlot, 22, nativeDraw,
                const_cast<float (*)[4]>(nativeEyeColors)) &&
            !ring.render_eye_pair(
                d3d.context, directSlot, 22, nullptr, nullptr) &&
            !ring.render_eye_pair(
                d3d.context, directSlot, 23, nativeDraw,
                const_cast<float (*)[4]>(nativeEyeColors)) &&
            ring.slot_state(directSlot) == SharedEyeSlotState::Acquired &&
            !ring.synchronization_faulted(),
            "00812 direct native eye GPU writer rejects foreign/empty/wrong frame");
    require(ring.render_eye_pair(
                d3d.context, directSlot, 22, nativeDraw,
                const_cast<float (*)[4]>(nativeEyeColors)) &&
            ring.slot_state(directSlot) == SharedEyeSlotState::ProducerPending &&
            !ring.cancel_acquired_slot(directSlot, 22),
            "00812 both real native eyes recorded before fence; no pending reuse");
    publish_bounded(ring, d3d.context, directSlot, 22);
    NativeSharedEyePublication directPublication{};
    require(ring.snapshot_published_frame(
                directSlot, 22, directPublication) &&
            ring.validate_publication_snapshot(directPublication),
            "00812 independently rendered game eyes publish only after EVENT");
    for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
    {
        d3d.context->CopyResource(readback, ring.eye(directSlot, eyeIndex));
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(d3d.context->Map(
                    readback, 0, D3D11_MAP_READ, 0, &mapped)),
                "00812 rendered eye GPU readback");
        const auto* pixel = static_cast<const std::uint8_t*>(mapped.pData);
        const bool match = eyeIndex == 0
            ? pixel[0] == 0 && pixel[1] == 255 && pixel[2] == 255 &&
              pixel[3] == 255
            : pixel[0] == 255 && pixel[1] == 255 && pixel[2] == 0 &&
              pixel[3] == 255;
        d3d.context->Unmap(readback, 0);
        require(match, "00812 direct GPU per-eye pixels retained, not mono");
    }
    require(ring.retire_acknowledged(
                make_ack(ring.identity(), directSlot, 22)) &&
            !ring.validate_publication_snapshot(directPublication),
            "00812 exact OpenXR host ACK retires directly rendered native eyes");

    // 00818: exercise the production submission object's direct producer
    // route end-to-end: two real D3D11 eye RTV writes -> one producer EVENT ->
    // exact Frame.v2 DirectGPU host metadata -> ACK lifetime retirement.
    // Rejected provenance must leave the acquired slot untouched.
    outrun::vr::dx11::NativeGameStereoSubmission directSubmit(ring);
    require(directSubmit.begin(d3d.context, 23, 31) &&
            directSubmit.active() && !directSubmit.in_flight(),
            "00818 direct game-eye submission acquired exact frame");
    void* eyeUser = const_cast<float (*)[4]>(nativeEyeColors);
    require(!directSubmit.render_direct_eyes(
                nativeDraw, eyeUser, 2, 2, 0x101, 0x101, 31) &&
            !directSubmit.render_direct_eyes(
                nativeDraw, eyeUser, 2, 2, 0x101, 0x202, 32) &&
            !directSubmit.render_direct_eyes(
                nativeDraw, eyeUser, 0, 2, 0x101, 0x202, 31) &&
            !directSubmit.render_direct_eyes(
                nullptr, eyeUser, 2, 2, 0x101, 0x202, 31) &&
            !directSubmit.in_flight() &&
            !ring.synchronization_faulted(),
            "00818 invalid source camera/pose/draw contract is rejected before GPU writes");
    require(directSubmit.render_direct_eyes(
                nativeDraw, eyeUser, 2, 3, 0x101, 0x202, 31) &&
            directSubmit.in_flight() &&
            !directSubmit.cancel(),
            "00818 two independent native game eyes recorded, pending frame not cancelable");
    outrun::vr::dx11::NativeGameStereoPublishedFrame directFrame{};
    bool directReady = false;
    for (int retry = 0; retry < 2000 && !directReady; ++retry) {
        directReady = directSubmit.try_publish(directFrame);
        require(!ring.synchronization_faulted(),
                "00818 direct game-eye producer fence must not fail");
        if (!directReady) Sleep(1);
    }
    require(directReady && !directSubmit.active() &&
            directFrame.sourcePoseSequence == 31 &&
            directFrame.eyeViewSignature[0] == 0x101 &&
            directFrame.eyeViewSignature[1] == 0x202 &&
            ring.validate_publication_snapshot(directFrame.gpu),
            "00818 exact two-eye pose and camera signatures persist across GPU fence");
    OutRunVR::SharedRenderFrameState hostFrame{};
    hostFrame.clientPid = generationB.producerPid;
    hostFrame.reserved[OutRunVR::RenderFrameRunGenerationIndex] = generationB.runGeneration;
    hostFrame.frameId = 23;
    hostFrame.sourcePoseSequence = 31;
    hostFrame.state = OutRunVR::StereoSbsActive;
    hostFrame.presentQpc = 1234;
    hostFrame.flags = OutRunVR::RenderFrameStereoComplete |
        OutRunVR::RenderFrameWorldStereo |
        OutRunVR::RenderFrameDrawDuplicated |
        OutRunVR::RenderFrameEffectivePoseValid;
    // The ring was rebound to generation 13 for the producer; the game frame
    // must match its current transport identity, not an older generation.
    require(directSubmit.attach_host_frame(directFrame, hostFrame) &&
            (hostFrame.flags & OutRunVR::RenderFrameDirectGpuTransport) &&
            hostFrame.reserved[OutRunVR::RenderFrameDirectSlotIndex] ==
                directFrame.gpu.slot &&
            hostFrame.reserved[OutRunVR::RenderFrameDirectGenerationIndex] ==
                ring.identity().generation &&
            hostFrame.backbufferWidth == 64 &&
            hostFrame.backbufferHeight == 64,
            "00818 native L/R host handoff stamped exact shared resources");
    for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex) {
        d3d.context->CopyResource(readback,
            ring.eye(directFrame.gpu.slot, eyeIndex));
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(d3d.context->Map(
                    readback, 0, D3D11_MAP_READ, 0, &mapped)),
                "00818 direct GPU eye readback");
        const auto* pixel = static_cast<const std::uint8_t*>(mapped.pData);
        const bool match = eyeIndex == 0
            ? pixel[0] == 0 && pixel[1] == 255 && pixel[2] == 255 &&
              pixel[3] == 255
            : pixel[0] == 255 && pixel[1] == 255 && pixel[2] == 0 &&
              pixel[3] == 255;
        d3d.context->Unmap(readback, 0);
        require(match, "00818 game eye GPU colors remain distinct without CopyResource producer");
    }
    auto mismatchedGame = hostFrame;
    mismatchedGame.sourcePoseSequence = 32;
    require(!directSubmit.attach_host_frame(directFrame, mismatchedGame),
            "00818 wrong game pose may not advertise native stereo");
    require(ring.retire_acknowledged(
                make_ack(ring.identity(), directFrame.gpu.slot, 23)) &&
            !directSubmit.attach_host_frame(directFrame, hostFrame),
            "00818 ACK invalidates old direct eye publication");

    // 00820: preserve the native game caller's desktop OM/RS bindings while
    // two actual per-eye RTVs are selected sequentially. Reject accidental
    // writes into a stale desktop target across the menu/race eye passes.
    D3D11_VIEWPORT preservedViewport{3.f, 5.f, 32.f, 24.f, 0.f, 1.f};
    D3D11_RECT preservedScissor{3, 5, 35, 29};
    ID3D11RenderTargetView* originalGameTarget = leftView;
    // Keep a real caller-owned DSV bound to prove that a two-eye native game
    // replay restores both RT0 and the original desktop depth attachment.
    D3D11_TEXTURE2D_DESC preservedDepthDesc{};
    preservedDepthDesc.Width = 64;
    preservedDepthDesc.Height = 64;
    preservedDepthDesc.MipLevels = 1;
    preservedDepthDesc.ArraySize = 1;
    preservedDepthDesc.Format = DXGI_FORMAT_D24_UNORM_S8_UINT;
    preservedDepthDesc.SampleDesc.Count = 1;
    preservedDepthDesc.Usage = D3D11_USAGE_DEFAULT;
    preservedDepthDesc.BindFlags = D3D11_BIND_DEPTH_STENCIL;
    ID3D11Texture2D* preservedDepthTexture = nullptr;
    ID3D11DepthStencilView* preservedDepthView = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &preservedDepthDesc, nullptr, &preservedDepthTexture)) &&
            SUCCEEDED(d3d.device->CreateDepthStencilView(
                preservedDepthTexture, nullptr, &preservedDepthView)),
            "00821 caller desktop DSV fixture created");
    d3d.context->OMSetRenderTargets(1, &originalGameTarget, preservedDepthView);
    d3d.context->RSSetViewports(1, &preservedViewport);
    d3d.context->RSSetScissorRects(1, &preservedScissor);
    D3D11_RASTERIZER_DESC preservedRasterDesc{};
    preservedRasterDesc.FillMode = D3D11_FILL_SOLID;
    preservedRasterDesc.CullMode = D3D11_CULL_NONE;
    preservedRasterDesc.DepthClipEnable = TRUE;
    preservedRasterDesc.ScissorEnable = TRUE;
    ID3D11RasterizerState* preservedRaster = nullptr;
    require(SUCCEEDED(d3d.device->CreateRasterizerState(
                &preservedRasterDesc, &preservedRaster)),
            "00822 original game raster state created");
    const FLOAT preservedBlendFactor[4]{0.125f, 0.25f, 0.5f, 0.75f};
    constexpr UINT preservedMask = 0xff01ff01u;
    constexpr UINT preservedStencilRef = 11u;
    d3d.context->RSSetState(preservedRaster);
    d3d.context->OMSetBlendState(nullptr, preservedBlendFactor, preservedMask);
    d3d.context->OMSetDepthStencilState(nullptr, preservedStencilRef);
    // A real game Draw can leave IA bindings/topology changed for the other
    // camera; ensure the producer never leaks one eye into the next or back
    // into the original game's desktop draw pipeline.
    D3D11_BUFFER_DESC gameBufferDesc{};
    gameBufferDesc.ByteWidth = 64u;
    gameBufferDesc.Usage = D3D11_USAGE_DEFAULT;
    gameBufferDesc.BindFlags = D3D11_BIND_VERTEX_BUFFER | D3D11_BIND_INDEX_BUFFER;
    ID3D11Buffer* originalGameBuffer = nullptr;
    ID3D11Buffer* alternateEyeBuffer = nullptr;
    require(SUCCEEDED(d3d.device->CreateBuffer(
                &gameBufferDesc, nullptr, &originalGameBuffer)) &&
            SUCCEEDED(d3d.device->CreateBuffer(
                &gameBufferDesc, nullptr, &alternateEyeBuffer)),
            "00823 original/changed game IA buffers created");
    constexpr UINT originalStride = 16u, originalOffset = 4u;
    d3d.context->IASetVertexBuffers(
        0u, 1u, &originalGameBuffer, &originalStride, &originalOffset);
    d3d.context->IASetIndexBuffer(originalGameBuffer, DXGI_FORMAT_R16_UINT, 2u);
    d3d.context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    // The game binds scene textures, samplers, and shader constants before
    // eye replay. Left-eye changes must not bleed into the right eye or back
    // into the original game context.
    D3D11_TEXTURE2D_DESC gameSampleDesc{};
    gameSampleDesc.Width = 2u;
    gameSampleDesc.Height = 2u;
    gameSampleDesc.MipLevels = 1u;
    gameSampleDesc.ArraySize = 1u;
    gameSampleDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    gameSampleDesc.SampleDesc.Count = 1u;
    gameSampleDesc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    ID3D11Texture2D* gameSampleTexture = nullptr;
    ID3D11ShaderResourceView* gameSampleView = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &gameSampleDesc, nullptr, &gameSampleTexture)) &&
            SUCCEEDED(d3d.device->CreateShaderResourceView(
                gameSampleTexture, nullptr, &gameSampleView)),
            "00823 game shader-resource input created");
    D3D11_SAMPLER_DESC gameSamplerDesc{};
    gameSamplerDesc.Filter = D3D11_FILTER_MIN_MAG_MIP_POINT;
    gameSamplerDesc.AddressU = gameSamplerDesc.AddressV =
        gameSamplerDesc.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    gameSamplerDesc.MaxLOD = D3D11_FLOAT32_MAX;
    ID3D11SamplerState* gameSampler = nullptr;
    require(SUCCEEDED(d3d.device->CreateSamplerState(
                &gameSamplerDesc, &gameSampler)),
            "00823 game sampler created");
    D3D11_BUFFER_DESC gameConstantsDesc{};
    gameConstantsDesc.ByteWidth = 64u;
    gameConstantsDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    ID3D11Buffer* gameConstants = nullptr;
    require(SUCCEEDED(d3d.device->CreateBuffer(
                &gameConstantsDesc, nullptr, &gameConstants)),
            "00823 game shader constants created");
    d3d.context->PSSetShaderResources(0u, 1u, &gameSampleView);
    d3d.context->PSSetSamplers(0u, 1u, &gameSampler);
    d3d.context->PSSetConstantBuffers(0u, 1u, &gameConstants);
    // Exercise a real inherited GS on the shared caller context. D3D9
    // live geometry must never inherit this shader on either stereo pass.
    constexpr char gameGeometrySource[] =
        "struct V { float4 p : SV_Position; };"
        "[maxvertexcount(3)] void main(triangle V input[3],"
        " inout TriangleStream<V> output) {"
        " for (uint i=0; i<3; ++i) output.Append(input[i]);"
        " output.RestartStrip(); }";
    // Test-only shader compiler is loaded explicitly: the Win32 isolated
    // transport target must not depend on an SDK import-library variant.
    // Failure remains an explicit WARP regression failure, never a fake PASS.
    HMODULE compilerModule = LoadLibraryW(L"d3dcompiler_47.dll");
    require(compilerModule != nullptr,
            "00827 WARP shader compiler runtime available");
    const auto compileShader = reinterpret_cast<decltype(&D3DCompile)>(
        GetProcAddress(compilerModule, "D3DCompile"));
    require(compileShader != nullptr,
            "00827 WARP shader compiler entrypoint available");
    ID3DBlob* geometryBytecode = nullptr;
    const HRESULT geometryCompileResult = compileShader(
        gameGeometrySource, sizeof(gameGeometrySource)-1u,
        "native_eye_game", nullptr, nullptr, "main", "gs_4_0",
        D3DCOMPILE_ENABLE_STRICTNESS, 0u, &geometryBytecode, nullptr);
    FreeLibrary(compilerModule);
    require(SUCCEEDED(geometryCompileResult) && geometryBytecode,
            "00827 caller geometry stage compiled");
    ID3D11GeometryShader* originalGeometryShader = nullptr;
    require(SUCCEEDED(d3d.device->CreateGeometryShader(
                geometryBytecode->GetBufferPointer(),
                geometryBytecode->GetBufferSize(), nullptr,
                &originalGeometryShader)) && originalGeometryShader,
            "00827 caller geometry stage created");
    geometryBytecode->Release();
    d3d.context->GSSetShader(originalGeometryShader, nullptr, 0u);
    struct GameEyeFixture {
        bool sawBoundEye[2]{};
        ID3D11DepthStencilView* eyeDepth[2]{};
        ID3D11DepthStencilView* callerDepth{};
        ID3D11Buffer* originalBuffer{};
        ID3D11Buffer* alternateBuffer{};
        ID3D11ShaderResourceView* originalResource{};
        ID3D11SamplerState* originalSampler{};
        ID3D11Buffer* originalConstants{};
        ID3D11RasterizerState* originalRaster{};
        UINT originalSampleMask{};
        UINT originalStencilRef{};
        const outrun::vr::dx11::NativeGameEyeRasterState* gameRaster{};
        ID3D11RenderTargetView* callerColor{};
        ID3D11GeometryShader* callerGeometryShader{};
        bool rejectedDetachedDraw[2]{};
        bool rejectedForeignDraw[2]{};
    } gameEyeFixture{{}, {}, preservedDepthView,
                     originalGameBuffer, alternateEyeBuffer,
                     gameSampleView, gameSampler, gameConstants,
                     preservedRaster, preservedMask, preservedStencilRef};
    const outrun::vr::dx11::NativeGameEyeColorSeed fullGameClear{
        {0xff00ffffu, 0xffffff00u}}; // actual per-eye game TARGET Clear colors
    outrun::vr::dx11::NativeGameEyeRasterState gameRaster{};
    // Model different actual source-camera crop regions within the two
    // full-sized GPU eyes; the original desktop raster must be restored.
    gameRaster.viewport[0] = {0.f, 0.f, 32.f, 64.f, 0.f, 1.f};
    gameRaster.viewport[1] = {32.f, 0.f, 32.f, 64.f, 0.f, 1.f};
    gameRaster.scissor[0] = {0, 0, 32, 64};
    gameRaster.scissor[1] = {32, 0, 64, 64};
    gameRaster.depthClear[0] = 0.35f;
    gameRaster.depthClear[1] = 0.65f;
    gameRaster.stencilClear[0] = 3u;
    gameRaster.stencilClear[1] = 5u;
    gameEyeFixture.gameRaster = &gameRaster;
    gameEyeFixture.callerColor = originalGameTarget;
    gameEyeFixture.callerGeometryShader = originalGeometryShader;

    // 00819: the renderer callback itself emits independent eye GPU work
    // and returns per-eye draw/pose/view evidence after command recording.
    const auto gameEyePass = [](
        void* user, ID3D11DeviceContext* ctx,
        ID3D11RenderTargetView* eyeTarget, std::uint32_t eyeIndex,
        outrun::vr::dx11::NativeGameEyeDrawEvidence& evidence,
        outrun::vr::dx11::NativeGameEyeDrawEncoder& encoder) noexcept -> bool {
        if (!ctx || !eyeTarget || eyeIndex >= 2u || !user) return false;
        auto& fixture = *static_cast<GameEyeFixture*>(user);
        ID3D11RenderTargetView* boundTarget = nullptr;
        ID3D11DepthStencilView* boundDepth = nullptr;
        ctx->OMGetRenderTargets(1, &boundTarget, &boundDepth);
        UINT viewportCount = 1, scissorCount = 1;
        D3D11_VIEWPORT viewport{};
        D3D11_RECT scissor{};
        ctx->RSGetViewports(&viewportCount, &viewport);
        ctx->RSGetScissorRects(&scissorCount, &scissor);
        D3D11_DEPTH_STENCIL_VIEW_DESC depthViewDesc{};
        if (boundDepth) boundDepth->GetDesc(&depthViewDesc);
        Microsoft::WRL::ComPtr<ID3D11Resource> depthResource;
        if (boundDepth) boundDepth->GetResource(depthResource.GetAddressOf());
        Microsoft::WRL::ComPtr<ID3D11Texture2D> eyeDepthTexture;
        if (depthResource) depthResource.As(&eyeDepthTexture);
        D3D11_TEXTURE2D_DESC eyeDepthDesc{};
        if (eyeDepthTexture) eyeDepthTexture->GetDesc(&eyeDepthDesc);
        ID3D11Buffer* boundVertexBuffer = nullptr;
        ID3D11Buffer* boundIndexBuffer = nullptr;
        UINT boundStride = 0u, boundOffset = 0u, boundIndexOffset = 0u;
        DXGI_FORMAT boundIndexFormat = DXGI_FORMAT_UNKNOWN;
        D3D11_PRIMITIVE_TOPOLOGY boundTopology{};
        ctx->IAGetVertexBuffers(0u, 1u, &boundVertexBuffer,
                                &boundStride, &boundOffset);
        ctx->IAGetIndexBuffer(&boundIndexBuffer,
                              &boundIndexFormat, &boundIndexOffset);
        ctx->IAGetPrimitiveTopology(&boundTopology);
        ID3D11ShaderResourceView* boundPSResource = nullptr;
        ID3D11SamplerState* boundPSSampler = nullptr;
        ID3D11Buffer* boundPSConstants = nullptr;
        ID3D11RasterizerState* boundRaster = nullptr;
        ID3D11BlendState* boundBlend = nullptr;
        ID3D11DepthStencilState* boundDepthState = nullptr;
        FLOAT boundBlendFactor[4]{};
        UINT boundSampleMask = 0u, boundStencilRef = 0u;
        ctx->PSGetShaderResources(0u, 1u, &boundPSResource);
        ctx->PSGetSamplers(0u, 1u, &boundPSSampler);
        ctx->PSGetConstantBuffers(0u, 1u, &boundPSConstants);
        ID3D11GeometryShader* boundGeometry = nullptr;
        ctx->GSGetShader(&boundGeometry, nullptr, nullptr);
        const bool isolatedEyeGeometry = boundGeometry == nullptr;
        if (boundGeometry) boundGeometry->Release();
        ctx->RSGetState(&boundRaster);
        ctx->OMGetBlendState(&boundBlend, boundBlendFactor, &boundSampleMask);
        ctx->OMGetDepthStencilState(&boundDepthState, &boundStencilRef);
        const bool originalGameShaderInputs =
            isolatedEyeGeometry &&
            boundPSResource == fixture.originalResource &&
            boundPSSampler == fixture.originalSampler &&
            boundPSConstants == fixture.originalConstants &&
            boundRaster == fixture.originalRaster &&
            boundBlend == nullptr && boundDepthState == nullptr &&
            boundSampleMask == fixture.originalSampleMask &&
            boundStencilRef == fixture.originalStencilRef;
        if (boundPSResource) boundPSResource->Release();
        if (boundPSSampler) boundPSSampler->Release();
        if (boundPSConstants) boundPSConstants->Release();
        if (boundRaster) boundRaster->Release();
        if (boundBlend) boundBlend->Release();
        if (boundDepthState) boundDepthState->Release();
        const bool originalGameIA =
            boundVertexBuffer == fixture.originalBuffer &&
            boundIndexBuffer == fixture.originalBuffer &&
            boundStride == 16u && boundOffset == 4u &&
            boundIndexFormat == DXGI_FORMAT_R16_UINT &&
            boundIndexOffset == 2u &&
            boundTopology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST;
        if (boundVertexBuffer) boundVertexBuffer->Release();
        if (boundIndexBuffer) boundIndexBuffer->Release();
        fixture.sawBoundEye[eyeIndex] = originalGameIA &&
            originalGameShaderInputs && boundTarget == eyeTarget && boundDepth != nullptr &&
            depthViewDesc.Format == DXGI_FORMAT_D24_UNORM_S8_UINT &&
            eyeDepthTexture.Get() != nullptr && eyeDepthDesc.Width == 64 &&
            eyeDepthDesc.Height == 64 &&
            (eyeDepthDesc.BindFlags & D3D11_BIND_DEPTH_STENCIL) != 0 &&
            boundDepth != fixture.eyeDepth[eyeIndex == 0u ? 1u : 0u] &&
            boundDepth != fixture.callerDepth &&
            fixture.gameRaster &&
            viewportCount == 1 &&
            viewport.TopLeftX == fixture.gameRaster->viewport[eyeIndex].TopLeftX &&
            viewport.TopLeftY == fixture.gameRaster->viewport[eyeIndex].TopLeftY &&
            viewport.Width == fixture.gameRaster->viewport[eyeIndex].Width &&
            viewport.Height == fixture.gameRaster->viewport[eyeIndex].Height &&
            scissorCount == 1 &&
            scissor.left == fixture.gameRaster->scissor[eyeIndex].left &&
            scissor.top == fixture.gameRaster->scissor[eyeIndex].top &&
            scissor.right == fixture.gameRaster->scissor[eyeIndex].right &&
            scissor.bottom == fixture.gameRaster->scissor[eyeIndex].bottom;
        if (fixture.sawBoundEye[eyeIndex]) {
            // The callback sees the live per-eye depth attachment and may
            // write its own D3D9-derived Z/stencil commands into THIS eye.
            fixture.eyeDepth[eyeIndex] = boundDepth;
            fixture.eyeDepth[eyeIndex]->AddRef();
            ctx->ClearDepthStencilView(boundDepth,
                D3D11_CLEAR_DEPTH | D3D11_CLEAR_STENCIL,
                eyeIndex == 0u ? 0.25f : 0.75f,
                static_cast<UINT8>(eyeIndex + 1u));
        }
        if (boundTarget) boundTarget->Release();
        if (boundDepth) boundDepth->Release();
        if (!fixture.sawBoundEye[eyeIndex]) return false;
        // The verified game full-TARGET Clear already wrote this eye's color.
        // Change the scene's OM/RS state as a live Draw would: the producer
        // must restore caller raster/depth/blend state after both eye passes.
        ctx->RSSetState(nullptr);
        ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);
        ctx->OMSetDepthStencilState(nullptr, 0u);
        ID3D11ShaderResourceView* nullResource = nullptr;
        ID3D11SamplerState* nullSampler = nullptr;
        ID3D11Buffer* nullConstants = nullptr;
        ctx->PSSetShaderResources(0u, 1u, &nullResource);
        ctx->PSSetSamplers(0u, 1u, &nullSampler);
        ctx->PSSetConstantBuffers(0u, 1u, &nullConstants);
        // Deliberate shader-stage mutation: the right eye must begin clean.
        ctx->GSSetShader(fixture.callerGeometryShader, nullptr, 0u);
        // Simulate a real per-eye Draw that rebinds the vertex/index path;
        // the next eye and original desktop must receive their own baseline.
        constexpr UINT eyeStride = 24u, eyeOffset = 8u;
        ctx->IASetVertexBuffers(
            0u, 1u, &fixture.alternateBuffer, &eyeStride, &eyeOffset);
        ctx->IASetIndexBuffer(
            fixture.alternateBuffer, DXGI_FORMAT_R32_UINT, 0u);
        ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
        // Game command replay may detach or change OM between eye passes.
        // The submission must rebind RT0 for the next eye and restore it
        // to the original desktop state after the second pass.
        ctx->OMSetRenderTargets(0, nullptr, nullptr);
        // Regression: an API Draw with no OM color/depth target does not
        // write an XR eye and must not count toward a completed stereo pair.
        fixture.rejectedDetachedDraw[eyeIndex] =
            !encoder.draw(3u, 0u) && encoder.draw_count() == 0u;
        ctx->OMSetRenderTargets(
            1u, &fixture.callerColor, fixture.callerDepth);
        // A game offscreen/desktop Draw is equally ineligible. Rebind the
        // ring-owned eye RTV+DSV explicitly before real geometry replay.
        fixture.rejectedForeignDraw[eyeIndex] =
            !encoder.draw_indexed(3u, 0u, 0) && encoder.draw_count() == 0u;
        if (!fixture.rejectedDetachedDraw[eyeIndex] ||
            !fixture.rejectedForeignDraw[eyeIndex] ||
            !encoder.bind_eye_output())
            return false;
        // Use the actual immediate D3D11 draw APIs through the per-eye
        // recorder with both correct eye OM bindings restored. The saved
        // game IA/VS/PS state is restored independently for both eye passes.
        // This WARP fixture does not assert real-game shader/pixel parity.
        for (UINT drawOrdinal = 0u; drawOrdinal < 2u + eyeIndex; ++drawOrdinal) {
            const bool issued = (drawOrdinal & 1u)
                ? encoder.draw_indexed(3u, 0u, 0)
                : encoder.draw(3u, 0u);
            if (!issued) return false;
        }
        evidence.drawCount = encoder.draw_count();
        evidence.viewSignature = eyeIndex == 0u ? 0x303u : 0x404u;
        evidence.sourcePoseSequence = 33u;
        return true;
    };
    auto invalidRaster = gameRaster;
    invalidRaster.scissor[1].right = 65; // Fail before any GPU commands.
    require(directSubmit.begin(d3d.context, 24, 33) &&
            !directSubmit.render_game_eye_passes(nullptr, &gameEyeFixture, 33) &&
            !directSubmit.render_game_eye_passes(gameEyePass, &gameEyeFixture, 32) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &invalidRaster) &&
            !ring.synchronization_faulted() &&
            directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster) &&
            directSubmit.in_flight() && !directSubmit.cancel() &&
            gameEyeFixture.sawBoundEye[0] && gameEyeFixture.sawBoundEye[1] &&
            gameEyeFixture.rejectedDetachedDraw[0] &&
            gameEyeFixture.rejectedDetachedDraw[1] &&
            gameEyeFixture.rejectedForeignDraw[0] &&
            gameEyeFixture.rejectedForeignDraw[1],
            "00826 only bound native eye Draw/DrawIndexed count; detached and foreign OM cannot publish XR");
    require(gameEyeFixture.eyeDepth[0] && gameEyeFixture.eyeDepth[1] &&
            gameEyeFixture.eyeDepth[0] != gameEyeFixture.eyeDepth[1] &&
            gameEyeFixture.eyeDepth[0] != preservedDepthView &&
            gameEyeFixture.eyeDepth[1] != preservedDepthView,
            "00821 eye GPU commands own distinct Z/stencil attachments");
    ID3D11RenderTargetView* restoredGameTarget = nullptr;
    ID3D11DepthStencilView* restoredGameDepth = nullptr;
    d3d.context->OMGetRenderTargets(1, &restoredGameTarget, &restoredGameDepth);
    UINT restoredViewportCount = 1, restoredScissorCount = 1;
    D3D11_VIEWPORT restoredViewport{};
    D3D11_RECT restoredScissor{};
    d3d.context->RSGetViewports(&restoredViewportCount, &restoredViewport);
    d3d.context->RSGetScissorRects(&restoredScissorCount, &restoredScissor);
    ID3D11RasterizerState* restoredRaster = nullptr;
    ID3D11BlendState* restoredBlend = nullptr;
    ID3D11DepthStencilState* restoredDepthState = nullptr;
    FLOAT restoredBlendFactor[4]{};
    UINT restoredMask = 0u, restoredStencilRef = 0u;
    d3d.context->RSGetState(&restoredRaster);
    d3d.context->OMGetBlendState(&restoredBlend, restoredBlendFactor, &restoredMask);
    d3d.context->OMGetDepthStencilState(&restoredDepthState, &restoredStencilRef);
    ID3D11Buffer* restoredVertexBuffer = nullptr;
    ID3D11Buffer* restoredIndexBuffer = nullptr;
    UINT restoredStride = 0u, restoredOffset = 0u, restoredIndexOffset = 0u;
    DXGI_FORMAT restoredIndexFormat = DXGI_FORMAT_UNKNOWN;
    D3D11_PRIMITIVE_TOPOLOGY restoredTopology{};
    d3d.context->IAGetVertexBuffers(0u, 1u, &restoredVertexBuffer,
                                     &restoredStride, &restoredOffset);
    d3d.context->IAGetIndexBuffer(&restoredIndexBuffer,
                                   &restoredIndexFormat, &restoredIndexOffset);
    d3d.context->IAGetPrimitiveTopology(&restoredTopology);
    ID3D11ShaderResourceView* restoredResource = nullptr;
    ID3D11SamplerState* restoredSampler = nullptr;
    ID3D11Buffer* restoredConstants = nullptr;
    d3d.context->PSGetShaderResources(0u, 1u, &restoredResource);
    d3d.context->PSGetSamplers(0u, 1u, &restoredSampler);
    d3d.context->PSGetConstantBuffers(0u, 1u, &restoredConstants);
    ID3D11GeometryShader* restoredGeometry = nullptr;
    d3d.context->GSGetShader(&restoredGeometry, nullptr, nullptr);
    const bool restoredGameState =
        restoredGeometry == originalGeometryShader &&
        restoredResource == gameSampleView &&
        restoredSampler == gameSampler &&
        restoredConstants == gameConstants &&
        restoredVertexBuffer == originalGameBuffer &&
        restoredIndexBuffer == originalGameBuffer &&
        restoredStride == originalStride && restoredOffset == originalOffset &&
        restoredIndexFormat == DXGI_FORMAT_R16_UINT &&
        restoredIndexOffset == 2u &&
        restoredTopology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        restoredRaster == preservedRaster &&
        restoredBlend == nullptr && restoredDepthState == nullptr &&
        restoredMask == preservedMask &&
        restoredStencilRef == preservedStencilRef &&
        restoredBlendFactor[0] == preservedBlendFactor[0] &&
        restoredBlendFactor[1] == preservedBlendFactor[1] &&
        restoredBlendFactor[2] == preservedBlendFactor[2] &&
        restoredBlendFactor[3] == preservedBlendFactor[3] &&
        restoredGameTarget == originalGameTarget &&
        restoredGameDepth == preservedDepthView &&
        restoredViewportCount == 1 &&
        restoredViewport.TopLeftX == preservedViewport.TopLeftX &&
        restoredViewport.TopLeftY == preservedViewport.TopLeftY &&
        restoredViewport.Width == preservedViewport.Width &&
        restoredViewport.Height == preservedViewport.Height &&
        restoredScissorCount == 1 &&
        restoredScissor.left == preservedScissor.left &&
        restoredScissor.top == preservedScissor.top &&
        restoredScissor.right == preservedScissor.right &&
        restoredScissor.bottom == preservedScissor.bottom;
    if (restoredResource) restoredResource->Release();
    if (restoredSampler) restoredSampler->Release();
    if (restoredConstants) restoredConstants->Release();
    if (restoredGeometry) restoredGeometry->Release();
    if (restoredVertexBuffer) restoredVertexBuffer->Release();
    if (restoredIndexBuffer) restoredIndexBuffer->Release();
    if (restoredGameTarget) restoredGameTarget->Release();
    if (restoredGameDepth) restoredGameDepth->Release();
    if (restoredRaster) restoredRaster->Release();
    if (restoredBlend) restoredBlend->Release();
    if (restoredDepthState) restoredDepthState->Release();
    require(restoredGameState,
            "00821 stereo game draw restores caller color, depth and raster");
    d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
    d3d.context->RSSetState(nullptr);
    ID3D11Buffer* nullVertexBuffer = nullptr;
    constexpr UINT resetStride = 0u, resetOffset = 0u;
    d3d.context->IASetVertexBuffers(
        0u, 1u, &nullVertexBuffer, &resetStride, &resetOffset);
    d3d.context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0u);
    ID3D11ShaderResourceView* nullGameResource = nullptr;
    ID3D11SamplerState* nullGameSampler = nullptr;
    ID3D11Buffer* nullGameConstants = nullptr;
    d3d.context->PSSetShaderResources(0u, 1u, &nullGameResource);
    d3d.context->PSSetSamplers(0u, 1u, &nullGameSampler);
    d3d.context->PSSetConstantBuffers(0u, 1u, &nullGameConstants);
    d3d.context->GSSetShader(nullptr, nullptr, 0u);
    originalGeometryShader->Release();
    gameSampleView->Release();
    gameSampleTexture->Release();
    gameSampler->Release();
    gameConstants->Release();
    originalGameBuffer->Release();
    alternateEyeBuffer->Release();
    preservedRaster->Release();
    for (auto*& depth : gameEyeFixture.eyeDepth) {
        if (depth) { depth->Release(); depth = nullptr; }
    }
    preservedDepthView->Release();
    preservedDepthTexture->Release();
    outrun::vr::dx11::NativeGameStereoPublishedFrame gameEyeFrame{};
    bool gameEyeReady = false;
    for (int retry = 0; retry < 2000 && !gameEyeReady; ++retry) {
        gameEyeReady = directSubmit.try_publish(gameEyeFrame);
        require(!ring.synchronization_faulted(),
                "00819 per-eye native renderer producer EVENT valid");
        if (!gameEyeReady) Sleep(1);
    }
    require(gameEyeReady &&
            gameEyeFrame.sourcePoseSequence == 33u &&
            gameEyeFrame.eyeViewSignature[0] == 0x303u &&
            gameEyeFrame.eyeViewSignature[1] == 0x404u &&
            ring.validate_publication_snapshot(gameEyeFrame.gpu),
            "00819 per-eye post-render camera identity persists through fence");
    for (std::uint32_t eyeIndex = 0; eyeIndex < 2u; ++eyeIndex) {
        d3d.context->CopyResource(readback,
            ring.eye(gameEyeFrame.gpu.slot, eyeIndex));
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(d3d.context->Map(
                    readback, 0, D3D11_MAP_READ, 0, &mapped)),
                "00819 distinct native game eye readback");
        const auto* pixel = static_cast<const std::uint8_t*>(mapped.pData);
        const bool distinctColor = eyeIndex == 0u
            ? pixel[0] == 0 && pixel[1] == 255 && pixel[2] == 255
            : pixel[0] == 255 && pixel[1] == 255 && pixel[2] == 0;
        d3d.context->Unmap(readback, 0);
        require(distinctColor, "00819 each eye callback wrote its own GPU RTV");
    }
    hostFrame.frameId = 24u;
    hostFrame.sourcePoseSequence = 33u;
    hostFrame.flags &= ~OutRunVR::RenderFrameDirectGpuTransport;
    require(directSubmit.attach_host_frame(gameEyeFrame, hostFrame) &&
            (hostFrame.flags & OutRunVR::RenderFrameDirectGpuTransport) &&
            hostFrame.reserved[OutRunVR::RenderFrameDirectSlotIndex] ==
                gameEyeFrame.gpu.slot &&
            ring.retire_acknowledged(
                make_ack(ring.identity(), gameEyeFrame.gpu.slot, 24u)) &&
            !directSubmit.attach_host_frame(gameEyeFrame, hostFrame),
            "00819 distinct native game eyes obey exact host ACK");

    // A recorder may fail AFTER one eye's GPU writes were queued. Neither a
    // cancellation nor another frame may reuse the ring without hard retire.
    const auto partialDraw = [](
        void*, ID3D11DeviceContext* context,
        ID3D11RenderTargetView* left, ID3D11RenderTargetView*) noexcept -> bool
    {
        const float partial[4] = {1.f, 0.f, 0.f, 1.f};
        context->ClearRenderTargetView(left, partial);
        return false;
    };
    std::uint32_t partialSlot = 99;
    require(ring.try_acquire_slot(d3d.context, 25, nullptr, partialSlot) &&
            !ring.render_eye_pair(d3d.context, partialSlot, 25, partialDraw, nullptr) &&
            ring.synchronization_faulted() &&
            !ring.cancel_acquired_slot(partialSlot, 25) &&
            !ring.activation_ready(),
            "00812 partial native eye draw quarantines transport until Reset");

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
