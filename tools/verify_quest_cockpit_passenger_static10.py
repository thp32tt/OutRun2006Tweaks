#!/usr/bin/env python3
"""Ten DISTINCT static call-path audits for native cockpit passenger behavior.

They check source reachability and scoped invariants; they do not imply a
running game, observable pixels, HMD parity, or measured frame timing.
The separately compiled C++ smoke checks the actual constexpr policy.
"""
from pathlib import Path

def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

hook = read("src/hooks_graphics.cpp")
policy = read("src/vr/game/quest_cockpit_v2_passenger_event.hpp")
occupant = read("src/vr/game/quest_cockpit_v2_occupant.hpp")
setting = read("src/vr/settings.cpp")
ui = read("src/overlay/settings_ui.cpp")
plugin = read("src/plugin.hpp")
ini = read("OutRun2006Tweaks.ini")
source_test = read("tools/tests/quest_cockpit_v2_passenger_event_smoke.cpp")
core_ci = read(".github/workflows/quest-cockpit-v2-core.yml")
build_ci = read(".github/workflows/vr-github-general-build.yml")
release_ci = read(".github/workflows/build.yml")
robot = hook.split("static void __cdecl RobotDisplay(EvWorkRobot* robot)", 1)[1].split(
    "static void PlayerState(SafetyHookContext& ctx)", 1
)[0]
owner = hook.split("ExactOriginalCockpitOccupant(EvWorkRobot* robot) noexcept {", 1)[1].split(
    "static bool OriginalRobotDrawSignature()", 1
)[0]
active = hook.split("static bool QuestCockpitV2Active(", 1)[1].split(
    "static bool QuestCockpitV2CameraPose(", 1
)[0]
section_match = ui.split("bool section_matches(", 1)[1].split(
    "void draw_search_box()", 1
)[0]
ui_settings = ui.split("void render(bool overlayEnabled) override", 1)[1]

def check(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)

def check_order(subject: str, *parts: str):
    cursor = -1
    for part in parts:
        pos = subject.find(part, cursor + 1)
        check(pos >= 0, "missing/inverted control-flow anchor: " + part)
        cursor = pos

def pass_01_native_source():
    check("OriginalPassengerEventId=0x16bu;" in policy, "wrong native ROB02 slot")
    check("OriginalEventFlagsRva=0x39fb48u;" in policy, "wrong original flags")
    check("class QuestCockpitV2PassengerStartEvent" not in hook, "synthesis hook restored")
    check("ShouldOpenMissingPassenger(" not in hook + policy, "synthesized ROB02")
    check("SetupHook.ccall<void>(" not in hook, "unverified native event insertion")

def pass_02_live_owner_identity():
    for slot in ("Driver", "Passenger"):
        check(
            f"OriginalEventLiveForDisplay(eventFlags[Original{slot}EventId])" in owner,
            f"stale {slot} callback may be accepted",
        )
    check("passenger->EventFunc.Disp==expected" in owner, "missing callback identity")
    check("passenger->data<EvWorkRobot>()" in owner, "missing native work identity")
    check("(flags & (OriginalEventPendingInit|OriginalEventInitialized)) ==" in policy,
          "native event state must compare low two bits to 2")
    check("!OriginalEventLiveForDisplay(0x03u)" in source_test,
          "pending-init+active low-bit regression missing")
    check("ResolveOriginalCockpitWork(" in owner, "missing exact pointer join")
    check("if(driver==passenger)return OriginalOccupantSlot::None;" in occupant,
          "ambiguous player-token alias may reach suppression")

def pass_03_camera0_passthrough():
    guard="if(!camera || camera->cam_mode_34A!=1 || !Game::pl_car())"
    check_order(robot, guard, "RobotHook.ccall<void>(robot);",
                "const auto slot=ExactOriginalCockpitOccupant(robot);",
                "ShouldSuppressOriginalPassenger(")
    check("camera->cam_mode_34A==1" in robot.split(
        "ShouldSuppressOriginalPassenger(", 1
    )[1].split("))", 1)[0], "native camera proof not part of hide gate")
    check("!suppress(true,true,false,true,false,true)" in source_test,
          "camera-0 remove-negative C++ regression missing")

