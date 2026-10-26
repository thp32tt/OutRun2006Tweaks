// Research-only clean-room ABI view of the hand entry decision tables in the
// user-owned OutRun Quest AArch64 binary. Not linked into PC game/runtime.
// ELF tables: 0x1AD558 (A), 0x1AD4A4 (B); two sets of 15 records, 12 bytes each.
// Source evidence: Draw::disp_514c30 (0xD61D58..0xD61DA8) and
// HandEntry::operator() (0xD62DD0..0xD62ED0).
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
namespace quest_research {
struct HandEntryRecord {
    bool requiresGuestResolve = false; // original byte at +0
    std::uint32_t target0 = 0;          // original dword at +4
    std::uint32_t target1 = 0;          // original dword at +8
};
// The native byte-layout record has an explicit padding gap.
struct HandEntryWire {
    std::uint8_t requiresGuestResolve;
    std::uint8_t padding[3];
    std::uint32_t target0;
    std::uint32_t target1;
};
static_assert(sizeof(HandEntryWire) == 12);
static_assert(offsetof(HandEntryWire, target0) == 4);
static_assert(offsetof(HandEntryWire, target1) == 8);
// These 30 numeric records are transcribed from two verified original ELF
// read-only table windows; A/B represent call order, not proven left/right.
inline constexpr std::array<HandEntryRecord, 15> kHandEntriesA = {{
    /* guest index 5 */ { false, 0x00C40020u, 0x00C40022u },
    /* guest index 6 */ { false, 0x00CA0021u, 0x00CA0023u },
    /* guest index 7 */ { true , 0x005E650Cu, 0x005E64FCu },
    /* guest index 8 */ { true , 0x005E64E8u, 0x005E64D4u },
    /* guest index 9 */ { false, 0x00BF001Bu, 0x00BF001Du },
    /* guest index 10 */ { true , 0x005E652Cu, 0x005E651Cu },
    /* guest index 11 */ { false, 0x00BE0016u, 0x00BE0018u },
    /* guest index 12 */ { true , 0x005E654Cu, 0x005E653Cu },
    /* guest index 13 */ { false, 0xFFFFFFFFu, 0xFFFFFFFFu },
    /* guest index 14 */ { false, 0xFFFFFFFFu, 0xFFFFFFFFu },
    /* guest index 15 */ { false, 0xFFFFFFFFu, 0xFFFFFFFFu },
    /* guest index 16 */ { false, 0xFFFFFFFFu, 0xFFFFFFFFu },
    /* guest index 17 */ { false, 0x01EB0017u, 0x01EB0019u },
    /* guest index 18 */ { false, 0x01EC001Eu, 0x01EC0020u },
    /* guest index 19 */ { false, 0x01ED001Eu, 0x01ED001Fu },
}};
inline constexpr std::array<HandEntryRecord, 15> kHandEntriesB = {{
    /* guest index 5 */ { false, 0x00C4001Fu, 0x00C40021u },
    /* guest index 6 */ { false, 0x00CA0020u, 0x00CA0022u },
    /* guest index 7 */ { true , 0x005E6614u, 0x005E6604u },
    /* guest index 8 */ { true , 0x005E65F0u, 0x005E65DCu },
    /* guest index 9 */ { false, 0x00BF001Au, 0x00BF001Cu },
    /* guest index 10 */ { true , 0x005E6634u, 0x005E6624u },
    /* guest index 11 */ { false, 0x00BE0017u, 0x00BE0019u },
    /* guest index 12 */ { true , 0x005E6654u, 0x005E6644u },
    /* guest index 13 */ { false, 0xFFFFFFFFu, 0xFFFFFFFFu },
    /* guest index 14 */ { false, 0xFFFFFFFFu, 0xFFFFFFFFu },
    /* guest index 15 */ { false, 0xFFFFFFFFu, 0xFFFFFFFFu },
    /* guest index 16 */ { false, 0xFFFFFFFFu, 0xFFFFFFFFu },
    /* guest index 17 */ { false, 0x01EB0018u, 0x01EB001Au },
    /* guest index 18 */ { false, 0x01EC001Fu, 0x01EC0021u },
    /* guest index 19 */ { false, 0x01ED001Cu, 0x01ED001Du },
}};
constexpr bool IsGuestHandEntryIndex(std::uint32_t guestValue) noexcept {
    return guestValue >= 5u && guestValue <= 19u;
}
constexpr const HandEntryRecord* GetHandEntry(
    bool selectTableB, std::uint32_t guestValue) noexcept {
    if (!IsGuestHandEntryIndex(guestValue)) return nullptr;
    return selectTableB ? &kHandEntriesB[guestValue - 5u]
                        : &kHandEntriesA[guestValue - 5u];
}
constexpr bool HasDirectTargets(const HandEntryRecord& e) noexcept {
    return !e.requiresGuestResolve &&
           e.target0 != 0xFFFFFFFFu && e.target1 != 0xFFFFFFFFu;
}
static_assert(kHandEntriesA[2].requiresGuestResolve);
static_assert(kHandEntriesB[3].requiresGuestResolve);
static_assert(!kHandEntriesA[8].requiresGuestResolve);
static_assert(GetHandEntry(false, 4u) == nullptr);
static_assert(GetHandEntry(true, 20u) == nullptr);
static_assert(GetHandEntry(false, 7u)->requiresGuestResolve);
static_assert(!HasDirectTargets(kHandEntriesA[8]));
// REA-recovered VirtualWheel state **prefix** (not full object size).
struct VirtualWheelStatePrefix {
    std::uint8_t grabbed[2];
    std::uint8_t reserved0[2];
    float steeringRadians;
    float previousAngle[2];
    std::uint8_t pendingGrab[2];
    std::uint8_t reserved1[2];
};
static_assert(offsetof(VirtualWheelStatePrefix, steeringRadians) == 4);
static_assert(offsetof(VirtualWheelStatePrefix, previousAngle) == 8);
static_assert(offsetof(VirtualWheelStatePrefix, pendingGrab) == 16);
// Numeric gates are float32 values observed in original VirtualWheel::update,
// with REA type propagation still partial.
inline constexpr float kGrabDistance = 0.13f;
inline constexpr float kReleaseDistance = 0.30f;
inline constexpr float kGripGate = 0.65f;
inline constexpr float kAngularEnter = 0.10f;
inline constexpr float kAngularRelease = 0.25f;
inline constexpr float kMaxFrameAngleDelta = 0.50f;
inline constexpr float kMaxSteeringRadians = 1.308997f;
// On failure/invalid tracking, let game stock input proceed; this header does
// not mutate the Wheel or native pointer/TLS, nor model skeleton data.
} // namespace quest_research
