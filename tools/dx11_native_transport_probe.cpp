#include <Windows.h>

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <type_traits>
#include <vector>

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
    std::cerr << "R178-DIAG main started\n";
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

    // Game compute passes may finish a stereo camera directly into a UAV-only
    // texture array. Carry both physical slices to distinct shared OpenXR
    // eyes without CPU staging, preserve the original compute UAV bindings,
    // and reject a doubled-up mono slice before touching the ring.
    D3D11_TEXTURE2D_DESC uavOnlyDesc = sourceDesc;
    uavOnlyDesc.ArraySize = 2u;
    uavOnlyDesc.BindFlags = D3D11_BIND_UNORDERED_ACCESS;
    ID3D11Texture2D* uavOnlyCamera = nullptr;
    ID3D11UnorderedAccessView* uavOnlyEyes[2]{};
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &uavOnlyDesc, nullptr, &uavOnlyCamera)) && uavOnlyCamera,
            "00863 game compute-only stereo texture array allocated");
    for (UINT eye = 0u; eye < 2u; ++eye) {
        D3D11_UNORDERED_ACCESS_VIEW_DESC view{};
        view.Format = uavOnlyDesc.Format;
        view.ViewDimension = D3D11_UAV_DIMENSION_TEXTURE2DARRAY;
        view.Texture2DArray.ArraySize = 1u;
        view.Texture2DArray.FirstArraySlice = eye;
        require(SUCCEEDED(d3d.device->CreateUnorderedAccessView(
                    uavOnlyCamera, &view, &uavOnlyEyes[eye])) &&
                uavOnlyEyes[eye],
                "00863 distinct compute camera eye UAV created");
        const float color[4] = {eye == 0u ? 1.f : 0.f, 0.f,
                                eye == 1u ? 1.f : 0.f, 1.f};
        d3d.context->ClearUnorderedAccessViewFloat(uavOnlyEyes[eye], color);
    }
    d3d.context->CSSetUnorderedAccessViews(0u, 2u, uavOnlyEyes, nullptr);
    std::uint32_t uavOnlySlot = 99u;
    require(ring.try_acquire_slot(d3d.context, 18u, nullptr, uavOnlySlot) &&
            !ring.submit_eye_pair(d3d.context, uavOnlySlot, 18u,
                                  uavOnlyCamera, uavOnlyCamera, 0u, 0u) &&
            ring.slot_state(uavOnlySlot) == SharedEyeSlotState::Acquired,
            "00863 identical camera slice cannot masquerade as stereo");
    require(ring.submit_eye_pair(d3d.context, uavOnlySlot, 18u,
                                 uavOnlyCamera, uavOnlyCamera, 0u, 1u) &&
            ring.slot_state(uavOnlySlot) == SharedEyeSlotState::ProducerPending,
            "00863 independent compute UAV camera slices enter native ring");
    ID3D11UnorderedAccessView* restoredUavOnly[2]{};
    d3d.context->CSGetUnorderedAccessViews(0u, 2u, restoredUavOnly);
    const bool restoredBothUavs =
        restoredUavOnly[0] == uavOnlyEyes[0] &&
        restoredUavOnly[1] == uavOnlyEyes[1];
    for (auto* view : restoredUavOnly) if (view) view->Release();
    require(restoredBothUavs,
            "00863 both original game compute outputs remain bound");
    ID3D11UnorderedAccessView* detachedUavOnly[2]{};
    d3d.context->CSSetUnorderedAccessViews(0u, 2u, detachedUavOnly, nullptr);
    publish_bounded(ring, d3d.context, uavOnlySlot, 18u);
    D3D11_TEXTURE2D_DESC uavReadbackDesc = sourceDesc;
    uavReadbackDesc.Usage = D3D11_USAGE_STAGING;
    uavReadbackDesc.BindFlags = 0u;
    uavReadbackDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D* uavReadback = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &uavReadbackDesc, nullptr, &uavReadback)) && uavReadback,
            "00863 test-only shared eye pixel readback allocated");
    for (UINT eye = 0u; eye < 2u; ++eye) {
        d3d.context->CopyResource(uavReadback, ring.eye(uavOnlySlot, eye));
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(d3d.context->Map(
                    uavReadback, 0u, D3D11_MAP_READ, 0u, &mapped)),
                "00863 independent UAV eye GPU pixels read");
        const auto* pixel = static_cast<const std::uint8_t*>(mapped.pData);
        const bool correct = eye == 0u
            ? pixel[0] == 255u && pixel[1] == 0u &&
              pixel[2] == 0u && pixel[3] == 255u
            : pixel[0] == 0u && pixel[1] == 0u &&
              pixel[2] == 255u && pixel[3] == 255u;
        d3d.context->Unmap(uavReadback, 0u);
        require(correct, "00863 computed L/R eye pixel identity");
    }
    require(ring.retire_acknowledged(
                make_ack(ring.identity(), uavOnlySlot, 18u)),
            "00863 exact OpenXR consumer ACK retires UAV-only eye pair");
    uavReadback->Release();
    for (auto* view : uavOnlyEyes) view->Release();
    uavOnlyCamera->Release();

    // A real menu/vehicle compute postpass can leave its camera color
    // bound as a CS UAV. Copying directly from that live output races the
    // producer. The native eye ring must detach the UAV, copy BOTH GPU eyes,
    // restore the exact caller binding and publish only after its EVENT.
    D3D11_TEXTURE2D_DESC computeSourceDesc = sourceDesc;
    computeSourceDesc.BindFlags =
        D3D11_BIND_RENDER_TARGET | D3D11_BIND_UNORDERED_ACCESS;
    ID3D11Texture2D* computeCamera = nullptr;
    ID3D11RenderTargetView* computeCameraRtv = nullptr;
    ID3D11UnorderedAccessView* computeCameraUav = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &computeSourceDesc, nullptr, &computeCamera)) &&
            SUCCEEDED(d3d.device->CreateRenderTargetView(
                computeCamera, nullptr, &computeCameraRtv)) &&
            SUCCEEDED(d3d.device->CreateUnorderedAccessView(
                computeCamera, nullptr, &computeCameraUav)),
            "00861 real camera postpass UAV/RTV source created");
    const float computeYellow[4] = {1.f, 1.f, 0.f, 1.f};
    const float computeCyan[4] = {0.f, 1.f, 1.f, 1.f};
    d3d.context->ClearRenderTargetView(computeCameraRtv, computeYellow);
    d3d.context->ClearRenderTargetView(rightView, computeCyan);
    d3d.context->CSSetUnorderedAccessViews(0u, 1u, &computeCameraUav, nullptr);
    std::uint32_t computeSlot = 99u;
    require(ring.try_acquire_slot(d3d.context, 19u, nullptr, computeSlot) &&
            ring.submit_eye_pair(d3d.context, computeSlot, 19u,
                                 computeCamera, rightSource) &&
            ring.slot_state(computeSlot) == SharedEyeSlotState::ProducerPending,
            "00861 CS UAV-bound camera enters native L/R GPU eye copy");
    ID3D11UnorderedAccessView* restoredComputeUav = nullptr;
    d3d.context->CSGetUnorderedAccessViews(0u, 1u, &restoredComputeUav);
    const bool computeRestored = restoredComputeUav == computeCameraUav;
    if (restoredComputeUav) restoredComputeUav->Release();
    require(computeRestored, "00861 original game CS UAV output restored");
    ID3D11UnorderedAccessView* nullComputeUav = nullptr;
    d3d.context->CSSetUnorderedAccessViews(0u, 1u, &nullComputeUav, nullptr);
    publish_bounded(ring, d3d.context, computeSlot, 19u);
    D3D11_TEXTURE2D_DESC computeReadbackDesc = sourceDesc;
    computeReadbackDesc.Usage = D3D11_USAGE_STAGING;
    computeReadbackDesc.BindFlags = 0u;
    computeReadbackDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D* computeReadback = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &computeReadbackDesc, nullptr, &computeReadback)),
            "00861 GPU L/R eye copy staging for WARP evidence");
    for (std::uint32_t eye = 0u; eye < 2u; ++eye) {
        d3d.context->CopyResource(computeReadback, ring.eye(computeSlot, eye));
        D3D11_MAPPED_SUBRESOURCE pixels{};
        require(SUCCEEDED(d3d.context->Map(
                    computeReadback, 0u, D3D11_MAP_READ, 0u, &pixels)),
                "00861 WARP eye copy mapped");
        const auto* color = static_cast<const std::uint8_t*>(pixels.pData);
        const bool expected = eye == 0u
            ? color[0] == 255u && color[1] == 255u &&
              color[2] == 0u && color[3] == 255u
            : color[0] == 0u && color[1] == 255u &&
              color[2] == 255u && color[3] == 255u;
        d3d.context->Unmap(computeReadback, 0u);
        require(expected, "00861 source UAV hazard-free L/R game pixels");
    }
    require(ring.retire_acknowledged(
                make_ack(ring.identity(), computeSlot, 19u)),
            "00861 exact GPU eye ACK retires compute-camera pair");
    computeReadback->Release();
    computeCameraUav->Release();
    computeCameraRtv->Release();
    computeCamera->Release();

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
    // Real game postpasses commonly leave both camera MRTs bound when
    // submitting the GPU-only stereo copy. Prove the producer unbinds them
    // for the transfer and restores the complete output set afterward.
    ID3D11RenderTargetView* boundGameMrt[2] = {leftView, rightView};
    d3d.context->OMSetRenderTargets(2u, boundGameMrt, nullptr);
    require(ring.submit_eye_pair(
                d3d.context, stereoSlot, 20, leftSource, rightSource) &&
            ring.slot_state(stereoSlot) == SharedEyeSlotState::ProducerPending,
            "00858 game MRT0/RT1 bound source stereo GPU copy and EVENT armed");
    ID3D11RenderTargetView* restoredGameMrt[2]{};
    // Keep this snapshot local to the 00858 MRT-bound producer case:
    // the full eye-renderer state regression below has its own DSV snapshot.
    ID3D11DepthStencilView* restoredSourceMrtDepth = nullptr;
    d3d.context->OMGetRenderTargets(
        2u, restoredGameMrt, &restoredSourceMrtDepth);
    const bool preservedMrt =
        restoredGameMrt[0] == leftView &&
        restoredGameMrt[1] == rightView &&
        restoredSourceMrtDepth == nullptr;
    if (restoredGameMrt[0]) restoredGameMrt[0]->Release();
    if (restoredGameMrt[1]) restoredGameMrt[1]->Release();
    if (restoredSourceMrtDepth) restoredSourceMrtDepth->Release();
    d3d.context->OMSetRenderTargets(0u, nullptr, nullptr);
    require(preservedMrt,
            "00858 stereo submission restores live game camera MRT bindings");
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
    // Keep compiler loaded until ID3DBlob is consumed and released below.
    require(SUCCEEDED(geometryCompileResult) && geometryBytecode,
            "00827 caller geometry stage compiled");
    ID3D11GeometryShader* originalGeometryShader = nullptr;
    require(SUCCEEDED(d3d.device->CreateGeometryShader(
                geometryBytecode->GetBufferPointer(),
                geometryBytecode->GetBufferSize(), nullptr,
                &originalGeometryShader)) && originalGeometryShader,
            "00827 caller geometry stage created");
    // ID3DBlob's COM vtable lives in d3dcompiler_47.dll. Unloading the
    // module before using and releasing the blob crashes the Win32 WARP
    // process (0xC0000005); keep it loaded through the final Release.
    geometryBytecode->Release();
    // Draw/DrawIndexed color evidence needs real bound vertex and pixel
    // shaders. An absent PS must still execute depth-only work, but may not
    // certify the native XR frame. Keep D3DCompiler loaded through each blob.
    constexpr char gameVertexSource[] =
        "float4 main(uint id : SV_VertexID) : SV_Position {"
        " float2 p = id == 0 ? float2(-0.99,-0.99) :"
        " (id == 1 ? float2(-0.98,-0.99) : float2(-0.99,-0.98));"
        " return float4(p,0,1); }";
    constexpr char gamePixelSource[] =
        "float4 main() : SV_Target { return float4(1,1,1,1); }";
    ID3DBlob* vertexBytecode = nullptr;
    ID3DBlob* pixelBytecode = nullptr;
    require(SUCCEEDED(compileShader(
                gameVertexSource, sizeof(gameVertexSource) - 1u,
                "native_eye_game", nullptr, nullptr, "main", "vs_4_0",
                D3DCOMPILE_ENABLE_STRICTNESS, 0u,
                &vertexBytecode, nullptr)) && vertexBytecode,
            "00830 native color vertex shader compiles");
    require(SUCCEEDED(compileShader(
                gamePixelSource, sizeof(gamePixelSource) - 1u,
                "native_eye_game", nullptr, nullptr, "main", "ps_4_0",
                D3DCOMPILE_ENABLE_STRICTNESS, 0u,
                &pixelBytecode, nullptr)) && pixelBytecode,
            "00830 native color pixel shader compiles");
    ID3D11VertexShader* gameVertexShader = nullptr;
    ID3D11PixelShader* gamePixelShader = nullptr;
    require(SUCCEEDED(d3d.device->CreateVertexShader(
                vertexBytecode->GetBufferPointer(),
                vertexBytecode->GetBufferSize(), nullptr, &gameVertexShader)) &&
            gameVertexShader &&
            SUCCEEDED(d3d.device->CreatePixelShader(
                pixelBytecode->GetBufferPointer(),
                pixelBytecode->GetBufferSize(), nullptr, &gamePixelShader)) &&
            gamePixelShader,
            "00830 native game VS and PS created");
    vertexBytecode->Release();
    pixelBytecode->Release();
    FreeLibrary(compilerModule);
    d3d.context->VSSetShader(gameVertexShader, nullptr, 0u);
    d3d.context->PSSetShader(gamePixelShader, nullptr, 0u);
    d3d.context->GSSetShader(originalGeometryShader, nullptr, 0u);
    // GPU-backed, game-owned intermediate color surface. Verify actual
    // per-eye post-Draw copy pixels rather than a simulated CPU image.
    D3D11_TEXTURE2D_DESC gameSurfaceDesc{};
    gameSurfaceDesc.Width = gameSurfaceDesc.Height = 64u;
    gameSurfaceDesc.MipLevels = gameSurfaceDesc.ArraySize = 1u;
    gameSurfaceDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    gameSurfaceDesc.SampleDesc.Count = 1u;
    gameSurfaceDesc.Usage = D3D11_USAGE_DEFAULT;
    gameSurfaceDesc.BindFlags = D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* gameSurface = nullptr;
    ID3D11RenderTargetView* gameSurfaceView = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &gameSurfaceDesc, nullptr, &gameSurface)) && gameSurface &&
            SUCCEEDED(d3d.device->CreateRenderTargetView(
                gameSurface, nullptr, &gameSurfaceView)) && gameSurfaceView,
            "00833 game-owned native GPU source surface created");
    constexpr float intermediateBlue[4]{0.f, 0.f, 1.f, 1.f};
    d3d.context->ClearRenderTargetView(gameSurfaceView, intermediateBlue);
    // The native game post-pass may transfer its RT into a GPU-only SRV
    // intermediate before replaying an unscaled copy into each real eye.
    // This is not a CPU staging/readback or a manufactured stereo Draw.
    D3D11_TEXTURE2D_DESC shaderIntermediateDesc = gameSurfaceDesc;
    shaderIntermediateDesc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    ID3D11Texture2D* gameShaderIntermediate = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &shaderIntermediateDesc, nullptr, &gameShaderIntermediate)) &&
            gameShaderIntermediate,
            "00834 native game shader-readable GPU intermediate created");
    d3d.context->CopyResource(gameShaderIntermediate, gameSurface);
    // Menu and vehicle render passes can retain smaller atlas mips while
    // their actual game-authored full-resolution color lives in mip 0.
    D3D11_TEXTURE2D_DESC mipGameDesc = shaderIntermediateDesc;
    mipGameDesc.MipLevels = 3u;
    ID3D11Texture2D* mipGameIntermediate = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &mipGameDesc, nullptr, &mipGameIntermediate)) &&
            mipGameIntermediate,
            "00841 game-owned mipmapped GPU postpass source created");
    std::vector<UINT> greenMip(32u * 32u, 0xff00ff00u);
    d3d.context->UpdateSubresource(
        mipGameIntermediate, 1u, nullptr, greenMip.data(),
        32u * sizeof(UINT), 0u);
    d3d.context->CopySubresourceRegion(
        mipGameIntermediate, 0u, 0u, 0u, 0u, gameSurface, 0u, nullptr);
    // Native left and right game postpasses can occupy independent slices
    // in one GPU array allocation. Each side must keep its own source data.
    D3D11_TEXTURE2D_DESC eyeArrayDesc = shaderIntermediateDesc;
    eyeArrayDesc.ArraySize = 2u;
    eyeArrayDesc.MipLevels = 2u;
    ID3D11Texture2D* gameEyeArray = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &eyeArrayDesc, nullptr, &gameEyeArray)) && gameEyeArray,
            "00841 native left/right GPU game array allocated");
    std::vector<UINT> leftEyePixels(64u * 64u, 0xffcc0011u);
    std::vector<UINT> rightEyePixels(64u * 64u, 0xff22bb33u);
    d3d.context->UpdateSubresource(
        gameEyeArray, D3D11CalcSubresource(0u, 0u, 2u), nullptr,
        leftEyePixels.data(), 64u * sizeof(UINT), 0u);
    d3d.context->UpdateSubresource(
        gameEyeArray, D3D11CalcSubresource(0u, 1u, 2u), nullptr,
        rightEyePixels.data(), 64u * sizeof(UINT), 0u);
    // CopyResource also produces GPU-only DEFAULT intermediates that have
    // neither RTV nor SRV bindings. They are still valid for unscaled native
    // CopySubresourceRegion, including independently authored stereo slices.
    D3D11_TEXTURE2D_DESC copyOnlyDesc = gameSurfaceDesc;
    copyOnlyDesc.ArraySize = 2u;
    copyOnlyDesc.BindFlags = 0u;
    ID3D11Texture2D* gameCopyOnlyArray = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &copyOnlyDesc, nullptr, &gameCopyOnlyArray)) &&
            gameCopyOnlyArray,
            "00853 game CopyResource-only stereo GPU intermediate allocated");
    for (UINT eye = 0u; eye < 2u; ++eye) {
        d3d.context->CopySubresourceRegion(
            gameCopyOnlyArray, eye, 0u, 0u, 0u, gameEyeArray,
            D3D11CalcSubresource(0u, eye, eyeArrayDesc.MipLevels), nullptr);
    }
    // GPU compute-produced camera outputs: two independent UAV-only array
    // slices, never staging/CPU readback or a duplicated mono texture.
    D3D11_TEXTURE2D_DESC computeDesc = gameSurfaceDesc;
    computeDesc.ArraySize = 2u;
    computeDesc.BindFlags = D3D11_BIND_UNORDERED_ACCESS;
    ID3D11Texture2D* gameComputeArray = nullptr;
    ID3D11UnorderedAccessView* gameComputeViews[2]{};
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &computeDesc, nullptr, &gameComputeArray)) && gameComputeArray,
            "00862 compute camera color texture created");
    for (UINT eye = 0u; eye < 2u; ++eye) {
        D3D11_UNORDERED_ACCESS_VIEW_DESC uavDesc{};
        uavDesc.Format = computeDesc.Format;
        uavDesc.ViewDimension = D3D11_UAV_DIMENSION_TEXTURE2DARRAY;
        uavDesc.Texture2DArray.ArraySize = 1u;
        uavDesc.Texture2DArray.FirstArraySlice = eye;
        require(SUCCEEDED(d3d.device->CreateUnorderedAccessView(
                    gameComputeArray, &uavDesc, &gameComputeViews[eye])) &&
                gameComputeViews[eye],
                "00862 game GPU camera per-eye UAV created");
        const float rgba[4]{eye == 0u ? 1.f : 0.f, 0.f,
                            eye == 0u ? 0.f : 1.f, 1.f};
        d3d.context->ClearUnorderedAccessViewFloat(gameComputeViews[eye], rgba);
    }
    // True game menu and vehicle postpasses can use BGRA camera arrays even
    // when the native OpenXR eye target uses RGBA. Preserve each camera's
    // pixels through a GPU point-sampled color conversion (no CPU readback).
    D3D11_TEXTURE2D_DESC convertedDesc = gameSurfaceDesc;
    convertedDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    convertedDesc.ArraySize = 2u;
    convertedDesc.BindFlags =
        D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
    ID3D11Texture2D* gameConvertedArray = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &convertedDesc, nullptr, &gameConvertedArray)) &&
            gameConvertedArray,
            "00844 GPU camera-array BGRA source allocated");
    std::vector<UINT> convertedLeft(64u * 64u, 0xffff0000u);
    std::vector<UINT> convertedRight(64u * 64u, 0xff00ff00u);
    d3d.context->UpdateSubresource(
        gameConvertedArray, 0u, nullptr, convertedLeft.data(),
        64u * sizeof(UINT), 0u);
    d3d.context->UpdateSubresource(
        gameConvertedArray, 1u, nullptr, convertedRight.data(),
        64u * sizeof(UINT), 0u);
    // A game scene may render to MSAA before a full-frame or cropped menu
    // postpass. The native eye path must GPU-resolve the *actual* RT instead
    // of dropping the pixels or staging the entire eye through system memory.
    D3D11_TEXTURE2D_DESC multisampleDesc = gameSurfaceDesc;
    UINT msaaQualityLevels = 0u;
    multisampleDesc.SampleDesc.Count = 4u;
    HRESULT qualityHr = d3d.device->CheckMultisampleQualityLevels(
        multisampleDesc.Format, multisampleDesc.SampleDesc.Count,
        &msaaQualityLevels);
    if (FAILED(qualityHr) || msaaQualityLevels == 0u) {
        multisampleDesc.SampleDesc.Count = 2u;
        qualityHr = d3d.device->CheckMultisampleQualityLevels(
            multisampleDesc.Format, multisampleDesc.SampleDesc.Count,
            &msaaQualityLevels);
    }
    require(SUCCEEDED(qualityHr) && msaaQualityLevels > 0u,
            "00835 WARP game MSAA color RT supported");
    ID3D11Texture2D* gameMultisample = nullptr;
    ID3D11RenderTargetView* gameMultisampleView = nullptr;
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &multisampleDesc, nullptr, &gameMultisample)) &&
            gameMultisample && SUCCEEDED(d3d.device->CreateRenderTargetView(
                gameMultisample, nullptr, &gameMultisampleView)) &&
            gameMultisampleView,
            "00835 game-owned multisample color surface created");
    constexpr float multisampleMagenta[4]{1.f, 0.f, 1.f, 1.f};
    d3d.context->ClearRenderTargetView(
        gameMultisampleView, multisampleMagenta);
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
        ID3D11PixelShader* gamePixelShader{};
        bool rejectedDetachedDraw[2]{};
        bool rejectedForeignDraw[2]{};
        bool rejectedOffscreenViewport[2]{};
        bool rejectedOffscreenScissor[2]{};
        bool rejectedNoColorOutput[2]{};
        bool rejectedForeignClear[2]{};
        bool rejectedInvalidClear[2]{};
        bool replayedMidSceneClear[2]{};
        bool replayedPartialDepthStencil[2]{};
        ID3D11Texture2D* gameSurface{};
        ID3D11Texture2D* gameShaderIntermediate{};
        ID3D11Texture2D* gameMipIntermediate{};
        ID3D11Texture2D* gameEyeArray{};
        ID3D11Texture2D* gameCopyOnlyArray{};
        ID3D11Texture2D* gameConvertedArray{};
        ID3D11Texture2D* gameComputeArray{};
        ID3D11UnorderedAccessView* gameComputeViews[2]{};
        bool replayedComputeCopyStretch[2]{};
        bool preservedComputeOutputs[2]{};
        bool inheritedComputeState[2]{};
        ID3D11Texture2D* gameMultisample{};
        ID3D11RenderTargetView* gameSurfaceView{};
        bool rejectedInvalidSurfaceCopy[2]{};
        bool replayedPostDrawSurfaceCopy[2]{};
        bool replayedPostDrawShaderCopy[2]{};
        bool replayedGpuOnlyArrayCopy[2]{};
        bool replayedGpuOnlyArrayStretch[2]{};
        bool replayedPostDrawMipZeroCopy[2]{};
        bool replayedDistinctArrayEyeCopy[2]{};
        bool replayedFormatConvertedArrayCopy[2]{};
        bool replayedPostDrawMsaaResolve[2]{};
        bool replayedClippedSurfaceCopy[2]{};
        bool replayedClippedConvertedCopy[2]{};
        bool replayedClippedMsaaResolve[2]{};
        bool replayedNegativeTopSurfaceCopy[2]{};
        bool replayedNegativeTopConvertedCopy[2]{};
        bool replayedNegativeLeftMsaaResolve[2]{};
        bool replayedScaledPostpass[2]{};
        bool replayedScaledArrayEye[2]{};
        bool preservedPostDrawMrt[2]{};
    } gameEyeFixture{{}, {}, preservedDepthView,
                     originalGameBuffer, alternateEyeBuffer,
                     gameSampleView, gameSampler, gameConstants,
                     preservedRaster, preservedMask, preservedStencilRef};
    const outrun::vr::dx11::NativeGameEyeColorSeed fullGameClear{
        {0xff00ffffu, 0xffffff00u}}; // actual per-eye game TARGET Clear colors
    outrun::vr::dx11::NativeGameEyeRasterState gameRaster{};
    outrun::vr::dx11::NativeGameEyePartialTargetClear partialGameClear{};
    partialGameClear.count[0] = partialGameClear.count[1] = 12u;
    // Game-origin full Z/stencil Clear after three masked geometry Draws,
    // followed by per-eye HUD TARGET Clears after the remaining geometry.
    // Chronological replay must preserve BOTH independent eye command lists.
    using SourceClear = outrun::vr::dx11::NativeGameEyePartialTargetClear;
    for (std::uint32_t eye = 0u; eye < 2u; ++eye) {
        auto& depthEvent = partialGameClear.entries[eye][0];
        depthEvent.afterDrawOrdinal = 3u;
        depthEvent.kind = SourceClear::Kind::FullDepthStencil;
        depthEvent.depth = eye == 0u ? 0.2f : 0.8f;
        depthEvent.stencil = static_cast<std::uint8_t>(eye + 11u);
        depthEvent.clearDepth = true;
        depthEvent.clearStencil = true;
    }
    partialGameClear.entries[0][2] = {{4, 4, 12, 12}, 0xffff0000u, 5u};
    partialGameClear.entries[1][2] = {{40, 4, 48, 12}, 0xff00ff00u, 6u};
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
    gameEyeFixture.gamePixelShader = gamePixelShader;
    gameEyeFixture.gameSurface = gameSurface;
    gameEyeFixture.gameShaderIntermediate = gameShaderIntermediate;
    gameEyeFixture.gameMipIntermediate = mipGameIntermediate;
    gameEyeFixture.gameEyeArray = gameEyeArray;
    gameEyeFixture.gameCopyOnlyArray = gameCopyOnlyArray;
    gameEyeFixture.gameConvertedArray = gameConvertedArray;
    gameEyeFixture.gameMultisample = gameMultisample;
    gameEyeFixture.gameSurfaceView = gameSurfaceView;
    // Two game-created GPU postpasses run between the REAL eye Draw calls:
    // an unscaled per-camera array-slice copy followed by a format-converting
    // scaled source overlay AFTER the original TARGET Clear. Later callback
    // postpasses remain independent of the source-ordered command stream.
    for (std::uint32_t eye = 0; eye < 2u; ++eye) {
        // Keep source GPU postpasses away from the callback's later x24/x52
        // manual TARGET rectangle Clears and its stereo camera raster.
        // The earlier check overlapped those legitimate game writes.
        const UINT x = eye == 0u ? 40u : 8u;
        auto& copy = partialGameClear.entries[eye][1];
        copy.kind = SourceClear::Kind::SourceCopy;
        copy.afterDrawOrdinal = 4u;
        copy.source = gameEyeArray;
        copy.sourceBox = {0u, 0u, 0u, 8u, 8u, 1u};
        copy.destX = x;
        copy.destY = 24u;
        copy.sourceArraySlice = eye;
        auto& stretch = partialGameClear.entries[eye][3];
        stretch.kind = SourceClear::Kind::SourceStretch;
        stretch.afterDrawOrdinal = eye == 0u ? 5u : 6u;
        stretch.source = gameConvertedArray;
        stretch.sourceBox = {0u, 0u, 0u, 8u, 8u, 1u};
        stretch.destination = {
            static_cast<LONG>(x + 2u), 26,
            static_cast<LONG>(x + 6u), 30};
        stretch.linearFilter = false;
        stretch.sourceArraySlice = eye;
        // A genuine game menu offscreen target can be RTV-only. Native
        // Stretch already samples a GPU-side copy of this owned target;
        // the source timeline must admit it without an original SRV flag.
        auto& rtOnly = partialGameClear.entries[eye][4];
        rtOnly.kind = SourceClear::Kind::SourceStretch;
        rtOnly.afterDrawOrdinal = eye == 0u ? 5u : 6u;
        rtOnly.source = gameSurface;
        rtOnly.sourceBox = {0u, 0u, 0u, 8u, 8u, 1u};
        rtOnly.destination = eye == 0u
            ? D3D11_RECT{2, 35, 10, 39}
            : D3D11_RECT{34, 35, 42, 39};
        // Interleave a genuine bounded game depth+stencil clear AFTER its
        // two GPU postpasses, without creating an extra source Draw.
        auto& zRect = partialGameClear.entries[eye][5];
        zRect.kind = SourceClear::Kind::FullDepthStencil;
        zRect.afterDrawOrdinal = eye == 0u ? 5u : 6u;
        zRect.rect = eye == 0u
            ? D3D11_RECT{12, 44, 20, 52}
            : D3D11_RECT{44, 44, 52, 52};
        zRect.depth = eye == 0u ? 0.22f : 0.78f;
        zRect.stencil = static_cast<std::uint8_t>(eye + 13u);
        zRect.clearDepth = true;
        zRect.clearStencil = true;
        // A genuine post-geometry eye-array Copy whose 8-pixel box
        // intersects only the final two native eye pixels. The other six
        // source texels must not invalidate the entire menu frame.
        auto& edgeCopy = partialGameClear.entries[eye][6];
        edgeCopy.kind = SourceClear::Kind::SourceCopy;
        edgeCopy.afterDrawOrdinal = eye == 0u ? 5u : 6u;
        edgeCopy.source = gameCopyOnlyArray;
        edgeCopy.sourceBox = {0u, 0u, 0u, 8u, 8u, 1u};
        edgeCopy.destX = 62u;
        edgeCopy.destY = 20u;
        edgeCopy.sourceArraySlice = eye;
        // Actual menu/car GPU-only scaled postpass follows the original Draw.
        auto& gpuScale = partialGameClear.entries[eye][7];
        gpuScale.kind = SourceClear::Kind::SourceStretch;
        gpuScale.afterDrawOrdinal = eye == 0u ? 5u : 6u;
        gpuScale.source = gameCopyOnlyArray;
        gpuScale.sourceBox = {0u, 0u, 0u, 8u, 8u, 1u};
        gpuScale.destination = eye == 0u
            ? D3D11_RECT{24, 30, 28, 32}
            : D3D11_RECT{56, 30, 60, 32};
        gpuScale.sourceArraySlice = eye;
        // Sustained game scenes may issue MORE than eight chronological
        // post-draw commands before Present. Replay four additional GPU-only
        // and array-sliced camera operations without dropping either eye.
        auto& followCopy = partialGameClear.entries[eye][8];
        followCopy.kind = SourceClear::Kind::SourceCopy;
        followCopy.afterDrawOrdinal = eye == 0u ? 5u : 6u;
        followCopy.source = gameCopyOnlyArray;
        followCopy.sourceBox = {0u, 0u, 0u, 8u, 8u, 1u};
        followCopy.destX = eye == 0u ? 0 : 32;
        followCopy.destY = 20;
        followCopy.sourceArraySlice = eye;
        auto& followScale = partialGameClear.entries[eye][9];
        followScale.kind = SourceClear::Kind::SourceStretch;
        followScale.afterDrawOrdinal = followCopy.afterDrawOrdinal;
        followScale.source = gameCopyOnlyArray;
        followScale.sourceBox = {0u, 0u, 0u, 8u, 8u, 1u};
        followScale.destination = eye == 0u
            ? D3D11_RECT{0, 12, 8, 16}
            : D3D11_RECT{32, 12, 40, 16};
        followScale.linearFilter = false;
        followScale.sourceArraySlice = eye;
        auto& followClear = partialGameClear.entries[eye][10];
        followClear.kind = SourceClear::Kind::TargetRect;
        followClear.afterDrawOrdinal = followCopy.afterDrawOrdinal;
        followClear.argb = 0xff4488ccu;
        followClear.rect = eye == 0u
            ? D3D11_RECT{12, 20, 16, 24}
            : D3D11_RECT{44, 20, 48, 24};
        auto& followArray = partialGameClear.entries[eye][11];
        followArray.kind = SourceClear::Kind::SourceCopy;
        followArray.afterDrawOrdinal = followCopy.afterDrawOrdinal;
        followArray.source = gameEyeArray;
        followArray.sourceBox = {0u, 0u, 0u, 8u, 8u, 1u};
        // Keep this late copy clear of the callback's typed-format GPU
        // postpass at x=0..7/32..39, y=42..49. It runs after the source
        // timeline and would otherwise legitimately overwrite our sample.
        followArray.destX = eye == 0u ? 8 : 40;
        followArray.destY = 48;
        followArray.sourceArraySlice = eye;
    }

    std::cerr << "R178-DIAG stereo fixture ready\n";
    // 00819: the renderer callback itself emits independent eye GPU work
    // and returns per-eye draw/pose/view evidence after command recording.
    const auto gameEyePass = [](
        void* user, ID3D11DeviceContext* ctx,
        ID3D11RenderTargetView* eyeTarget, std::uint32_t eyeIndex,
        outrun::vr::dx11::NativeGameEyeDrawEvidence& evidence,
        outrun::vr::dx11::NativeGameEyeDrawEncoder& encoder) noexcept -> bool {
        if (!ctx || !eyeTarget || eyeIndex >= 2u || !user) return false;
        std::cerr << "R178-DIAG eye callback " << eyeIndex << '\n';
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
        ID3D11ShaderResourceView* csResource = nullptr;
        ID3D11SamplerState* csSampler = nullptr;
        ID3D11Buffer* csConstants = nullptr;
        ID3D11UnorderedAccessView* csOutputs[2]{};
        ctx->CSGetShaderResources(0u, 1u, &csResource);
        ctx->CSGetSamplers(0u, 1u, &csSampler);
        ctx->CSGetConstantBuffers(0u, 1u, &csConstants);
        ctx->CSGetUnorderedAccessViews(0u, 2u, csOutputs);
        fixture.inheritedComputeState[eyeIndex] =
            csResource == fixture.originalResource &&
            csSampler == fixture.originalSampler &&
            csConstants == fixture.originalConstants &&
            csOutputs[0] == fixture.gameComputeViews[0] &&
            csOutputs[1] == fixture.gameComputeViews[1];
        if (csResource) csResource->Release();
        if (csSampler) csSampler->Release();
        if (csConstants) csConstants->Release();
        for (auto* output : csOutputs) if (output) output->Release();

        ID3D11ShaderResourceView *gsResource = nullptr, *hsResource = nullptr, *dsResource = nullptr;
        ID3D11SamplerState *gsSampler = nullptr, *hsSampler = nullptr, *dsSampler = nullptr;
        ID3D11Buffer *gsConstants = nullptr, *hsConstants = nullptr, *dsConstants = nullptr;
        ctx->GSGetShaderResources(0u, 1u, &gsResource);
        ctx->HSGetShaderResources(0u, 1u, &hsResource);
        ctx->DSGetShaderResources(0u, 1u, &dsResource);
        ctx->GSGetSamplers(0u, 1u, &gsSampler);
        ctx->HSGetSamplers(0u, 1u, &hsSampler);
        ctx->DSGetSamplers(0u, 1u, &dsSampler);
        ctx->GSGetConstantBuffers(0u, 1u, &gsConstants);
        ctx->HSGetConstantBuffers(0u, 1u, &hsConstants);
        ctx->DSGetConstantBuffers(0u, 1u, &dsConstants);
        const bool inheritedStagesIntact =
            gsResource == fixture.originalResource &&
            hsResource == fixture.originalResource &&
            dsResource == fixture.originalResource &&
            gsSampler == fixture.originalSampler &&
            hsSampler == fixture.originalSampler &&
            dsSampler == fixture.originalSampler &&
            gsConstants == fixture.originalConstants &&
            hsConstants == fixture.originalConstants &&
            dsConstants == fixture.originalConstants;
        if (gsResource) gsResource->Release();
        if (hsResource) hsResource->Release();
        if (dsResource) dsResource->Release();
        if (gsSampler) gsSampler->Release();
        if (hsSampler) hsSampler->Release();
        if (dsSampler) dsSampler->Release();
        if (gsConstants) gsConstants->Release();
        if (hsConstants) hsConstants->Release();
        if (dsConstants) dsConstants->Release();
        const bool originalGameShaderInputs =
            isolatedEyeGeometry && inheritedStagesIntact &&
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
        // Even with the right OM eye targets, empty viewport/scissor GPU
        // coverage must not certify a native left/right game frame.
        const D3D11_VIEWPORT invisibleViewport{
            64.f, 0.f, 16.f, 16.f, 0.f, 1.f};
        ctx->RSSetViewports(1u, &invisibleViewport);
        fixture.rejectedOffscreenViewport[eyeIndex] =
            !encoder.draw(3u, 0u) && encoder.draw_count() == 0u;
        ctx->RSSetViewports(1u, &viewport);
        const D3D11_RECT invisibleScissor{64, 0, 80, 16};
        ctx->RSSetState(fixture.originalRaster); // ScissorEnable=TRUE.
        ctx->RSSetScissorRects(1u, &invisibleScissor);
        fixture.rejectedOffscreenScissor[eyeIndex] =
            !encoder.draw_indexed(3u, 0u, 0) && encoder.draw_count() == 0u;
        ctx->RSSetScissorRects(1u, &scissor);

        if (boundTarget) boundTarget->Release();
        if (boundDepth) boundDepth->Release();
        if (!fixture.sawBoundEye[eyeIndex] ||
            !fixture.rejectedOffscreenViewport[eyeIndex] ||
            !fixture.rejectedOffscreenScissor[eyeIndex]) return false;
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

        // Exercise real callback pollution. Right-eye Draw must recover all
        // inherited host stage bindings; scene exit must restore them again.
        ctx->GSSetShaderResources(0u, 1u, &nullResource);
        ctx->HSSetShaderResources(0u, 1u, &nullResource);
        ctx->DSSetShaderResources(0u, 1u, &nullResource);
        ctx->GSSetSamplers(0u, 1u, &nullSampler);
        ctx->HSSetSamplers(0u, 1u, &nullSampler);
        ctx->DSSetSamplers(0u, 1u, &nullSampler);
        ctx->GSSetConstantBuffers(0u, 1u, &nullConstants);
        ctx->HSSetConstantBuffers(0u, 1u, &nullConstants);
        ctx->DSSetConstantBuffers(0u, 1u, &nullConstants);
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
        fixture.rejectedForeignClear[eyeIndex] =
            !encoder.clear_target_argb(0xff123456u) &&
            !encoder.clear_depth_stencil(0.25f, 3u, true, true);
        ctx->OMSetRenderTargets(
            1u, &fixture.callerColor, fixture.callerDepth);
        // A game offscreen/desktop Draw is equally ineligible. Rebind the
        // ring-owned eye RTV+DSV explicitly before real geometry replay.
        fixture.rejectedForeignDraw[eyeIndex] =
            !encoder.draw_indexed(3u, 0u, 0) && encoder.draw_count() == 0u;
        if (!fixture.rejectedDetachedDraw[eyeIndex] ||
            !fixture.rejectedForeignDraw[eyeIndex] ||
            !fixture.rejectedForeignClear[eyeIndex] ||
            !encoder.bind_eye_output())
            return false;
        // Depth-only commands remain in the real GPU stream and in the Draw
        // evidence ordinal, but cannot publish an empty native color eye.
        const auto maskedBaseline = encoder.draw_count();
        ctx->OMSetBlendState(nullptr, nullptr, 0u);
        const bool zeroSample = encoder.draw(3u, 0u) &&
            encoder.draw_count() == maskedBaseline + 1u &&
            encoder.color_draw_count() == 0u;
        ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);
        D3D11_BLEND_DESC maskedDesc{};
        maskedDesc.RenderTarget[0].SrcBlend = D3D11_BLEND_ONE;
        maskedDesc.RenderTarget[0].DestBlend = D3D11_BLEND_ZERO;
        maskedDesc.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;
        maskedDesc.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;
        maskedDesc.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_ZERO;
        maskedDesc.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;
        maskedDesc.RenderTarget[0].RenderTargetWriteMask = 0u;
        ID3D11Device* ownerDevice = nullptr;
        ID3D11BlendState* maskedBlend = nullptr;
        ctx->GetDevice(&ownerDevice);
        const bool maskedCreated = ownerDevice &&
            SUCCEEDED(ownerDevice->CreateBlendState(&maskedDesc, &maskedBlend)) &&
            maskedBlend != nullptr;
        if (ownerDevice) ownerDevice->Release();
        if (!maskedCreated) return false;
        ctx->OMSetBlendState(maskedBlend, nullptr, 0xffffffffu);
        const bool zeroWrite = encoder.draw_indexed(3u, 0u, 0) &&
            encoder.draw_count() == maskedBaseline + 2u &&
            encoder.color_draw_count() == 0u;
        ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);
        maskedBlend->Release();
        ctx->PSSetShader(nullptr, nullptr, 0u);
        const bool unshaded = encoder.draw(3u, 0u) &&
            encoder.draw_count() == maskedBaseline + 3u &&
            encoder.color_draw_count() == 0u;
        ctx->PSSetShader(fixture.gamePixelShader, nullptr, 0u);
        fixture.rejectedNoColorOutput[eyeIndex] =
            zeroSample && zeroWrite && unshaded;
        if (!fixture.rejectedNoColorOutput[eyeIndex]) return false;
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
        // A game menu/HUD can Clear a TARGET rectangle AFTER real geometry.
        // Validate ordered eye pixels, selected Z/stencil and no phantom draw.
        const D3D11_RECT badRect{63, 24, 68, 30};
        fixture.rejectedInvalidClear[eyeIndex] =
            !encoder.clear_target_argb(0xffffffffu, &badRect) &&
            !encoder.clear_depth_stencil(-0.5f, 0u, true, false) &&
            !encoder.clear_depth_stencil(0.5f, 0u, false, false) &&
            !encoder.clear_depth_stencil(0.5f, 0u, true, true, &badRect);
        const LONG patchLeft = eyeIndex == 0u ? 24 : 52;
        const D3D11_RECT afterDrawPatch{patchLeft, 24, patchLeft + 6, 30};
        const auto issuedDraws = encoder.draw_count();
        fixture.replayedMidSceneClear[eyeIndex] =
            encoder.clear_target_argb(
                eyeIndex == 0u ? 0xffff0000u : 0xff00ff00u,
                &afterDrawPatch) &&
            encoder.clear_depth_stencil(
                eyeIndex == 0u ? 0.30f : 0.70f,
                static_cast<std::uint8_t>(eyeIndex + 7u), true, true) &&
            encoder.draw_count() == issuedDraws;
        const D3D11_RECT zOnly{eyeIndex == 0u ? 8 : 40, 48,
                               eyeIndex == 0u ? 14 : 46, 54};
        const auto beforePartial = encoder.draw_count();
        fixture.replayedPartialDepthStencil[eyeIndex] =
            encoder.clear_depth_stencil(0.41f, 0u, true, false, &zOnly) &&
            encoder.clear_depth_stencil(
                1.0f, static_cast<std::uint8_t>(eyeIndex + 19u),
                false, true, &zOnly) &&
            encoder.draw_count() == beforePartial &&
            encoder.color_draw_count() > 0u;
        // Replay a same-device game post-process COPY after real eye Draws.
        // Negative cases must leave OM/depth state and both eyes unchanged.
        const D3D11_BOX sourcePatch{0u, 0u, 0u, 8u, 8u, 1u};
        const D3D11_BOX invalidSourcePatch{60u, 0u, 0u, 68u, 8u, 1u};
        const UINT destX = eyeIndex == 0u ? 16u : 48u;
        fixture.rejectedInvalidSurfaceCopy[eyeIndex] =
            !encoder.copy_game_surface(nullptr, &sourcePatch, destX, 38u) &&
            !encoder.copy_game_surface(
                fixture.gameSurface, &invalidSourcePatch, destX, 38u) &&
            !encoder.copy_game_surface(
                fixture.gameSurface, &sourcePatch, 64u, 38u) &&
            !encoder.copy_game_surface(
                fixture.gameMultisample, &invalidSourcePatch, destX, 54u) &&
            !encoder.copy_game_surface(
                fixture.gameMultisample, &sourcePatch, 64u, 54u);
        const auto beforeCopyDraws = encoder.draw_count();
        const auto beforeCopyColorDraws = encoder.color_draw_count();
        // A real game can bind its offscreen intermediate as MRT1 while the
        // eye remains RTV0. Source must be unbound for CopySubresourceRegion,
        // and both MRT slots plus the eye DSV must survive the GPU operation.
        ID3D11RenderTargetView* beforeCopyMrt[2]{
            eyeTarget, fixture.gameSurfaceView};
        ctx->OMSetRenderTargets(2u, beforeCopyMrt, fixture.eyeDepth[eyeIndex]);
        fixture.replayedPostDrawSurfaceCopy[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameSurface, &sourcePatch, destX, 38u) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // Preserve the same OM MRT1 and eye DSV while copying a game-owned
        // shader-readable (not RT-bindable) GPU post-pass into each eye.
        fixture.replayedPostDrawShaderCopy[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameShaderIntermediate, &sourcePatch, destX, 48u) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // Both live CS UAV slots persist while the source is used by a
        // genuine post-Draw Copy and a bilinear GPU Stretch into this eye.
        const UINT computeX = eyeIndex == 0u ? 20u : 52u;
        const D3D11_RECT computeRect{
            static_cast<LONG>(computeX), 6,
            static_cast<LONG>(computeX + 4u), 10};
        fixture.replayedComputeCopyStretch[eyeIndex] =
            !encoder.copy_game_surface(
                fixture.gameComputeArray, &sourcePatch, computeX, 2u, 2u) &&
            encoder.copy_game_surface(
                fixture.gameComputeArray, &sourcePatch,
                computeX, 2u, eyeIndex) &&
            encoder.stretch_game_surface(
                fixture.gameComputeArray, sourcePatch,
                computeRect, true, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        ID3D11UnorderedAccessView* computeAfter[2]{};
        ctx->CSGetUnorderedAccessViews(0u, 2u, computeAfter);
        fixture.preservedComputeOutputs[eyeIndex] =
            computeAfter[0] == fixture.gameComputeViews[0] &&
            computeAfter[1] == fixture.gameComputeViews[1];
        for (auto* v : computeAfter) if (v) v->Release();
        // The no-RTV/no-SRV intermediate is GPU-written by CopyResource;
        // its camera slice must still be replayed without a shader blit.
        // An invalid slice or fully off-eye destination must fail closed.
        const UINT copyOnlyX = eyeIndex == 0u ? 26u : 34u;
        fixture.replayedGpuOnlyArrayCopy[eyeIndex] =
            !encoder.copy_game_surface(
                fixture.gameCopyOnlyArray, &sourcePatch, copyOnlyX, 56u, 2u) &&
            !encoder.copy_game_surface(
                fixture.gameCopyOnlyArray, &sourcePatch, 64, 56u, eyeIndex) &&
            encoder.copy_game_surface(
                fixture.gameCopyOnlyArray, &sourcePatch,
                copyOnlyX, 56u, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // Copy the real mip-0 full-resolution game pixels from a multi-mip
        // GPU postpass. Do not accidentally use the green mip-1 or increase
        // the native Draw evidence; preserve RT0, MRT1 and both eye Z owners.
        fixture.replayedPostDrawMipZeroCopy[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameMipIntermediate, &sourcePatch, destX, 32u) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // Choose exactly one game-authored eye array slice. A foreign slice
        // is rejected before GPU mutation and never counts as a stereo draw.
        fixture.replayedDistinctArrayEyeCopy[eyeIndex] =
            !encoder.copy_game_surface(
                fixture.gameEyeArray, &sourcePatch, destX, 16u, 2u) &&
            encoder.copy_game_surface(
                fixture.gameEyeArray, &sourcePatch, destX, 16u, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // Source BGRA != eye RGBA. A genuine unscaled game GPU postpass
        // must now convert and sample the correct independent camera slice.
        // A foreign slice or out-of-bounds destination must fail closed.
        // Copying must leave native Draw/DrawIndexed evidence untouched.
        // Use a disjoint eye rectangle: the existing real-game SRV
        // postpass is sampled at x=17/49, y=49 and must survive untouched.
        // Replaying BGRA at the old y=42, x=16/48 overlapped that sample
        // and falsely failed the previous copy regression.
        const UINT convertedDestX = eyeIndex == 0u ? 0u : 32u;
        fixture.replayedFormatConvertedArrayCopy[eyeIndex] =
            !encoder.copy_game_surface(
                fixture.gameConvertedArray, &sourcePatch,
                convertedDestX, 42u, 2u) &&
            !encoder.copy_game_surface(
                fixture.gameConvertedArray, &sourcePatch, 64u, 42u, eyeIndex) &&
            encoder.copy_game_surface(
                fixture.gameConvertedArray, &sourcePatch,
                convertedDestX, 42u, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // A real game MSAA RT must resolve on the GPU before copying just
        // the selected menu/vehicle patch, preserving the rest of both eyes.
        fixture.replayedPostDrawMsaaResolve[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameMultisample, &sourcePatch, destX, 54u) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // Preserve GPU-visible overlap for menu/vehicle postpasses with
        // right-edge destinations (including format conversion and MSAA).
        // These do not count as extra game geometry Draws.
        fixture.replayedClippedSurfaceCopy[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameEyeArray, &sourcePatch, 62u, 14u, eyeIndex) &&
            !encoder.copy_game_surface(
                fixture.gameEyeArray, &sourcePatch, 64u, 14u, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        fixture.replayedClippedConvertedCopy[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameConvertedArray, &sourcePatch, 62u, 44u, eyeIndex) &&
            !encoder.copy_game_surface(
                fixture.gameConvertedArray, &sourcePatch, 64u, 44u, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        fixture.replayedClippedMsaaResolve[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameMultisample, &sourcePatch, 62u, 58u) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // Game menu/camera postpasses may begin LEFT or ABOVE the XR eye.
        // Exercise real GPU Copy, typed format conversion and MSAA resolve
        // with source-box trimming (no rescale, no synthetic Draw evidence).
        fixture.replayedNegativeTopSurfaceCopy[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameEyeArray, &sourcePatch, 30u, -3, eyeIndex) &&
            !encoder.copy_game_surface(
                fixture.gameEyeArray, &sourcePatch, -8, 38, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        fixture.replayedNegativeTopConvertedCopy[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameConvertedArray, &sourcePatch, 55u, -4, eyeIndex) &&
            !encoder.copy_game_surface(
                fixture.gameConvertedArray, &sourcePatch, 55u, -8, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        fixture.replayedNegativeLeftMsaaResolve[eyeIndex] =
            encoder.copy_game_surface(
                fixture.gameMultisample, &sourcePatch, -4, 52u) &&
            !encoder.copy_game_surface(
                fixture.gameMultisample, &sourcePatch, -9, 52u) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // A real game StretchRect scales 8x8 GPU pixels into a 12x5
        // menu/vehicle eye region, not a CPU/desktop intermediate.
        const D3D11_RECT scaledDest{
            static_cast<LONG>(destX), 58,
            static_cast<LONG>(destX + 12u), 63};
        // A partially offscreen game StretchRect is now valid: the native
        // eye viewport and sampled UVs are cropped together. Fully offscreen
        // destination is still rejected without producing draw evidence.
        const D3D11_RECT clippedDest{
            static_cast<LONG>(destX), 63, 65, 67};
        const D3D11_RECT badDest{65, 58, 77, 63};
        std::cerr << "R178-DIAG stretch begin " << eyeIndex << '\n';
        fixture.replayedScaledPostpass[eyeIndex] =
            !encoder.stretch_game_surface(
                nullptr, sourcePatch, scaledDest, false) &&
            !encoder.stretch_game_surface(
                fixture.gameSurface, invalidSourcePatch, scaledDest, false) &&
            !encoder.stretch_game_surface(
                fixture.gameSurface, sourcePatch, badDest, false) &&
            encoder.stretch_game_surface(
                fixture.gameSurface, sourcePatch, scaledDest, true) &&
            encoder.stretch_game_surface(
                fixture.gameSurface, sourcePatch, clippedDest, true) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        std::cerr << "R178-DIAG stretch returned " << eyeIndex << '\n';
        // Full-size per-camera color can live in a multi-mip GPU array.
        // The original game StretchRect scales the correct array slice,
        // never the other camera or an implicit mono mip. Invalid slices
        // must leave both the eye and draw evidence untouched.
        const D3D11_RECT scaledArrayDest{
            static_cast<LONG>(destX), 8,
            static_cast<LONG>(destX + 12u), 14};
        fixture.replayedScaledArrayEye[eyeIndex] =
            !encoder.stretch_game_surface(
                fixture.gameEyeArray, sourcePatch, scaledArrayDest,
                false, 2u) &&
            encoder.stretch_game_surface(
                fixture.gameEyeArray, sourcePatch, scaledArrayDest,
                false, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        // Camera-sliced GPU-only DEFAULT output must scale without CPU staging
        // or extra geometry Draw evidence, while preserving caller OM/DSV.
        const D3D11_RECT gpuOnlyDest = eyeIndex == 0u
            ? D3D11_RECT{4, 58, 10, 62}
            : D3D11_RECT{36, 58, 42, 62};
        fixture.replayedGpuOnlyArrayStretch[eyeIndex] =
            !encoder.stretch_game_surface(
                fixture.gameCopyOnlyArray, sourcePatch,
                gpuOnlyDest, true, 2u) &&
            encoder.stretch_game_surface(
                fixture.gameCopyOnlyArray, sourcePatch,
                gpuOnlyDest, true, eyeIndex) &&
            encoder.draw_count() == beforeCopyDraws &&
            encoder.color_draw_count() == beforeCopyColorDraws;
        ID3D11RenderTargetView* afterCopyMrt[2]{};
        ID3D11DepthStencilView* afterCopyDepth = nullptr;
        ctx->OMGetRenderTargets(2u, afterCopyMrt, &afterCopyDepth);
        fixture.preservedPostDrawMrt[eyeIndex] =
            afterCopyMrt[0] == eyeTarget &&
            afterCopyMrt[1] == fixture.gameSurfaceView &&
            afterCopyDepth == fixture.eyeDepth[eyeIndex];
        for (auto* target : afterCopyMrt)
            if (target) target->Release();
        if (afterCopyDepth) afterCopyDepth->Release();
        // A game compute camera callback can replace stage bindings after
        // postpass dispatch. Verify next eye and caller recover their inputs.
        ID3D11ShaderResourceView* detachedComputeResource = nullptr;
        ID3D11SamplerState* detachedComputeSampler = nullptr;
        ID3D11Buffer* detachedComputeConstants = nullptr;
        ID3D11UnorderedAccessView* detachedComputeOutputs[2]{};
        ctx->CSSetShaderResources(0u, 1u, &detachedComputeResource);
        ctx->CSSetSamplers(0u, 1u, &detachedComputeSampler);
        ctx->CSSetConstantBuffers(0u, 1u, &detachedComputeConstants);
        ctx->CSSetUnorderedAccessViews(0u, 2u, detachedComputeOutputs, nullptr);
        if (!fixture.inheritedComputeState[eyeIndex] ||
            !fixture.rejectedInvalidClear[eyeIndex] ||
            !fixture.replayedMidSceneClear[eyeIndex] ||
            !fixture.replayedPartialDepthStencil[eyeIndex] ||
            !fixture.rejectedInvalidSurfaceCopy[eyeIndex] ||
            !fixture.replayedPostDrawSurfaceCopy[eyeIndex] ||
            !fixture.replayedPostDrawShaderCopy[eyeIndex] ||
            !fixture.replayedComputeCopyStretch[eyeIndex] ||
            !fixture.preservedComputeOutputs[eyeIndex] ||
            !fixture.replayedGpuOnlyArrayCopy[eyeIndex] ||
            !fixture.replayedGpuOnlyArrayStretch[eyeIndex] ||
            !fixture.replayedPostDrawMipZeroCopy[eyeIndex] ||
            !fixture.replayedDistinctArrayEyeCopy[eyeIndex] ||
            !fixture.replayedFormatConvertedArrayCopy[eyeIndex] ||
            !fixture.replayedPostDrawMsaaResolve[eyeIndex] ||
            !fixture.replayedClippedSurfaceCopy[eyeIndex] ||
            !fixture.replayedClippedConvertedCopy[eyeIndex] ||
            !fixture.replayedClippedMsaaResolve[eyeIndex] ||
            !fixture.replayedNegativeTopSurfaceCopy[eyeIndex] ||
            !fixture.replayedNegativeTopConvertedCopy[eyeIndex] ||
            !fixture.replayedNegativeLeftMsaaResolve[eyeIndex] ||
            !fixture.replayedScaledPostpass[eyeIndex] ||
            !fixture.replayedScaledArrayEye[eyeIndex] ||
            !encoder.color_draw_count()) return false;
        evidence.drawCount = encoder.draw_count();
        evidence.viewSignature = eyeIndex == 0u ? 0x303u : 0x404u;
        evidence.sourcePoseSequence = 33u;
        return true;
    };
    auto invalidRaster = gameRaster;
    invalidRaster.scissor[1].right = 65; // Fail before any GPU commands.
    auto invalidPartialClear = partialGameClear;
    invalidPartialClear.entries[1][2].rect.right = 65; // No partial GPU work.
    auto invalidClearOrder = partialGameClear;
    invalidClearOrder.entries[1][1].afterDrawOrdinal = 1u;
    auto invalidDepthClear = partialGameClear;
    invalidDepthClear.entries[1][0].depth = -0.1f;
    auto invalidPartialDepth = partialGameClear;
    // A bounded partial DSV Clear is now supported. Reject a genuinely
    // invalid negative RECT before any L/R GPU command, not the once-valid
    // {1,1,4,4} gameplay region used by the old full-only regression.
    invalidPartialDepth.entries[1][0].rect = {-1, 1, 4, 4};
    auto invalidDepthFlags = partialGameClear;
    invalidDepthFlags.entries[1][0].clearDepth = false;
    invalidDepthFlags.entries[1][0].clearStencil = false;
    auto invalidSourceSlice = partialGameClear;
    invalidSourceSlice.entries[1][1].sourceArraySlice = 2u;
    auto invalidStretchSource = partialGameClear;
    invalidStretchSource.entries[1][3].source = nullptr;
    // Bindless scaling is valid now; a foreign right camera slice is NOT.
    // Reject before the left eye can enqueue any native GPU commands.
    auto invalidCopyOnlyStretch = partialGameClear;
    invalidCopyOnlyStretch.entries[1][7].sourceArraySlice = 2u;
    auto invalidStretchBounds = partialGameClear;
    invalidStretchBounds.entries[1][3].destination = {65, 26, 71, 30};
    // Neither a late unordered race postpass nor an oversized event stream
    // may write eye L before the bad eye R timeline is rejected.
    auto invalidLateOrder = partialGameClear;
    invalidLateOrder.entries[1][11].afterDrawOrdinal = 2u;
    auto invalidEventCapacity = partialGameClear;
    invalidEventCapacity.count[1] =
        SourceClear::kMaxRectsPerEye + 1u;

    // Preserve the original host geometry/tessellation inputs when native
    // menu/car/race eye callbacks borrow the immediate graphics context.
    // These stages are disabled for actual D3D9 Draws but their bindings
    // must survive for the next OpenXR/desktop pass.
    d3d.context->GSSetShaderResources(0u, 1u, &gameSampleView);
    d3d.context->GSSetSamplers(0u, 1u, &gameSampler);
    d3d.context->GSSetConstantBuffers(0u, 1u, &gameConstants);
    d3d.context->HSSetShaderResources(0u, 1u, &gameSampleView);
    d3d.context->HSSetSamplers(0u, 1u, &gameSampler);
    d3d.context->HSSetConstantBuffers(0u, 1u, &gameConstants);
    d3d.context->DSSetShaderResources(0u, 1u, &gameSampleView);
    d3d.context->DSSetSamplers(0u, 1u, &gameSampler);
    d3d.context->DSSetConstantBuffers(0u, 1u, &gameConstants);
    gameEyeFixture.gameComputeArray = gameComputeArray;
    gameEyeFixture.gameComputeViews[0] = gameComputeViews[0];
    gameEyeFixture.gameComputeViews[1] = gameComputeViews[1];
    d3d.context->CSSetUnorderedAccessViews(
        0u, 2u, gameComputeViews, nullptr);
    d3d.context->CSSetShaderResources(0u, 1u, &gameSampleView);
    d3d.context->CSSetSamplers(0u, 1u, &gameSampler);
    d3d.context->CSSetConstantBuffers(0u, 1u, &gameConstants);
    require(directSubmit.begin(d3d.context, 24, 33) &&
            !directSubmit.render_game_eye_passes(nullptr, &gameEyeFixture, 33) &&
            !directSubmit.render_game_eye_passes(gameEyePass, &gameEyeFixture, 32) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &invalidRaster) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidPartialClear) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidClearOrder) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidDepthClear) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidPartialDepth) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidDepthFlags) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidSourceSlice) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidStretchSource) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidCopyOnlyStretch) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidStretchBounds) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidLateOrder) &&
            !directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &invalidEventCapacity) &&
            !ring.synchronization_faulted() &&
            directSubmit.render_game_eye_passes(
                gameEyePass, &gameEyeFixture, 33, &fullGameClear,
                &gameRaster, &partialGameClear) &&
            directSubmit.in_flight() && !directSubmit.cancel() &&
            gameEyeFixture.sawBoundEye[0] && gameEyeFixture.sawBoundEye[1] &&
            gameEyeFixture.rejectedDetachedDraw[0] &&
            gameEyeFixture.rejectedDetachedDraw[1] &&
            gameEyeFixture.rejectedForeignDraw[0] &&
            gameEyeFixture.rejectedForeignDraw[1] &&
            gameEyeFixture.rejectedOffscreenViewport[0] &&
            gameEyeFixture.rejectedOffscreenViewport[1] &&
            gameEyeFixture.rejectedOffscreenScissor[0] &&
            gameEyeFixture.rejectedOffscreenScissor[1] &&
            gameEyeFixture.rejectedNoColorOutput[0] &&
            gameEyeFixture.rejectedNoColorOutput[1] &&
            gameEyeFixture.rejectedForeignClear[0] &&
            gameEyeFixture.rejectedForeignClear[1] &&
            gameEyeFixture.rejectedInvalidClear[0] &&
            gameEyeFixture.rejectedInvalidClear[1] &&
            gameEyeFixture.replayedMidSceneClear[0] &&
            gameEyeFixture.replayedMidSceneClear[1] &&
            gameEyeFixture.replayedPartialDepthStencil[0] &&
            gameEyeFixture.replayedPartialDepthStencil[1] &&
            gameEyeFixture.rejectedInvalidSurfaceCopy[0] &&
            gameEyeFixture.rejectedInvalidSurfaceCopy[1] &&
            gameEyeFixture.replayedPostDrawSurfaceCopy[0] &&
            gameEyeFixture.replayedPostDrawSurfaceCopy[1] &&
            gameEyeFixture.replayedPostDrawShaderCopy[0] &&
            gameEyeFixture.replayedPostDrawShaderCopy[1] &&
            gameEyeFixture.replayedComputeCopyStretch[0] &&
            gameEyeFixture.replayedComputeCopyStretch[1] &&
            gameEyeFixture.preservedComputeOutputs[0] &&
            gameEyeFixture.preservedComputeOutputs[1] &&
            gameEyeFixture.inheritedComputeState[0] &&
            gameEyeFixture.inheritedComputeState[1] &&
            gameEyeFixture.replayedGpuOnlyArrayCopy[0] &&
            gameEyeFixture.replayedGpuOnlyArrayCopy[1] &&
            gameEyeFixture.replayedGpuOnlyArrayStretch[0] &&
            gameEyeFixture.replayedGpuOnlyArrayStretch[1] &&
            gameEyeFixture.replayedPostDrawMipZeroCopy[0] &&
            gameEyeFixture.replayedPostDrawMipZeroCopy[1] &&
            gameEyeFixture.replayedDistinctArrayEyeCopy[0] &&
            gameEyeFixture.replayedDistinctArrayEyeCopy[1] &&
            gameEyeFixture.replayedFormatConvertedArrayCopy[0] &&
            gameEyeFixture.replayedFormatConvertedArrayCopy[1] &&
            gameEyeFixture.replayedPostDrawMsaaResolve[0] &&
            gameEyeFixture.replayedPostDrawMsaaResolve[1] &&
            gameEyeFixture.replayedClippedSurfaceCopy[0] &&
            gameEyeFixture.replayedClippedSurfaceCopy[1] &&
            gameEyeFixture.replayedClippedConvertedCopy[0] &&
            gameEyeFixture.replayedClippedConvertedCopy[1] &&
            gameEyeFixture.replayedClippedMsaaResolve[0] &&
            gameEyeFixture.replayedClippedMsaaResolve[1] &&
            gameEyeFixture.preservedPostDrawMrt[0] &&
            gameEyeFixture.preservedPostDrawMrt[1],
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
    ID3D11ShaderResourceView *restoredGSResource = nullptr, *restoredHSResource = nullptr, *restoredDSResource = nullptr;
    ID3D11SamplerState *restoredGSSampler = nullptr, *restoredHSSampler = nullptr, *restoredDSSampler = nullptr;
    ID3D11Buffer *restoredGSConstants = nullptr, *restoredHSConstants = nullptr, *restoredDSConstants = nullptr;
    d3d.context->GSGetShaderResources(0u, 1u, &restoredGSResource);
    d3d.context->HSGetShaderResources(0u, 1u, &restoredHSResource);
    d3d.context->DSGetShaderResources(0u, 1u, &restoredDSResource);
    d3d.context->GSGetSamplers(0u, 1u, &restoredGSSampler);
    d3d.context->HSGetSamplers(0u, 1u, &restoredHSSampler);
    d3d.context->DSGetSamplers(0u, 1u, &restoredDSSampler);
    d3d.context->GSGetConstantBuffers(0u, 1u, &restoredGSConstants);
    d3d.context->HSGetConstantBuffers(0u, 1u, &restoredHSConstants);
    d3d.context->DSGetConstantBuffers(0u, 1u, &restoredDSConstants);
    const bool originalHostStagesRestored =
        restoredGSResource == gameSampleView && restoredHSResource == gameSampleView &&
        restoredDSResource == gameSampleView && restoredGSSampler == gameSampler &&
        restoredHSSampler == gameSampler && restoredDSSampler == gameSampler &&
        restoredGSConstants == gameConstants && restoredHSConstants == gameConstants &&
        restoredDSConstants == gameConstants;
    const bool restoredGameState =
        originalHostStagesRestored && restoredGeometry == originalGeometryShader &&
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
    if (restoredGSResource) restoredGSResource->Release();
    if (restoredHSResource) restoredHSResource->Release();
    if (restoredDSResource) restoredDSResource->Release();
    if (restoredGSSampler) restoredGSSampler->Release();
    if (restoredHSSampler) restoredHSSampler->Release();
    if (restoredDSSampler) restoredDSSampler->Release();
    if (restoredGSConstants) restoredGSConstants->Release();
    if (restoredHSConstants) restoredHSConstants->Release();
    if (restoredDSConstants) restoredDSConstants->Release();
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
    d3d.context->GSSetShaderResources(0u, 1u, &nullGameResource);
    d3d.context->HSSetShaderResources(0u, 1u, &nullGameResource);
    d3d.context->DSSetShaderResources(0u, 1u, &nullGameResource);
    d3d.context->GSSetSamplers(0u, 1u, &nullGameSampler);
    d3d.context->HSSetSamplers(0u, 1u, &nullGameSampler);
    d3d.context->DSSetSamplers(0u, 1u, &nullGameSampler);
    d3d.context->GSSetConstantBuffers(0u, 1u, &nullGameConstants);
    d3d.context->HSSetConstantBuffers(0u, 1u, &nullGameConstants);
    d3d.context->DSSetConstantBuffers(0u, 1u, &nullGameConstants);
    d3d.context->GSSetShader(nullptr, nullptr, 0u);
    d3d.context->VSSetShader(nullptr, nullptr, 0u);
    d3d.context->PSSetShader(nullptr, nullptr, 0u);
    gameVertexShader->Release();
    gamePixelShader->Release();
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
    gameSurfaceView->Release();
    gameShaderIntermediate->Release();
    mipGameIntermediate->Release();
    gameEyeArray->Release();
    ID3D11UnorderedAccessView* nullComputeViews[2]{};
    d3d.context->CSSetUnorderedAccessViews(0u, 2u, nullComputeViews, nullptr);
    for (auto* v : gameComputeViews) if (v) v->Release();
    gameComputeArray->Release();
    gameCopyOnlyArray->Release();
    gameConvertedArray->Release();
    gameMultisampleView->Release();
    gameMultisample->Release();
    gameSurface->Release();
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
        // Read back exact native GPU camera colors, not merely successful
        // Copy/Stretch API returns. L=red and R=blue from separate UAVs.
        const UINT computeX = eyeIndex == 0u ? 21u : 53u;
        const auto* computeCopy = pixel + 3u * mapped.RowPitch + computeX * 4u;
        const auto* computeScale = pixel + 7u * mapped.RowPitch + computeX * 4u;
        const bool computePixels = eyeIndex == 0u
            ? computeCopy[0] == 255u && computeCopy[1] == 0u &&
              computeCopy[2] == 0u && computeScale[0] == 255u &&
              computeScale[1] == 0u && computeScale[2] == 0u
            : computeCopy[0] == 0u && computeCopy[1] == 0u &&
              computeCopy[2] == 255u && computeScale[0] == 0u &&
              computeScale[1] == 0u && computeScale[2] == 255u;
        require(computePixels,
                "00862 compute UAV camera Copy and scaled Stretch preserve separate native eye pixels");
        const bool distinctColor = eyeIndex == 0u
            ? pixel[0] == 0 && pixel[1] == 255 && pixel[2] == 255
            : pixel[0] == 255 && pixel[1] == 255 && pixel[2] == 0;
        // Check genuine GPU pixels from the AFTER-draw TARGET rectangles.
        const UINT clearX = eyeIndex == 0u ? 6u : 42u;
        const auto* clearPixel = pixel + 6u * mapped.RowPitch + clearX * 4u;
        require(eyeIndex == 0u
            ? clearPixel[0] == 255u && clearPixel[1] == 0u && clearPixel[2] == 0u
            : clearPixel[0] == 0u && clearPixel[1] == 255u && clearPixel[2] == 0u,
            "00847 GPU game TARGET Clear after genuine left/right Draw stream");
        // Verify genuine source-ordered GPU Copy THEN GPU Stretch after
        // separate game Draw ordinals. These are native shared-eye pixels,
        // not accepted calls or a left-eye image duplicated to both eyes.
        const UINT postX = eyeIndex == 0u ? 41u : 9u;
        const auto* copyPixel = pixel + 25u * mapped.RowPitch + postX * 4u;
        const bool chronologicalCopy = eyeIndex == 0u
            ? copyPixel[0] == 0x11u && copyPixel[1] == 0u &&
              copyPixel[2] == 0xccu
            : copyPixel[0] == 0x33u && copyPixel[1] == 0xbbu &&
              copyPixel[2] == 0x22u;
        const UINT postOverlayX = eyeIndex == 0u ? 43u : 11u;
        const auto* postPixel =
            pixel + 27u * mapped.RowPitch + postOverlayX * 4u;
        const bool chronologicalStretch = eyeIndex == 0u
            ? postPixel[0] == 255u && postPixel[1] == 0u &&
              postPixel[2] == 0u
            : postPixel[0] == 0u && postPixel[1] == 255u &&
              postPixel[2] == 0u;
        const UINT rtX = eyeIndex == 0u ? 4u : 36u;
        const auto* rtPixel = pixel + 36u * mapped.RowPitch + rtX * 4u;
        const bool chronologicalRtOnly = rtPixel[0] == 0u &&
            rtPixel[1] == 0u && rtPixel[2] == 255u;
        require(chronologicalCopy && chronologicalStretch &&
                chronologicalRtOnly,
                "00849 GPU source Copy/Stretch/RT-only chronological pixels");
        // SourceCopy on the chronological game timeline used a DEFAULT
        // GPU-only resource with BindFlags=0. A separate post-draw copy uses
        // the same GPU-only per-eye source: both must preserve actual pixels.
        const UINT copyOnlyX = eyeIndex == 0u ? 27u : 35u;
        const auto* timelineGpuOnly =
            pixel + 21u * mapped.RowPitch + 63u * 4u;
        const auto* copiedGpuOnly =
            pixel + 57u * mapped.RowPitch + copyOnlyX * 4u;
        const bool gpuOnlyCameraPixels =
            eyeIndex == 0u
                ? (timelineGpuOnly[0] == 0x11u &&
                   timelineGpuOnly[1] == 0u && timelineGpuOnly[2] == 0xccu &&
                   copiedGpuOnly[0] == 0x11u &&
                   copiedGpuOnly[1] == 0u && copiedGpuOnly[2] == 0xccu)
                : (timelineGpuOnly[0] == 0x33u &&
                   timelineGpuOnly[1] == 0xbbu && timelineGpuOnly[2] == 0x22u &&
                   copiedGpuOnly[0] == 0x33u &&
                   copiedGpuOnly[1] == 0xbbu && copiedGpuOnly[2] == 0x22u);
        require(gpuOnlyCameraPixels,
                "00853 GPU-only CopyResource camera pixels survive timeline and native L/R postpass");
        const auto* gpuScaleTimeline =
            pixel + 31u * mapped.RowPitch + (eyeIndex == 0u ? 25u : 57u) * 4u;
        const auto* gpuScaleDirect =
            pixel + 60u * mapped.RowPitch + (eyeIndex == 0u ? 6u : 38u) * 4u;
        const bool realGpuScale = eyeIndex == 0u
            ? (gpuScaleTimeline[0] == 0x11u && gpuScaleTimeline[1] == 0u &&
               gpuScaleTimeline[2] == 0xccu &&
               gpuScaleDirect[0] == 0x11u && gpuScaleDirect[1] == 0u &&
               gpuScaleDirect[2] == 0xccu)
            : (gpuScaleTimeline[0] == 0x33u && gpuScaleTimeline[1] == 0xbbu &&
               gpuScaleTimeline[2] == 0x22u &&
               gpuScaleDirect[0] == 0x33u && gpuScaleDirect[1] == 0xbbu &&
               gpuScaleDirect[2] == 0x22u);
        require(realGpuScale,
                "00854 GPU-only scaled game postpass actual L/R eye pixels");
        // All four late commands must land AFTER the eighth event, with
        // camera-specific pixels and an interleaved real TargetRect Clear.
        // A stale eight-event limit or mono source silently fails these.
        const UINT longEyeX = eyeIndex == 0u ? 1u : 33u;
        const UINT lateClearX = eyeIndex == 0u ? 13u : 45u;
        const auto* lateCopy = pixel + 21u * mapped.RowPitch + longEyeX * 4u;
        const auto* lateScale = pixel + 14u * mapped.RowPitch +
            (longEyeX + 1u) * 4u;
        const UINT lateArrayX = eyeIndex == 0u ? 9u : 41u;
        const auto* lateArray = pixel + 49u * mapped.RowPitch + lateArrayX * 4u;
        const auto* lateClear = pixel + 22u * mapped.RowPitch + lateClearX * 4u;
        const auto expectedCamera =
            [&](const std::uint8_t* p) noexcept {
                return eyeIndex == 0u
                    ? (p[0] == 0x11u && p[1] == 0x00u && p[2] == 0xccu)
                    : (p[0] == 0x33u && p[1] == 0xbbu && p[2] == 0x22u);
            };
        const bool lateCopyMatches = expectedCamera(lateCopy);
        const bool lateScaleMatches = expectedCamera(lateScale);
        const bool lateArrayMatches = expectedCamera(lateArray);
        // The shared L/R color targets are R8G8B8A8_UNORM: ClearView's
        // ARGB(0xff4488cc) maps to raw RGBA bytes [0x44,0x88,0xcc,0xff].
        // This is NOT the BGRA channel order used by the separate converted
        // game source. WARP readback at bb57f328 confirmed the real bytes.
        const bool lateClearMatches =
            lateClear[0] == 0x44u && lateClear[1] == 0x88u &&
            lateClear[2] == 0xccu && lateClear[3] == 0xffu;
        if (!lateCopyMatches || !lateScaleMatches ||
            !lateArrayMatches || !lateClearMatches) {
            // Surface actual WARP sample values on failure rather than
            // guessing a color-order bug or weakening native-eye coverage.
            const auto show = [](const char* tag,
                                 const std::uint8_t* sample) {
                std::cerr << ' ' << tag << '='
                          << unsigned(sample[0]) << ','
                          << unsigned(sample[1]) << ','
                          << unsigned(sample[2]) << ','
                          << unsigned(sample[3]);
            };
            std::cerr << "00855 source timeline WARP pixel mismatch eye="
                      << eyeIndex;
            show("copy", lateCopy);
            show("scale", lateScale);
            show("array", lateArray);
            show("clear", lateClear);
            std::cerr << '\n';
        }
        // Keep the original source-graph activation's exact executable
        // negative/positive pixel contract, not a replacement metadata flag.
        require(expectedCamera(lateCopy) &&
                expectedCamera(lateScale) &&
                expectedCamera(lateArray) &&
                lateClear[0] == 0x44u && lateClear[1] == 0x88u &&
                lateClear[2] == 0xccu && lateClear[3] == 0xffu,
                "00855 twelve-event source timeline actual L/R GPU pixels and Clear order");
        // Mip 1 was deliberately green, but the unscaled eye transfer must
        // preserve blue mip-0 pixels in both independent GPU eye targets.
        const UINT arrayX = eyeIndex == 0u ? 18u : 50u;
        const auto* arrayPixel = pixel + 18u * mapped.RowPitch + arrayX * 4u;
        const bool actualDistinctArrayEye = eyeIndex == 0u
            ? arrayPixel[0] == 0x11u && arrayPixel[1] == 0x00u &&
              arrayPixel[2] == 0xccu
            : arrayPixel[0] == 0x33u && arrayPixel[1] == 0xbbu &&
              arrayPixel[2] == 0x22u;
        // Confirm actual D3D11 stretched GPU pixels, not a merely accepted
        // API call. Camera 0 is solid 0xffcc0011; camera 1 0xff22bb33.
        // A slice-zero default for BOTH eyes would fail this readback.
        const UINT scaledArrayX = eyeIndex == 0u ? 19u : 51u;
        const auto* scaledArrayPixel =
            pixel + 10u * mapped.RowPitch + scaledArrayX * 4u;
        const bool actualScaledArrayEye = eyeIndex == 0u
            ? scaledArrayPixel[0] == 0x11u &&
              scaledArrayPixel[1] == 0x00u &&
              scaledArrayPixel[2] == 0xccu
            : scaledArrayPixel[0] == 0x33u &&
              scaledArrayPixel[1] == 0xbbu &&
              scaledArrayPixel[2] == 0x22u;
        // BGRA source is sampled as colors rather than raw reordered
        // bytes. Left camera is red; right camera green, despite sharing
        // one game-owned GPU array and converting into RGBA eye targets.
        const UINT convertedX = eyeIndex == 0u ? 2u : 34u;
        const auto* convertedPixel =
            pixel + 43u * mapped.RowPitch + convertedX * 4u;
        const bool actualConvertedArrayEye = eyeIndex == 0u
            ? convertedPixel[0] == 255u &&
              convertedPixel[1] == 0u && convertedPixel[2] == 0u
            : convertedPixel[0] == 0u &&
              convertedPixel[1] == 255u && convertedPixel[2] == 0u;
        // Read actual edge pixels after the source timeline AND immediate
        // postpasses; checked separately for each camera to reject copying
        // one eye's buffer to the other. The unmodified inner-eye samples
        // below still prove that clipping did not rescale the scene.
        const auto* timelineEdge = pixel + 22u * mapped.RowPitch + 63u * 4u;
        const auto* copyEdge = pixel + 15u * mapped.RowPitch + 63u * 4u;
        const auto* convertEdge = pixel + 45u * mapped.RowPitch + 63u * 4u;
        const auto* msaaEdge = pixel + 59u * mapped.RowPitch + 63u * 4u;
        const bool expectedSourceEdge = eyeIndex == 0u
            ? timelineEdge[0] == 0x11u && timelineEdge[1] == 0u &&
              timelineEdge[2] == 0xccu && copyEdge[0] == 0x11u &&
              copyEdge[1] == 0u && copyEdge[2] == 0xccu
            : timelineEdge[0] == 0x33u && timelineEdge[1] == 0xbbu &&
              timelineEdge[2] == 0x22u && copyEdge[0] == 0x33u &&
              copyEdge[1] == 0xbbu && copyEdge[2] == 0x22u;
        const bool expectedConvertedEdge = eyeIndex == 0u
            ? convertEdge[0] == 255u && convertEdge[1] == 0u &&
              convertEdge[2] == 0u
            : convertEdge[0] == 0u && convertEdge[1] == 255u &&
              convertEdge[2] == 0u;
        const bool expectedMsaaEdge = msaaEdge[0] == 255u &&
            msaaEdge[1] == 0u && msaaEdge[2] == 255u;
        require(expectedSourceEdge && expectedConvertedEdge &&
                expectedMsaaEdge,
                "00851 real GPU clipped Copy/convert/Resolve left/right edge pixels");
        // Read back the actual partially visible GPU pixels, independently
        // for each camera. Existing top-left scene color and right/bottom
        // clipped postpass samples remain unchanged.
        const auto* negativeTopCopy = pixel + 1u * mapped.RowPitch + 31u * 4u;
        const auto* negativeTopConvert =
            pixel + 1u * mapped.RowPitch + 56u * 4u;
        const auto* negativeLeftMsaa =
            pixel + 53u * mapped.RowPitch + 1u * 4u;
        const bool actualNegativeCopy = eyeIndex == 0u
            ? negativeTopCopy[0] == 0x11u &&
              negativeTopCopy[1] == 0u && negativeTopCopy[2] == 0xccu
            : negativeTopCopy[0] == 0x33u &&
              negativeTopCopy[1] == 0xbbu && negativeTopCopy[2] == 0x22u;
        const bool actualNegativeConvert = eyeIndex == 0u
            ? negativeTopConvert[0] == 255u &&
              negativeTopConvert[1] == 0u && negativeTopConvert[2] == 0u
            : negativeTopConvert[0] == 0u &&
              negativeTopConvert[1] == 255u && negativeTopConvert[2] == 0u;
        require(actualNegativeCopy && actualNegativeConvert &&
                negativeLeftMsaa[0] == 255u &&
                negativeLeftMsaa[1] == 0u && negativeLeftMsaa[2] == 255u,
                "00852 left/top clipped GPU Copy/convert/resolve both-eye pixels");
        const UINT mipX = eyeIndex == 0u ? 18u : 50u;
        const auto* mipPixel = pixel + 34u * mapped.RowPitch + mipX * 4u;
        const bool actualMipZeroCopy =
            mipPixel[0] == 0u && mipPixel[1] == 0u && mipPixel[2] == 255u;
        const UINT patchX = eyeIndex == 0u ? 6u : 44u;
        const auto* patch = pixel + 6u * mapped.RowPitch + patchX * 4u;
        const bool actualPartialClear = eyeIndex == 0u
            ? patch[0] == 255u && patch[1] == 0u && patch[2] == 0u
            : patch[0] == 0u && patch[1] == 255u && patch[2] == 0u;
        const UINT laterX = eyeIndex == 0u ? 26u : 54u;
        const auto* later = pixel + 26u * mapped.RowPitch + laterX * 4u;
        const bool orderedAfterDrawClear = eyeIndex == 0u
            ? later[0] == 255u && later[1] == 0u && later[2] == 0u
            : later[0] == 0u && later[1] == 255u && later[2] == 0u;
        if (!distinctColor || !actualMipZeroCopy || !actualDistinctArrayEye ||
            !actualScaledArrayEye || !actualConvertedArrayEye ||
            !actualPartialClear ||
            !orderedAfterDrawClear) {
            std::cerr << "00829 eye=" << eyeIndex
                      << " convertedRGBA="
                      << unsigned(convertedPixel[0]) << ","
                      << unsigned(convertedPixel[1]) << ","
                      << unsigned(convertedPixel[2]) << ","
                      << unsigned(convertedPixel[3])
                      << " convertedOK=" << actualConvertedArrayEye
                      << " full RGBA=" << unsigned(pixel[0]) << ","
                      << unsigned(pixel[1]) << "," << unsigned(pixel[2]) << ","
                      << unsigned(pixel[3]) << " patch RGBA="
                      << unsigned(patch[0]) << "," << unsigned(patch[1]) << ","
                      << unsigned(patch[2]) << "," << unsigned(patch[3])
                      << " after-Draw RGBA="
                      << unsigned(later[0]) << ","
                      << unsigned(later[1]) << ","
                      << unsigned(later[2]) << ","
                      << unsigned(later[3])
                      << " rowPitch=" << mapped.RowPitch << '\n';
        }
        const UINT copyX = eyeIndex == 0u ? 17u : 49u;
        const auto* copied = pixel + 39u * mapped.RowPitch + copyX * 4u;
        const bool gameSurfaceCopied =
            copied[0] == 0u && copied[1] == 0u &&
            copied[2] == 255u && copied[3] == 255u;
        const auto* shaderCopied =
            pixel + 49u * mapped.RowPitch + copyX * 4u;
        const bool gameShaderIntermediateCopied =
            shaderCopied[0] == 0u && shaderCopied[1] == 0u &&
            shaderCopied[2] == 255u && shaderCopied[3] == 255u;
        const auto* msaaResolved =
            pixel + 55u * mapped.RowPitch + copyX * 4u;
        const bool gameMsaaResolved =
            msaaResolved[0] == 255u && msaaResolved[1] == 0u &&
            msaaResolved[2] == 255u && msaaResolved[3] == 255u;
        const auto* scaled = pixel + 60u * mapped.RowPitch +
            (eyeIndex == 0u ? 20u : 52u) * 4u;
        const bool scaledGpuPixel =
            scaled[0] == 0u && scaled[1] == 0u &&
            scaled[2] == 255u && scaled[3] == 255u;
        d3d.context->Unmap(readback, 0);
        require(distinctColor && scaledGpuPixel && actualPartialClear &&
                orderedAfterDrawClear && gameSurfaceCopied &&
                gameShaderIntermediateCopied && gameMsaaResolved &&
                actualDistinctArrayEye && actualScaledArrayEye &&
                actualMipZeroCopy && actualConvertedArrayEye,
                "00835 native L/R Draw, ordered Clear, RT, SRV and GPU MSAA patch resolve");
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


    // 00842: game camera eyes may be captured in different array slices of
    // one GPU texture with a full mip chain, not only separate allocations.
    D3D11_TEXTURE2D_DESC arrayDesc = sourceDesc;
    arrayDesc.MipLevels = 2u;
    arrayDesc.ArraySize = 2u;
    ID3D11Texture2D* gameEyeArray842 = nullptr;
    ID3D11RenderTargetView* gameArrayViews[2][2]{};
    require(SUCCEEDED(d3d.device->CreateTexture2D(
                &arrayDesc, nullptr, &gameEyeArray842)) && gameEyeArray842,
            "00842 two-eye game texture-array producer");
    for (UINT eye = 0u; eye < 2u; ++eye) {
        for (UINT mip = 0u; mip < 2u; ++mip) {
            D3D11_RENDER_TARGET_VIEW_DESC viewDesc{};
            viewDesc.Format = arrayDesc.Format;
            viewDesc.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2DARRAY;
            viewDesc.Texture2DArray.MipSlice = mip;
            viewDesc.Texture2DArray.FirstArraySlice = eye;
            viewDesc.Texture2DArray.ArraySize = 1u;
            require(SUCCEEDED(d3d.device->CreateRenderTargetView(
                        gameEyeArray842, &viewDesc, &gameArrayViews[eye][mip])),
                    "00842 game left/right camera array RTV");
        }
    }
    d3d.context->ClearRenderTargetView(gameArrayViews[0][0], red);
    d3d.context->ClearRenderTargetView(gameArrayViews[1][0], blue);
    // Deliberately invert lower-mip colors: mistakenly copying mip one
    // must fail actual GPU pixel comparison, not merely a metadata check.
    d3d.context->ClearRenderTargetView(gameArrayViews[0][1], blue);
    d3d.context->ClearRenderTargetView(gameArrayViews[1][1], red);
    outrun::vr::dx11::NativeGameStereoSubmission arraySubmit(ring);
    require(arraySubmit.begin(d3d.context, 25u, 35u) &&
            !arraySubmit.capture_eye(0u, gameEyeArray842, 1u, 0xa1u, 35u, 2u) &&
            arraySubmit.capture_eye(0u, gameEyeArray842, 1u, 0xa1u, 35u, 0u) &&
            arraySubmit.capture_eye(1u, gameEyeArray842, 1u, 0xb2u, 35u, 0u) &&
            !arraySubmit.submit() && arraySubmit.cancel() &&
            !ring.synchronization_faulted(),
            "00842 aliased same slice and invalid slice reject before GPU");
    require(arraySubmit.begin(d3d.context, 26u, 35u) &&
            arraySubmit.capture_eye(0u, gameEyeArray842, 1u, 0xa1u, 35u, 0u) &&
            arraySubmit.capture_eye(1u, gameEyeArray842, 1u, 0xb2u, 35u, 1u) &&
            arraySubmit.submit() && arraySubmit.in_flight(),
            "00842 native producer submits two independent GPU array-slice eyes");
    outrun::vr::dx11::NativeGameStereoPublishedFrame arrayFrame{};
    bool arrayReady = false;
    for (int retry = 0; retry < 2000 && !arrayReady; ++retry) {
        arrayReady = arraySubmit.try_publish(arrayFrame);
        require(!ring.synchronization_faulted(), "00842 GPU fence healthy");
        if (!arrayReady) Sleep(1);
    }
    require(arrayReady && arrayFrame.eyeViewSignature[0] == 0xa1u &&
            arrayFrame.eyeViewSignature[1] == 0xb2u &&
            arrayFrame.sourcePoseSequence == 35u,
            "00842 exact stereo camera signatures survive GPU publication");
    for (UINT eye = 0; eye < 2u; ++eye) {
        d3d.context->CopyResource(readback, ring.eye(arrayFrame.gpu.slot, eye));
        D3D11_MAPPED_SUBRESOURCE mapped{};
        require(SUCCEEDED(d3d.context->Map(
                    readback, 0u, D3D11_MAP_READ, 0u, &mapped)),
                "00842 GPU eye pixel readback");
        const auto* px = static_cast<const std::uint8_t*>(mapped.pData);
        const bool distinct = eye == 0u
            ? px[0] == 255 && px[1] == 0 && px[2] == 0 && px[3] == 255
            : px[0] == 0 && px[1] == 0 && px[2] == 255 && px[3] == 255;
        d3d.context->Unmap(readback, 0u);
        require(distinct, "00842 independent mip-zero L/R GPU pixel identity");
    }
    hostFrame.frameId = 26u;
    hostFrame.sourcePoseSequence = 35u;
    hostFrame.flags &= ~OutRunVR::RenderFrameDirectGpuTransport;
    require(arraySubmit.attach_host_frame(arrayFrame, hostFrame) &&
            (hostFrame.flags & OutRunVR::RenderFrameDirectGpuTransport) &&
            ring.retire_acknowledged(
                make_ack(ring.identity(), arrayFrame.gpu.slot, 26u)) &&
            !arraySubmit.attach_host_frame(arrayFrame, hostFrame),
            "00842 stereo GPU host handoff and exact ACK retirement");
    for (UINT eye = 0; eye < 2u; ++eye)
        for (UINT mip = 0; mip < 2u; ++mip)
            gameArrayViews[eye][mip]->Release();
    gameEyeArray842->Release();

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
    require(ring.try_acquire_slot(d3d.context, 27, nullptr, partialSlot) &&
            !ring.render_eye_pair(d3d.context, partialSlot, 27, partialDraw, nullptr) &&
            ring.synchronization_faulted() &&
            !ring.cancel_acquired_slot(partialSlot, 27) &&
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
