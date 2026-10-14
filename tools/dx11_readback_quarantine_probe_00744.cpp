#include "../src/vr/d3d11/native_game_frame_publication.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;

// For real game menu/car/race Draw->D3D11 CopyResource->fenced readback,
// ONLY exact EVENT completion can make the staging allocation reusable.
constexpr bool readback_quarantine_contract() {
    constexpr auto classify = GameNativeFramePublication::classify_fence;
    if (classify(0) != GameNativeReadbackFence::Complete ||
        classify(1) != GameNativeReadbackFence::Pending ||
        classify(-1) != GameNativeReadbackFence::Failed ||
        classify(static_cast<std::int32_t>(0x887a0005u)) !=
            GameNativeReadbackFence::Failed ||
        classify(2) != GameNativeReadbackFence::Failed)
        return false;
    // A broken native fence must not be treated as a free staging resource,
    // even when the next valid game frame could otherwise select its slot.
    constexpr std::uint32_t errorSlot = 1u;
    const std::uint32_t occupiedMask = (1u << errorSlot);
    return GameNativeFramePublication::select_available_slot(
                occupiedMask, 3u, errorSlot) == 2u &&
           GameNativeFramePublication::select_available_slot(
                0b111u, 3u, errorSlot) == 3u &&
           !GameNativeFramePublication::should_upload(
                true, false, true, 0u);
}
static_assert(readback_quarantine_contract(),
              "DX11 native frame GPU-fence failure must quarantine staging");
int main() { assert(readback_quarantine_contract()); return 0; }
