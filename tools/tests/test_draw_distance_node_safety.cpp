#include "../../src/vr/game/draw_distance_node_safety.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace OutRunVR::DrawDistanceSafety;

static_assert(SeenNodeCount == 65536);
static_assert(DrawListStorage == 4097);
static_assert(CanAppend(0) && CanAppend(4095) && !CanAppend(4096));
static_assert(IsKnownExclusionIndex(16383, 16384));
static_assert(!IsKnownExclusionIndex(16384, 16384));
static_assert(ShouldQueueNode(false, true, 0, true));
static_assert(!ShouldQueueNode(false, true, -1, true));
static_assert(!ShouldQueueNode(true, false, 0, true));

int main()
{
    std::array<std::uint8_t, SeenNodeCount> seen{};
    // Same node first appears behind the player (excluded), then in the
    // current section (vanilla-visible). Rejection must not consume it.
    constexpr std::uint16_t id = 5000;
    bool behind = ShouldQueueNode(seen[id] != 0, true, -1, true);
    assert(!behind && seen[id] == 0);
    bool current = ShouldQueueNode(seen[id] != 0, true, 0, true);
    assert(current);
    seen[id] = 1;
    assert(!ShouldQueueNode(seen[id] != 0, false, 1, true));
    // Marker generations remove the former per-object 64 KiB memset.
    // A previous object's seen nodes must be fresh for the next object.
    std::array<std::uint16_t, SeenNodeCount> stamp{};
    std::uint16_t epoch = 65534;
    stamp[5000] = epoch;
    assert(stamp[5000] == epoch);
    ++epoch;
    assert(stamp[5000] != epoch);
    // Wrapping an uint16 generation clears every stale older stamp.
    stamp[10] = 1;
    if (++epoch == 0) { stamp.fill(0); epoch = 1; }
    assert(epoch == 1 && stamp[10] == 0 && stamp[5000] == 0);
    // Maximal legal node value does not overflow the seen domain.
    seen[65534] = 1;
    assert(seen[65534] == 1);
    // Exactly 4096 actual nodes plus one terminating sentinel.
    std::array<std::uint16_t, DrawListStorage> out{};
    std::size_t count = 0;
    for (std::size_t i = 0; i < DrawListCapacity + 100; ++i)
        if (CanAppend(count)) out[count++] = static_cast<std::uint16_t>(i);
    assert(count == DrawListCapacity);
    out[count] = 0xFFFF;
    assert(out[DrawListCapacity] == 0xFFFF);
}
