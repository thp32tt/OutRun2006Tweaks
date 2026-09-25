#include "vr/ipc/direct_ack_r13.hpp"

#include <cstdint>

int main()
{
    using namespace OutRunVR::R13;
    static_assert(DirectGpuAckVersion == 2);
    static_assert(sizeof(DirectGpuAckState) == 48);

    DirectGpuAckState ack{};
    ack.hostPid = 10;
    ack.clientPid = 20;
    ack.runGeneration = 30;
    ack.transportGeneration = 40;

    if (ack.version != 2) return 1;
    if (!DirectGpuAckIdentityMatches(ack, 10, 20, 30, 40)) return 7;
    if (DirectGpuAckIdentityMatches(ack, 11, 20, 30, 40)) return 2;
    if (DirectGpuAckIdentityMatches(ack, 10, 21, 30, 40)) return 3;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 31, 40)) return 4;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 30, 41)) return 5;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 0, 40)) return 6;
    return 0;
}