def pass_04_follow_requires_real_guest():
    check("SelectCockpitOccupantRender(" in robot, "missing original display selector")
    check("PassengerOtherCameraDraws.fetch_add(" in hook,
          "camera 2/30 were incorrectly counted as original camera 0")
    check("slot==OriginalOccupantSlot::Passenger363&&keepPassenger" in occupant,
          "follow no longer gated to native passenger")
    check("OriginalPassengerForceVisible" in occupant, "scoped LOD0 mode lost")
    check_order(robot,
                "if(action==CockpitOccupantRender::OriginalPassengerForceVisible)",
                "ScopedOriginalOccupantLod0 passengerVisible(true);",
                "VR PASSENGER NATIVE LOCK:",
                "RobotHook.ccall<void>(robot);")
    check(robot.index("ScopedOriginalOccupantLod0 passengerVisible(true);") <
          robot.index("if(OriginalRobotCorrectionActive())"),
          "passenger visibility still waits for driver W*C recursion gate")
    check(robot.index("ScopedOriginalOccupantLod0 passengerVisible(true);") <
          robot.index("if(!NativeFrameTrace().Active() || InSceneEffect())"),
          "passenger visibility still waits for native-frame/XR gate")
    check("if(!Settings::VRQuestCockpitV2OccupantCorrection)" in robot,
          "native fallback path missing")

def pass_05_remove_scope_and_non_passenger():
    check("activeRacingCockpit && nativeCameraModeOne && exactLivePassenger" in policy,
          "hide gate not scoped to actual cockpit passenger")
    check("slot==OriginalOccupantSlot::Passenger363" in robot, "guest token not checked")
    check("if(action==CockpitOccupantRender::SuppressDriver)return;" in robot,
          "driver hiding path missing")
    for negative in ("!suppress(true,true,false,true,true,false)",
                     "!suppress(false,true,false,true,true,true)",
                     "!suppress(true,false,false,true,true,true)"):
        check(negative in source_test, "missing non-passenger/off negative case "+negative)

def pass_06_goal_start_scene_boundaries():
    race_helper = hook.split("static bool IsCockpitRacePhase() noexcept",1)[1].split(
        "// Live Quest mode1 player glass hook",1
    )[0]
    check("STATE_GAME" in race_helper and "STATE_START" in race_helper,
          "race states changed")
    check("game_start_progress_code==65" in race_helper, "early START not gated")
    check("STATE_GOAL" not in race_helper,
          "GOAL wrongly admitted by cockpit race helper")
    check("cockpitActive && racing" in robot, "racing+active proof not passed to hide")
    check("InSceneEffect()" in active, "scene effect not excluded from active cockpit")
    check_order(robot, "const bool racing=", "const bool cockpitActive=",
                "ShouldSuppressOriginalPassenger(")
    check("!suppress(true,true,false,false,true,true)" in source_test,
          "GOAL/early START negative case missing")
    check("const bool racing=IsCockpitRacePhase();" in robot,
          "robot race phase no longer uses shared GOAL-excluding gate")
    check_order(robot,
                "if(action==CockpitOccupantRender::OriginalPassengerForceVisible)",
                "if(!racing)",
                "if(!NativeFrameTrace().Active() || InSceneEffect())")
    check("QuestCockpitV2Active(camera)&&racing" in robot,
          "driver W*C owner can still admit GOAL")
    player_cb=hook.split("static void __cdecl OnPlayerCallback(EVWORK_CAR* player)",1)[1].split(
        "template<std::size_t N>",1
    )[0]
    check("!IsCockpitRacePhase()" in player_cb,
          "F0 identity scope can still admit GOAL")
    check("!IsPlayableCarGameplay()" not in player_cb,
          "F0 scope still uses GOAL-inclusive gameplay helper")
    check(hook.count("const bool race=IsCockpitRacePhase();")==2,
          "passenger car-gate/scene recovery race predicates drifted")
    player_state=hook.split("static void PlayerState(SafetyHookContext& ctx)",1)[1].split(
        "public:",1
    )[0]
    check("if(IsCockpitRacePhase() && QuestCockpitV2Active(cam) &&" in player_state,
          "FullCar candidate flag can still be forced in GOAL")

