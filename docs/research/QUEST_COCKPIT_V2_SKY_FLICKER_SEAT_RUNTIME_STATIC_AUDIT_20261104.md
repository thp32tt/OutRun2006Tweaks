# QuestCockpitV2 PCVR seat / sky flicker source-flow audit

**Audit date:** 2026-11-04 KST  
**Exact audited material SHA:** `743061fce7fa3bdc1a1f7415eb3d36cbd2ec914f`  
**Branch:** `vr-quest-cockpit-v2`, stable focus and released beta not edited  
**Type:** SOURCE REVIEW ONLY; **source code unchanged**, no CI/build rerun for an already verified material SHA.  
**Quest3 HMD sky-pixel/seat runtime validation:** UNTESTED. Original APK/PC reverse-engineering supports code-path claims but does not prove displayed pixels.  
**Previous user observed:** sky flashes on start and during driving even with a saved run displaying SkyGlowFactor=0; B0 camera double-transform shakes; seat formerly high/forward. No new synchronized sky visual/host diagnostic capture in this audit.

## A. Native Quest 30-profile seat: line-by-line execution contract

| Step | Original code/evidence | Observed effect and confidence |
|---|---|---|
| 1 | `RUN-QUEST-COCKPIT-V2.cmd`: `-TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON` | Dedicated experimental route, not the stable release. |
| 2 | `tools/Run-OutRunVRTest.ps1` line 325: `-VR.QuestCockpitV2Enabled=true`; line 329: `-VR.QuestCockpitV2NativeSeatProfile=true`; line 328: `-VR.QuestCockpitV2RawB0Camera=false`; manual shifts 0 | Runtime switches set explicitly even with stale user ini; natural F11 switch is available. |
| 3 | `src/hooks_graphics.cpp` `FixZBufferPrecision::validate()` ~3146: hook enabled for experimental cockpit even if Z precision off; `CalcCameraMatrix_dest()` ~3062; at ~3097 run `QuestCockpitV2CameraPose(camera,pose)` | Calls before original CalcCameraMatrix and restores camera fields after. Must keep original 2D/menu/GOAL. |
| 4 | `QuestCockpitV2Active()` ~662: VREnabled, cockpit switch, original mode1, playable game, not SceneEffect, player car, native-hook installed | Mode1 gameplay owner. **Important gap:** native-hook-installed bit is not a per-frame current `NativeFrameTrace().ActiveEpoch()` proof at camera calculation. Avoid claiming full native frame ownership. |
| 5 | `QuestCockpitV2CameraPose()` ~690: `model=static_cast<int>(static_cast<int8_t>(car->car_kind_11))`; reject not in 0..29 | Signed model index matches independently inspected PC car model byte. However Quest native `run_game::$_2` reads guest global selection byte `0x92F31`; source inspection does NOT prove that this global and current car byte agree on every race/transition frame. |
| 6 | ~694-699: live `0x818BB0` original PC mode1 table, 30*36 byte validation, XYZ | First (ordinary camera) anchor; not VR's second table. |
| 7 | ~709-725: live `Module::exe_ptr(0x1B0CB8)` profile record area and `0x1B2F68` pointer list | Both RVAs are from original PE VAs 0x5B0CB8 and 0x5B2F68 minus 0x400000 image base. `OriginalQuestVrProfileAnchor` requires 30 pointers exactly `0x5B0CB8+0x128*i`, reads original bytes +0x4C/+0x50/+0x54, rejects invalid/NaN/unknown layout. The canonical PE layout and original native APK instruction sequence are previously established. **No per-car data from Quest APK is redistributed.** |
| 8 | `src/vr/game/quest_cockpit_v2_seat.hpp` `NativeVrProfilePose` ~72-107 | Computes `deltaLocal = (profile.x-view1.x, profile.y-view1.y, profile.z-view1.z)` plus optional user tune; rotates only horizontal local X/Z according to smoothed camera horizontal view, moves world Y directly; applies the SAME world delta to camera eye/look. No second B0 transform and no persistent pointer writes. |
| 9 | `FixZBufferPrecision::CalcCameraMatrix_dest` `ScopedCamera` ~3100-3120 | Replaces `cam_pos_F8/look_pos_104` temporarily, calls original `CalcCameraMatrix`, then RAII restores both. The resulting render matrices receive the shifted camera, game simulation camera fields remain original on exit. Nested SceneEffect has separate exclusion gate. |
| 10 | `src/vr/game/outrun_renderer.cpp` `LatchFramePose`, `ApplyCullingCameraSync` ~1331-1435 | OpenXR head inverse and eye offsets are added in rendering. Culling camera replacement temporarily replaces live F8/look during render; restoration is expected in `RestoreCullingCamera`. |
| 11 | `src/vr/d3d9/stereo_renderer_r7.inc` ~854-905 | Eligible world/fixed-function draw consumes latched HMD inverse + independent eye orientation/offset; sky rotation-only path excludes head/IPD translation. |
| 12 | Synthetic tests `tools/tests/quest_cockpit_v2_seat_smoke.cpp`; Actions `41669839083`, Win32/x64 build `41669839013` both SUCCESS for exact SHA | Compilation and synthetic math **PASS**; **not a HMD equivalence proof**. No actual screenshot or live per-model admission log provided for this SHA. |

