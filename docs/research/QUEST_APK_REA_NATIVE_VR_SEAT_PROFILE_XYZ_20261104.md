# Quest APK REA: original native VR seat XYZ profile-table lookup and XR pose composition

**Date:** 2026-11-04 KST  
**Purpose:** locate *actual data sources* for Quest's correct cockpit seating, NOT conflate the old original PC view1 camera table with Quest's separate live VR seating input.  
**Status:** `NATIVE_ARM64_CONTROL_FLOW=VERIFIED`; `PC_GUEST_PROFILE_SOURCE_BYTES=VERIFIED`; `QUEST_GUEST_RUNTIME_BYTES=UNTESTED`; `QUEST3_HMD_ALIGNMENT=UNTESTED`; `SOURCE_CHANGE=RESEARCH_ONLY`.

## 1. Essential new distinction: TWO DIFFERENT seat-related tables

The original PC guest 1st-person mode1 camera reads `0x818BB0` (initialized from PE `0x5BA4E0`), 30 records ×36 bytes, first three XYZ. It is explicitly read in both Quest ELF `race_camera_eye_look_485590` `0x119275C..0x1192790` and original PC `485590`. Pair i and i+15 have the same 3 XYZ. **This is not, by itself, the native Quest final VR seat position.** Earlier test branch set extra static back/down offsets of 0.35/0.18 and later zero; neither proves matching Quest view.

**New:** Quest `run_game::$_2::operator()()` at ELF `0x2E13AC` references the **independent guest profile-pointer table at PE VA `0x5B2F68`**, indexed by a byte read from guest state (ARM64 `0x2E1434..0x2E149C`, selector limited to 0..29). Each pointer references a 0x128-byte (296-byte) record. The callback reads independent XYZ floats at record **`+0x4C`, `+0x50`, `+0x54`** into a three-float capture array: ARM64 `0x2E1598` (X), `0x2E1650` (Y), `0x2E16C4` (Z). They are `guest-image float32`, not presumed OpenXR metres.

These 30 profiles **must not be reduced to 15 by modulus 15**. Example: index0 Z=-0.390 vs index15 Z=-0.450, index7 Z=-0.442 vs index22 Z=-0.350, index12 (-0.351,0.750,-0.458) vs index27 (-0.351,0.720,-0.410).

### Recovered 30 guest-profile XYZ values

**Source of NUMERIC values:** user's canonical original PC retail PE `OR2006C2C_CANONICAL_FOR_GLASS.EXE`, SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`. File-backed PE `.rdata` VA `0x5B2F68` contains the 30 record addresses at sequential stride `0x128`: index0 `0x5B0CB8`, index29 `0x5B2E40`. This is corroboration of Quest's **addresses and lookup algorithm**, **NOT** a claim that Quest in-memory guest data definitely equals this PC retail EXE for every build.

| Selector index | X | Y | Z |
|---:|---:|---:|---:|
| 0 | -0.353 | 0.627 | -0.390 |
| 1 | -0.331 | 0.688 | -0.258 |
| 2 | -0.357 | 0.635 | -0.396 |
| 3 | -0.319 | 0.673 | -0.244 |
| 4 | -0.345 | 0.773 | -0.019 |
| 5 | -0.325 | 0.698 | -0.472 |
| 6 | -0.330 | 0.620 | -0.400 |
| 7 | -0.365 | 0.679 | -0.442 |
| 8 | -0.351 | 0.674 | -0.458 |
| 9 | -0.331 | 0.766 | 0.035 |
| 10 | -0.353 | 0.650 | -0.340 |
| 11 | -0.320 | 0.640 | -0.340 |
| 12 | -0.351 | 0.750 | -0.458 |
| 13 | -0.351 | 0.770 | 0.000 |
| 14 | -0.351 | 0.674 | -0.025 |
| 15 | -0.353 | 0.627 | -0.450 |
| 16 | -0.331 | 0.688 | -0.258 |
| 17 | -0.357 | 0.635 | -0.396 |
| 18 | -0.319 | 0.673 | -0.244 |
| 19 | -0.345 | 0.773 | -0.050 |
| 20 | -0.325 | 0.698 | -0.472 |
| 21 | -0.330 | 0.620 | -0.400 |
| 22 | -0.365 | 0.679 | -0.350 |
| 23 | -0.351 | 0.674 | -0.458 |
| 24 | -0.331 | 0.766 | 0.035 |
| 25 | -0.353 | 0.650 | -0.340 |
| 26 | -0.320 | 0.640 | -0.340 |
| 27 | -0.351 | 0.720 | -0.410 |
| 28 | -0.351 | 0.770 | 0.000 |
| 29 | -0.351 | 0.750 | -0.025 |

