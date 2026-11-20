#!/usr/bin/env python3
"""Native camera-0 parity and removal static proof for cockpit passenger.

The game decides whether its original ROB02 exists, independently of camera.
No code may fabricate ROB02 or claim a GPU screenshot without HMD evidence.
Run without args for source checks or --exe PATH for canonical PC ABI proof.
"""
from pathlib import Path

hook = Path("src/hooks_graphics.cpp").read_text(encoding="utf-8")
launcher = Path("tools/Run-OutRunVRTest.ps1").read_text(encoding="utf-8")
assert "-VR.QuestCockpitV2PassengerVisible=true" in launcher, (
    "one-test PASSENGER diagnostics must force Follow Camera 0"
)
assert "if($QuestCockpitV2PassengerDiagnostics -eq 'ON')" in launcher, (
    "Follow Camera 0 must be limited to explicit passenger diagnostics"
)
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
assert "ShouldBypassPassengerCarDisplayGate(" in policy
assert "OriginalRobDisplayLayer=0x80u" in policy
assert "ShouldRecoverOriginalPassengerScenePass(" in policy
assert "OriginalEventSceneDisplaySignature()" in hook
assert "PassengerSceneHook.ccall<void>(mask,first,last);" in hook
assert "PassengerGateThreadCalls" in hook
assert "PassengerModelCorrectionNearNative" not in hook
assert "VR PASSENGER NATIVE MATRIX:" not in hook
assert "VR PASSENGER NESTED VISIBLE:" not in hook
assert "VR PASSENGER EARLY NATIVE:" not in hook
assert "correctionOwnerActive={}" in hook
analyzer = Path("tools/Analyze-OutRunVRSession.ps1").read_text(encoding="utf-8")
assert "gameExitCode=(-?\\d+)" in analyzer
assert "\\b(crash|" not in analyzer
assert "unhandled exception" in analyzer.lower()
assert "PassengerPipelineStatus" in analyzer
assert "D3D9_DIP_CONFIRMED_HMD_VISUAL_REQUIRED" in analyzer
assert "passengerNativeDipSuccessCount" in analyzer
assert "skyOpaqueQueueDrawCount" in analyzer
sky = Path("src/vr/d3d9/stereo_renderer_r7.inc").read_text(encoding="utf-8")
assert "fixedNativeEyePair=rotationOnly ? nullptr :" in sky
assert "exactWorldSky ? nullptr :" in sky
assert "VR SKY COHERENT BASIS:" in sky
assert "VR SKY NONEXACT DEPTH-OFF:" in sky
assert "shaderNonSkyDepthOffDraws={}" in sky
assert "VR SKY OPAQUE QUEUE TAG:" in hook
assert "VR SKY OPAQUE QUEUE DRAW:" in hook
assert "effectiveScope={} producer={} queueActive={}" in hook
assert "thread={}" in hook
assert "RaceSkyObjectQueueRva = 0x56D0" in hook
assert "WorldSkyOpaqueQueue::RecordDeferred" in hook
assert "WorldSkyOpaqueQueue::Find(entry)" in hook
assert "ScopedExactProducerSemantic queuedSkyScope(" in hook
assert "VR SKY SOURCE OWNER:" in hook
assert "RenderScope::WorldSky,nullptr,true" in hook
assert "queuedSkyIndex>=0 ? RenderScope::WorldSky : RenderScope::None" in hook
assert "nullptr,true" in hook
copyrun = Path("QuestCockpit-CopyRun.ps1").read_text(encoding="utf-8")
# PASSENGER explicitly enables both bounded traces in the SAME mode.
passenger_block = copyrun.split("if($Mode -eq 'PASSENGER'){",1)[1].split(
    "if($Mode -eq 'INTERP')",1
)[0]
assert "QuestCockpitV2PassengerDiagnostics='ON'" in passenger_block
assert "QuestCockpitV2SkyProbe='ON'" in passenger_block
assert "DriverGateThreadCalls" in hook
assert "originalOwner==OriginalOccupantSlot::Driver362" in hook
assert "VR PASSENGER SCENE PASS:" in hook
assert "VR PASSENGER NATIVE LOCK:" in hook
assert "nativeWorkLocked=1" in hook
assert "workFlagsNative=0x{:08X} workFlagsRender=0x{:08X}" in hook
assert "nativeGateOpen={} renderGateBypass={}" in hook
assert "f0Neutralized={}" in hook
assert "matrixScope={}" in hook
assert "NeutralizePassengerVehicleF0(" in render
assert "OriginalRobotDisplayGateRenderFlags(nativeWorkFlags)" in hook
assert "OriginalRobotDisplayGateOpen(nativeWorkFlags)" in hook
assert "ScopedPassengerRobotDisplayGate" in hook
assert "VR PASSENGER PHYSICAL PMT:" in hook
assert "authority=405890_404700" in hook
assert '#include "vr/game/quest_cockpit_v2_passenger_event.hpp"' in sky
assert "VR PASSENGER NATIVE DIP:" in sky
assert "ExactPassengerRenderActive()" in sky
assert "authority=D3D9_DIP_VTABLE_82" in sky
assert "ScopedExactPassengerRender exactPassenger(true);" in hook
assert "ExactPassengerRenderActive()" in hook
assert "ScopedQuestSkyTransitionProbe" in hook
assert "VR SKY TRANSITION PHASE:" in hook
assert "RotationIndices" in hook
assert "mutation=0 probePreStartSuppression=1" in hook
assert "ScopedQuestStartSkySingleLayer" in hook
assert "*Game::current_mode!=STATE_START" in hook
assert "std::memcpy(base_+0xc8,&zero,sizeof(zero));" in hook
assert "std::memcpy(base_+0xcc,&zero,sizeof(zero));" in hook
assert "std::memcpy(base_+0xc8,&oldC8_,sizeof(oldC8_));" in hook
assert "std::memcpy(base_+0xcc,&oldCC_,sizeof(oldCC_));" in hook
assert "base+0xe0+byte,&" not in hook
assert "constexpr std::uint32_t None=0xffffffffu;" in hook
assert "(n0!=None || n1!=None)" in hook
assert "(o0!=None || o1!=None)" in hook
assert "state!=STATE_START && state!=STATE_GAME" in hook
assert "base+0x50+byte" in hook and "base+0xe0+byte" in hook
assert "const auto* base=reinterpret_cast<const std::uint8_t*>(work);" in hook
assert "sceneEvidence.driverReached,sceneEvidence.guestReached" in hook
assert "passengerScene==OriginalRobDisplayLayer" in policy
assert "driverWrapperReached" in policy
assert "const auto before=PassengerGateThreadCalls;" in hook
assert "const auto after=PassengerGateThreadCalls;" in hook
assert "const auto sceneEvidence=CurrentPassengerSceneEvidence();" in hook
assert "PassengerDriverDisplay(work);" in hook
assert "driver->field_C,passenger->field_C," in hook
assert "sceneEvidence.driverReached,sceneEvidence.guestReached);" in hook
assert "live,ExactPassengerSceneOwnerActive()," in hook
assert "0x83,0xEC,0x10,0x83,0x3D,0x58,0x02,0x78,0x00,0x02" in hook
assert "(flags & (OriginalEventPendingInit|OriginalEventInitialized)) ==" in policy
assert "PassengerOtherCameraDraws.fetch_add(" in hook
assert "PassengerGateCamera1Entries.fetch_add(" in hook
assert "PassengerGateNonPassenger.fetch_add(" in hook
assert "cockpit && race && renderOwner" in hook
assert "const bool legacyFrameOwner=" in hook
assert "!PassengerSceneHook && frameReady && stereoReady" in hook
assert "const bool renderOwner=sceneOwner || legacyFrameOwner;" in hook
assert "ScopedPassengerSceneOwner sceneOwner(exactRobScene);" in hook
assert "ExactPassengerSceneOwnerActive()" in hook
assert "struct PassengerSceneEvidence final" in hook
assert "NotePassengerSceneWrapper(originalOwner);" in hook
assert "sceneEvidence.driverReached,sceneEvidence.guestReached" in hook
assert "OriginalPassengerDisplayGateSignature()" in hook
assert "PassengerGateHook=std::move(guest);" in hook
assert "Module::fn_ptr<NativeRobotDisplay>(" in hook
assert "OriginalCommonRobotDisplayRva)(work);" in hook
assert "PassengerGateRestores.fetch_add(" in hook
assert "car->flags_4" in hook
assert "static void __cdecl PassengerDriverDisplay(EvWorkRobot* work)" in hook
assert "0xA1,0x18,0x9D,0x79" in hook
assert "if(!restore){original();return;}" in hook
assert "OriginalEventLiveForDisplay(std::uint8_t flags)" in policy
assert "OriginalEventLiveForDisplay(eventFlags[OriginalDriverEventId])" in owner
assert "OriginalEventLiveForDisplay(eventFlags[OriginalPassengerEventId])" in owner
assert "Module::exe_ptr<std::uint8_t>(OriginalEventFlagsRva)" in owner

