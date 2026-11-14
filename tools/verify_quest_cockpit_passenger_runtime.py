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
assert "OriginalEventScheduled(eventFlags[OriginalPassengerEventId])" in start
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
