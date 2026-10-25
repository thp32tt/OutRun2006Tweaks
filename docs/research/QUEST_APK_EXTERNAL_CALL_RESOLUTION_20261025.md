# Quest APK — external call resolution against original ELF (2026-10-25)

## Scope
Authorized offline reverse engineering of the user's own OutRun Quest VR port. This report reconciles earlier REA 6.5.0 / Ghidra 12.1.4 raw-function-slice unresolved calls with original-ELF AArch64 `BL` symbol labels and earlier full-ELF Ghidra call-reference readback. **Direct calls are distinguished from indirect `BLR` calls.** No patch, runtime test, or compilation occurred.

Original ELF: `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. Original-ELF addresses below, NOT Ghidra's rebased addresses (which add `0x100000`).

## 1. OpenXR `XrRig::locate` (ELF `0x2D69C8`, REA 10 unresolved)
All **10 direct call sites** have been mapped by *whole-ELF* `aarch64-linux-gnu-objdump -d -C`. Raw REA slices did not include their callees; thus their earlier unresolved status does not imply missing native code.

| ELF call site | Resolved callee | Category |
|---|---|---|
| `0x2D6A34` | `xrLocateSpace@plt` | OpenXR API |
| `0x2D6A40` | `outrun::quest::(anonymous namespace)::checked(XrResult,char const*)` (`0x2D4DC8`) | Own ELF implementation |
| `0x2D6A90` | `atan2f@plt` | C math |
| `0x2D6AA4` | `sincosf@plt` | C math |
| `0x2D6B68` | `xrLocateViews@plt` | OpenXR API |
| `0x2D6B74` | same own `checked` at `0x2D4DC8` | Own ELF implementation |
| `0x2D6BA0` | `outrun::quest::inverse(XrPosef const&)@plt` | Project function through PLT |
| `0x2D6BB4`, `0x2D6BDC` | `outrun::quest::compose(XrPosef const&,XrPosef const&)@plt` | Project function through PLT |
| `0x2D6C24` | `__stack_chk_fail@plt` | Security/runtime epilogue |

Resolved exact names and calls: **10/10**. Recovered logic from the complete-ELF version: `xrLocateSpace` location flags & 3 valid, `xrLocateViews` view count 2 and view-state flags & 3 valid, then invert/compose left and right poses. An imported PLT symbol's name is known; the **runtime binding instance** is not determined by a purely static PLT label.

## 2. `race_camera_view_switch_484a40` (ELF `0x119240C`, REA 10 unresolved)
Independent full-ELF Ghidra script `InspectQuestCallBoundariesResolved20261025.java` confirms all ten `BL` sites. Remove image-base delta `0x100000` when comparing its logs with the original ELF.

| ELF call sites | Original ELF destination | Status |
|---|---|---|
| `0x119248C`, `0x11924C8`, `0x1192514`, `0x1192550` | `0x1233690` | **Exact target address found**, but target symbol / PLT meaning **not verified**. Ghidra labels rebased `SUB_01333690`; do not invent a function name. |
| `0x11925D0`, `0x11925E0`, `0x11925F0`, `0x1192600`, `0x1192610`, `0x1192620` | `0x1220590` | `outrun::driving::Bytes::out_of_view` bound-check exception helper `@plt` as corroborated by other whole-ELF objdump call label. |

All ten `BL` **target addresses** identified; six target names verified, four calls still have an unknown symbolic target. The public PC decompilation `r4dius/outrun2-decomp` at `src/driving/pc_race_camera.cpp` is only a **comparison hypothesis**, not validation that the unknown call has the same name as in that PC source.

## 3. `race_robot_driver_chara_487ee0` (ELF `0x39F33C`, REA 13 unresolved)
- Direct `BL` calls **12/12 target names identified** from earlier whole-ELF objdump: `PcRaceMemory::u32` at `0x39F370`, `0x39F3E4`, `0x39F40C`; exception allocation at `0x39F450` and `0x39F490`; `std::logic_error` construction at `0x39F460`; throws at `0x39F488`, `0x39F4C8`; `std::out_of_range` construction at `0x39F4A0`; exception free at `0x39F4D8`; `_Unwind_Resume` at `0x39F4F0`; `__stack_chk_fail` at `0x39F4F4`.
- One indirect `BLR x8` at **`0x39F3CC`** remains runtime-class unresolved. The separate complete-ELF Ghidra decompiler shows an object method call via `PcRaceContext[6]`'s object vtable **+0x30**, with a local output parameter. This identifies the interface *slot*, not the concrete class implementation. Resolving the concrete receiver requires vtable/data-flow/reachable class construction or runtime tracing.

## 4. Remaining four REA native functions
The seven-function manifest `quest_apk_rea_seven_functions_manifest_20261025.json` also records:
- `Flush::draw_404700`: REA **40** raw-slice unresolved calls.
- `PcSceneRenderer::render_frame`: REA **27** raw-slice unresolved calls.
- `Draw::disp_514c30` (occupant draw): REA **248** raw-slice unresolved calls.
- `ps5_runtime::cockpit_fragment`: REA **6** raw-slice unresolved calls.

These **321 unresolved raw-slice observations** are *not yet individually resolved against the whole ELF* in the current pass. The earlier full-ELF Ghidra decompositions and original source symtab remain available on N100 for future verification; do not claim they have been exhausted. Additionally, `ps5_runtime::cockpit_fragment` manipulates text for a shader stage, and is not proof of the final passenger/glass output pixel shader.

## Audit evidence and limitations
- N100 previous raw REA evidence manifest: `apk/_analysis_focus/quest_apk_rea_seven_functions_manifest_20261025.json`, all seven with hashes/Evidence IDs.
- N100 previously run whole-ELF Ghidra boundary resolver: `apk/_analysis_focus/run_quest20261025_callbounds2.py`, printed all ten camera `BL` sites and destinations, with rebasing.
- N100 previously run whole-ELF objdump call listing: `apk/_analysis_focus/quest_rea_xr_plt_names_20261025.py`, printed all named OpenXR and driver-selection call sites.
- Direct targets from the raw 7 function slices cannot by themselves prove *transitive* implementations; REA explicitly describes those callee edges as partial when a slice omits the rest of the ELF.
- A new **seven-function full-ELF machine-readable callgraph** was attempted in the current session but the external N100 write tool was blocked, so no such unverified graph is claimed or scored.

Status: **partial external-call resolution**. OpenXR 10/10 named, camera 10/10 addresses (6/10 names), driver 12/12 direct named + 1 vtable BLR unresolved, remaining four functions await whole-ELF individual mapping. `CODE_CHANGE=NO`, `DX9Ex=REVIEW_ONLY`, `BUILD=NOT_RUN`, `HMD_RUNTIME_VALIDATION=UNTESTED`.
