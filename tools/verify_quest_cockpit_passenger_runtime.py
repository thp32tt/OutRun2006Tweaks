#!/usr/bin/env python3
"""Source-level passenger event lifecycle checks for the Quest cockpit test branch.

Complements (does not replace) the C++ pure-gate tests and the real Quest 3
runtime test. No claim about GPU visibility can be inferred from source alone.
"""
from pathlib import Path
import re

hook = Path("src/hooks_graphics.cpp").read_text(encoding="utf-8")
settings = Path("src/vr/settings.cpp").read_text(encoding="utf-8")
overlay = Path("src/overlay/settings_ui.cpp").read_text(encoding="utf-8")
ini = Path("OutRun2006Tweaks.ini").read_text(encoding="utf-8")
policy = Path("src/vr/game/quest_cockpit_v2_passenger_event.hpp").read_text(
    encoding="utf-8"
)
assert "class QuestCockpitV2PassengerStartEvent final : public Hook" in hook
start = hook.split("class QuestCockpitV2PassengerStartEvent final : public Hook", 1)[1]
start = start.split("class QuestCockpitV2PlayerCandidateProbe final : public Hook", 1)[0]
render = hook.split("static void __cdecl RobotDisplay(EvWorkRobot* robot)", 1)[1]
render = render.split("static void PlayerState(SafetyHookContext& ctx)", 1)[0]

# Source provenance: the original PC START successor is event 0x16C/0x3B;
# 0x16B/0x39 installs the game's original passenger callbacks.
assert "OriginalPassengerEventId=0x16bu;" in policy
assert "OriginalPassengerFunctionId=0x39u;" in policy
assert "OriginalStartAfterPassengerEventId=0x16cu;" in policy
assert "OriginalStartAfterPassengerFunctionId=0x3bu;" in policy
assert "static constexpr int EventSetupRva=0x40110" in start
assert "Settings::VRQuestCockpitV2PassengerVisible" in start
assert "*Game::current_mode==STATE_START" in start
assert "NativeOriginalHooksReady.load(std::memory_order_acquire)" in start
assert "driver->EventFunc.Disp==originalDisplay" in start
# Canonical game 440110 uses a *separate* flag array at VA 0x79FB48.
assert "OriginalEventFlagsRva=0x39fb48u;" in policy
assert "OriginalDriverEventId=0x16au;" in policy
assert "OriginalEventScheduled(eventFlags[OriginalDriverEventId])" in start
assert "OriginalPassengerVacant(" in start
assert "eventFlags[OriginalPassengerEventId]" in start
assert "passengerOccupied" in start
assert "OriginalLicenceSlotRva=0x3c2400u;" in policy
assert "OriginalPassengerCharacterIndexValid(*licenceSlot)" in start
assert "Module::exe_ptr<std::uint8_t>(OriginalEventFlagsRva)" in start
assert "field_0 &" not in start
assert "ShouldOpenMissingPassenger(" in start

# Only one conditional passenger setup, followed by the *unchanged* original
# requested setup. No extra work allocation, player-state mutation, or render
# redirection is allowed here.
request = "SetupHook.ccall<void>(\n                    OriginalPassengerEventId,OriginalPassengerFunctionId);"
forward = "SetupHook.ccall<void>(eventId,functionId);"
assert start.count("SetupHook.ccall<void>") == 2
assert request in start and forward in start
assert start.index(request) < start.index(forward)
# Verified 27-byte canonical EXE entry 0x440110 is __cdecl (C3 epilogue).
# The signature includes its separate flag-array read + write instructions.
sig_match = re.search(
    r"constexpr std::array<std::uint8_t,27> signature\{\{(.*?)\}\};",
    start, re.S
)
assert sig_match, "missing exact original event setup signature"
signature = bytes(int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{2})", sig_match.group(1)))
assert signature.hex() == "8b5424048a8a48fb790080e1e78bc280c9016bc03c888a48fb7900"
assert "VirtualQuery(entry,&info,sizeof(info))" in start
assert "!std::equal(signature.begin(),signature.end(),entry)" in start
assert 'return "VRQuestCockpitV2PassengerStartEvent";' in start
assert "auto setup=safetyhook::create_inline(entry,EventSetup);" in start
assert "SetupHook=std::move(setup);" in start
assert "const bool queued=eventFlags && passenger &&" in start
assert "OriginalEventSetupAccepted(" in start
assert "eventFlags[OriginalPassengerEventId]" in start
assert "passenger->EventFunc.Disp==originalDisplay" in start
assert "setup rejected" in start
assert "original ROB02/0x39 accepted" not in start or "if(queued)" in start

# Renderer must preserve driver hiding, exact ROB02 ownership, native LOD0,
# and the original fallback. The callback log is evidence of callback entry,
# explicitly not a claim of GPU visibility.
assert "ExactOriginalCockpitOccupant(robot)" in render
assert "if(action==CockpitOccupantRender::SuppressDriver)return;" in render
assert "slot==OriginalOccupantSlot::Passenger363" in render
assert "display callback observed" in render
assert "not proof" in render.lower() or "NOT proof" in render
assert "ScopedOriginalOccupantLod0 passengerVisible(passengerLod0);" in render
assert "RobotHook.ccall<void>(robot);" in render

# F11 must remain live, user-INI-persistent, and searchable by its displayed
# name. Default ON is only for configured cockpit; non-cockpit is original.
assert 'VRQuestCockpitV2PassengerVisible{ "VR", "QuestCockpitV2PassengerVisible", true,' in settings
assert "QuestCockpitV2PassengerVisible = true" in ini
assert 'matches_search("Passenger Always Visible", search)' in overlay
assert '? "Passenger Always Visible" : setting->key());' in overlay
assert "queue_setting_change(setting);" in overlay
assert "flush_settings();" in overlay
print("PASS: original ROB02 setup, hook ordering, postcondition, renderer, F11")

# Optional CI binary contract: Windows Build downloads the actual upstream
# replacement EXE and proves the addresses and callbacks above are native,
# not merely textual assumptions.
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
        assert binary[0:2] == b"MZ" and binary[pe:pe + 4] == b"PE\\0\\0"
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
        assert at_va(0x440110 + 102, 1) == b"\\xc3", "event_setup is not cdecl"
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
