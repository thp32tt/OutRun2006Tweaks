# Quest standalone APK cockpit recovery: corrected Ghidra load-base, 3 focused passes (2026-10-25)

## Status and scope
**USER-REQUESTED IMMEDIATE ANALYSIS, NOT SCHEDULED.** User-owned offline APK `/home/chatgpt-runner/apk/outrun2.apk`. Target `liboutrun_quest_core.so` SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`, **recomputed from the actual N100 ELF on 2026-10-25**.

**Findings: materially new decompilation/algorithm evidence. CODE_CHANGE=NO, BUILD=NOT_RUN, HMD_RUNTIME_VALIDATION=UNTESTED.** The stable R26+HUD DX9Ex mod remains unchanged. No complete original C++ source claim. Raw decompiler output, original ELF and game material stay on user's N100, not in GitHub.

## 1. ROOT CAUSE of previously misleading Ghidra 'success'
- `readelf/objdump` ELF symbol virtual address: e.g. `cockpit_fragment=0x002F7734`.
- The persisted Ghidra project `OutRunQuest` has `IMAGEBASE=0x00100000`. **Correct Ghidra address = ELF symbol VADDR + 0x00100000**.
- First byte sequences proved actual mapping:
  - ELF `0x002F7734` -> Ghidra `0x003F7734`: `ff 83 01 d1 fd 7b 02 a9...` = function prologue `sub sp,sp,#0x60` and `stp x29,x30...`.
  - ELF `0x010B9894` -> Ghidra `0x011B9894`: matched native `Flush::draw_404700` bytes.
  - ELF `0x010CBE9C` -> Ghidra `0x011CBE9C`: matched `PcSceneRenderer::render_frame`.
  - ELF `0x00D60FD4` -> Ghidra `0x00E60FD4`: matched `Draw::disp_514c30`.
  - ELF `0x0119240C` -> Ghidra `0x0129240C`: matched native camera view switching.
- Older `RepairDecompileFocus.java` passed *unadjusted* ELF addresses to Ghidra; it often decoded unrelated code or fake stubs such as `halt_baddata()` yet marked `decompileCompleted=true`. It is **not reliable evidence of a recovered source**.
- Corrected scripts verify symbol length with `readelf -Ws`, set function body to that exact extent, disassemble each 4-byte ARM64 instruction, then invoke Ghidra DecompInterface on the *rebased* address.
- **Qualification:** the function-body fix eliminates the wrong-address failure. But Ghidra may still infer invalid out-of-function control flow (PIC, exception unwind, indirect branch or tail call), and generated C is **not verified equivalence**. Do not declare recovered source merely from `decompileCompleted=true`.

## 2. Three consecutive live recovery passes
Original file-local manifests on N100:
1. `apk/_analysis_focus/correctbase_20261025/manifest.tsv`;
2. `apk/_analysis_focus/correctbase_more_20261025/manifest.tsv`;
3. `apk/_analysis_focus/correctbase_third_20261025/manifest.tsv`.

A separately executed integrity program recomputed ELF SHA256, inspected all 20 manifests/output files and wrote `apk/_analysis_focus/quest20261025_recovery_manifest.json`:
- **20 uniquely targeted function extents**, **13,053/13,053 ARM64 instructions decoded** over those extents.
- **20/20 Ghidra decompileCompleted=true**, **no literal halt_baddata** in the generated C.
- **727,941 generated C-like characters**, **16 of 20 functions still have Ghidra warnings**, e.g. PIC/tail-flow, type propagation, possible incorrect jump tables. Not a claim of 727,941 source characters faithfully recovered.
- Known red flags: `race_camera_view_switch` ELF 536 bytes produced 106,845 characters; `guest_object_render` ELF 536 bytes produced 94,745 characters. This is likely uncontrolled inferred flow or function contamination. Use bounded A64 disassembly and direct branch validation for such functions; never copy the oversized C into PC source.

