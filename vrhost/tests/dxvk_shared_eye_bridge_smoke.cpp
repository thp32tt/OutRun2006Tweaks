#include <cstdint>
#include "vr/ipc/dxvk_shared_eye_bridge.hpp"

int main()
{
    using namespace OutRunVR::DxvkSharedEyeBridge;
    static_assert(OutRunVR::RenderFrameRingSize == 4);
    static_assert(Magic == 0x4258444Fu);
    static_assert(Version == 1);
    static_assert(DxgiB8G8R8A8Unorm == 87);
    static_assert(sizeof(Slot) == 16);
    static_assert(sizeof(State) == 136);
    State state{};
    state.magic = Magic;
    state.version = Version;
    state.structSize = sizeof(State);
    state.flags = HostAlive | ResourcesReady;
    state.generation = 7;
    state.width = 2064;
    state.height = 2208;
    state.format = DxgiB8G8R8A8Unorm;
    state.slots[3].leftHandle = 0xC0001234u;
    state.slots[3].rightHandle = 0xC0005678u;
    return state.magic == Magic && state.version == Version &&
        state.structSize == sizeof(State) &&
        (state.flags & ResourcesReady) != 0 &&
        state.slots[3].leftHandle != state.slots[3].rightHandle ? 0 : 1;
}
