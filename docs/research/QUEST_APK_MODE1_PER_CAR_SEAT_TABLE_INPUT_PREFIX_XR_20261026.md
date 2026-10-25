# Quest APK cockpit mode-1 camera: original per-car anchor tables, input override prefix, and XR recenter (2026-10-26 KST)

## Scope and evidence quality
Immediate read-only analysis requested by the user, in support of PCVR implementation on `thp32tt/OutRun2006Tweaks/vr-d3d9ex-focus` / R26+HUD. No Windows game source, APK binary, or PMT content was changed; no CI/build or Quest3 validation. **BINARY VERIFIED** means direct ARM64 or original PE data checked; **CORRELATED** means an independent public PC reverse implementation matches; **UNTESTED** means runtime/behavioral equivalence unproven. This is NOT a byte-identical recovery of the original authored C++.

User-owned binaries inspected on N100:
- Native Quest ELF `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8bcbced6120b6`.
- Canonical original PC EXE `OR2006C2C_CANONICAL_FOR_GLASS.EXE`, SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, image base 0x400000, 3,674,112 bytes.

## 1. NEW: the Quest renderer truly loads original PC camera parameter tables

ELF `PcSceneRenderer::invoke` at `0x10C6CDC`, entry at `0x10C6E1C..0x10C6E60`, loads three `EmbeddedCameraTable` pointers with exact byte lengths **0x64C, 0x438 and 0x5460**, respectively. `0x10C7178` invokes `camera_init_484ee0`; `0x10C7358` invokes `camera_control_485fe0`. It is therefore an observable original Quest runtime dependency on the same game camera tables, not merely a suggested copy from a separate PC source.

Extracted by parsing original PE `.rdata` on the user's N100 with strict bounds checks (SHA hashes computed for table byte windows, no proprietary table data uploaded):

| Original EXE VA | Original bytes | Table shape / per-record stride | SHA256 of original table window |
|---|---:|---|---|
| `0x5B4A30` | `0x64C` (1612) | 31 view entries ×52 bytes | `4f215e53376e9e4e965a0ad6b19476f92fbb0a8b4eebb7359623855a06295d8b` |
| `0x5BA4E0` | `0x438` (1080) | 30 car entries ×36 bytes | `43b7438262d2f8f7a581bc56e756fb2b5c25509998d203b6e87a5993b952f3fb` |
| `0x5B5080` | `0x5460` (21600) | 20 camera modes ×30 cars ×36 bytes | `01a14852bdacdf3031edb641e49ad07eb1514f97c7c082ff50ff2b1e217c86f7` |

All parsed table entries were finite IEEE754 float32. The `0x818FE8/0x818BB0/0x813750` **live addresses are zero-filled .data virtual storage** in the original PE file; they require runtime copy/initialization from the embedded ROM tables. Do not treat the BSS addresses as file offsets containing initialized seat data.

Cross-reference: `r4dius/outrun2-decomp/src/platform/embedded_camera_data.cpp` explicitly binds the three EXE VA windows; `src/driving/pc_race_camera.cpp` uses their live counterparts. Quest native ELF independently confirms the exact table sizes and pointers.

## 2. NEW: original Quest mode-1 camera has an extra conditional anchor override missing from independently recovered PC path

Original ELF `outrun::driving::race_camera_eye_look_485590` at `0x1192624`, size6592:
- `0x1192714..0x1192734`: obtains `camera[+0x34A]` mode and signed `car[+0x11]` car-model index.
- **Only when mode==1**, `0x1192738..0x1192758` calculates `car_model * 0x24`, validates the available model table size, and reads `PcRaceCameraInputs` `Bytes` from +0x30/+0x38.
- `0x119275C..0x1192790`: `copy_words` of the model record's first 3 float32 into the temporary view entry's first 3 floats, and again into floats 3..5.
- **Previously overlooked QUEST-SPECIFIC branch:** `0x1192794` tests the first byte of the `PcRaceCameraInputs` object (`ldrb w8,[x24]`), and if enabled `0x119279C..0x11927C8` copies **`float32 at inputs[+4,+8,+12]`** over *both* temporary 3D vectors. This establishes a 16-byte opt-in override prefix and uniform eye/target anchor source. **The source of the enable byte and real-world activation rate are NOT proved.**
- `0x11927DC..0x11927E4`: target vector **Z -= 1.0f** after the override (or default) path.
- `0x11928C8..0x11928E0`: also subtracts entry `f32[11]` (entry byte+0x2C) from the eye Z in common camera code.
- Modes2..21 `0x11927EC..0x1192864`: instead index per-view×per-model table by `(view-2)*30+model`, stride0x24, copying distinct 3-float eye and target vectors.