| Focus | ELF VADDR | Instructions decoded | Generated C chars | Notes |
|---|---|---:|---:|---|
| `cockpit_fragment` shader alteration | `0x2F7734` | 94 | 5,964 | Several control-flow/PIC warnings |
| `race_camera_view_switch_484a40` | `0x119240C` | 134 | 106,845 | **Untrustworthy oversized C**; ASM gate only |
| `view_matrix` | `0x2D468C` | 100 | 1,892 | Quaternion/translation math readable |
| `Flush::draw_404700` | `0x10B9894` | 666 | 32,815 | **Clean relevant material draw branch** |
| `PcSceneRenderer::render_frame` | `0x10CBE9C` | 704 | 18,185 | Mode 1 and 16-float matrix; jump-table caveats |
| `Draw::disp_514c30` | `0xD60FD4` | 1,919 | 73,595 | Scoped occupant correction |
| `XrRig::locate_hands` | `0x2D67CC` | 127 | 8,863 | Independent hand validity/pose |
| `XrRig::input` | `0x2D6058` | 477 | 24,631 | Buttons/axis and action reads |
| `XrSessionHost::clip_matrix` | `0x2DA33C` | 344 | 23,792 | Eye projection and clip guards |
| `PcSceneRenderer::display_race_car` | `0x10C8D00` | 508 | 55,984 | Car display path; type warning |
| `race_robot_driver_display_4879b0` | `0x39FD04` | 27 | 500 | Very compact verified state check |
| `GlD3D9Device::flush` | `0x2FCFDC` | 1,984 | 57,374 | GPU pipeline; indirect call caveats |
| `GlD3D9Device::capture_motion` | `0x300100` | 1,474 | 46,507 | Motion frame data, indirect call caveats |
| `Flush::material_408c80` | `0x10B62C0` | 1,843 | 50,340 | PMT material and state writes |
| `GlD3D9Device::apply_state` | `0x2FF264` | 322 | 7,536 | GL blend/state code |
| `GlD3D9Device::bind_textures` | `0x2FF76C` | 273 | 14,387 | Texture stage setup with PIC warnings |
| `render_object_405360` | `0x10ABC90` | 134 | 94,745 | **Untrustworthy oversized C** |
| `race_camera_eye_look_485590` | `0x1192624` | 1,648 | 95,888 | Game eye/look producer; control-flow caveats |
| `race_robot_driver_chara_487ee0` | `0x39F33C` | 111 | 2,867 | Driver character table logic |
| `XrRig::locate` | `0x2D69C8` | 164 | 5,231 | OpenXR stereo frame generation |

## 3. New concrete recovered cockpit behavior

### 3a. Glass: reconstructed producer state machine from real C-like output + A64
The decompiler now directly exposes these conditions inside `Flush::draw_404700`, on the exact **material draw**, not a global game render state:

1. `DrawEntry` flag at byte offset **`+0x34`** has **bit 1 set** and field at `+0x20` equals **1**. The semantic names of these fields are still unknown.
2. Effective render-state getter **20** (D3D9-style DESTBLEND) returns **6**.
3. Resolve the PMT material record (stride **0x58 = 88 bytes**) and linked color record (stride **0x48 = 72 bytes**), with strict bounds checks.
4. Read material-associated float: `abs(alpha-0.55)<0.001` **OR** `abs(alpha-0.425)<0.001`.
5. Effective render-state getter **19** (D3D9-style SRCBLEND) is **2 or 5**. When matched, opacity is **0.25** (`0x3E800000`); otherwise **1.0** (`0x3F800000`). Set premultiplied flag iff srcBlend==2.
6. Submit the specific draw to native device virtual-call slot **+0xC8** and immediately reset TLS opacity to 1.0 and premultiplied flag to 0, even before the next material iteration.

Grounding: corrected C-like `glass_material_draw.c.txt` lines ~805-849, corroborating instruction VAs ELF `0x10B9F68...`, `0x10BA03C-0x10BA078`, `0x10B9C64/0x10B9C98/0x10B9CA0`. This is a **conditional per-draw opacity modifier**, not proof of the exact front/side-window polygon ID or the final on-screen opacity of every texture. Shader alpha and blend output are still to be separately validated. Do not globally modify water/HUD/smoke.

Clean-room contract:
```text
for exact player-owned material draw:
    if entry.flag34.bit1 && entry.category20==1 && dstBlend==6:
        materialAlpha = verified_pmt_color_float
        if approximately(materialAlpha,0.55,0.001) OR approximately(materialAlpha,0.425,0.001):
            opacity = srcBlend in [2,5] ? 0.25 : 1.0
            premultiplied = (srcBlend==2)
    render identified draw with opacity/premultiplied
    restore opacity=1.0, premultiplied=false
```
This is an independent behavioral sketch, not copied source. Extra guards for geometry owner, blend-state restore on exceptional exit, left/right eye and Reset required on Windows.

