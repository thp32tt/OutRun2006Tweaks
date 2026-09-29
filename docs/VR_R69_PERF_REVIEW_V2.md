# R69 performance EXP_ALL_V2 review

Base: `vr-d3d9ex-candidate/r69-perf-exp-all`

Reviewed V2 source checkpoint: `60d1c483d79eb2d883ab9fd4f3d65bcbb693695b`

## Fixes applied before re-review
1. SafeEye 2 ms fallback budget now uses QueryPerformanceCounter instead of GetTickCount64.
2. Explicit SkyGlow state restore distinguishes FVF vs custom vertex declaration.
3. SkyGlow explicitly disables/restores culling and scissor test for fullscreen passes.
4. XYZRHW shadow registry generation advances on full registry rollback/reset.
5. DirectGPU frames referenced by a failed fresh projection receive a separate asynchronous EVENT before producer ACK.
6. A failed DirectGPU source frame is dropped from future selection after the deferred EVENT is armed, preventing re-sampling behind an older completion fence.
7. Deferred failed-projection ACKs are polled in every gameplay configuration, not only direct-only mode.
8. Old poisoned deferred state is discarded without ACK when producer run/generation identity changes.
9. SkyGlow telemetry caches QPC frequency instead of querying it per measured frame.

## Ten-pass static re-review
1. Compile/reference pass: no stale CopyFenceTimeoutMs reference; required std::max include present.
2. D3D9 input-state pass: FVF/custom declaration capture and restore are mutually correct.
3. D3D9 fullscreen-state pass: RT/depth/viewport/shader/texture/stream/sampler/blend/color-write/cull/scissor/PS c0 touched state is restored.
4. DrawPrimitiveUP side-effect pass: stream 0 is restored explicitly.
5. XYZRHW lifetime pass: insert/erase/full-clear all invalidate lookup generations.
6. Fence-timing pass: 2 ms budget uses QPC ticks; no GetTickCount64 timeout remains in the fence loop.
7. Failed-projection lifetime pass: no referenced DirectGPU producer slot is immediately ACKed.
8. Retry/race pass: failed source frame is marked processed, so the same shared texture is not sampled again after an older deferred EVENT.
9. Zero-copy success pass: successful projection remains protected by the existing R32 async EVENT ACK before producer reuse.
10. Transport/reset pass: new run/generation cannot receive an ACK for an older failed reference.

## Residual test-only risks
- Explicit touched-state restore may be slower than D3DSBT_ALL on some drivers because it still performs several Get* calls; this requires HMD A/B timing.
- The 2 ms fallback path still calls D3D11 Flush before polling. The wait is QPC-bounded, but the driver cost of Flush itself is not cancellable.
- A D3D11 EVENT query error intentionally poisons one producer slot until transport generation changes; this is fail-closed rather than risking texture overwrite.

Status: STATIC_REVIEW_PASS_FOR_HMD_TEST. Not approved for production merge until EXP_ALL_V2 runtime logs and visual checks pass.
