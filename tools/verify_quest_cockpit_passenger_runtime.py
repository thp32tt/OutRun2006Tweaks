#!/usr/bin/env python3
"""Native camera-0 parity and removal static proof for cockpit passenger.

The game decides whether its original ROB02 exists, independently of camera.
No code may fabricate ROB02 or claim a GPU screenshot without HMD evidence.
Run without args for source checks or --exe PATH for canonical PC ABI proof.
"""
from pathlib import Path

hook = Path("src/hooks_graphics.cpp").read_text(encoding="utf-8")
settings = Path("src/vr/settings.cpp").read_text(encoding="utf-8")
overlay = Path("src/overlay/settings_ui.cpp").read_text(encoding="utf-8")
ini = Path("OutRun2006Tweaks.ini").read_text(encoding="utf-8")
policy = Path("src/vr/game/quest_cockpit_v2_passenger_event.hpp").read_text(
    encoding="utf-8"
)
plugin = Path("src/plugin.hpp").read_text(encoding="utf-8")
owner = hook.split("ExactOriginalCockpitOccupant(EvWorkRobot* robot) noexcept {", 1)[1]
owner = owner.split("static bool OriginalRobotDrawSignature()", 1)[0]
render = hook.split("static void __cdecl RobotDisplay(EvWorkRobot* robot)", 1)[1]
render = render.split("static void PlayerState(SafetyHookContext& ctx)", 1)[0]

# The native game, not the mod, creates ROB02 at stage 60 when required.
assert "class QuestCockpitV2PassengerStartEvent final : public Hook" not in hook
assert "ShouldOpenMissingPassenger(" not in hook + policy
assert "SetupHook.ccall<void>(\n                    OriginalPassengerEventId" not in hook
assert "OriginalEventFlagsRva=0x39fb48u;" in policy
assert "OriginalPassengerEventId=0x16bu;" in policy
assert "OriginalEventLiveForDisplay(std::uint8_t flags)" in policy
assert "OriginalEventLiveForDisplay(eventFlags[OriginalDriverEventId])" in owner
assert "OriginalEventLiveForDisplay(eventFlags[OriginalPassengerEventId])" in owner
assert "Module::exe_ptr<std::uint8_t>(OriginalEventFlagsRva)" in owner

# The REMOVE gate precedes camera!=1 and native-frame early returns:
# exact live ROB02 disappears from camera 0 AND cockpit, without touching
# driver, unrelated NPC, original event setup, animation or work pointers.
assert "const auto slot=ExactOriginalCockpitOccupant(robot);" in render
assert "ShouldSuppressOriginalPassenger(" in render
assert "slot==OriginalOccupantSlot::Passenger363" in render
assert render.index("ShouldSuppressOriginalPassenger(") < render.index(
    "if(!NativeFrameTrace().Active() || InSceneEffect())"
)
assert render.index("ShouldSuppressOriginalPassenger(") < render.index(
    "camera->cam_mode_34A!=1"
)
assert "return;" in render.split("ShouldSuppressOriginalPassenger(", 1)[1].split(
    "if(!NativeFrameTrace().Active()", 1
)[0]
assert "RobotHook.ccall<void>(robot);" in render
assert "SelectCockpitOccupantRender(" in render
assert "ScopedOriginalOccupantLod0 passengerVisible(passengerLod0);" in render

# One persistent bool drives two checkboxes; complement guarantees exactly
# one selected even when an existing user INI supplies the older key.
assert 'VRQuestCockpitV2PassengerVisible{ "VR", "QuestCockpitV2PassengerVisible", true,' in settings
assert "QuestCockpitV2PassengerVisible = true" in ini
assert "VRQuestCockpitV2PassengerVisible.hidden(true);" in overlay
assert 'ImGui::Checkbox("Passenger: Follow Camera 0",&follow)' in overlay
assert 'ImGui::Checkbox("Passenger: Remove",&remove)' in overlay
assert "bool remove=!Settings::VRQuestCockpitV2PassengerVisible.get();" in overlay
assert "Settings::VRQuestCockpitV2PassengerVisible=follow;" in overlay
assert "Settings::VRQuestCockpitV2PassengerVisible=!remove;" in overlay
assert overlay.count("queue_setting_change(&Settings::VRQuestCockpitV2PassengerVisible)") == 2
assert "VRQuestCockpitV2PassengerVisible;" in plugin
assert "flush_settings();" in overlay
assert 'matches_search("Remove Passenger",search)' in overlay