# Camera-0 must reach the original renderer regardless of passenger mode.
# Only after rejecting camera!=1 may the exact live ROB02 suppression run.
camera_guard = "if(!camera || camera->cam_mode_34A!=1 || !Game::pl_car())"
assert camera_guard in render
before_suppress=render.split("ShouldSuppressOriginalPassenger(", 1)[0]
assert before_suppress.index(camera_guard) < before_suppress.index(
    "const auto slot=ExactOriginalCockpitOccupant(robot);"
)
assert "RobotHook.ccall<void>(robot);" in before_suppress.split(
    camera_guard, 1
)[1]
assert "ShouldSuppressOriginalPassenger(" in render
after_suppress=render.split("ShouldSuppressOriginalPassenger(", 1)[1]
assert "camera->cam_mode_34A==1" in after_suppress.split("))", 1)[0]
assert "slot==OriginalOccupantSlot::Passenger363" in after_suppress
assert "return;" in after_suppress.split(
    "if(!NativeFrameTrace().Active()", 1
)[0]
assert render.index("ShouldSuppressOriginalPassenger(") < render.index(
    "if(!NativeFrameTrace().Active() || InSceneEffect())"
)
assert "nativeCameraModeOne && exactLivePassenger" in policy
assert "camera 0" in ini.lower() or "Camera 0" in ini
assert "only in cockpit mode 1" in settings
assert "ONLY in cockpit view" in overlay
assert "RobotHook.ccall<void>(robot);" in render
assert "SelectCockpitOccupantRender(" in render
assert "ScopedOriginalOccupantLod0 passengerVisible(true);" in render
assert render.index("ScopedOriginalOccupantLod0 passengerVisible(true);") < render.index(
    "if(OriginalRobotCorrectionActive())"
)
assert render.index("ScopedOriginalOccupantLod0 passengerVisible(true);") < render.index(
    "if(!racing)"
)
assert render.index("if(!racing)") < render.index(
    "if(!NativeFrameTrace().Active() || InSceneEffect())"
)
assert "QuestCockpitV2Active(camera)&&racing" in render
player_cb = hook.split("static void __cdecl OnPlayerCallback(EVWORK_CAR* player)",1)[1].split(
    "template<std::size_t N>",1
)[0]
assert "!IsCockpitRacePhase()" in player_cb
assert "!IsPlayableCarGameplay()" not in player_cb
player_state = hook.split("static void PlayerState(SafetyHookContext& ctx)",1)[1].split(
    "public:",1
)[0]
assert "if(IsCockpitRacePhase() && QuestCockpitV2Active(cam) &&" in player_state
assert "const bool race=IsCockpitRacePhase();" in hook
assert hook.count("const bool race=IsCockpitRacePhase();") == 2

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

print("PASS: native camera-0 untouched, cockpit-only ROB02 removal, F11 exclusive mode")

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
        # rob_disp 514C30: [work+4] bit15 display enable, then 0x08/0x04 gate.
        assert at_va(0x514C30, 48) == bytes.fromhex(
            "83ec0c5356578b7c241c8b378b470469f6a400000081c6f0f58200"
            "84e48bd90f89f3010000a8087408a8040f84e70100"
        )
        assert at_va(0x4056D0, 24) == bytes.fromhex(
            "51558b6c240c83fdff0f843f010000568bc5c1e8108bf550"
        )
        # Deferred 4521C0 sky provenance rejoins the real opaque PMT consumer
        # only at these two retail 405890 -> 404700 call edges.
        for call_va in (0x405A41, 0x405C44):
            call = at_va(call_va, 5)
            assert call[0] == 0xE8, f"expected CALL at {call_va:#x}"
            rel = struct.unpack_from("<i", call, 1)[0]
            assert call_va + 5 + rel == 0x404700, (
                f"unexpected PMT consumer target at {call_va:#x}"
            )
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
        print("PASS: canonical PE32 event/ROB/sky queue + 405890 PMT edges, callbacks, SHA")