### Numerically grounded spot checks

- Model0: ordinary view1 `(-0.353,0.990,-0.345)`, VR profile `(-0.353,0.627,-0.390)`; applied local delta `(0,-0.363,-0.045)`.
- Model4: ordinary `(-0.345,1.170,-0.040)`, profile `(-0.345,0.773,-0.019)`; delta `(0,-0.397,+0.021)`.
- Model9: ordinary `(-0.322,1.065,+0.165)`, profile `(-0.331,0.766,+0.035)`; delta `(-0.009,-0.299,-0.130)`.
- Model13: ordinary `(-0.353,1.250,0)`, profile `(-0.351,0.770,0)`; delta `(+0.002,-0.480,0)`.
- Model14: ordinary `(-0.353,1.200,-0.150)`, profile `(-0.351,0.674,-0.025)`; delta `(+0.002,-0.526,+0.125)`.

These values explain why this change should LOWER the camera relative to ordinary view1 **when actually admitted**. Missing profile/table compatibility fails closed to original camera (user could still see a high stock seat). Unchanged camera is NOT proof the option is working.

### Remaining parity gaps, ordered by impact

1. **Coordinate space/timing:** Quest native applies the guest profile *inside* `race_camera_eye_look_485590`, before `eye_swing_483ce0` and later camera blend/correction, while PCVR adds only a yaw-based delta *after* the original camera update. Camera pitch/roll, slope, oscillation, collision and source camera interpolation can differ. Full Quest equivalent requires the correctly gated live camera-input override at the original mode1 seat producer and coherent XR pivot, NOT another raw B0 absolute transform.
2. **Quest XR pivot:** ARM64 `run_game::$_2` adds `(+0.32,+0.55)` to captured Y/Z, later native XR view combines head movement with `(-0.32,-0.55)` and +0.04 rotation. Our raw-profile delta is a **head-neutral approximation**, not the full Quest HMD-dependent pose. Blindly adding all these constants to the PCVR game camera would double-count.
3. **Car selector coherence:** Quest gets global guest selection byte `0x92F31`, PC gets current player car `car_kind_11`. Need a synchronous game-frame comparison for identity during transitions; both are 0..29 but no proof that they are always equal.
4. **Runtime admission/validity:** camera entry gates mode1/gameplay/hook installed, but no current-frame exact XR pose handshake; recording only C++ synthetic success is insufficient. Exact model, values, delta, applied/rejected reason and resultant matrix should be one **bounded** event per model/transition (no per-draw logs).

## B. Sky source and stereo route, traced