def pass_07_nested_draw_and_restore():
    check_order(robot, "ShouldSuppressOriginalPassenger(",
                "const auto action=SelectCockpitOccupantRender(",
                "if(action==CockpitOccupantRender::OriginalPassengerForceVisible)",
                "ScopedOriginalOccupantLod0 passengerVisible(true);",
                "VR PASSENGER NATIVE LOCK:",
                "if(OriginalRobotCorrectionActive())",
                "if(!NativeFrameTrace().Active() || InSceneEffect())")
    check("ScopedOriginalRobotCorrectionOwner correctionOwner(true);" in robot,
          "W*C recursion owner lost")
    check("ScopedOriginalRobotWorkMatrix scoped(" in robot,
          "original robot work restore lost")
    gate = hook.split("static void __cdecl PassengerDriverDisplay(EvWorkRobot* work)",1)[1].split(
        "static void __cdecl RobotDisplay(EvWorkRobot* robot)",1)[0]
    check_order(gate, "PassengerGateEntries.fetch_add(", "if(!owner){",
                "PassengerGateNonPassenger.fetch_add(", "const bool frameReady=",
                "const bool stereoReady=", "const bool sceneOwner=",
                "ShouldBypassPassengerCarDisplayGate(",
                "if(!restore){original();return;}",
                "OriginalCommonRobotDisplayRva)(work);")
    check("cockpit && race && sceneOwner" in gate,
          "force draw must own exact native 43FB40 ROB scene")
    check("frameReady" in gate and "stereoReady" in gate,
          "XR readiness diagnostics unexpectedly removed")
    check("PassengerModelCorrectionNearNative" not in robot,
          "dead 4-unit passenger threshold still exists below native lock")
    check("VR PASSENGER NESTED VISIBLE:" not in robot,
          "passenger still has a separate recursion-dependent visibility route")
    check("VR PASSENGER EARLY NATIVE:" not in robot,
          "passenger visibility still depends on frame readiness")
    check("correctionOwnerActive={}" in robot,
          "native-lock diagnostics do not expose nested driver ownership")
    sky=read("src/vr/d3d9/stereo_renderer_r7.inc")
    check("fixedNativeEyePair=rotationOnly ? nullptr :" in sky,
          "fixed original sky can still switch between native/fallback bases")
    check("VR SKY COHERENT BASIS:" in sky,
          "sky-headset basis diagnostics unavailable")
    check("VR SKY NONEXACT DEPTH-OFF:" in sky and
          "shaderNonSkyDepthOffDraws={}" in sky,
          "one-per-present non-exact depth-off world draw remains unidentified")
    scene=hook.split("static void __cdecl PassengerEventSceneDisplay(",1)[1].split(
        "static void __cdecl RobotDisplay(",1)[0]
    check_order(scene,"ScopedPassengerSceneOwner sceneOwner(exactRobScene);",
                "PassengerSceneHook.ccall<void>(mask,first,last);",
                "ExactPassengerSceneOwnerActive()",
                "ShouldRecoverOriginalPassengerScenePass(",
                "if(!recover)return;",
                "PassengerDriverDisplay(work);")
    check("OriginalRobDisplayLayer=0x80u;" in policy,
          "canonical ROB01/ROB02 mask must be 0x80")
    check("OriginalEventSceneDisplaySignature()" in hook,
          "original scene hook must be signature-verified and fail closed")
    check("PassengerSceneRestores.fetch_add(" in hook,
          "missing actual upstream scene restore counter")
    check("DriverGateThreadCalls" in hook and
          "afterDriver!=beforeDriver,after!=before" in hook,
          "restored 0x80 event must prove native ROB01 from the same pass")
    check("passengerScene==OriginalRobDisplayLayer" in policy,
          "active original ROB02 0x80 mask may not silently skip recovery")
    check("VR PASSENGER SCENE PASS:" in hook,
          "one-session diagnostic does not distinguish layer from wrapper")
    check("if(!correctionOwner.Active())" in robot,
          "nested W*C correction not rejected")
    check("VR PASSENGER NATIVE LOCK:" in hook and "nativeWorkLocked=1" in hook,
          "passenger can still switch between corrected and native matrices")
    check("ScopedQuestSkyTransitionRotationLock" in hook and
          "VR SKY TRANSITION ROTATION LOCK:" in hook and
          "VR SKY TRANSITION PHASE:" in hook,
          "sky transition phase/rotation ownership is not observable")
    check("orientationWords=9" in hook and "RotationIndices" in hook,
          "sky repair still overwrites more than the 3x3 orientation consumed by 40A190")
    check("constexpr std::uint32_t None=0xffffffffu;" in hook and
          "(n0!=None || n1!=None)" in hook and "(o0!=None || o1!=None)" in hook,
          "sky overlap phase can still be armed by an all-None non-drawing layer")
    check("state!=STATE_START && state!=STATE_GAME" in hook,
          "first-stage camera 30/2 sky window is still excluded")
    check("base_+0x50" in hook and "base_+0xe0" in hook,
          "proven 4521C0 two-layer rotation records are not paired")

