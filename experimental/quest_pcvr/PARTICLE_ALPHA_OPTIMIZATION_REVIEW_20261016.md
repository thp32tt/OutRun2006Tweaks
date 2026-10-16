# Quest APK particle / transparent rendering → independent PCVR optimization candidates

Date: 2026-10-16 KST. **Research-only, no speedup measured, no rendering implementation changed.**
Source: user's ARM64 `liboutrun_quest_core.so` symbol index, [Quest symbol index](https://github.com/thp32tt/OutRun2006Tweaks/tree/vr-d3d9ex-focus/docs/research/quest_function_index), [previous verified disassembly](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/research/QUEST_N100_NATIVE_DECOMP_FOCUS_20261016.md), and actual [DX9Ex R33/R29/R30 sources](https://github.com/thp32tt/OutRun2006Tweaks/tree/vr-d3d9ex-focus/src/vr/d3d9).

## Exact function evidence from native ELF symbols (not performance samples)

| Native ELF VA | Size | Function | Caution |
|---|---:|---|---|
| `0x1067d94` | 18052 B | `outrun::platform::(anonymous namespace)::particle_draw_418490` | Draw routine name and size only; actual blending/UP uploads not yet profiled |
| `0x1067308` | 1568 B | `particles_display_41bd10` | Strong display-stage candidate |
| `0x104b370` | 720 B | `native_race_effects_smoke_4208a0` | Effect wrapper |
| `0x10666c8` | 528 B | `particles_smoke_emit_4208a0` | Emitter, not proof of a Draw cost |
| `0x105700c` | 6268 B | `particles_detail::smoke_ctrl_41d330` | Smoke update |
| `0x1053cec` | 5060 B | `particles_detail::tire_smoke_41cb30` | Tire smoke |
| `0x105b314` | 2700 B | `particles_detail::gravel_req_41df00` | Gravel, possible sand spray but not confirmed every sand effect |
| `0x105d390` | 5136 B | `particles_detail::water_req_41e9f0` | Water-particle request, **not evidence of water-surface shading** |
| `0x105e984` | 808 B | `particles_detail::water_ctrl_41ed80` | Water effect update |
| `0x105e7a0` | 484 B | `particles_detail::water_born_41ed00` | Water effect spawn |
| `0x10254c8` | 1372 B | `native_car_reflection_leaf` | **Car** reflection, not proof of water reflection |
| `0x2fcfdc` | 7936 B | `GlD3D9Device::flush` | Verified GLES bind_target/apply_state/bind_textures/glDraw calls |
| `0x2fefc4` | 672 B | `GlD3D9Device::pooled_upload` | GPU buffer upload point, per-draw frequency unmeasured |
| `0x2f8524` | 1084 B | `GlD3D9Device::invalidate_mesh` | CPU mesh invalidation, not proof of immediate GPU deletion |

Named routines establish that Quest separates particle generation/control from GPU submission. Their actual producer-to-material mapping, calls per frame, texture identity, alpha blend equation and GPU occupancy are **unknown**. Do not infer from the `water` token that this is the full course-water surface; do not infer `gravel` is all sand.

## Opportunities for a *new* PC VR mod — conditional, ordered

1. **P0: one logical particle update/geometry upload, independent two-eye draws.**
   - Preserve game simulation (including particle birth/control/timers/audio) exactly once per displayed game tick.
   - If a proven particle producer uses CPU transient vertices or D3D9 `*UP` calls, stage geometry to reusable dynamic VB/IB **once**, then draw both eyes with their own WVP and target, without overwriting busy GPU ranges. Record bytes uploaded, upload/Lock stalls, number of physical eye draws, per-frame vertex generations.
   - For a dynamic `D3DUSAGE_DYNAMIC` buffer follow Microsoft documented `D3DLOCK_NOOVERWRITE` until filled, then `D3DLOCK_DISCARD` for the whole allocation. Lock failure before eye 0 must leave original game draw path active; never replay a partially submitted eye.

2. **P0 if GPU pixel-bound: smoke/dust **only** at optional reduced eye-target resolution.**
   - A transparent puff spanning many eye pixels may be dominated by blended pixel overdraw, not Draw count. Per-eye low-resolution offscreen composition (e.g. half-size each axis, depth-aware upsample and proper depth occlusion) is a well-established candidate; NVIDIA GPU Gems 3 Ch.23 discusses its savings and artifacts.
   - Must identify the actual smoke/dust producer and preserve scene color, alpha blend ordering, depth testing, head movement/reprojection, color space, and eye-specific positions. No mono particle texture copied into both eyes. This changes visual fidelity and is **not** equal-quality by default.
   - Do **not** apply it globally to water surface, windshield, UI, markers, crisp spray or lens flare. Offscreen RT switching and MSAA costs can offset the savings.