The first 16 bytes of Quest `PcRaceCameraInputs` form a **layout prefix that does not exist at the start of the independently reconstructed PC `r4dius/outrun2-decomp/src/driving/pc_race_camera.hpp` struct**. On Quest, model table pointer+length sit at +0x30/+0x38; view2..21 pointer+length at +0x40/+0x48. Do not port the PC struct's offsets unchanged to parse this Quest native function.

### Recovered bounded pseudocode (clean-room semantics, not original source)
```cpp
// Only for the native game's race camera algorithm, view == 1.
// Bounds and model identity must be validated before reading.
auto anchor = original_model_camera_rom[car_model].first_xyz;
if (quest_inputs.override_enabled_byte != 0) {
    anchor = quest_inputs.override_xyz; // float32 at +4/+8/+12
}
temporary_view.eye_xyz    = anchor;
temporary_view.target_xyz = anchor;
temporary_view.target_z  -= 1.0f;
temporary_view.eye_z     -= temporary_view.extra_offset_at_0x2c;
// Then the original game camera swing/blend/course-height stage runs;
// original temporary view entry's initial floats are eventually restored.
```
The Quest `attach_pc_scene::$_7` callable **`0x2D17DC..0x2D1908`** was independently found by ELF symbols as `bool(PcRaceCameraInputs&)`, and its read/write path populates timed/gameplay camera data, ground-query callback, etc. It does not itself prove any nonzero override flag; `PcSceneRenderer::invoke` performs extensive local input initialization. Thus `override_enabled` is a **capability in ELF**, not a demonstrated active user feature.

## 3. NEW original PE structural result: only 15 unique effective mode-1 seat anchors across 30 car records

Read-only comparison of all 30 × 36-byte original records:
- Every `car[i]` **first 3 float32** matches `car[i+15]` for i=0..14 (15/15 pairs).
- 14 of 15 pairs match **all** 36 bytes.
- Pair i=9 vs i=24 differs **only** at float index8 (record byte+0x20): about 1.17 vs0.17, **not** among the 3 mode-1 seat-anchor floats.
- Result: **15 distinct mode-1 XYZ anchors**, though the complete 36-byte records have 16 unique values. Do not infer what the i+15 variant represents (car color, trim etc.) without separate evidence.
- Anchor coordinate examples in original game units: model0 (-0.353,0.990,-0.345), model1 (-0.331,0.995,-0.320), model2(-0.357,0.985,-0.350), model4(-0.345,1.170,-0.040). These are **not calibrated OpenXR meters**. Model i=9 and i=24 receive the same first 3 anchor values even though a non-anchor record float differs.

**PCVR implication:** for initial camera-basis reconstruction, use the existing original game's **per-model view1 table**, not a single constant or experimental scale 1.15. Separate the guest camera's game-unit basis from HMD room-scale tracking and never apply the table as a raw OpenXR meter translation.

## 4. Verified Quest OpenXR recenter and two-eye composition

