// Quest VR VirtualWheel steering conversion, research-only clean-room reference.
// User-owned Quest APK: VirtualWheel::update @ ELF 0x2E1E18;
// run_game PadSnapshot callback: 0x2E1A2C (update) and 0x2E1A34..0x2E1A84
// (on update success, wheel.angle -> signed 16-bit-compatible game steer).
// THIS HEADER IS NOT PART OF THE RUNTIME BUILD. NO INPUT HOOK OR DEVICE WRITE.
// REA 6.5.0 + Ghidra 12.1.4 evidence:
// ev_baa70ecce97e329628fc78178effec1da63c7ec44e44882ec8cf86d8f77c9868
#pragma once
#include <cmath>
#include <cstdint>
#include <optional>

namespace quest_cockpit_research {

inline constexpr float kVirtualWheelFullLockRad = 1.3089970350265503f;
inline constexpr float kQuestGameSteerRange = 32767.0f;

// The native code uses:
///  0x2E1A3C: wheel angle (VirtualWheel+0x04)
///  0x2E1A5C: fdiv angle / -1.308997035f
///  0x2E1A68..78: clamp to +/- 1 and scale to +/-32767
///  0x2E1A80: fcvtzs (truncate toward zero)
///  0x2E1A84: write PadSnapshot +0x20
// No value is emitted when VirtualWheel::update returned false.
// In the PCVR port, an empty result must leave the existing MOZA R3 or
// other physical-wheel steering axis intact, not force steering to center.
inline std::optional<std::int32_t> GuestSteerFromVirtualWheel(
    const bool virtualWheelUpdated,
    const float wheelAngleRad) noexcept {
    if (!virtualWheelUpdated || !std::isfinite(wheelAngleRad))
        return std::nullopt;

    const float steering = wheelAngleRad / -kVirtualWheelFullLockRad;
    const float clamped = steering > 1.0f ? 1.0f :
                          steering < -1.0f ? -1.0f : steering;
    return static_cast<std::int32_t>(clamped * kQuestGameSteerRange);
}

// The XR input frame uses one layout (TouchFrame+0x74/+0x75 validity).
// Its rendering hand scope is a distinct object, with 0/1 hand slots:
//   trackingCtx+0x100, trackingCtx+0x101
// The 5th argument to Quest Draw::hand_513e40 is explicitly 0 and 1
// respectively at original ELF 0xD61E3C and 0xD61E60.
// These are offset contracts for research/diagnostics; not definitions of
// complete XrSessionHost or guest character memory structures.
inline constexpr std::uint32_t kTouchFrameLeftValidOffset = 0x74u;
inline constexpr std::uint32_t kTouchFrameRightValidOffset = 0x75u;
inline constexpr std::uint32_t kHandRenderLeftValidOffset = 0x100u;
inline constexpr std::uint32_t kHandRenderRightValidOffset = 0x101u;

// Tentative native VirtualWheel per-hand state layout, from original
// opcode loads/stores. Caller still needs validated XR hand points.
// The two hands are processed independently; tracking failure is NOT a
// reason to apply previously cached pose in another Present epoch.
struct VirtualWheelResearchState {
    bool handActive[2]{};
    float steeringAngle = 0.f;  // VirtualWheel+0x04
    float lastHandAngles[2]{};   // VirtualWheel+0x08/+0x0C
    bool handArming[2]{};        // VirtualWheel+0x10/+0x11
};

} // namespace quest_cockpit_research
