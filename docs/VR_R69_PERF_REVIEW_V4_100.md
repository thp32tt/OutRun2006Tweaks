# R69 EXP_ALL_V4 — second diversified 100-unit review

Reviewed source checkpoint: `670fda17836012d61be399bd03ac3287ab689294`

This pass was executed after applying V3 review findings F1/F2. It intentionally used different questions from the previous 100-unit pass and focused on race windows, stale-generation faults, teardown, reset, failure escalation, and CI reproducibility.

## Applied before/during this review

1. XYZRHW tracked-buffer publication race:
   - registration-in-flight guards added;
   - tracked Bloom bit is pre-published before map insertion;
   - map insertion republishes the definitive bit while the registry mutex is held;
   - registration guard is exception-safe.

2. DirectGPU deferred EVENT failure:
   - generation quarantine helper added to R32;
   - failed deferred `CreateQuery` marks the active generation faulted;
   - deferred `GetData` failure also quarantines only the active matching generation;
   - faulted generation is rejected before future zero-copy commit;
   - direct-only policy dynamically relaxes to cached/classic recovery while active generation is faulted.

3. Same-slot lifetime violation:
   - a producer reusing the same slot before deferred GPU completion now quarantines the generation;
   - latest-frame immediate ACK refuses every same-generation slot with an unresolved deferred reference.

4. Stale-generation fault isolation:
   - a late failure from a superseded EVENT cannot roll `ActiveAckGeneration` backward or overwrite the newer generation's quarantine state.

## Review groups

### 001–020 — registration / publication / quarantine
- Registration flight guards: PASS.
- Vertex/index pre-publication: PASS.
- Definitive post-insert Bloom publication: PASS.
- Registration exception cleanup: PASS.
- Deferred query creation quarantine: PASS.
- Deferred query polling quarantine: PASS.
- Faulted generation zero-copy rejection: PASS.
- Dynamic direct-only fallback: PASS.
- Same-slot reuse quarantine: PASS.
- Unsafe speculative ACK after deferred reference: blocked.

### 021–040 — producer ACK / ABI / fallback
- Per-slot ACK scan and producer fence ownership: PASS.
- Frame.v2 usability contract: PASS.
- D3D9Ex creation fallback transaction: PASS.
- Producer run/generation identity: PASS.
- Verified bundle freshness: PASS.
- black-screen/recenter fallback chain: PASS.
- cadence ownership and bounded waits: PASS.

### 041–060 — SkyGlow / projection source / R32
- VR-only factor 2: PASS.
- state-block removal path still explicit and Reset-safe: PASS.
- FVF/declaration/stream restore: PASS.
- cull/scissor/RT/depth/shader/sampler restoration: PASS.
- zero-copy shared SRV ownership: PASS.
- failed fresh projection deferred ACK: PASS.
- R32 EVENT polling remains asynchronous: PASS.
- session pending-query release: PASS.
- Three automated grep checks produced false negatives because the relevant state/unbind implementation is inherited/included from lower files; direct source inspection confirmed the paths.

### 061–080 — reset / lifetime / stale generations
- SkyGlow resources released before Reset: PASS.
- shadow registry cleanup and Bloom rebuild: PASS.
- registration guards survive exceptions: PASS.
- stale-generation EVENT failure ignored for active-generation fault state: PASS.
- deferred-query shutdown cleanup: PASS.
- same-generation slot violation quarantines rather than ACKs: PASS.
- legacy SafeEye 2 ms QPC cap remains intact: PASS.

### 081–100 — CI / packaging / worst-case performance
- Deterministic host smoke suite remains enabled: PASS.
- source SHA and SHA256 package provenance: PASS.
- test-only marker: PASS.
- matrix fail-fast disabled: PASS.
- untracked world-buffer fast path: PASS.
- relaxed atomic telemetry: PASS.
- dynamic classic/cached fallback while DirectGPU generation is faulted: PASS.
- V4 workflow registration was the only missing item and is fixed in the same V4 branch.

## Additional findings found and fixed during this pass

### V4-F3 — Bloom rebuild vs concurrent registration
A tracked release can rebuild Bloom while another registration is waiting for the registry mutex. Pre-publication alone could therefore be erased before map insertion. V4 now republishes the definitive Bloom bit while holding the registry mutex after `emplace`.

### V4-F4 — stale EVENT fault rollback
A late query failure from a superseded generation could overwrite `AckFaultGeneration` and make the current generation's fault state incorrect. `MarkGenerationFault` now ignores a generation different from the active one, and R32's own query-error path uses that helper.

### V4-F5 — same-slot reuse before ACK
If the producer replaces a slot whose older identity still owns a deferred GPU reference, the new identity is no longer eligible for latest-frame immediate ACK. The generation is quarantined and recovery falls back rather than gambling on texture lifetime.

## Residual runtime-only questions

- Cost of the registration-in-flight wait if a D3D9 multithreaded workload registers a new tracked buffer during a hot Lock burst.
- First indexed-XYZRHW draw before its IB has any observed CPU Lock.
- Driver cost of legacy `Flush` itself; the 2 ms QPC loop cannot bound time already spent inside the driver call.
- P5 vs V4 frame-time P95/P99 and 1% low in the same heavy route.
- Explicit SkyGlow touched-state save/restore vs D3DSBT_ALL on the user's RTX 4070 driver.

Status: **STATIC_REVIEW_PASS_FOR_HMD_TEST**. No new normal-success-path P0 defect remained after the fixes above.