Contrast the separately parsed PC view1 camera at `0x5BA4E0`: model0 (-0.353,0.990,-0.345), whereas the new *VR profile source* index0 is (-0.353,0.627,-0.390). The new Y is substantially lower. This directly motivates why keeping only the original mode1 camera gives the user a higher/forward bumper-like viewpoint.

## 2. Exact native runtime producer and consumer chain

1. Quest `android_main` ELF `0x2DBA60..0x2DBA98` initializes stack XYZ `sp+0x350..+0x35B` to `0,0,0` and toggle byte `sp+0x48=0`. **Those zeros are initial storage, not the final sitting position.**
2. `android_main` `0x2DBAB4..0x2DBB10` constructs `run_game::$_2` PadSnapshot closure (vtable `0x1237FD8` +16) capturing its writable three-float destination (`[closure+0x40]=sp+0x350`) and input view-mapping structure (`[closure+0x38]=sp+0x68`), plus view/angle toggles.
3. After an original guest camera profile selection changes, `run_game::$_2` resolves selector's profile from `0x5B2F68[selector]`. It reads the three profile float32 fields at +4C,+50,+54 through the mapped guest memory reader, writing captured XYZ at `0x2E1598`, `0x2E1650`, `0x2E16C4`. It also marks a candidate override toggle `[closure+0x20]` via `0x2E14F0`.
4. **Instruction-level destination proof, rechecked 2026-11-05:** `0x2E14E8` loads `x12=[closure+0x40]`, `0x2E1598` stores guest X to `[x12]`, `0x2E1650` stores guest Y to `[x12+4]`, and `0x2E16C4` stores guest Z to `[x12+8]`. Then `0x2E17B0..0x2E1808` loads **the same captured XYZ buffer's Y/Z** and adds native ELF float32 rodata `0x1722C8` = `(+0.319999993,+0.550000012)`. It applies the pair **after** successful profile loading and must not be reapplied to OpenXR eye poses. A temporary zero-initialized stack location does not prove this was a different controller-only vector: the guest-profile stores overwrite it. Native eligibility still depends on the original captured toggle and guest-state transitions; the PCVR hook approximates that by limiting its consumer to mode1.
5. In `android_main` ELF `0x2DC030..0x2DC0F0`, `run_game::$_5` callback captures `[closure+0x40]=sp+0x48` toggle, guest game-state pointer, `[closure+0x50]=sp+0x350` XYZ source. `run_game::$_5` at `0x2E3690..0x2E36C8` sets `PcRaceCameraInputs[+0]=toggle && guestState==0x10` and copies float XYZ to [+4,+8,+12] on a successful upstream path.
6. `race_camera_eye_look_485590` ELF `0x1192794..0x11927C8` uses those XYZ in native camera view 1 **only when enabled**, replacing the ordinary per-model view1 anchor for both temporary eye and target before the game's original swing/blend/ground transforms.
7. **2026-11-10 correction after bounded re-disassembly:** `run_game::$_2` `0x2E1B00..0x2E1BF0` / `0x2E1C20..0x2E1D18` must NOT be treated as a generic stereo-eye camera composer. The callback's closure+0x10 is the verified `TouchFrame` input; immediately before these branches, closure+0x28 is passed as the `VirtualWheel::update` this object at `0x2E1A14..0x2E1A2C`, and successful update reads its steering float from `VirtualWheel+0x04` at `0x2E1A34..0x2E1A3C`. The first later matrix branch reloads that exact object and tests `VirtualWheel+0` at `0x2E1AF0/0x2E1B00`; the mirrored branch tests `VirtualWheel+1` at `0x2E1C24`. Its +0.55/+0.32, +0.04 and -0.32/-0.55 sin/cos/atan2 calculations therefore belong to the two tracked-hand/virtual-wheel state paths, not an unconditional physical-wheel cockpit eye transform. The matrix outputs remain useful for hand/virtual-wheel research, but must not be re-applied to ordinary MOZA mode1 camera eyes.
8. Quest `XrRig::locate` `0x2D69C8` uses `xrLocateSpace`, recentered reference and `xrLocateViews` for exactly two eyes. The **final rendered eye location is dynamic**: it cannot be replaced with just a constant XYZ.

