# Quest 3 standalone OutRun 2006 native implementation audit & PCVR adoption
Date: 2026-10-16 (KST). Target PCVR: `thp32tt/OutRun2006Tweaks` R84 DX9Ex `vr-d3d9ex-focus`. **Static/binary analysis; do not treat as HMD performance proof or full decompilation.**

## 1. Provenance, scope and confidence

- User-provided `/home/chatgpt-runner/apk/outrun2.apk`; **1,491,573,201 bytes**, 3,909 ZIP entries, 0 ZIP-encrypted entries. This is separate from `CrazyTaxiVR.apk`.
- Main AArch64 ELF `lib/arm64-v8a/liboutrun_quest_core.so` (21,959,856 bytes; SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`); `libopenxr_loader.so` (1,583,992 bytes). Other imports: Android, EGL, OpenGL ES 3, AAudio and media APIs.
- Manifest package `org.outrun.quest.vr`; `versionName=0.4.25-music-indicators`. Embedded version banner `v0.4.11` is stale/independent and is **not** the APK manifest version.
- ELF `.symtab` and `.strtab` expose C++ names; N100 read-only tools analyzed **22,621 executable `.text` symbol rows**, including duplicate aliases; this is **not** a claim to have reviewed every algorithm or resolved every call.
- Call edges recovered from AArch64 32-bit direct `BL` immediate instructions in executable text, symbolized with `readelf`/`c++filt`, bounded by symbol ranges. Indirect/virtual calls, data references and PLT trampolines require further analysis. Some named call sites appear only as immediate call edges; absence of an edge is **not** absence of behavior. N100 analysis: `apk/_static_out/quest_callgraph_selected.json`, `static_inventory.json`, `deep_structure.json`; original APK untouched.
- Classification: **FACT** = observed symbol/import/byte/BL edge; **INFERENCE** = likely role derived from naming, needs code/dataflow analysis; **UNTESTED** = real Quest display/performance not measured. Licensed art/code remains excluded from Git.

## 2. High-priority named functions and observed call relationships

| Function, ELF virtual address | Grounded evidence | PCVR implication & decision |
|---|---|---|
| `XrSessionHost::make_warp_chain` `0x2d8bd0` | 332-byte function; three direct calls to XR `check(XrResult,...)`; one vector append of `XrSwapchainImageOpenGLESKHR`. XR swapchain APIs imported. | **Inspect/compare** per-eye image lifetime with DX9Ex DirectGPU ring and DX11 swapchain. Do **not** copy GLES swapchain code to D3D/OpenXR Windows. |
| `XrSessionHost::bind_eye` `0x2da1c8` | 372-byte body, XR/GL FBO APIs imported, no decisive direct game-function call in this BL-only graph. | **Inspect/compare** ownership of eye targets, depth, stencil and reset/reacquire; require actual FBO call tracing. |
| `GlD3D9Device::flush` `0x2fcfdc` | 7,936 bytes; direct call into `cockpit_fragment` and a vertex shader utility; std::map/string operations. | **High value** for draw/state batching and cockpit material shader routing; not a drop-in replacement for R84 D3D9Ex. |
| `GlD3D9Device::invalidate_mesh` `0x2f8524` | 1,084-byte body; direct std::tree removal and vector/error routines. | **Audit** R84 and DX11 mesh invalidation at D3D9 resource update/Reset; no justified change to our cache key without trace. |
| `sphere_in_stereo` `0x2d49a0` | 968-byte standalone function accepting `StereoFrame`, `XrVector3f`, radius. No direct internal `BL` edges in bounded graph; arithmetic path not fully reconstructed. | **Compare** two-eye union culling to existing `VRCullingUnionFov` and ScreenEdgeCullFix. Avoid extra broad culling changes without runtime ground truth. |
| `native_race_hud_display` `0x1044820` | 5,964-byte body; calls `run_navi_draws` (four BL), `queue_unmarked_glyphs` (two), HUD `note` and `rebuild` utilities. | **High value:** producer→glyph→HUD-space separation; R84 already tracks exact HUD producer semantics. Reuse ownership concept, not APK glyph/assets. |
| `shadow_draw_422550` `0x10d6d60` | 5,436-byte body; direct call to `restore_textures(PcShadowFrame&,PcD3D9Device&)`. Shadow stencil diagnostics also embedded in ELF. | **High value:** validate per-eye depth/stencil/texture-state restoration in R84/R31/R30 and DX11 after shadow pass. Avoid turning on console shadow paths without regression tests. |
| `native_race_effects_flare_420560` `0x104b8d0` | 668-byte wrapper; direct `map_memory(...)`, `fault_pc(...)` edges; callback dispatch involved. | **Investigate** world/scene-effect producer scope and per-eye submission for duplicate lens flare; call name does not prove it fixes our flare. |
| `GlD3D9Device::begin_frame` `0x2f8d88` / `prepare_gpu` `0x2fc458` | Native engine methods present, OpenGL ES GL draw calls imported. | **Compare** frame submission, persistent objects and invalidation; current 60FPS/120Hz claim is string evidence only. |
| `XrSessionHost::begin/end` `0x2d9b18` / `0x2d904c` | Native functions and OpenXR `xrWaitFrame/xrBeginFrame/xrEndFrame/xrAcquireSwapchainImage/xrReleaseSwapchainImage` imports. | **Compare** XR predicted display time, release before submit, 72Hz cadence; current R84 host/IPC owners must remain authoritative. |
| `projection_gles` `0x2d481c`; `view_matrix` `0x2d468c` | Defined camera/projection methods using `XrFovf`, `XrPosef`; archived A64 disassembly indicates off-axis per-eye projection. | **Reuse mathematics only**, check handedness/row-major, D3D [0,1] vs GL [-1,1] Z, canted-eye orientation and malformed FOV guards against existing R84 math. |

Addresses are ELF virtual addresses for **this exact** `.so`, not stable Windows game addresses or ASLR-adjusted pointers.

## 3. Cockpit and related dataflow proof

| ELF symbol | Type / evidence | What is and is not proven |
|---|---|---|
| `cockpit_render_active` | 1-byte TLS and `R_AARCH64_TLSDESC` relocation | Explicit per-thread cockpit enable state exists; not yet traced to every draw |
| `cockpit_vehicle_draw` | 1-byte TLS/relocation | Vehicle render state exists; specific game object identity not proven |
| `cockpit_occupant_draw` | 1-byte TLS/relocation | Occupant handling exists; driver/passenger distinction not proven |
| `cockpit_glass_opacity` | 4-byte TLS/relocation | Glass opacity value exists; visual material mapping not proven |
| `cockpit_glass_premultiplied` | 1-byte TLS/relocation | Premultiplication mode state exists; exact blend factors not proven |
| `cockpit_body_correction` | 64-byte TLS/relocation | Likely 4×4 transform due size, **inference** only until traced |
| `cockpit_hand_tracking` | 8-byte TLS/relocation | Tracking data/status exists; controller-to-wheel rig not recovered |
| `outrun::ps5_runtime::cockpit_fragment` `0x2f7734` | 376-byte local function; **direct BL caller** `GlD3D9Device::flush` and device constructor; embedded error `cockpit fragment output missing`. | Shader generation is associated with draw flush and device setup. **Do not** assume all glass geometry or correct stereo without further tracing. |

Shader text in `.rodata` includes `questClip`, `questOldClip`, `mvCurrent`, `mvPrevious`, a `gl_FragCoord` path, and alpha operations `c.a*=opacity` / premultiplied-like `c.rgb*=opacity`. These are **byte evidence for shader features**, not a proven linkage to the cockpit glass pass nor proof that Meta ASW or any interpolated FPS mode is enabled.

The standalone has a distinct seated recenter label and XR controller action API. No Windows x86 game object offsets or graphics resources have been extracted from these names.

## 4. PCVR capability mapping and adoption priority

| Area | Existing GitHub implementation | Verified transfer | Remaining blocker |
|---|---|---|---|
| Native cockpit pose and body | `src/hooks_graphics.cpp`, `src/vr/game/driver_seat_camera_math.hpp`, INI `DriverSeatView` and offsets | **IMPLEMENTED:** scoped cockpit eligibility now unified for camera offset, cockpit near clip, car body and driver suppression; invalid camera fails closed | Seat physical positioning and mirror/HMD visual approval |
| Native car and driver | Existing full car render-state hook, configurable robot workId; passenger left untouched | **KEEP**; no unverified passenger hiding introduced | True driver workId + car model identity per vehicle |
| Glass alpha | Existing R84 D3D9 render-state and transparency paths | **RESEARCH ONLY**, no unsafe GLSL-to-D3D copy | Material ID, texture alpha, blend state and per-eye transparency validation |
| Hand/steering interaction | User steering wheel support separate from graphics/cockpit | **RESEARCH ONLY** | Rig/animation source, touch input mapping and FFB domain ownership |
| XR images, FOV, 6DoF | R84 DirectGPU + x64 host, latched per-eye transforms | **COMPARE/VERIFY**; do not duplicate XR host | Exact predicted-time, eye reuse, canted-eye HMD checks |
| HUD, sprites, menu | R84 semantic HUD and per-eye transformations | **DESIGN REFERENCE** | Per item HMD regressions, transient +TIME / results |
| Shadow and flare | R84 original state and exact producer hooks | **DESIGN REFERENCE** | Stencil/alpha/lens-space, correct eye submit |
| Persistent GL meshes | R84 CPU scratch and DirectGPU caches; independent DX11 code | **RESEARCH ONLY** | Resource key/Reset invalidation and performance measurements |
| Motion vectors | `mvCurrent`, `mvPrevious` shader strings | **RESEARCH ONLY** | Verified frame history lifecycle; Windows XR extension support and legal assets |

Important: `R84` mainline is `R33→R32→R31→R30→R29`. Older R26 paths are fallback only; DX11 and DXVK separate code/branches. The research inputs do not justify altering unrelated pipelines or guessing performance wins.

## 5. Concrete source change: share *one* native cockpit eligibility decision

Before this fix the car/driver hook's `VRDriverSeatRenderTest::Active()` checked `VRDriverSeatCameraDelta`, while `FixZBufferPrecision::DriverSeatCameraActive()` only checked the mode and transition timer; a degenerate/NaN camera could therefore enable cockpit near-plane **without** corresponding cockpit geometry or camera offset. The Quest render-active state separation makes this incoherence an especially worthwhile audit target.

The pure `DriverSeatCamera::CameraAndBodyEligible` validates:
1. VR/cockpit enabled and gameplay eligible.
2. Matching native camera mode and exactly completed finite transition timer.
3. Finite native position/look, finite cockpit offsets and non-degenerate right/up/forward basis.

Both vehicle/occupant hook and near-plane hook call `VRDriverSeatCameraEligible()`; actual position translation continues using the existing checked `ComputeTranslation()`. No camera model or option defaults are changed. `vrhost/tests/driver_seat_camera_smoke.cpp` adds NDEBUG-safe failure returns for enabled, disabled, wrong mode, moving transition, non-finite timer/offset and recovery.

## 6. Release and HMD acceptance (NOT yet complete)

1. Run mandatory **exact source SHA** Windows R84 x86 DLL, x64 XR host, R26_SAFE rollback, Domain Guard, HUD Inspector, package selector and test launcher. Check the cockpit smoke *was executed*, not just compiled.
2. Test Quest3/VDXR in native gameplay, pause/restart/reset, and all camera-mode changes; look for full car visible, correct driver-only hide, unaffected passenger, no floating geometry, no near-plane clipping, no HMD-recentering offset drift.
3. Verify each-eye dashboard/glass/shadows/flare and alpha state after device reset. Test both center lens and +TIME/result overlays as independent existing defects.
4. For extra cockpit features, recover authoritative original EXE car/material identity and shader/body call sites first. Track separate feature changes, don't count observational research as complete functional implementation.
5. Record headset test metrics and only mark `RUNTIME_VALIDATION=PASS` after real evidence. Otherwise **UNTESTED**; do not claim full Quest parity or 72/120FPS based on strings.

## 7. Traceability & restrictions
- This audit and earlier [Quest cockpit comparison](QUEST_COCKPIT_APK_ANALYSIS_20261016.md) are human-readable. Raw scripts and JSON stay on user N100 as local reference, not under git as game binaries.
- Source changes are clean-room reproduction of behavioral contracts within the existing GPL/OutRun Tweaks project, no third-party object code, shaders or game assets copied.
- The original standalone APK is ARM64 GLES3; it cannot be inserted into Windows D3D9Ex/DX11. Only independently validated algorithms, interface decisions and test cases are portable.
- No assertion that the entire 22K-function ELF has been fully decompiled. Focused classes/functions above were inventoried with symbolic calls; the remainder is open for further target-oriented investigation.
