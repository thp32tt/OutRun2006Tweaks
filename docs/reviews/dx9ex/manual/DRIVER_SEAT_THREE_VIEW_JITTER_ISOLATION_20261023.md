# DX9Ex R26 cockpit: DriverSeatView A/B isolates all-three-view jitter (2026-10-23 KST)

Status: REVIEW_ONLY / user-provided HMD A/B observation; no game-source modification.
SOURCE_HEAD examined: `48764b643bb4974ed7774eeb803637d881adcfab` (branch `vr-d3d9ex-focus`).
Earlier exact source blob: `src/hooks_graphics.cpp` `3a1be4813cabbff9e27199da60d5ff70fd66cd43`.
Tested baseline artifact reported previously: `b7ca566b0098dba8b7a4746c7950c65a7309006b` / PC FAST.

## Fresh user runtime observation

On Quest3 with current DX9Ex test, `DriverSeatView=true`: original camera views 1, 2 and 3 all shake severely; the effective viewpoint never settles near the driver seat. With `DriverSeatView=false`, the same original views 1, 2 and 3 progress normally. This is a strong **cockpit-feature isolation result**, NOT proof that the original OpenXR transport, game camera controller, or source matrix is faulty.

Two diagnostic ZIP files were found in the user's ChatGPT project Library on 2026-10-23 (~00:06 KST uploads; filenames containing `20261022T145745359Z-62ab93bf` and `20261022T150256068Z-0f712161`). Their ZIP contents were inaccessible from the current file runtime; do NOT claim numeric camera deltas, mode counts, or frame traces.

## Exact source-path findings (static, directly verified)

1. `VRDriverSeatCameraEligible` calls `PersistentDriverSeatSessionEligible(VREnabled && VRDriverSeatView, VRDriverSeatGameplayActive())` and pose validation; it **does not use** `cam_mode_34A`, `cam_mode_timer_364`, `word340/word344`, or `VRDriverSeatNativeMode`. This was introduced by [ec7ba91f](https://github.com/thp32tt/OutRun2006Tweaks/commit/ec7ba91fcb55ded); compare the older scoped gate from [2a80f4f](https://github.com/thp32tt/OutRun2006Tweaks/commit/2a80f4fab8eaa41). Consequently all valid gameplay camera modes can satisfy cockpit eligibility while DriverSeatView is on. **A credible explanation for all 1/2/3 views being affected.**
2. `VRDriverSeatCameraPose` computes `ComputeStableSeatPose(native cam_pos_F8, native look_pos_104, optional player matrix_B0 axes, offsets)` and holds the last valid pose only if computation fails. When native camera position and orientation are finite but change rapidly, every new finite result passes; there is no temporal discontinuity check or per-frame immutable seat origin. [daccfaa5](https://github.com/thp32tt/OutRun2006Tweaks/commit/daccfaa5c68ef3a) restores a camera-relative anchor after the user observed that absolute car-origin placement put the head inside the player model. Do not revert blindly to car origin.
3. `FixZBufferPrecision::CalcCameraMatrix_dest` obtains eligibility, optionally substitutes both original camera vectors before `CalcCameraMatrix.call(camera)`, then restores the original vectors. `Clr_SceneEffect_dest` rebuilds a camera for effects and again after the scene effect. Source shows separate camera-matrix constructions and potential pose-origin changes; **not independently verified as oscillation root**.
4. `VRDriverSeatRenderTest::Active()` and `VRDriverSeatVehicleScaleRenderHook` depend on the same global cockpit eligibility; therefore full player car and occupant treatment can also apply in views 1/2/3. This does not prove camera jitter, but visual occlusion may magnify perceived zoom/jump.
5. Repo `OutRun2006Tweaks.ini` still explicitly sets `DriverSeatVehicleScale = 1.15`, while `src/vr/settings.cpp` C++ default was corrected to `1.0` in [0baa6e5](https://github.com/thp32tt/OutRun2006Tweaks/commit/0baa6e5c1412). The shipped explicit INI overrides the corrected default unless launch profile overrides it. This is a **confirmed configuration discrepancy**, separate from temporal jitter. `DriverSeatCarSpaceBasis = false` by default.

## Static counterexample / expected semantics

For a valid gameplay sample with `DriverSeatView=true` and finite camera+car pose:
- camera native mode 0 => current persistent gate = true;
- camera native mode 1 => current persistent gate = true;
- camera native mode 2 => current persistent gate = true.
However, the configured `DriverSeatNativeMode=1` is no longer evaluated. A cockpit implementation intended to be anchored to one stable bumper/in-car basis must not consume arbitrary 0/2 external/chase camera positions for seat coordinates.

## Minimal safe next validation and repair design

- Control already PASS from user's Quest3 test: `DriverSeatView=false` restores all three original views. Preserve it unchanged.
- While explicitly testing `DriverSeatView=true`, pin `DriverSeatCarSpaceBasis=false` and `DriverSeatVehicleScale=1.0` to remove experimental basis/model-scale confounders; verify effective command-line overrides before comparing.
- Diagnostic A/B: with cockpit still enabled, temporarily set `DriverSeatForward/Right/Up=0` (no displacement but same hook) to determine whether the amplified jitter originates in the translation offset/basis versus other side-effects of cockpit activation. This is a *diagnostic*, not a fixed cockpit view.
- Source-side candidate: introduce a **single session-owned, mode-consistent** seat basis and camera-mode transition policy. Use exactly one scene-wide snapshot per game frame; preserve native camera simulation vectors and explicit enter/leave semantics. Avoid simply restoring a per-frame mode/timer hard veto, which previously induced rapid native/seat bounce and was deliberately removed. Guard car render/driver suppression and near plane using the identical session/frame seat decision.
- Capture bounded pose evidence by native camera mode (0/1/2), input position/look, output seat position/look, selected offset basis, last-pose fallback, calls per frame and scene pass; focus on discontinuities, camera-mode transitions and duplicate per-frame CalcCameraMatrix invocations. Do not claim confirmed mathematical root until logs show which signal jumps.

CODE_CHANGE=NO
BUILD=NOT_RUN
RUNTIME_VALIDATION=PARTIAL_USER_A_B_ONLY
ROOT_CAUSE_CONFIDENCE=CAMERA_PATH_ISOLATED_HIGH; MODE_GATING_AND_POS_ORIGIN_HYPOTHESES_NOT_YET_FRAME_PROVEN
