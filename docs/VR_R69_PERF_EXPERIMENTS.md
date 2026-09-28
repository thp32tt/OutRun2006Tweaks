# R69 performance experimental test builds

Safe baseline:
- P5 branch: `vr-d3d9ex-candidate/r69-perf-p5`
- P5 head: `9774abbb64f2b288f69930639caefe0bd963403a`

These candidates are TEST-ONLY. They are not approved for `vr-d3d9ex-focus` integration until HMD logs show no visual/state/lifetime regressions.

## EXP_STATEBLOCK
- Branch: `vr-d3d9ex-candidate/r69-perf-exp-stateblock`
- SHA: `7d795e8270dfdbeb5d328a7e104a6bf9dffedcc8`
- Removes per-Present `D3DSBT_ALL` creation/apply from stereo SkyGlow.
- Explicitly captures/restores only touched state: RT/depth/viewport, vertex/pixel shader, vertex declaration, texture0, stream0, sampler0 states, relevant render states and PS c0.
- Includes stream0 restoration because `DrawPrimitiveUP` clears stream 0.
- Risk: missing an implicit D3D9 side effect could cause later draw corruption. Test menus, stage transitions, shadows and post-effects carefully.

## EXP_ZEROCOPY
- Branch: `vr-d3d9ex-candidate/r69-perf-exp-zerocopy`
- SHA: `35de66e01d08f3e4c1a5102e1cfb7c9a37eb3977`
- Removes the normal fresh-frame pair of full-eye `CopyResource` calls into host-owned DirectHold textures.
- Projection samples the validated shared-ring SRVs directly.
- Producer slot reuse is still gated by the existing R32 asynchronous GPU EVENT completion ACK.
- Cached XR projection ticks reuse the released projection image and do not re-sample the producer slot.
- Risk: slot lifetime/ACK bugs can show as flicker, stale eye, black frame or left/right mismatch.

## EXP_FENCE2
- Branch: `vr-d3d9ex-candidate/r69-perf-exp-fence2`
- SHA: `aa4a6d29a470eea343a9f0f5e1b9a7ec0a3ac09a`
- Legacy SafeEye recovery path synchronous copy-fence budget reduced from 8 ms to 2 ms.
- Normal R32 DirectGPU fast path is unchanged.
- Goal: prevent a rare recovery path from consuming most of a 72/90 Hz frame budget.
- Risk: a busy GPU may hit fallback/cached projection more often.

## EXP_XYZCACHE
- Branch: `vr-d3d9ex-candidate/r69-perf-exp-xyzcache`
- SHA: `e7ca33e06d60a996a09305f729e4397c9f62700b`
- Adds thread-local weak lookup caches for XYZRHW VB/IB CPU shadow entries.
- A global registry generation invalidates caches on map insert/erase, avoiding stale pointer reuse while bypassing the registry mutex on steady repeated lookups.
- Risk: low, but test sprite-heavy menus/HUD and particle-heavy scenes.

## EXP_ALL
- Branch: `vr-d3d9ex-candidate/r69-perf-exp-all`
- Current source combines EXP_STATEBLOCK + EXP_ZEROCOPY + EXP_FENCE2 + EXP_XYZCACHE on top of P5.
- Test this first to minimize HMD runtime. If it is clean and faster, keep the isolated builds only as diagnosis fallbacks.

## Runtime test order
1. EXP_ALL first.
2. If clean and the known frame-drop section improves, stop.
3. If visual corruption appears, test EXP_STATEBLOCK and EXP_ZEROCOPY individually first.
4. If only hitching remains, test EXP_FENCE2.
5. If HUD/particle CPU spikes remain, test EXP_XYZCACHE.
6. Use P5_BASE only for a before/after confirmation.

For every run keep the same route, HMD refresh, Virtual Desktop quality/codec and in-game settings. Exit the game normally and upload only the generated `OutRun2_VR_ANALYZE_*.zip`.


## Build trigger
- The dedicated six-way test workflow is intentionally retriggered after its workflow file exists on the branch, so the push event can build P5_BASE, EXP_STATEBLOCK, EXP_ZEROCOPY, EXP_FENCE2, EXP_XYZCACHE and EXP_ALL in parallel.


## EXP_ALL_V2
- Reviewed source checkpoint: `60d1c483d79eb2d883ab9fd4f3d65bcbb693695b`.
- Ten-pass static review status: PASS for HMD test.
- Includes QPC 2 ms fence timing, FVF/cull/scissor SkyGlow restore hardening, reset-generation invalidation, and failed-projection deferred DirectGPU ACK protection.
- Test EXP_ALL_V2 before the older EXP_ALL candidate.


## EXP_ALL_V3
- Source checkpoint: `f19745bf88bbab6dc765f326148cb557f3984631`.
- Adds draw-proven selective XYZRHW shadow ownership, lock-free Bloom fast rejection for untracked VB/IB Lock/Unlock/Release, long-session Bloom rebuild, relaxed atomic diagnostics, explicit deferred-query cleanup, and deterministic smoke-test execution for every experiment matrix candidate.
- Additional orthogonal review: `docs/VR_R69_PERF_REVIEW_V3.md`.
- Test EXP_ALL_V3 before V2/older combined candidates.
