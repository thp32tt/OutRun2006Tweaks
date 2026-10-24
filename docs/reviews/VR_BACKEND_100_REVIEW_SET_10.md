# VR Backend 100-Review Campaign — Set 10/10

This final set is derived from Sets 01-09 and is intentionally a convergence review rather than another local file scan. It asks whether the complete evidence chain is closed from recovered game semantics through packaging, lifecycle, transport, test execution and CI.

## Passes

| ID | Direction | Result | Converged finding |
|---|---|---|---|
| S10-R01 | Canonical game-semantic source | NOT_CLOSED | WVP/address anchors are genuinely centralized and consumed, but the producer-space catalog is not. `hud_semantics.hpp`, `analyze_outrun_exe.py` and `disasm_render_contract.hpp` have drift, and the shared 23-range classifier is not yet the active runtime classifier. Sets 04 F13-F15 remain architecture blockers for backend-neutral semantic ownership. |
| S10-R02 | Package -> selector -> loaded-binary identity | NOT_CLOSED | Preflight strongly binds BUILD_INPUTS/branch/renderer/backend and critical backend payloads, but stale `slots/<VariantId>` can outrank the attested backend payload and there is no post-selection root attestation or transactional rollback. Sets 01-02 F01/F03/F06 and Set 09 F34 remain open. |
| S10-R03 | Reset/device/state lifecycle reference | STRONG_REFERENCE | The R15/R13/R20/R21/R22 D3D9Ex path is fail-closed across promotion, Reset, state-block invalidation, host freshness and re-baselining. It is the correct behavioral reference for future native/DXVK lifecycle work. No later set contradicted this result. |
| S10-R04 | DX11 native activation barrier | BLOCKED_BY_DESIGN | `NativeDrawPathActive=false` is correct. Census exactness currently omits failed introspection, resource usage/update semantics, full input-layout readiness, shader translation readiness and exhaustive draw coverage; the native eye ring also lacks proven run/generation/consumer-ACK parity. F17-F23 and F26 must be closed before any native draw ownership. |
| S10-R05 | DXVK SAFE promotion barrier | OPEN | Same-provider D3D9/D3D9Ex handling and multiview isolation are strong, but cached/upstream provider provenance is not cryptographically pinned, full device recreation lacks explicit re-attestation, and the analyzer can report stock-provider verified without an observed runtime version. Most importantly, the Quest 3 visual gate has not yet been proven for the exact branch build. |
| S10-R06 | Frame transport / synchronization parity | PARTIAL_CONVERGENCE | The current D3D9Ex DirectGPU transport has a coherent producer-fence -> host hold-copy/render -> D3D11 EVENT -> exact consumer ACK chain with run/transport generations. DX11 native resources must reuse equivalent semantics; a simplified native protocol would reopen stale-slot/use-after-release risks. |
| S10-R07 | Performance evidence validity | NOT_YET_BENCHMARK_GRADE | Current DX11/DXVK SAFE sessions use fixed conservative 60-Hz/cadence-off launch settings while the D3D9 reference profiles can use XR cadence/unlocked rendering. HUD inspector, shader fingerprint and DX11 census are also forced on. Current measurements can find gross regressions but cannot support clean backend performance conclusions. |
| S10-R08 | Failure evidence survivability | PARTIAL | Normal game nonzero exits are collected before propagation and analyzer failures are contained. Start-process exceptions, an unkillable host and pre-session selector failures can still bypass automatic ZIP sealing. The one-run workflow is therefore strong for in-game failures but weaker at process/mutation boundaries. |
| S10-R09 | CI proof strength | BLOCKED_BY_VERIFIER_DRIFT | Recent Build failures on both branches occur at `Verify HMD-proven VR baseline`, before configure/compile. The exact failure is `P8_STEREO_SHARED_PREDICATE`: verifier still requires the literal `return Game::is_vr_gameplay_presentation();` in `stereo_renderer_r7.inc`. Therefore the current red Build is **not evidence of a DX11/DXVK compile failure**; it is evidence that the proven-baseline verifier drifted from the refactored source. Until that gate is reconciled, hosted CI cannot prove compilation of the current heads. |
| S10-R10 | One-run usability and merge-gate readiness | TOOLING_CLOSE / RUNTIME_GATE_OPEN | The intended UX is now coherent: target-locked START_HERE, preflight, selector, runner, automatic backend summary, visual checklist and ZIP. However the branch policy requires the same exact runtime build to pass startup/menu/race/goal, stereo geometry/shadows, menu car, flare, arrows/HUD, world rank markers, Reset/recenter and CI. That evidence does not yet exist for either active backend, so neither branch is merge-ready. |

## Final deduplicated priorities after 100 reviews

### Activation / merge blockers

1. **Semantic single-source closure:** reconcile the missing HUD ranges and projected semantic classes, then make the shared semantic contract the live backend-neutral source rather than a parallel catalog.
2. **Loaded-payload identity closure:** eliminate or attest slot override precedence, attest root payload after selector mutation, and make selector failure recoverable/transactional.
3. **DX11 exactness closure:** make observation failures fail closed; add resource behavior, input-layout and shader readiness to activation gates; adopt the proven transport generation/ACK contract.
4. **DXVK SAFE evidence closure:** strengthen provider provenance/version verdicts and obtain exact-build Quest 3 SAFE/two-pass visual parity before touching multiview.
5. **CI baseline gate repair:** reconcile `P8_STEREO_SHARED_PREDICATE` with the current refactored ownership model so configure/compile can actually execute.

### Validation-quality blockers

6. Separate discovery instrumentation from clean performance benchmarking and apply equivalent cadence/profile policy across backends.
7. Add behavior-level one-click tests for payload precedence, mutation failure, target locking and post-selection identity.
8. Seal diagnostics even when process launch or host teardown fails.

## What should remain unchanged

- R70 stays untouched as the reference baseline.
- DX12 stays frozen/reference-only.
- Queue entry RVA 0x2D734 stays non-hookable.
- Unknown/inexact rendering stays fail-closed.
- DX11 native draw remains dormant until explicit activation gates close.
- DXVK custom multiview remains blocked until stock SAFE/two-pass graphics parity.
- The current D3D9Ex Reset/eligibility and DirectGPU ACK ordering remain the lifecycle/synchronization reference.

## Review campaign completion

- Sets completed: **10 / 10**
- Distinct review passes completed: **100**
- Review method: every set chose its next ten directions from the preceding set's unresolved evidence rather than repeating the same checklist.
- Production source changes during this campaign: **none**; only review evidence documents were committed.
- Runtime merge gate: **still open** for both DX11 and DXVK.
