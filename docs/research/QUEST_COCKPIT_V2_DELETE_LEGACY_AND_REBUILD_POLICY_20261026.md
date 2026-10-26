# DX9Ex R26+HUD — legacy DriverSeatView complete replacement policy and cutover plan
Date: 2026-10-26 KST. Scope: user-owned OutRun 2006 C2C, Quest3/OpenXR + MOZA R3 physical wheel. Target: `thp32tt/OutRun2006Tweaks` branch `vr-d3d9ex-focus`. Source snapshot reviewed at `9f351b1218084057b4e2054fa7ce97c5b7db3c41` (live branch may advance independently).

## Binding policy — DELETE and REBUILD, NOT incremental patching

1. **Entire existing experimental driver-seat rendering implementation is LEGACY/REJECTED.** Do not copy its `VRDriverSeatCameraPose`, `PersistentDriverSeatSessionEligible`, last-valid pose cache, frame-unaware camera translation, player model scale hack, or guessed material probe as a functioning cockpit foundation.
2. **The complete legacy subsystem MUST be physically removed from active production source at cutover**, not merely disabled with `DriverSeatView=false`. Old header/tests may remain as historical GitHub evidence but must not be built, included, or registered in the new runtime. Do not ship two competing cockpit hooks or run old and new simultaneously.
3. A new self-contained `QuestCockpitV2` module will own a single game-render-frame snapshot, native camera-mode-1 admission, player vehicle matrices, scoped player/occupant draw correction, optional exact glass ownership, and the OpenXR pose relationship. Use `Quest` original reverse-engineering evidence; do not pretend the reconstructed source is the author's exact original C++.
4. **MOZA R3 steering, FFB, XInput/dinput, wheel calibration and physics stay untouched**. Quest TouchFrame/VirtualWheel/hands are explicitly OUT of scope.
5. **Never destroy independent R26 rendering functions:** 4:3 menus, HUD 1920×1080/0.55, existing stereo submission, F11, screen effects, culling 8, regular `FixZBufferPrecision`, `RestoreCarBaseShadow`, lens flare and resolution policy. R26+HUD known-good should remain an immutable rollback reference.
6. **Opt-in only:** keep `DriverSeatView=false` (or new `QuestCockpitV2Enabled=false`) until GitHub Actions Windows x86 DLL + x64 host CI, bounded HMD-less test and Quest3 runtime testing. Do not claim success from only a native Linux unit test.
7. DX9Ex automation is **REVIEW_ONLY** unless user explicitly initiates the reviewed production cutover. This research commit changes only documentation and standalone reference code, NOT `src/`, INI, workflow or the live gameplay DLL.

## Verified current legacy footprint; source and precise cutover edits