print("PASS: native camera-0 ROB02 parity, both-view removal, F11 exclusive mode")

# Actual game entrypoint 0x440110 reads 0x79FB48[eventId], cdecl, and its
# callbacks are identified by the exact original native table. It is not
# hooked by this mode; this constant exists solely for binary contract QA.
signature=bytes.fromhex(
    "8b5424048a8a48fb790080e1e78bc280c9016bc03c888a48fb7900"
)

if __name__ == "__main__":
    import hashlib
    import struct
    import sys

    if len(sys.argv) not in (1, 3) or (
        len(sys.argv) == 3 and sys.argv[1] != "--exe"
    ):
        raise SystemExit("usage: verify_quest_cockpit_passenger_runtime.py [--exe PATH]")

    if len(sys.argv) == 3:
        binary = Path(sys.argv[2]).read_bytes()
        expected_sha = (
            "68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3"
        )
        assert hashlib.sha256(binary).hexdigest() == expected_sha, (
            "unexpected original EXE identity"
        )
        def u16(at):
            return struct.unpack_from("<H", binary, at)[0]
        def u32(at):
            return struct.unpack_from("<I", binary, at)[0]

        pe = u32(0x3C)
        assert binary[0:2] == b"MZ" and binary[pe:pe + 4] == bytes.fromhex("50450000")
        nsections = u16(pe + 6)
        optional = pe + 24
        assert u16(optional) == 0x10B, "expected 32-bit original"
        image_base = u32(optional + 28)
        assert image_base == 0x400000
        first_section = optional + u16(pe + 20)
        sections = []
        for i in range(nsections):
            h = first_section + i * 40
            sections.append((u32(h + 12), u32(h + 16), u32(h + 20)))

        def at_va(va, count):
            rva = va - image_base
            for start, raw_size, raw_offset in sections:
                if start <= rva and rva + count <= start + raw_size:
                    at = raw_offset + rva - start
                    assert at + count <= len(binary)
                    return binary[at:at + count]
            raise AssertionError(f"unmapped native address {va:#x}")

        # Every literal below was cross-read from the canonical PC EXE:
        # event flags at 0x79FB48 + eventId, work at 0x799B30 + id*0x3C,
        # original 0x440110 cdecl function and 20-byte callback table.
        assert at_va(0x440110, len(signature)) == signature
        assert at_va(0x440110 + 102, 1) == bytes.fromhex("c3"), "event_setup is not cdecl"
        assert at_va(0x440110 + 4, 6) == bytes.fromhex("8a8a48fb7900")
        assert at_va(0x440110 + 21, 6) == bytes.fromhex("888a48fb7900")
        assert at_va(0x4879B0, 4) == bytes.fromhex("a1189d79")
        def original_callbacks(function_id):
            return struct.unpack("<5I", at_va(0x59BE78 + function_id * 20, 20))
        assert original_callbacks(0x37) == (
            0x4884D0, 0x488DD0, 0x4879B0, 0, 0x487980
        )
        assert original_callbacks(0x39) == (
            0x4885A0, 0x489A90, 0x4879B0, 0, 0x487980
        )
        assert original_callbacks(0x3B) == (
            0x488710, 0x488820, 0x4879D0, 0, 0x487A00
        )
        print("PASS: canonical PE32 machine-code event flags, cdecl, callbacks, SHA")
