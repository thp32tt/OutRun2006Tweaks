# R69 performance EXP_ALL_V3 additional review

Source checkpoint: `f19745bf88bbab6dc765f326148cb557f3984631`

This review intentionally does not repeat the V2 checklist. It focuses on ten new post-change questions.

## 1. Selectivity proof
Question: can an unrelated world VB/IB become shadowed merely because the global Lock hook is installed?
Result: PASS. Lock/Unlock/Release enter the registry only when the tracked-buffer Bloom gate says the pointer may belong to a registered shadow. New shadows are created only by explicit XYZRHW FVF creation evidence or an actual XYZRHW draw.

## 2. First-write behavior
Question: can an explicitly fixed-function XYZRHW VB miss its first CPU write?
Result: PASS for explicit FVF buffers. The CreateVertexBuffer hook pre-registers only `(fvf & D3DFVF_POSITION_MASK) == D3DFVF_XYZRHW`, so its first subsequent Lock can be captured.
Residual: an index buffer has no creation-time vertex semantic, so a newly created indexed XYZRHW path can still fail open on its first draw until a later Lock supplies CPU bytes. This preserves safety and should be checked in HMD logs/visuals.

## 3. Negative-cache invalidation
Question: can a thread-local known-miss remain stale after a shadow is later registered?
Result: PASS. Every insert/erase advances `R30ShadowRegistryGeneration`, invalidating cached misses.

## 4. Bloom false-positive/false-negative behavior
Question: can the fast gate make a tracked buffer invisible?
Result: PASS. Registration sets the bit before use; false positives only add a map lookup. Tracked Release rebuilds the Bloom from the live registry, preventing long-session saturation.

## 5. Lock/Unlock/Release symmetry
Question: does optimization apply only to Lock while Unlock/Release still serialize on the map mutex?
Result: PASS after V3 hardening. All three methods use the same tracked-buffer gate.

## 6. Multithreaded diagnostics
Question: can buffer hooks race on telemetry counters or first-log flags?
Result: PASS. Shadow counters are atomic with relaxed increments; first-log flags use atomic exchange. Registry and per-entry state remain mutex protected.

## 7. Reset and lifetime
Question: can stale tracked identity survive resource destruction/reset?
Result: PASS for tracked resources. Release erases registry entries and rebuilds the Bloom; full rollback clears registries/Blooms and advances generation. Default-pool resources destroyed for Reset therefore cannot retain live shadow ownership.

## 8. Deferred DirectGPU query lifetime
Question: can the V2 failed-projection EVENT queries leak across normal host shutdown?
Result: PASS after V3 cleanup. `R23ReleaseDeferredReferenceAcks()` releases all query COM objects on normal and exception shutdown.

## 9. CI falsification
Question: does the performance experiment only compile, or does it execute deterministic safety tests?
Result: PASS after workflow hardening. Every matrix candidate builds and runs shader, runtime-eligibility, verified-bundle, R32 policy, direct-ACK identity, protocol-v3, core-math, host-state-v3, v2/v3 conversion and host-pose-v3 smoke tests.

## 10. Performance self-regression
Question: did thread-safety hardening add expensive sequentially-consistent atomics to the hot shadow path?
Result: PASS after final V3 change. High-frequency shadow counters use `fetch_add(..., memory_order_relaxed)`. Untracked buffer operations only pay pointer hashing + one relaxed Bloom load.

## Remaining runtime questions
- Measure whether global vtable hook call overhead itself is visible in a buffer-heavy scene even after the Bloom fast reject.
- Verify newly created indexed XYZRHW buffers do not produce a visible one-frame fail-open before their next CPU Lock.
- Compare P5 vs V3 P95/P99 frame time; do not infer benefit from average FPS.
- Compare SkyGlow explicit touched-state restore against P5 D3DSBT_ALL timing because driver behavior may differ.

Status: STATIC_REVIEW_PASS_FOR_HMD_TEST.
