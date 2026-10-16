# DX9Ex R84 — Quest-derived exact WorldParticle dual-eye upload path

Date: 2026-10-16 KST. Branch: `vr-d3d9ex-focus`.

## Implementation
- **Live owner:** `src/vr/d3d9/stereo_renderer_r30.cpp` in the actual R84 R33→R32→R31→R30→R29 chain; R26_SAFE untouched.
- **New:** `src/vr/d3d9/r30_particle_upload_policy.hpp` provides negative/positive compile-time policy regressions; `r30_particle_dual_eye_ring.hpp` provides a 4 MiB D3D9 DYNAMIC|WRITEONLY DEFAULT-pool VB with one bounded Lock/Unlock staging **two different per-eye XYZRHW buffers**, followed by each eye's independent `DrawPrimitive`.
- **Opt-in:** `OUTRUN_VR_R30_PARTICLE_VB=1` at game launch. Default OFF; all baseline stereo paths remain unmodified when disabled.
- **Gate:** original physical draw must carry exact `RenderScope::WorldParticle`, `state.worldEffect`, reliable R29 effect-state snapshot, alpha blend ON, depth write OFF, non-indexed UP, no StateBlock recording, 16–256 byte stride, at least 1 KiB and at most 1 MiB **per eye**, and successful original R30 two-eye CPU reprojection. Glass, water-surface, HUD, flare, offscreen unknown alpha and unclassified smoke never qualify from alpha state alone.
- **Semantics:** no change to HMD render resolution, stereo pose/FOV, scene simulation ticks, alpha blend order, material state, or indexed UP/VB paths. Two eye vertex buffers are **not equal** and never shared as mono geometry. The GPU optimization is one Lock/Unlock holding both eye copies rather than **two implicit UP uploads**.
- **Device safety:** one mutex holds ownership across upload + both submitted eye draws + final stream-0 restore. DISCARD when ring wraps and NOOVERWRITE otherwise; no DISCARD between eyes. Cached DEFAULT-pool buffer invalidates before R30 Reset. If preparation fails before a physical eye draw, preserve original DrawPrimitiveUP path. If a physical Draw or RT restore fails, keep R30's existing right-eye frame-failure policy. Stream-0 cleared to NULL after the stereo draw as D3D9 DrawPrimitiveUP would do.
- **Tracking:** existing opt-in `OUTRUN_VR_GPU_PROFILE=1` and DX9Ex CPU/XR diagnostics remain the comparison baseline. Neither an enabled alpha render state nor an offscreen RT sample proves a water/glass producer.

## Why this is *not* a blind port of the independent new VR batcher
The Quest/new-mod `ParticleStereoBatcher` assumes contiguous homogeneous trusted producers and per-eye GPU callbacks. R84 already performs per-draw stereo XYZRHW reconstruction and has separate R29/R30/R33 fail-closed owners. Cross-draw transparent batching and generic glass/water grouping would violate sorting, StateBlock, and world/HUD provenance. This R84 change instead targets one known existing non-indexed UP seam, with independent per-eye geometry and zero added game simulation ticks.

## Verification / status
The policy header compiles as part of the real Win32 R84 chain, with `static_assert` controls for rejected untrusted scope, depth writing, indexed path, missing cache, invalid stride and tiny draws.
Actual exact-SHA DX9Ex Active Validation, Domain Isolation and Full Source Impact are required before `BUILD_VERIFIED`.
Because no matching Quest3/VDXR runtime test has yet been performed, `HMD_RUNTIME_VALIDATION=UNTESTED`, `FPS_GAIN=UNMEASURED`, `MATERIAL_ATTRIBUTION=UNTESTED`. A real game can have no qualifying WorldParticle draws; enable only for controlled tests and measure safe acceptance.
