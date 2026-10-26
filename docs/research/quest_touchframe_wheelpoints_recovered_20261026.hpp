// Quest APK hand-to-virtual-wheel source ABI, research-only (2026-10-26).
// Reviewed ELF instructions: XrRig::locate_hands 0x2D67CC,
// XrSessionHost::begin 0x2D9CEC..0x2D9CF8,
// run_game PadSnapshot callback 0x2E191C..0x2E1A2C.
// This is a read-only extractor; not a game/VR hook, not HMD validated.
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <cmath>
namespace quest_research {

struct WheelHandInput {
    std::array<std::array<float,3>,2> points{};
    std::array<std::uint8_t,2> valid{};
    std::array<float,2> grip{};
};

inline bool ExtractWheelHandInput(const void* touchFrame,
                                  std::size_t touchFrameBytes,
                                  WheelHandInput& destination) noexcept {
    // Native TouchFrame pose[0] begins at +0x3C, pose[1] at +0x58.
    // Each 28-byte XrPosef = quaternion[4] followed by position[3].
    // The last float read for two grip channels is at +0x7C.
    if (!touchFrame || touchFrameBytes < 0x80u) return false;
    const auto* const bytes = static_cast<const std::uint8_t*>(touchFrame);
    WheelHandInput temp{};
    std::memcpy(temp.points[0].data(), bytes+0x4Cu, 3u*sizeof(float));
    std::memcpy(temp.points[1].data(), bytes+0x68u, 3u*sizeof(float));
    std::memcpy(temp.valid.data(), bytes+0x74u, 2u);
    std::memcpy(temp.grip.data(), bytes+0x78u, 2u*sizeof(float));
    for (std::size_t hand=0; hand<2u; ++hand) {
        if (temp.valid[hand] != 0u) {
            for (float v : temp.points[hand])
                if (!std::isfinite(v)) return false;
        }
        if (!std::isfinite(temp.grip[hand])) return false;
    }
    destination=temp;
    return true;
}
// Use only with a latched frame that has valid XR head+eye tracking. The native
// XrSessionHost::begin skips locate_hands if xrLocateViews failed; the exact
// behavior of its preceding frame field copies during tracking loss still
// requires proof. Do NOT feed cached TouchFrame points to a fresh frame.
// The guest pad path also gates wheel behavior on game state/mode-1.
// Raw VirtualWheel::update uses sincosf, atan2f, hypotf and remainderf,
// with 0.13/0.30 distance hysteresis, grip gate 0.65, angle gates 0.10/0.25,
// max frame delta 0.5 rad and steering clamp +/-1.308997 rad.
static_assert(0x4Cu+3u*sizeof(float)==0x58u);
static_assert(0x68u+3u*sizeof(float)==0x74u);
static_assert(0x78u+2u*sizeof(float)==0x80u);
} // namespace quest_research