Original ELF `XrRig::locate` at `0x2D69C8` (size656):
1. `0x2D6A34` calls `xrLocateSpace`, checks `XrSpaceLocationFlags&3==3` at `0x2D6A44..0x2D6A50`.
2. `0x2D6A54..0x2D6A5C` decides to initialize/recenter reference orientation if rig byte +0xC4 is zero or the incoming force-recenter flag bit0 is true; `0x2D6A90` calls `atan2f` with head quaternion to calculate yaw and `0x2D6AA4` uses `sincosf` half angle to construct a yaw reference quaternion.
3. Byte `XrRig+0xC6` at `0x2D6AD4` chooses full reference orientation and overrides the yaw-only initialization when enabled; position is copied from `xrLocateSpace` reference pose. Byte +0xC4 becomes recentered latch.
4. `0x2D6B68` calls `xrLocateViews` with two-eye capacity, accepts only **count==2** and flags `&3==3` at `0x2D6B78..0x2D6B94`.
5. `0x2D6BA0` calls `inverse(referencePose)`, and **twice** `compose(referenceInverse,eyePose)` at `0x2D6BB4` and `0x2D6BDC` to emit respective left/right eye poses, copying eye FOV data as well. Success returns1; invalid tracking returns0, not a synthesized normal pose.

**PCVR implication:** keep eye pose on a shared per-frame tracking generation, reference-space recenter generation and dual-eye validity. Vehicle model correction, camera game view and XR room-scale head adjustment are separate transformations. The original Quest XR routine does not settle exact Windows view-matrix multiplication handedness.

## 5. Camera transition state and game-coordinate basis

Native `race_camera_view_switch_484a40` ELF 0x119240C and `race_camera_view_timers_4832f0` ELF 0x1192130:
- camera `+0x340` countdown, `+0x342` initial, `+0x344` hold, `+0x346` transitional timer, `+0x348` starting timer; `+0x34A` current view, `+0x34B` previous view and `+0x360` event mode.
- Input `featureMask & 0x40000` + input byte0 permits normal 0→2 cycle with staged save `race_camera_save_4833e0(...,30)`; special camera modes (e.g. 0x1B/0x1C/0x1D) get timed replacement/restoration.
- Native `race_camera_car_matrices_484810` ELF `0x1191260` selects a signed `view*0x34` table entry and computes vehicle-world/steering/suspension camera reference matrices into camera `+0x280`, `+0x200`, `+0x240`, with `pc_matrix_push/identity/translate/rotate/get` calls. Original camera view is not a single static local translation.
- The user reported that PCVR `DriverSeatView=true` caused all three views to shake. Different camera game states and multiple VR pose consumers can cause conflicts, but **no runtime trace yet isolates that as the actual observed cause**.

## 6. Replication instructions and unresolved gates

N100 local research files (not public binary uploads):
- `apk/_analysis_focus/quest_20261026_camera_symbol_focus.py` plus `quest_20261026_camera_disasm.py` and seven native ARM64 instruction windows in `quest_20261026_camera_asm/`.
- `quest_20261026_original_pe_table_probe.py`; `quest_20261026_pe_camera_tables_extract.py` and PRIVATE results `quest_20261026_camera_tables_PRIVATE.json`; `quest_20261026_model_variants.py` and `quest_20261026_model9_diff.py`.
- `quest_20261026_eyelook_input_offsets.py`, `quest_20261026_input_lambda_symbols.py`, `quest_20261026_camera_inputs_fill_disasm.py`, `quest_20261026_invoke_camera_calls.py`, `quest_20261026_invoke_ctor_scope.py`.

Remaining:
- Determine writer/lifetime for `PcRaceCameraInputs.override_enabled` byte0 and frame construction to say whether alternate anchor is used in real Quest gameplay.
- Identify the exact eye anchor transform multiplication, seated physical calibration, choice of suppress driver nodes but retain passenger, steering animation skeleton bones, and per-mesh glass polygon/material IDs.
- Compare HMD real frames with stable R26+HUD without double pose injection.
- Keep `DriverSeatView=false` safe default until controlled tests.

Status: `BINARY_REVIEW=PASS`, `CLEAN_ROOM_CONTRACT=PARTIAL`, `SOURCE_CHANGE=NO`, `HMD_TEST=UNTESTED`, `CI=NOT_RUN`, `ORIGINAL_FULL_SOURCE_NOT_RECOVERED`.