## 3. Native constants, NOT game-space XYZ literals

- `0x1722C8` ELF original rodata two float32: `0.319999993`, `0.550000012`, exact source for the Y/Z native capture adjustment in `run_game::$_2`. Verified by mapping ELF64 PT_LOAD to file bytes; source ELF SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8bcbced6120b6`.
- `0x2E1B18`: `+0.55`, `0x2E1B20`: `+0.32`, `0x2E1B70`: `+0.04`; `0x2E1B88`: `-0.32`, `0x2E1B98`: `-0.55`. These constants are now proven to sit inside the VirtualWheel/TouchFrame hand-state matrix path. They are **not a one-time manual forward/up offset and not a generic cockpit-eye correction**.
- Applying the rodata pair at the **captured camera-source input** remains verified; applying it again as a Windows world-space or OpenXR headset offset is incorrect. The formerly suspected `0x2E1B...` generic eye-pose parity gap is now closed as a false lead: that branch is VirtualWheel/TouchFrame hand-state owned. Ordinary stereo eyes should continue to follow the independently verified `XrRig::locate` two-eye contract.

## 4. Correct PCVR engineering direction

- **Source of truth:** actual selected guest profile index 0..29 + `0x5B2F68[selector]` + profile offsets `+4C,+50,+54`, not only `0x818BB0`. Validate original executable version/loaded content and never treat index+15 as identical for this table.
- Snapshot profile coordinates at a verified native mode1 game-frame owner; apply the **Quest formula and coordinate spaces** only once alongside VR recenter/HMD inverse. Do not double car B0, alter original 2D view1, other cars, menus, GOAL, or FFB.
- A controlled hardware run must measure `(selector,profile,mode,enabled,originalEye,originalLook,capturedXYZ,XR pose,final per-eye)`, including switching models, and verify seat location against Quest APK. **No user Quest-runtime guest RAM snapshot has been recorded**. No C++/DLL patch has been deployed under this research TASK.
- The original 2026-11-03 branch `17278584...` merely verifies the *other* `0x818BB0` view1 table and zeros the former hand-tuned seat offsets; it still lacks this separate Quest native profile+XR composition. It therefore does **not yet replicate the APK's known-correct seated location**.

## 5. Reproducible read-only evidence (no assets pushed to GitHub)

Original user-owned files under N100 authorized home:

- `apk/_static_out/liboutrun_quest_core.so`: original Quest ARM64 ELF.
- `apk/_analysis_focus/OR2006C2C_CANONICAL_FOR_GLASS.EXE`: original 2006 PC executable.
- `apk/_analysis_focus/quest_20261103_pad_snapshot_run2.asm`, `quest_20261103_android_main_for_seat.asm`, `quest_20261103_guest_draw_event_run0.asm`: bounded disassemblies collected from original ELF (reviewed only, not embedded in this repo).
- `apk/_analysis_focus/quest_20261104_camera_keymap_pe.py`: PE section-to-file-backed VA mapping and 30 profiles.
- `apk/_analysis_focus/quest_20261104_seat_const_rodata.py`: ELF PT_LOAD mapped rodata at `0x1722C8`.
- Previous independent REA evidence `apk/_analysis_focus/rea_slices_20261026/run_camera_override.rea.json` with evidence ID `ev_58ae0041f7fb011b01bcd072aa0644918c67053ef02bbe3bc87a12c0d0a9a857`, Ghidra 12.1.4, plus the native instruction window. Do not use pseudocode warnings as proof where ELF ARM64 disagrees.

**Conclusion:** new ORIGINAL QUEST CAMERA XYZ source pinpointed, with numeric 30-entry PC guest data and native XR composer constants. This is substantially different from earlier 15-entry view1 camera anchor. `VISUAL_RUNTIME_PARITY=UNTESTED`; a guest memory snapshot and real Quest3 test remain required.