3. **P1: pack truly consecutive transparent draws sharing shader/material/texture into bounded batches.**
   - Flush on blending-order change, render-target/depth-stencil changes, Clear, shader/stateblock, particle producer boundary, query or unknown state. Maintain each eye's original particle order and correct source/target blend. No broad reorder of alpha draws.

4. **P1: eliminate only proven redundant reflection or GPU CPU-upload passes.**
   - Existing DX9Ex `ReflectionFrameBudget` and opt-in profiler already exist. Extra global refresh reductions are a fidelity trade-off. Eye-dependent water refraction/reflection cannot be universally shared or made mono, while independently proven eye-invariant cubemap producers could be computed once.
   - Do not globally disable alpha, write Z for particles, turn off glass/water, lower whole-scene resolution or blindly enable alpha-to-coverage.

5. **P2: XR/GPU synchronization.**
   - No synchronous per-draw readback / `D3DGETDATA_FLUSH` / spin waits. Preserve frame pose/FOV used for rendering until `xrEndFrame`. Treat cached eye frames and missed XR submits separately from GPU Draw-time.

## Already present in Windows DX9Ex — not novel improvements

- [R29 effect state cache](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/vr/d3d9/stereo_renderer_r29.cpp) avoids repeated state getters when setter/StateBlock tracking is reliable.
- [R30 XYZRHW shadow](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/vr/d3d9/stereo_renderer_r30.cpp) avoids blocking READONLY GPU locks during Draw, caches flat-particle eye-independent geometry.
- [R33 FastWorld](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/vr/d3d9/stereo_renderer_r33.cpp) explicitly routes fragile alpha/ZWRITE-disabled draws through safer R29/R30 rather than assuming stable world geometry.
- [GPU water profiler](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/vr/d3d9/gpu_water_profiler.hpp) samples blend/Z/RT/shader and async GPU timestamps, but blend samples are **not material IDs or attributable water/smoke cost**.
- [Transparency perf contract](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/DX9EX_TRANSPARENCY_OPTIMIZATION_20261015.md) has safeguards and measurement protocol; do not independently reapply a fix merely because this plan mentions it.

## Prioritized diagnostic/acceptance

Capture identical 72-Hz headset scene (13.89 ms budget), fixed build SHA/car/camera/track, 3×60-second warm A/B runs with particle on-screen/off-screen controls and water-surface-only negative control.

Report:
- p50/p95/p99 app CPU render+Present, GPU timestamp intervals with invalid/dropped samples, XR fresh/cached/reprojection counts.
- Producer class (smoke/gravel/water spray/water surface/windshield/other) **only once proven** via producer token + texture/shader + render-target generation and draw lineage, not blend flag alone.
- per-frame logical draws vs left/right physical draws; DrawPrimitiveUP bytes; VB/IB lock counts and stalls; upload bytes; shader/state/RT switches; GPU blended-pixel cost if profiling tool available.
- Head translation/canted-eye stereo, transparent overlap, water boundary and glass, dense spray, Reset/device loss, alpha order, shimmer/popping.

Go/no-go:
- If CPU-bound: optimize state/UP/RT route with same-quality output before half-resolution.
- If GPU overdraw-bound: try **per-eye** depth-aware low-res smoke/dust and record actual image-quality tradeoff.
- If reflection/shader-bound: profile exact water/glass material, **not** guessed from water_req.
- No FPS improvement claim, full Windows build claim, or HMD verification until measured.

References: [Microsoft D3D9 performance](https://learn.microsoft.com/en-us/windows/win32/direct3d9/performance-optimizations); [NVIDIA GPU Gems 3, chapter 23](https://developer.nvidia.com/gpugems/gpugems3/part-iv-image-effects/chapter-23-high-speed-screen-particles); [Khronos OpenXR frame submission](https://github.com/KhronosGroup/OpenXR-Guide/blob/main/chapters/frame_submission.md).

**Status:** BINARY_SYMBOL_EVIDENCE=VERIFIED; MATERIAL_ATTRIBUTION=UNTESTED; OPTIMIZATION=NOT_IMPLEMENTED; WINDOWS_CI=NOT_RUN; QUEST3_RUNTIME_VALIDATION=UNTESTED.