### 3b. Native seat/body path
- `PcSceneRenderer::render_frame` explicitly reads game camera byte `+0x34A` and tests `==1` before the cockpit body-correction construction path. Exact Ghidra excerpt has `if (*(char *)(lStack_240+0x34a) == 1)`.
- It pulls floats from game state offsets `0xB0..0x128`, performs extensive dot-products/FMADD composition, and writes **16 32-bit float values** to 64-byte TLS `cockpit_body_correction`. `Draw::disp_514c30` consumes the matrix only under cockpit render/occupant state checks.
- This corroborates **APK renderer has a distinct vehicle/occupant-space correction**, not only a camera position offset. The exact matrix semantics and whether model-space, world-space or view-space multiplication is earlier/later are still **UNPROVEN** due nontrivial generated formulas and indirect call target mapping.
- Current PC `VRDriverSeatCameraEligible` with `PersistentDriverSeatSessionEligible` does not use native mode byte; mode 0/1/2 may take a frame-to-frame displaced camera. The user observed shaking for all three with `DriverSeatView=true` and normal camera motion with false. **Hypothesis:** frame anchor/mode owner mismatch; must instrument frame IDs and actual camera origins before attributing causality.
- Existing PC `DriverSeatVehicleScale=1.15` is not proven to match APK. Preserve stable DriverSeatView=false for real use.

### 3c. Driver identity/visibility
- `race_robot_driver_display_4879b0` generated C is small and matches A64: dispatch original robot drawing only when `(flags & 0xC000)==0x4000`.
- `race_robot_driver_chara_487ee0` generated C accesses a **six-entry indexed character selector**, with out-of-range failure and distinct special returns on skipped conditions. It queries a native character table pointer associated with `Passenger`, but do **not** infer that this proves player driver and passenger always have different work IDs. Need original PC character table/actual draw owner mapping.

### 3d. OpenXR head/hands and projection
- `XrRig::locate_hands` independently populates two hand states, setting validity bytes at frame offsets **+0x74** and **+0x75** only after action/location success and valid tracking flags; calibrated basis transformation occurs before saving the poses.
- `XrSessionHost::clip_matrix` handles per-eye transform, optionally decomposes the game's projection and falls back to near=**0.05**, far=**10000** where valid near/far cannot be inferred. This shows a more involved camera pipeline than a fixed projection. The coordinate conversion/eye timing still needs visual validation, especially canted views.
- The hand state is not enough to claim a complete native steering-wheel-to-hand animation algorithm or compatible MOZA FFB.

## 4. Remaining accuracy issues / next immediate work
1. **Decompiler control-flow hygiene:** misidentified function fallthrough, PIC stubs, landing pads and external branches. Specifically 536-byte guest object draw yielding 94k C and 536-byte camera switch yielding 106k C must be bounded to real branch targets. Never score these as complete high-level source.
2. **Types:** `DrawEntry`, `PcPmtResources`, materials, active player vehicle identity, left/right side glass mesh/texture, vehicle model variants and LOD; recover exact field semantics, not just constants.
3. **Cockpit matrix:** resolve per-float matrix row/column, model/world/view order, vehicle attach point, XR head offset, heading changes, car pitch/loop/respawn, one-frame ownership and which render stages read it.
4. **GL state/shader:** locate exact TLS getter consumers in `GlD3D9Device::flush`, shader epilogue and premult RGB/alpha equation; test what D3D9 state IDs 19 and 20 map to inside the compatibility layer. Confirm source vs premult blending.
5. **Runtime validation:** compare actual Quest APK to PC R26+HUD on 360SP and other vehicles: seat location, driver/passenger, windshield/side windows, both eyes, recenter, camera modes, Reset, HUD/SceneEffect suppression and 120Hz frame timing. No test has been run here.
6. **Completion standard:** user requested original source; a stripped/optimized ARM64 binary cannot generally reproduce its original variable names, comments or exact C++ authoring. Seek **functionally equivalent, typed, testable reconstructed logic** with explicit remaining unknowns.

## 5. Local research artifacts retained on N100
- Original `/home/chatgpt-runner/apk/_static_out/liboutrun_quest_core.so` unchanged.
- New corrected Ghidra scripts: `apk/_ghidra_scripts/DecompileQuestCorrectBase20261025.java`, `DecompileQuestCorrectBaseMore20261025.java`, `DecompileQuestCorrectBaseThird20261025.java`.
- Three associated runners: `apk/_analysis_focus/run_quest20261025_correctbase*.py`.
- 20 individual `.c.txt` files with imperfect machine-generated C-like pseudocode, stored only in `apk/_analysis_focus/correctbase{,_more,_third}_20261025` on user's own N100.
- `apk/_analysis_focus/quest20261025_recovery_manifest.json` evidence index and hashes.
- GitHub contains only independent analysis, instructions and clean-room reimplementation contracts, not the user APK or original game binary.

**RUNTIME_VALIDATION=UNTESTED, CODE_CHANGE=NO, BUILD=NOT_RUN.**
