#!/usr/bin/env python3
"""Ten independent static call-path reviews for the Quest cockpit passenger.

Unlike re-running the same SHA ten times, these are ten different invariants
from original event provenance through x86 callback, camera 0, cockpit-only
suppression, goal transitions, nested rendering, LOD, settings, and packaging.
They are source-level checks, NOT evidence of Quest 3/VDXR GPU visibility.
"""
from pathlib import Path


def source(path):
    return Path(path).read_text(encoding="utf-8")


hook = source("src/hooks_graphics.cpp")
policy = source("src/vr/game/quest_cockpit_v2_passenger_event.hpp")
occupant = source("src/vr/game/quest_cockpit_v2_occupant.hpp")
visibility = source("src/vr/game/quest_cockpit_v2_visibility.hpp")
settings = source("src/vr/settings.cpp")
ui = source("src/overlay/settings_ui.cpp")
setting_io = source("src/settings.cpp")
launcher = source("tools/Run-OutRunVRTest.ps1")
ini = source("OutRun2006Tweaks.ini")
core_ci = source(".github/workflows/quest-cockpit-v2-core.yml")
package_ci = source(".github/workflows/vr-github-general-build.yml")

owner = hook.split("ExactOriginalCockpitOccupant(EvWorkRobot* robot) noexcept {", 1)[1]
owner = owner.split("static bool OriginalRobotDrawSignature()", 1)[0]
render = hook.split("static void __cdecl RobotDisplay(EvWorkRobot* robot)", 1)[1]
render = render.split("static void PlayerState(SafetyHookContext& ctx)", 1)[0]
guard = "if(!camera || camera->cam_mode_34A!=1 || !Game::pl_car())"
gate = "ShouldSuppressOriginalPassenger("
recursion = "if(OriginalRobotCorrectionActive()) {"
native_frame = "if(!NativeFrameTrace().Active() || InSceneEffect())"

passed = []


def verify(name, *conditions):
    assert all(conditions), f"FAIL [{len(passed) + 1}/10]: {name}"
    passed.append(name)
    print(f"PASS [{len(passed):02d}/10]: {name}")


# 1. Unmodified native 440110 event table: no forced passenger creation.
verify("native ROB02 event ID/flags; no synthetic event",
       "OriginalPassengerEventId=0x16bu;" in policy,
       "OriginalEventFlagsRva=0x39fb48u;" in policy,
       "class QuestCockpitV2PassengerStartEvent" not in hook,
       "ShouldOpenMissingPassenger(" not in hook + policy)

# 2. A live event requires initialized native flags and no destroy pending.
verify("original event lifecycle excludes stale and destroy-pending work",
       "OriginalEventLiveForDisplay(std::uint8_t flags)" in policy,
       "(flags & OriginalEventInitialized)!=0u" in policy,
       "(flags & 0x04u)==0u" in policy,
       "OriginalEventLiveForDisplay(eventFlags[OriginalDriverEventId])" in owner,
       "OriginalEventLiveForDisplay(eventFlags[OriginalPassengerEventId])" in owner)

# 3. Ownership uses callback and work pointer, never a guessed character.
verify("exact ROB01/ROB02 callback + robot work identity",
       "Game::event(EVENT_ROB01)" in owner,
       "Game::event(EVENT_ROB02)" in owner,
       "driver->EventFunc.Disp==expected" in owner,
       "passenger->EventFunc.Disp==expected" in owner,
       "ResolveOriginalCockpitWork(" in owner,
       "if(driver==passenger)return OriginalOccupantSlot::None;" in occupant)

# 4. Camera 0 exits BEFORE probing passenger tokens or making a decision.
prefix = render.split(gate, 1)[0]
camera_exit = render.split(gate, 1)[1].split(gate + "UNREACHABLE", 1)[0]
verify("camera 0 always forwards unmodified original callback",
       guard in render,
       render.index(guard) < render.index("const auto slot=ExactOriginalCockpitOccupant(robot);"),
       render.index(guard) < render.index(gate),
       "RobotHook.ccall<void>(robot);" in camera_exit.split("const auto slot=", 1)[0],
       gate not in prefix)

