# Quest APK cockpit/seat/glass: focused binary-to-PCVR reproduction contract (2026-10-25)

**Status:** source/binary REVIEW ONLY; no PC gameplay source changed, no HMD runtime proof. Canonical Quest input is user-owned `/home/chatgpt-runner/apk/outrun2.apk` (`org.outrun.quest.vr`, manifest version `0.4.25-music-indicators`), ARM64 `liboutrun_quest_core.so` (21,959,856 bytes, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`). A different embedded `v0.4.11` banner does not override the manifest. Original files and proprietary artwork remain local on N100.

## Confidence model
- **BINARY VERIFIED:** explicit ARM64 instructions, TLS relocations, read/write, fixed values, native symbol names, or known Windows source instructions.
- **CORRELATED:** independently cross-checked against existing Quest/PC reports and public mod source but exact material/scene runtime identity remains unknown.
- **PROPOSED:** clean-room Windows adaptation/acceptance, not APK byte-identical reconstruction.
- **UNTESTED:** physical Quest3 runtime, exact eye pixels, performance, actual material/polygon mapping.

The prior Ghidra 12.1.4 decompilation was incomplete for some GLES/renderer functions (bad instruction/overlapping exception spans). For this review, a lightweight, bounded ARM64 objdump pass was executed on N100 to extend four disassembly windows; **no massive Ghidra full-library analysis or graphics/game source edit**.

## 1. APK native cockpit state and frame contract
| Symbol | Observed evidence | Constraint |
| --- | --- | --- |
| `cockpit_render_active` | 1-byte thread-local flag, native scene-render/vehicle/occupant access | Scope world cockpit work, not menu/effects |
| `cockpit_vehicle_draw` | 1-byte TLS; vehicle draw → mesh/node rendering | Player mesh owner must be scoped |
| `cockpit_occupant_draw` | 1-byte TLS; `Draw::disp_514c30` reads it | Treat passenger vs driver distinctly |
| `cockpit_body_correction` | 64-byte TLS; `PcSceneRenderer::render_frame` produces 16 float stores and `Draw::disp_514c30` reads/processes matrix | 4x4 transformation is actually used, not just a named variable |
| `cockpit_glass_opacity` | 4-byte TLS; `Flush::draw_404700` writer and `GlD3D9Device::flush` reader | Scoped draw opacity, not global alpha |
| `cockpit_glass_premultiplied` | 1-byte TLS; same producer/consumer | Shader/blend convention must match |
| `cockpit_hand_tracking` | 8-byte TLS; `XrRig::locate_hands`, `XrRig::input` and cockpit diagnostics exist | Specific steering rig/controller algorithm is not yet recovered |

`PcSceneRenderer::render_frame` at **ELF `0x10cbf4c`** explicitly reads **guest camera `+0x34A`** and compares it with **`1`** before its cockpit-active/body-correction path (`0x10cbf58` and body writer `0x10cc2ac` → `0x10cc2e0-0x10cc2fc`). This is evidence of an actual **native mode-1 selection check** in the APK producer, not evidence that all other frame logic must use the same condition. The separate original view-switch function `race_camera_view_switch_484a40`, **`0x119240c`**, maintains `0x340/0x344/0x34A/0x34B/0x360` camera fields and transition counters.

The 16-float matrix is read in `Draw::disp_514c30` near **`0xD61124`**, with many FP FMADD operations applying correction to occupant/geometry coordinates. This is stronger evidence than a guessed 64-byte matrix type, but the exact composition order, unit conversion, HMD-to-car anchor, vehicle-specific seat offsets, sign conventions and prediction/correction timing are not fully reconstructed. **Do not call `matrix_B0` the exact APK correction.**

## 2. NEW: precise conditional glass draw state (verified 2026-10-25)
New bounded disassembly: N100 local `apk/_analysis_focus/disasm/glass_draw_full_20261025.asm` covering ELF `0x10b98b0-0x10ba230`, correlated with `glass_flush_extra_20261025.asm`, prior TLS relocations and the original PC PMT renderer.

**Preconditions seen inside APK `Flush::draw_404700`:**
1. A draw-entry flag at `[x25+0x34]` (bit 1) must be set (`0x10b9f68-0x10b9f70`); an entry field at `[x25+0x20]` must equal `1` (`0x10b9f74`). Names/types of these two underlying entry fields are **not recovered**.
2. Render-state getter with numeric ID **20**, interpreted as D3D9-style DESTBLEND, must return **6** (`0x10b9f80-0x10b9f98`, commonly `INVSRCALPHA` in D3D9). Other values skip the opacity specialization.
3. A material/colour record float is loaded at `0x10b9fd0`. It is compared to **0.55 ± 0.001** or **0.425 ± 0.001**. Verified AArch64 IEEE754 immediates: `0xbf0ccccd = -0.55000001`, `0xbed9999a = -0.42500001`, `0x3a83126f = 0.0010000`; decisions `0x10ba004-0x10ba038`.
4. Getter for render-state numeric ID **19** (D3D9-style SRCBLEND) at `0x10b9fd4`: values **2 or 5** select glass scale; `2` additionally sets the premultiplied flag. The ordinary D3D9 enumeration maps 2 to ONE and 5 to SRCALPHA, but any custom converter-layer remapping must be checked rather than assumed.
5. Float select `fcsel` at **`0x10ba058`** takes **`0.25` or `1.0`** based on those predicates. The per-draw TLS opacity is written at **`0x10b9c68`**. Its premultiplied flag is written at **`0x10ba05c`** (or another nonselected-material branch at `0x10ba078`).
6. **State is restored after each draw:** TLS opacity reset to **`1.0`** at **`0x10b9c98`**, and the flag cleared at **`0x10b9ca0`**. Thus **not a global alpha override**.

The verified shader text embedded in the same native ELF includes an epilogue where an opacity multiplies the fragment alpha and conditionally multiplies RGB for a premultiplication path; `GlD3D9Device::flush` obtains TLS pointers at **`0x2fd140/0x2fd15c`**. This supports a source/flush/shader chain, but it still does **not** prove every presumed windshield pixel or the exact effective final alpha. **0.25 is a draw opacity multiplier, not necessarily a displayed pixel alpha of 0.25.**

Pre-existing APK PMT inventory found **31** player-car model variants and **48** distinct dark-tint material candidates, with texture/material diffuse alpha often around 0.55/0.425, raw PMT blend-bit pairs `(src,dst)=(1,5)` or `(4,5)`. These custom PMT bitfields are *not identical* to the D3D9 render-state enumeration used at getter 19/20 without proving the translation. Actual front/side glass face ownership and mesh ID remain **UNVERIFIED**. Do **not** patch every matching alpha in a PC model.

### Clean-room glass replication contract (proposed)
```text
scene + player car ID + named PMT draw/material owner + model/texture identity
  -> check entry bits / category and effective blend state
  -> check diffuse alpha about 0.55 or 0.425 (epsilon 0.001)
  -> if same exact native predicate, scoped opacity=0.25,
     premult=(effective srcBlend==2) when selected
  -> draw ONLY that identified player-glass primitive to each eye,
     preserving D3D9 color/depth order
  -> restore opacity=1, premult=0 and prior blend/depth/shader states,
     including exception/skip/reset path
```
This is an implementation specification, **not copied APK code**. Must log exact car/mesh, material pointer+index, alpha, texture hash, camera mode, per-eye frame ID, active D3DRS 19/20, skip/restore; tag false positives (NPCs, water, HUD, scenery) before a live hook.

## 3. Vehicle, driver, eye and hand scope
APK vehicle and occupant TLS are distinct. `PcSceneRenderer::display_race_car` checks/transitions scoped vehicle state, while `Draw::disp_514c30` checks cockpit render/occupant flags and consumes body-correction. Native `race_robot_driver_display_4879b0` dispatches original `RobotDisplay` using car flags `(flags&0xC000)==0x4000`. Do not treat this as identifying a driver or erasing the passenger.

Quest OpenXR `XrRig::locate`, `view_matrix` (`0x2d468c`), `projection_gles` (`0x2d481c`), per-eye `bind_eye` and swapchain acquisition exist. Windows should preserve the game/seat transform and apply per-eye OpenXR head pose **once**, without feeding corrected eye pose back into the game simulation camera. Only relevant world/cockpit render draws inherit cockpit transform; SceneEffect/flat HUD and menu/theater do not.

`XrRig::locate_hands` (ELF `0x2d67cc`), `XrRig::input` (`0x2d6058`) and native debug text `[Quest cockpit] model=%d hands=%u/%u grip=%u/%u steer=%.3f radius=%.3f tilt=%.3f` prove tracked controller/steering instrumentation exists. They **do not prove** how hand poses map to steering-wheel rotation, driver arm bones or MOZA R3 FFB; separate reverse trace required.

## 4. Current Windows R26+HUD implementation, actual focus branch at read time
Read GitHub `vr-d3d9ex-focus` source `src/hooks_graphics.cpp` blob `f30c4c2751360d55fcfea91328e141728013476d`, `src/vr/game/driver_seat_{camera_math,car_space,render_pass,occupant}.hpp`, `OutRun2006Tweaks.ini`.

- `VRDriverSeatCameraEligible` uses `PersistentDriverSeatSessionEligible(VREnabled&&DriverSeatView, gameplay)` and **ignores** native `+0x34A` mode and transition timer. All camera modes 0/1/2 can accept camera offset and activate body/driver/near plane while DriverSeatView is true. This conflicts with APK's mode-1 render producer and is consistent with user-reported all-three-view jitter, but **a complete causal frame trace has not been captured**.
- `VRDriverSeatCameraPose` uses the smoothed native `cam_pos_F8/look_pos_104`, optionally axes of `player->matrix_B0`, and independently computes translation upon each eligible call. Last-valid fallback only handles invalid inputs; valid but discontinuous pose is accepted. It is **not** one immutable, latched car/seat frame transform.
- The old absolute player origin failed in the user's actual Quest3 test, putting the camera inside geometry. Replacing it blindly or simply reinstating a hard per-frame mode check causes bounce. The desired fix is a latched, vehicle-specific **seat transform**, native-mode transition policy, and one per-frame snapshot, not stock camera offsets replayed for modes 0/2.
- Current PC `DriverSeatFullCar` forces player-only render-state 1 at `EXE+0x69764`. Driver suppression at `RobotDisplay` `EXE+0x114C10` uses driver/heroine character tables and avoids removing the passenger. A temporary player-only model matrix scale hook is at `EXE+0x697BD`; it changes *render size*, not a verified APK scale.
- `VRDriverSeatGlassMaterialProbe` hooks `EXE+0x4901`, just logs <=32 candidate material pointers after a blend prefilter. It does **not** isolate a player/windshield draw or change alpha; unrelated world/NPC candidate material records may be logged.
- The actual shipped focus INI sets `DriverSeatView=false`, `DriverSeatCarSpaceBasis=false`, `DriverSeatVehicleScale=1.15` (despite C++ default 1.0), `DriverSeatForward=-1.35`, `DriverSeatRight=-0.32`, `DriverSeatUp=0.65`, `DriverSeatNativeMode=1`, `DriverSeatGlassOpacity=0.30`, `DriverSeatGlassMaterialTrace=true`. **GlassOpacity=0.30 is NOT connected to actual game draw state**.
- Current original PC material path: `DrawObject_Internal` EXE VA `0x405360`, material record `0x58` (88 bytes), `0x404901` pushes material, `0x408C80` applies it. Match scoped player PMT and draw owner before hooking alpha.
- Camera hook temporarily substitutes camera vectors before `CalcCameraMatrix`, restores original work after, and `Clr_SceneEffect` rebuilds the camera again. Track per-frame sequence and eliminate view-matrix wobble without changing native camera state. Android's TLS body correction is separate from that PC detour.

## 5. Reproduction order & negative/regression gates (proposed, NOT implemented)
1. **Snapshot & mode owner:** bind user-selected cockpit to player ID, race camera mode 1, stable frame generation and one vehicle-local seat frame. During camera switches suspend or transition cockpit coherently; never toggle only one of camera/geometry/occupant/near plane. Log input native camera, car matrix, HMD pose, selected anchor and call-site count per frame.
2. **Body pose:** reconstruct 16-float correction composition from APK `render_frame` (includes `0x10cbf58`/ `0x10cc2e0` writer), compare `Draw::disp_514c30` matrix consumer. Confirm sign, units and actual dashboard/wheel reach per car with snapshots across straight/corner/drift/loop. Do not use a constant `1.15` player-scale unless calibrated.
3. **Vehicle/occupant:** restrict to actual player vehicle mesh; retain cockpit interior/dash/window/steering; exclude verified driver *only* and keep heroine/passenger. Restore game render-state 0/1 outside cockpit.
4. **Glass:** recover player-window triangle/material identity and exact alpha pipeline; implement precise 0.55/0.425 ±0.001 + dstBlend=6 + srcBlend=2/5 conditions and draw-scoped 0.25 opacity, separate premult and restoration. Verify glass/backdrop through both eyes, front and sides, day/night, with water/smoke and HUD unchanged.
5. **OpenXR:** independent left/right projection and depth (near-plane suitable for dash/HMD lean); scoped SceneEffect; XR recenter only changes headset reference; world-space car seat tracking never accumulates HMD movement twice.
6. **Hands/controller:** only after proven bone/hand rig. MOZA R3 input/FFB is not equivalent to Quest tracked controller poses.
7. **Tests:** native camera modes 0/1/2 and switch, GOAL/restart/pauses, 360SP plus another vehicle, vertical loop/collision, model switch, near-plane, left/right eyes, smoke/glass alpha restoration, long-drive no jitter. Use GitHub Actions Windows x86 DLL + x64 host, complete CMD/PowerShell/INI launcher packages; **physical Quest3/VDXR validation is required**. Keep `DriverSeatView=false` user-stable default until pass.

## 6. Remaining decompilation blockers
- Exact producer→material→triangle/texture lookup for front and side windows and identity by car/LOD; static 31/48 candidate counts cannot substitute for proof.
- Full native `render_frame` to `Draw::disp_514c30` matrix composition with car/HMD units, time source, recenter, and per-eye application.
- Precise `GlD3D9Device::flush` shader transformation/blend equation for glass, GPU discard/depth order and behavior on early returns.
- Verified native cockpit settings/defaults and hands-to-wheel/occupant animation; don't infer them from symbols.
- No direct APK real-device HMD comparison performed for this review.

**Evidence files (N100 local, no game content on GitHub):** `apk/_analysis_focus/disasm/glass_draw_full_20261025.asm`, `glass_flush_extra_20261025.asm`, `cockpit_renderframe_full_20261025.asm`, `occupant_scope_full_20261025.asm`, and prior `glass_draw_writer_20261016.asm`, `glass_gl_reader_20261016.asm`, `camera_view_switch_20261016.asm`, `car_body_correction_20261016.asm`, `cockpit_robot_scope_20261016.asm`. Existing docs: `QUEST_CAMERA_GUEST_CORRESPONDENCE_20261016.md`, `QUEST_COCKPIT_GLASS_PATCH_20261016.md`, `QUEST_COCKPIT_GLASS_RUNTIME_HOOK_20261017.md`, `QUEST_APK_FULL_VR_FUNCTION_COCKPIT_ADOPTION_20261016.md`, and `docs/reviews/dx9ex/manual/DRIVER_SEAT_THREE_VIEW_JITTER_ISOLATION_20261023.md`.

**CODE_CHANGE=NO; BUILD=NOT_RUN; RUNTIME_VALIDATION=UNTESTED (APK static), user PC jitter A/B previously observed.**
