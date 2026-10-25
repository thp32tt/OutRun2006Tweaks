// Quest APK cockpit camera override and driver-hand admission, clean-room reference.
// Research only; NOT hooked into the game and NOT compiled or HMD validated.
// Native Quest functions: run_game::$_5 @ ELF 0x2E3664 (124 bytes);
//                      run_game::$_0 @ ELF 0x2E315C (656 bytes).
// REA 6.5.0/Ghidra 12.1.4 Evidence:
//  ev_58ae0041f7fb011b01bcd072aa0644918c67053ef02bbe3bc87a12c0d0a9a857
//  ev_6aed23e5e809b20dc867d1d209ed5fb1980820be203573c9ddc1510aba6889d8
// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace quest_cockpit_research {

struct CameraInputOverridePrefix {
    std::uint8_t enabled = 0;
    std::uint8_t alignment_padding[3] = {};
    float xyz[3] = {};
};

static_assert(std::is_standard_layout_v<CameraInputOverridePrefix>);
static_assert(offsetof(CameraInputOverridePrefix, enabled) == 0x00);
static_assert(offsetof(CameraInputOverridePrefix, xyz) == 0x04);
static_assert(sizeof(CameraInputOverridePrefix) == 16);

// Mirrors the checked arm64 conditions AFTER an existing upstream camera-input
// callback succeeded. The native source obtains toggle/state/xyz through
// captured pointers. These arguments are plain values to avoid touching game
// or NativeRuntimeContext memory.
constexpr bool QuestCameraOverrideEnabled(bool questToggle,
                                          std::uint32_t guestGameState) noexcept {
    return questToggle && guestGameState == 0x10u;
}

// Exact narrow write contract for run_game::$_5: a failed upstream callback
// does not write the override prefix; on success it stores the mode flag and
// copies three float values to offsets +4, +8, +12 regardless of flag value.
// This does NOT imply the override is active in normal gameplay.
inline bool ApplyQuestCameraOverrideAfterUpstream(
    bool upstreamSucceeded, bool questToggle,
    std::uint32_t guestGameState,
    const float (&xyz)[3],
    CameraInputOverridePrefix& input) noexcept {
    if (!upstreamSucceeded) return false;
    input.enabled = QuestCameraOverrideEnabled(questToggle, guestGameState) ? 1u : 0u;
    input.xyz[0] = xyz[0];
    input.xyz[1] = xyz[1];
    input.xyz[2] = xyz[2];
    return true;
}

// Driver animation dispatch admission observed at native 0x2E3198..0x2E31E0.
// This is one necessary predicate, not a complete hand rendering decision.
// Guest callback 0x4879B0 is a display callback ID, not a host code address.
constexpr bool IsQuestCockpitDriverDispatch(
    bool guestReady, std::uint32_t guestModeFlags,
    std::uint32_t displayCallbackId,
    std::uint8_t gameCameraMode) noexcept {
    return guestReady && ((guestModeFlags | 2u) == 0x12u) &&
           displayCallbackId == 0x4879B0u && gameCameraMode == 1u;
}

// The native run_game callback temporarily installs an object pointer into
// cockpit_hand_tracking TLS. Draw::hand_513e40 later checks an entry validity
// byte at trackingPtr + 0x100 + handSlot. This is NOT the layout of
// TouchFrame (+0x74/+0x75). No live pointer dereference occurs in this file.
constexpr std::size_t QuestHandValidityOffset(std::size_t handSlot) noexcept {
    return 0x100u + handSlot;
}

static_assert(QuestCameraOverrideEnabled(true, 0x10u));
static_assert(!QuestCameraOverrideEnabled(true, 0x12u));
static_assert(!QuestCameraOverrideEnabled(false, 0x10u));
static_assert(IsQuestCockpitDriverDispatch(true, 0x10u, 0x4879B0u, 1u));
static_assert(IsQuestCockpitDriverDispatch(true, 0x12u, 0x4879B0u, 1u));
static_assert(!IsQuestCockpitDriverDispatch(true, 0x14u, 0x4879B0u, 1u));
static_assert(!IsQuestCockpitDriverDispatch(true, 0x10u, 0x4879B0u, 2u));
static_assert(QuestHandValidityOffset(0u) == 0x100u);
static_assert(QuestHandValidityOffset(1u) == 0x101u);

} // namespace quest_cockpit_research
