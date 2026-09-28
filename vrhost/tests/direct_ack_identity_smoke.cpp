#include "vr/ipc/direct_ack_r13.hpp"
#include "vr/core/transport.hpp"

#include <cstdint>

int main()
{
    using namespace OutRunVR::R13;
    DirectGpuAckState ack{};
    ack.hostPid = 10;
    ack.clientPid = 20;
    ack.runGeneration = 30;
    ack.transportGeneration = 40;

    if (!DirectGpuAckIdentityMatches(ack, 10, 20, 30, 40)) return 1;
    if (DirectGpuAckIdentityMatches(ack, 11, 20, 30, 40)) return 2;
    if (DirectGpuAckIdentityMatches(ack, 10, 21, 30, 40)) return 3;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 31, 40)) return 4;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 30, 41)) return 5;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 0, 40)) return 6;

    // Backend-neutral DX11/DXVK transports inherit the same identity model:
    // producer + consumer + run + transport + slot must all match, and only a
    // completion ACK covering the published frame may release the slot.
    OutRunVR::Core::FrameSlot published{};
    published.producerPid = 20;
    published.consumerPid = 10;
    published.runGeneration = 30;
    published.generation = 40;
    published.slot = 2;
    published.frameId = 100;

    OutRunVR::Core::FrameAck genericAck{};
    genericAck.consumerPid = 10;
    genericAck.producerPid = 20;
    genericAck.runGeneration = 30;
    genericAck.generation = 40;
    genericAck.slot = 2;
    genericAck.completedFrameId = 100;

    if (!OutRunVR::Core::ConsumerAckCoversFrame(published, genericAck)) return 7;
    genericAck.consumerPid = 11;
    if (OutRunVR::Core::ConsumerAckCoversFrame(published, genericAck)) return 8;
    genericAck.consumerPid = 10;
    genericAck.runGeneration = 31;
    if (OutRunVR::Core::ConsumerAckCoversFrame(published, genericAck)) return 9;
    genericAck.runGeneration = 30;
    genericAck.generation = 41;
    if (OutRunVR::Core::ConsumerAckCoversFrame(published, genericAck)) return 10;
    genericAck.generation = 40;
    genericAck.slot = 1;
    if (OutRunVR::Core::ConsumerAckCoversFrame(published, genericAck)) return 11;
    genericAck.slot = 2;
    genericAck.completedFrameId = 99;
    if (OutRunVR::Core::ConsumerAckCoversFrame(published, genericAck)) return 12;
    genericAck.completedFrameId = 101;
    if (!OutRunVR::Core::ConsumerAckCoversFrame(published, genericAck)) return 13;

    return 0;
}