| Active code | Verified references (HEAD snapshot) | How to replace/remove safely |
|---|---|---|
| `src/hooks_graphics.cpp` includes | Lines 9–14 include `driver_seat_camera_math.hpp`, `driver_seat_car_space.hpp`, `driver_seat_render_pass.hpp`, `driver_seat_vehicle_scale.hpp`, `driver_seat_occupant.hpp`, `cockpit_glass_material_probe.hpp` | Remove these *active* include dependencies and substitute one **new** QuestCockpitV2 header once implemented. Old files can be archived with historical tests but are not included/linked. |
| `src/hooks_graphics.cpp` Settings declarations | Lines 50–62: 13 `VRDriverSeat*` extern declarations | Remove old setting externs. Introduce a minimal **new** opt-in setting namespace, avoid retaining obsolete tuning knobs merely because they existed. |
| Legacy camera/session | Lines 164–275: `VRDriverSeatCameraPose`, `VRDriverSeatGameplayActive`, `VRDriverSeatCameraEligible` | Delete legacy pose/session eligibility. **CAUTION:** `VRDriverSeatGameplayActive` is also used at **line 533 in unrelated `RestoreCarBaseShadow`**. First extract a neutral helper `IsPlayableCarShadowGameplay()` with identical game-state semantics and migrate that shadow call; otherwise wholesale deletion regresses vehicle shadows. |
| Player car / occupant | Lines 278–388: `VRDriverSeatRenderTest`, player state hook EXE+0x69764, robot display EXE+0x114C10 | Remove both active hooks and installation on cutover; new V2 owns an **atomic** camera/body/occupant frame decision, player only. Passenger untouched. Do not install only the car detour while the occupant path fails. |
| Player car artificial scale | Lines 395–458: `VRDriverSeatVehicleScaleRenderHook` EXE+0x697BD | Remove active detour altogether; do **not** port the 1.15 model-size hack. Quest native reference uses vehicle B0/F0 scoped transforms, **not** a proven uniform 1.15x player scale. |
| Global glass probe | Lines 463–512: `VRDriverSeatGlassMaterialProbe` EXE+0x4901 | Remove global material probe from production. Its `validate()` currently returns `VRDriverSeatGlassMaterialTrace` (shipped `true`), so its hook can install even when `DriverSeatView=false`. New glass diagnostic must be off by default and require known player-car PMT ownership. No global opacity edits. |
| Camera/Z precision shared class | Lines 2015–2208: `FixZBufferPrecision` has `DriverSeatCameraActive`, `ApplyDriverSeatCameraOffset`, `CalcCameraMatrix_dest`, `Clr_SceneEffect_dest` | **Do not delete entire class.** Remove **only** legacy camera override, legacy near-plane cockpit branch and reference-based hook validation. Preserve normal 2D Z precision, ordinary VR near-plane path and independent SceneEffect behavior; new V2 may later enter a scoped render-matrix owner without persistent `EvWorkCamera` writes. |
| Config/GUI | `src/vr/settings.cpp:143–168` and `OutRun2006Tweaks.ini:507–536` | Retire old `DriverSeatVehicleScale=1.15`, CarSpaceBasis, Forward/Right/Up offsets, NativeMode user override, guesswork DriverWorkId/Chrset, FullCar, GlassMaterialTrace and opacity tuning. Keep general **`VRNearPlane`**. New opt-in V2 should expose only tested, necessary settings; F11 generated controls depend on Setting registrations. |
| Pure legacy helpers | `src/vr/game/driver_seat_*.hpp`, `src/vr/game/cockpit_glass_material_probe.hpp` | Remove from active source/build only after no references remain. Retain relevant source-level lessons in immutable Git history and research docs. |
| Legacy smoke tests | `vrhost/tests/driver_seat_{camera,car_space,occupant,render_pass,vehicle_scale}_smoke.cpp`, `tools/verify_vr_driver_seat_basis_stability.py`, `tools/tests/test_quest_cockpit_glass.py` | Replace assertions with V2-specific tests and regression tests. Do NOT make old tests a prerequisite to new source even if a stale test file remains. |
| Baseline / backup | current focus branch and GitHub workflows | Preserve a readable baseline SHA; create a separate dedicated reviewed cutover commit and exact SHA CI. **GitHub Actions only**, no PCFAST/PC runner. User ZIPs require .cmd/.bat, .ps1, INI, x86 `dinput8.dll`, x64 host EXE. |

## New architecture: exact Quest event scope, not a camera-offset shim

**Quest binary evidence:** Native `PcSceneRenderer::render_frame` ELF `0x10CBE9C` enables a cockpit body correction only when `(renderEventFlags & ~2)==0x10`, renderer cockpit flag is active, paired vehicle/camera provider returns valid buffers and camera `+0x34A==1`. Original provider callback `attach_pc_scene::$_1` ELF `0x2D0C10` returns car data size 0x10F0 and camera data size 0x400. `EVWORK_CAR::matrix_B0+0xB0` and `matrix_F0+0xF0` produce the correction, **F0 is renderer-scope identity-substituted**, 16 float elements are restored on normal/exceptional exits. `cockpit_vehicle_draw` and `cockpit_occupant_draw` are scoped independently. The original XR rig validates both eye views and position/orientation. The raw Quest event flags are **not** the PC `STATE_GAME` enum or the stereo `FrameDescriptor.flags`: require an explicit PC event-owner mapping.