1. Original `r4dius/outrun2-decomp/src/platform/race_sky.cpp` `race_sky_display_4521c0` lines 94-115: push 3D sky matrix, force original D3DRS_ZENABLE OFF, draw **two** sky layers with their saved rotation and alpha, restore depth ON. Original `race_sky_step_451e90` lines 133-168 changes fade/state during course changes. Blank/flash *at the same transition frame* could therefore involve layer state, not only a GPU bloom filter.
2. Original `race_sky_object_452080` lines 69-93 has a **branch at alpha >= 0.9**: depending on object node count, uses a different one- vs two-pass blend path. This is a genuine original draw-policy discontinuity near full-opacity and could expose stereo/right-eye state inconsistencies; DOES NOT prove an actual user-visible defect by itself.
3. The **actual dedicated cockpit launcher** is `RUN-QUEST-COCKPIT-V2.cmd` -> `-TestProfile CORRECTNESS` -> `OutRunVR-TestProfiles.ps1` `$commonVr` with `'-SkyGlowFactor=0'` line 15. ReleaseParity adds render/reflection/etc flags but does NOT override SkyGlowFactor. The shipped .ini default is `SkyGlowFactor=4`; however the dedicated launcher passes zero. The unrelated non-DX9 backend fallback in the launcher hardcodes 4 but Quest cockpit explicitly requires d3d9. Distinguish what command the user actually executed.
4. At `SkyGlowFactor<=0`, stock mono glow `src/hooks_graphics.cpp` `SkyGlowAllowed()` returns false; R30 `R30CaptureSkyGlowSceneBeforeHud`, `R30ApplyStereoSkyGlow` and `PresentDestR30` explicitly require positive factor. **Thus when this dedicated launch value is effective, the R30 postprocess is NOT the reason the original SKY GEOMETRY disappears.**
5. R7 `src/vr/d3d9/stereo_renderer_r7.inc` ~756-931 classifies fixed-function XYZ perspective draws as world or `SkyRotationOnly` using the **depth-enabled heuristic**, first excluding physical HUD-semantic owners. Rotation-only removes HMD inverse translation and independent eye offset, but still applies HMD rotation and per-eye FOV.
6. This is **not exact original `4521c0` source ownership**. A different fixed-function perspective draw with depth off may be classified as sky; original sky may also use programmable c64 instead of this fixed-function branch. Need a real physical source/Draw receipt to establish which path produces the user's sky pixels.
7. R7 `PrepareDuplicatedDraw()` ~1625: if resource/eye pose/depth/stencil/surface provenance invalid, it marks the frame poisoned and draws **only once**, leaving the right-eye duplicate absent; valid later frames do stereo again. At startup or occasional state reset, that eligibility change can create visible eye instability. This is a grounded, high-priority **candidate**, not a proven root cause.
8. R7 `ReadTrackedRenderState(D3DRS_ZENABLE)` ~967-1018 primarily trusts the StateBlock tracker and occasionally samples live D3D9 state. An unaccounted original state-block transition could change depth heuristic for *sky candidates*; need evidence of live/cached mismatch in same source frame.
9. `DisableStageCulling` in `src/hooks_graphics.cpp` ~2758-3023: VR `StageCullingMode=1` widens projection ONLY inside original PMT-visible call, then restores it. When no latched XR FOV/pose exists, `AfterVisible` with `!scoped` intentionally forces visibility EAX=1. When it becomes available, original PMT visibility result is honored. This is a real visibility-policy discontinuity at startup/pose loss. Which specific **sky PMT nodes**, if any, reach this code is not yet proven.
10. `src/vr/game/outrun_renderer.cpp` `ApplyCullingCameraSync()` ~1331-1435 can temporarily replace game F8/look with HMD-corrected camera during world rendering. Original sky uses independent saved sky rotation and may not consume that live camera at the same point. A per-frame original-sky-vs-culling-camera mismatch remains an additional hypothesis.

### Prioritized hypotheses, not conclusions

| Priority | Candidate | What would prove / disprove it |
|---|---|---|
| 1 | R7 first-frame or stage-transition missing stereo pose, resource or depth synchronization | Within the same frame: `StereoFailureMissingLatchedPose`, `WorldClassificationFailed`, `RightDepthUnsynchronized`, `FrameStereoIncomplete`, `FrameRightDrawFailed`, and actual sky-draw receipt |
| 2 | Sky object fade/alpha>=0.9 switch draws one eye or alpha pass differently | Exact original sky-layer/object id, sky alpha, fixedfn vs programmable draw class, both eye render results at the switching frame |
| 3 | Stage PMT wide-cull fail-open transition | Exact original sky object/node PMT receipt and `GetWideFov` success vs fail-open in the flashing frame |
| 4 | Render-time HMD camera vs original sky rotation mismatch | Same-frame HMD pose seq, original sky matrix/rotation, culling camera before/after, final per-eye view |

**Do not** globally force PMT visibility, re-enable raw B0 or disable SkyGlow when it is already zero; any such speculative change risks more world popping, HUD disruption or large FPS losses.

### Minimal discriminating HMD test (NO new giant per-draw log)

Use the same tested ZIP and course, first with SkyGlowFactor=0, cockpit ON, F11 `QuestCockpitV2NativeSeatProfile=true`, `StageCullingMode=1`; record short start + stage transition clip with left/right eye observation. Then **only one variable** at a time: `StageCullingMode=2` for a short interval (may cost GPU) and return to 1; optionally `VRCullingCameraSync=false` separately. If sky persists with both settings, prioritize the R7 stereo/sky source over culling.

Seat: compare F11 `QuestCockpitV2NativeSeatProfile=true` vs false on **same car** while parked, F12 recenter in each run, then test a slope to expose yaw-only approximation. Original profile/model pointer admission can be observed with *bounded* logging, not blanket telemetry. Do not interpret CI as Quest3 runtime PASS.

## Final disposition

- **Static source path:** verified actual 30-profile data lookup, mode1 camera patch/RAII restoration and existing OpenXR path.
- **Exact Quest native seat parity:** not yet verified, yaw-only delta and global selector timing remain material differences.
- **Sky cause:** narrowed to original sky 2-layer transition vs R7 pose/right-eye classification vs PMT culling eligibility; **no causal attribution** from code alone.
- **Code changes this audit:** NONE. **No game test build / CI repeated**. HMD test of source SHA `743061fc...` is still needed.
