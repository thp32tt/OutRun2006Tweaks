# Quest-based particle optimization implementation
Date: 2026-10-16 KST. New independent branch
`vr-quest-native-rebuild-20261016`; no changes to production DX9Ex/DX11.

## Observed APK evidence
`particle_draw_418490`, `particles_display_41bd10`,
`tire_smoke_41cb30`, `gravel_req_41df00`, `water_req_41e9f0`,
`GlD3D9Device::flush`, `GlD3D9Device::pooled_upload` exist in the
ARM64 symbol/call catalog. These names alone do **not** prove per-eye
duplicate uploads, pixel overdraw, or a frame-time bottleneck.

## Actual new C++ behavior
- `ParticleStereoBatcher` requires consecutive draw IDs and identical
  trusted material, alpha state, render-target serial, triangle vertex
  stride, producer identity, and both eyes' frame/pose/generation stamps.
  Source particle simulation runs only once; each eye receives a separate
  GPU Draw with its own pose/target. No alpha sorting or geometry simplification.
- The batcher is OFF by default. Uncertain Glass, WaterSurface, Flare,
  Unknown draws retain the original route. Smoke, Dust, Gravel and WaterSpray
  are allowed only after the *Windows PC* producer token has been verified.
- `ParticleD3D9Gpu` owns a 2-MiB DYNAMIC|WRITEONLY DEFAULT-pool VB and
  uses DISCARD for first upload/wrap and NOOVERWRITE for nonoverlap.
  Preserves stream-0 binding across separate eye callbacks. Must invalidate
  on Reset/ResetEx/device destruction. Caller retains material, shader and
  blend state; per-eye binder must restore original RT/DS/viewport/WVP.
- Upload failure before eye 0 returns `NeedsOriginal`, supporting complete
  original fallback. A failed physical eye Draw or restoration returns
  `FrameInvalid` — no replay after partial raster submission.
- `eligible_for_optional_half_resolution` only classifies trusted smoke/dust.
  No half-resolution GPU render path implemented. That requires measured GPU
  pixel overdraw and depth-aware upsampling with HMD optical acceptance.

## Limits and integration contract
No installed OutRun Win32 DrawPrimitiveUP hook or x64 OpenXR compositor is
connected in the new branch. An owner must capture *immutable consecutive*
triangle-list commands and flush on any intervening state/target/shader/
blend change or unknown producer. Unknown vertex layouts stay on the original
path. This implementation does not assume all transparent water or glass is
a particle and does not turn ZWRITE on globally.

Validation: local Linux Release CMake and CTest 2/2 pass (portable core).
New GitHub workflow builds both Linux and Windows to validate D3D9 code.
Quest3/VDRX real-game frame p50/p95/p99, effect class mapping, GPU upload bytes,
latency and stereo visual parity are **UNTESTED**. No FPS claim or release.
