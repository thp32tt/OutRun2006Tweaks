#include "../src/runtime/direct_ring_skip_ack.hpp"
#include <cassert>
#include <cstdint>
using namespace OutRunVrDirectRingSkipAck;
constexpr auto wrapBefore = [](std::uint32_t a, std::uint32_t b) noexcept {
    return a != b && static_cast<std::int32_t>(a - b) < 0;
};
int main()
{
    const FrameIdentity chosen{2, 8, 40, 900};
    assert(CanAcknowledge({0xffffffffu, 8, 40, 900}, chosen,
        0xfffffffeu, wrapBefore));
    assert(!CanAcknowledge({3, 8, 40, 900}, chosen, 0, wrapBefore));
    assert(!CanAcknowledge({0xffffffffu, 8, 39, 900}, chosen,
        0xfffffffeu, wrapBefore));
    assert(!CanAcknowledge({0xffffffffu, 8, 40, 901}, chosen,
        0xfffffffeu, wrapBefore));
    assert(!CanAcknowledge({0xffffffffu, 8, 40, 900}, chosen,
        0xffffffffu, wrapBefore));
}