# 5. Remove acts only on native mode 1 + exact original ROB02.
gate_args = render.split(gate, 1)[1].split("))", 1)[0]
verify("mode-1-only remove; driver and traffic cannot match",
       "camera->cam_mode_34A==1" in gate_args,
       "slot==OriginalOccupantSlot::Passenger363" in gate_args,
       "nativeCameraModeOne && exactLivePassenger" in policy,
       "!followCamera0" in policy,
       "return;" in render.split(gate, 1)[1].split(recursion, 1)[0])

# 6. Stage-goal and effect renders must not be suppressed by cockpit choice.
racing = render.split("const bool racing=", 1)[1].split("// STATE_GOAL", 1)[0]
verify("STATE_GOAL and scene effects preserve original passenger",
       "STATE_GAME" in racing,
       "STATE_START" in racing,
       "game_start_progress_code==65" in racing,
       "STATE_GOAL" not in racing,
       "racing && !InSceneEffect()" in gate_args)

# 7. A nested ROB02 inside the W*C correction still obeys Remove.
verify("nested ROB02 evaluated before recursion fast-path",
       render.index(gate) < render.index(recursion),
       render.index(recursion) < render.index(native_frame),
       "RobotHook.ccall<void>(robot);" in render.split(recursion, 1)[1].split(native_frame, 1)[0],
       render.index(guard) < render.index(recursion))

# 8. Original driver hiding is independent and NPCs retain original draw.
verify("driver and NPC callback are independent of passenger remove",
       "SelectCockpitOccupantRender(" in render,
       "if(action==CockpitOccupantRender::SuppressDriver)return;" in render,
       "if(slot==OriginalOccupantSlot::Driver362&&hideDriver)" in occupant,
       "if(slot==OriginalOccupantSlot::Passenger363&&keepPassenger)" in occupant,
       "if(currentWork==0)return OriginalOccupantSlot::None;" in occupant,
       "if(driver==passenger)return OriginalOccupantSlot::None;" in occupant)

# 9. Passenger follow uses scoped LOD0 and W*C restoration, never mutates event.
verify("native passenger LOD0 and W*C scoped restore",
       "ScopedOriginalOccupantLod0 passengerVisible(passengerLod0);" in render,
       "action==CockpitOccupantRender::OriginalPassengerForceVisible" in render,
       "ScopedOriginalRobotWorkMatrix scoped(" in render,
       "RobotHook.ccall<void>(robot);" in render,
       "~ScopedOriginalRobotWorkMatrix() noexcept" in occupant,
       "std::memcpy(target_,original_.data(),sizeof(Matrix));" in occupant,
       "if(active_)--ActiveOriginalOccupantLod0;" in visibility)

# 10. Exclusive F11 controls persist, launchers do not override, CI ships ZIP.
verify("two F11 controls, one saved bool, no launcher override, ZIP CI",
       'ImGui::Checkbox("Passenger: Follow Camera 0",&follow)' in ui,
       'ImGui::Checkbox("Passenger: Remove",&remove)' in ui,
       "bool remove=!Settings::VRQuestCockpitV2PassengerVisible.get();" in ui,
       "Settings::VRQuestCockpitV2PassengerVisible=!remove;" in ui,
       ui.count("queue_setting_change(&Settings::VRQuestCockpitV2PassengerVisible)") == 2,
       "QuestCockpitV2PassengerVisible = true" in ini,
       "VRQuestCockpitV2PassengerVisible" in settings,
       "commandLineOverrides.find(setting) == commandLineOverrides.end()" in setting_io,
       "QuestCockpitV2PassengerVisible" not in launcher,
       "python3 tools/verify_quest_cockpit_passenger_runtime.py" in core_ci,
       "tools/verify_quest_cockpit_passenger_ten_paths.py" in core_ci,
       "src/hooks_graphics.cpp" in package_ci,
       "Upload test ZIP" in package_ci)

assert len(passed) == 10
print("PASS: ten distinct, exact-source passenger call-path audits; headset runtime UNTESTED")