def pass_08_f11_exclusive_and_search():
    for phrase in ("Passenger: Follow Camera 0", "Passenger: Remove"):
        check(f'ImGui::Checkbox("{phrase}"' in ui, "missing F11 checkmark "+phrase)
        check(f'matches_search("{phrase}",search)' in section_match,
              "VR category hidden when searching "+phrase)
    check('matches_search("Cockpit View",search)' in section_match,
          "Cockpit View search previously returned zero categories")
    check("bool remove=!Settings::VRQuestCockpitV2PassengerVisible.get();" in ui,
          "independent booleans permit contradictory options")
    check("Settings::VRQuestCockpitV2PassengerVisible=!remove;" in ui,
          "remove checkbox not mapped to complement")
    check("VRQuestCockpitV2PassengerVisible.hidden(true);" in ui,
          "old independent checkbox remains visible")

def pass_09_settings_and_user_ini():
    check('VRQuestCockpitV2PassengerVisible{ "VR", "QuestCockpitV2PassengerVisible", true,'
          in setting, "default or INI key drifted")
    check("QuestCockpitV2PassengerVisible = true" in ini, "shipped default changed")
    check('Settings::write(Module::UserIniPath)' in ui,
          "F11 changes no longer saved in user INI")
    check("queue_setting_change(&Settings::VRQuestCockpitV2PassengerVisible)" in ui,
          "F11 toggle not marked dirty")
    check("VRQuestCockpitV2PassengerVisible;" in plugin,
          "setting declaration not exported")
    check("Camera 0 always retains native passenger display" in ini,
          "persisted setting not documented correctly")

def pass_10_ci_package_and_boundary():
    for src in ("tools/verify_quest_cockpit_passenger_runtime.py",
                "tools/tests/quest_cockpit_v2_passenger_event_smoke.cpp",
                "src/hooks_graphics.cpp", "src/overlay/settings_ui.cpp"):
        check(src in core_ci, "core CI missing "+src)
    for src in ("src/hooks_graphics.cpp", "src/overlay/settings_ui.cpp",
                "src/vr/game/quest_cockpit_v2_passenger_event.hpp"):
        check(src in build_ci, "VR integrated CI missing "+src)
    check("Verify original Quest passenger hook ABI from EXE" in release_ci,
          "native ABI binary verification unexpectedly removed")
    check("RUN-QUEST-COCKPIT-V2.cmd" in build_ci,
          "copy-run package launcher omitted from workflow")
    check("RUNTIME_VALIDATION=UNTESTED" in read("AGENTS.md"),
          "Quest 3 runtime boundary not documented")

rounds = [
    ("01 native event provenance", pass_01_native_source),
    ("02 live ROB02 callback/work identity", pass_02_live_owner_identity),
    ("03 camera 0 original pass-through", pass_03_camera0_passthrough),
    ("04 original passenger follow and LOD0", pass_04_follow_requires_real_guest),
    ("05 cockpit-only removal and NPC separation", pass_05_remove_scope_and_non_passenger),
    ("06 GOAL, START and scene-effect boundaries", pass_06_goal_start_scene_boundaries),
    ("07 nested robot draws and W*C restoration", pass_07_nested_draw_and_restore),
    ("08 F11 exclusivity and discoverability", pass_08_f11_exclusive_and_search),
    ("09 persistent INI and live settings", pass_09_settings_and_user_ini),
    ("10 exact-source CI and packaging contract", pass_10_ci_package_and_boundary),
]
if __name__ == "__main__":
    for name, fn in rounds:
        fn()
        print("PASS:", name)
    print(f"PASS: {len(rounds)}/10 distinct cockpit passenger static call-path audits")