**New proposed ownership model:**
```text
verified game-frame entry [NOT assumed equal to PresentEpoch or XR poseSequence]
  -> snapshot immutable player EVWORK_CAR B0/F0, EvWorkCamera, current car-model,
     game camera mode, car generation, time/scene state, native car transition,
     XR frame+headPoseSequence+referenceSpaceGeneration+both-eye validity
  -> commit ONE frame decision (or Reject)
  -> on World pass only:
       compute per-car native view1 anchor from source game's 30 x 36 B table
       build Quest-style body matrix correction and renderer-local F0 identity
       scoped player-only full-body draw, matching driver-only treatment
       optional scoped windshield (after exact player-draw PMT classification)
       both eyes reuse the SAME game-car owner and XR pose, apply HMD transform ONCE
  -> on SceneEffect, 2D menu/HUD, non-player car: existing R26 paths unchanged
  -> on normal/exceptional exit: release local matrix/near/TLS state atomically
  -> on car change, scene transition, recenter, tracking failure: invalidate
  -> never reuse stale camera/game/eye matrix across a different frame owner
```

Game frame generation MUST be demonstrated in PC callbacks first. `src/vr/d3d9/stereo_renderer.cpp::PresentEpoch`, `FrameDescriptor::frameId`, and `OutRunVRRenderer::LatchedPoseSequence` are real counters but **are NOT proven native game-render epochs**. No live V2 installation before verifying source timing and correlation (log `CalcCameraMatrix/BeginScene/Clr_SceneEffect/EndScene/Present` with current vehicle and camera mode, pose generation).

## Newly created pure V2 replacement skeleton and independent smoke result

Standalone reference code, **not imported by production hooks**:
`docs/research/quest_cockpit_v2_clean_rebuild_20261026.hpp`.

It contains `FrameInput`, `SnapshotKey`, `Eligible`, `Decision::BeginOrObserve`, `WorldOnly`, `Reset`. It uses **zero legacy DriverSeat implementation functions/headers** and zero wheel input functions. Under one game frame, camera/player/XR pose/space changes permanently fail closed until the next verified game epoch (the rendering integration must supply that epoch); HUD and SceneEffect are rejected.

N100 readback of the exact GitHub header, compile:
`g++ -std=c++17 -Wall -Wextra -Werror -pedantic` **PASS**. Executed test binary `PASS QuestCockpitV2 frame-only state contract`, including mode 1/2 conflict, no same-frame reentry, player switch, XR pose change, space generation change, tracking invalidation and SceneEffect skip. This verifies only the independent state machine, not runtime eye/vehicle model equivalence or Windows x86 compilation.

## Cutover order, no fallback mixing

**Phase 0 — freeze and prove preconditions (research/diagnostic):** Determine actual native gameplay render frame boundary and two-eye correspondence, cross-check Quest B0/F0 arithmetic with original measured matrices, mark player and passenger ownership, establish undo and exact runner/build packaging. Document all cross references above. No code deletion until this proof.

**Phase 1 — sever legacy and restore baseline (one coherent future source cutover):** Remove all old cockpit detours/settings/uses, preserve `FixZBufferPrecision` core, rename/extract the shared `RestoreCarBaseShadow` gameplay predicate first. Keep V2 disabled, so gameplay is **identical to normal non-cockpit R26**. Verify no old hook is installed, no legacy setting controls in F11 and no glass probe overhead.

**Phase 2 — new isolated V2 render owner:** Integrate new game epoch/snapshot, implement original mode1 per-car anchor and scoped B0/F0 correction with normal/error restore. Both eyes share decision; driver suppression and car display atomically staged. Build diagnostics and standard user test separately through GitHub Actions only.

**Phase 3 — optional front/side windshield:** Identity-prove PMT draw material/mesh texture first; no blanket glass alpha. Keep optional pass off until verified. No hand tracking/virtual wheel implementation.

**Phase 4 — verify and ship:** Quest3 mode0/1/2 switching, start→race→goal→results, static/moving cars, recenter, transport recovery, menu 4:3, F11 size and cursor, HUD 1920×1080 0.55, lens flare/goal, culling default8, performance SSW off; MOZA R3 FFB/input unaffected. Run exact GitHub SHA workflows and confirm artifacts include launcher scripts.

**Rollback:** if any new V2 test fails, disable V2 and use preserved non-cockpit R26 baseline; **do not re-enable old cockpit** as the fallback.

## Immediate verdict

**Policy established: YES. Clean V2 research interface compiled/smoked: YES. Active legacy source deleted: NO (requires controlled cutover after verified frame mapping). V2 game-render source integrated: NO. Quest 3 HMD validated: NO.** Historical docs are retained, but production fallback must not call legacy code.
