#include "vr/ipc/protocol_v3.hpp"
#include "vr/ipc/win32_channel.hpp"

#include <cstddef>
#include <cstdint>

int main()
{
    using namespace OutRunVR::IpcV3;

    static_assert(ProtocolVersion == 3);
    static_assert(RingSize == 4);
    static_assert(sizeof(WireHandle) == 8);
    static_assert(sizeof(WireFov) == 16);
    static_assert(sizeof(WireEyeView) == 48);
    static_assert(sizeof(FrameRing) == 32 + sizeof(FrameDescriptor) * RingSize);

    HostState host{};
    ClientState client{};
    FrameRing frames{};
    AckState ack{};

    if (host.magic != HostMagic || client.magic != ClientMagic ||
        frames.magic != FrameMagic || ack.magic != AckMagic)
        return 1;

    // Verify the shared IPC primitive independently of the HostState reader:
    // a failed read must not publish stale or partially written caller data.
    struct Probe
    {
        volatile std::uint32_t sequence{};
        std::uint32_t value{};
    };
    Probe shared{};
    Probe observed{};
    shared.sequence = 2;
    shared.value = 0xABCD1234u;
    if (!OutRunVR::Ipc::StableRead(&shared, observed) ||
        observed.value != shared.value || observed.sequence != 2)
        return 2;

    shared.sequence = 3; // writer in progress, do not expose old value
    observed.value = 0xDEADBEEFu;
    if (OutRunVR::Ipc::StableRead(&shared, observed, 1) ||
        observed.value != 0 || observed.sequence != 0)
        return 3;

    shared.value = 0x01020304u;
    shared.sequence = 4; // writer completed, reader can recover
    if (!OutRunVR::Ipc::StableRead(&shared, observed) ||
        observed.value != shared.value || observed.sequence != 4)
        return 4;

    observed.value = 99;
    if (OutRunVR::Ipc::StableRead(static_cast<const Probe*>(nullptr), observed) ||
        observed.value != 0)
        return 5;
    observed.value = 99;
    if (OutRunVR::Ipc::StableRead(&shared, observed, 0) || observed.value != 0)
        return 6;
    return 0;
}
