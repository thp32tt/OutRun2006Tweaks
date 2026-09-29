# R69 EXP_ALL_V4 — third diversified 100-unit review

Target: `vr-d3d9ex-candidate/r69-perf-exp-all-v4`

This pass intentionally avoids repeating the previous 200 review questions. It focuses on allocation failure, pointer ABA, hook lifecycle, wait amplification, boundary arithmetic, partial OpenXR submission, fallback chaining, long-run timing, and packaging reproducibility.

## 1–20 — allocation / exception / memory boundaries
- Shadow size and index-format guards: PASS.
- Lock/copy offset and size subtraction guards: PASS.
- Copy-vector resize failures fail open: PASS.
- Shadow-byte resize/range update is inside a catch-protected block: PASS.
- FINDING P1: `std::make_shared<R30BufferShadow>()` occurs before the local try/catch in both ensure functions. An allocation failure can escape a D3D hook and terminate/crash the game instead of failing open.
- Registration counters are RAII-cleaned once constructed: PASS.
- Scratch storage is thread-local and reentrancy-aware: PASS.

## 21–40 — COM lifetime / pointer reuse / registration waits
- Registry and per-entry locks: PASS.
- Tracked Lock/Unlock/Release fast gate: PASS.
- Bloom rebuild and generation invalidation: PASS.
- FINDING P1: Release hook calls the real COM `Release` first, then erases the registry entry only by raw pointer key. In a multithreaded allocator reuse window, a new buffer can reuse the same address before the old hook erases it (ABA), causing the new object's shadow entry to be erased.
  Recommended fix: capture the old shared_ptr before real Release and, when refs reaches zero, erase only if the map still points to that exact captured entry.
- FINDING P1-performance: `R30WaitFor*Registration` uses a global in-flight counter. While any tracked VB/IB registration is active, an unrelated buffer Lock can spin/yield until all registrations of that class finish. This closes the correctness race but can create a scene-specific CPU hitch.
  Recommended fix: replace the global wait with a per-Bloom-bit/per-bucket in-flight mask or equivalent targeted publication barrier.
- Bloom false positives remain safe: PASS.

## 41–60 — long-run IDs / clocks / stale state
- PresentEpoch explicitly skips zero: PASS.
- Direct frame ID zero is rejected: PASS.
- Frame comparisons use wrap-safe signed-delta semantics in active windows: PASS.
- Slot arithmetic for frameId uses unsigned wrap safely: PASS.
- QPC age calculations guard against negative deltas: PASS.
- Verified-bundle age checks are monotonic guarded: PASS.
- Bounded swapchain wait uses 20 ms slices / 250 ms total: PASS.
- Publish sequence retry remains bounded.
- Note: verified-bundle sequence-lock uses a plain `Frame` object, but current Read/Publish call sites are in the host submission flow; no independent reader thread was found in this review, so this is not promoted to a defect.

## 61–80 — partial OpenXR / DirectGPU fallback
- Projection swapchain image is released after two-eye render attempt: PASS.
- Safe projection validates acquired image index: PASS.
- Safe projection restores temporary SourceSrv/SourceFormat: PASS.
- Emergency / cached / live theater fallback chain remains intact: PASS.
- Recenter is not falsely completed by R24 view fallback: PASS.
- R32 successful zero-copy path remains asynchronous: PASS.
- SafeEye fallback performs host-owned CopyResource + GPU fence + per-slot ACK: PASS.
- Previous concern that generation quarantine permanently freezes direct-only mode is NOT CONFIRMED: when R32 rejects a faulted generation, lower R24 can still use the DirectGPU verified bundle through SafeEye copy/fence/ACK.
- RESILIENCE P2: if R32 `EnsureFence` itself cannot create an EVENT, it does not mark the generation faulted; it falls to R24. This is safe because no ACK is published, but repeated query-creation failure can cause repeated fallback/ring pressure. Consider explicit fault escalation if runtime logs show this path.

## 81–100 — CI / provenance / configuration combinations
- V4 is a distinct matrix candidate: PASS.
- Win32 game + x64 host architecture split: PASS.
- Deterministic smoke tests are built and executed in the experiment workflow: PASS.
- Direct-ACK identity and R32 policy smoke tests are included: PASS.
- Exit codes are enforced: PASS.
- SOURCE_SHA and SHA256SUMS are packaged: PASS.
- Candidate stays TEST_ONLY_NOT_FOR_INTEGRATION: PASS.
- fail-fast=false preserves diagnostics from independent candidates: PASS.
- V4 remains first in runtime test order: PASS.
- The older active workflow does not contain every experiment-only smoke target, but the V4 experiment workflow does; this is not a V4 candidate defect.

# New actionable findings

## P1 — shadow allocation exception can escape hook
Move allocation/construction of `R30BufferShadow` inside a fail-open try/catch or use a noexcept helper.

## P1 — COM Release ABA registry erase
Capture old registry identity before calling the real `Release`; erase only if refs==0 and the map entry still equals that old identity.

## P1-performance — global registration wait amplification
Replace one global per-class registration counter with targeted in-flight identity/bucket tracking so unrelated world-buffer locks never wait for an XYZRHW registration.

## P2 — R32 EVENT allocation failure escalation
If runtime evidence shows repeated `EnsureFence` creation failures, quarantine or explicitly demote that generation instead of re-attempting the fast path every XR tick.

# Result
100/100 new review units completed. No new normal-success-path P0 defect found. Three P1 items and one P2 resilience item remain for a V5 hardening pass.
