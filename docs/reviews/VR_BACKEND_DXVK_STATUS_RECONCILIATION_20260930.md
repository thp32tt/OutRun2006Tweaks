# DXVK Status Reconciliation Review — CONVERSION-DXVK-00095

Status: SUPERSEDED_BY_VALIDATED_SOURCE_RESULT
Branch: vr-dxvk-r71-disasm
Base SHA: 8d8275951ce2da04c4eb41acd559d6e01e1f9dff
Runtime validation: UNTESTED
This review note's own runtime source change: none
Task source result: f5374416de2db3c77be7da787320cdae47de1a8e
Validation-bearing descendant: 0a9471b603623e77ec51ac0a85d11341690b1d58

## Scope

This bounded C1 review follows the CONVERSION-DXVK-00093 handoff. It does not tune copy/wait/cadence behavior and does not claim Quest 3/VDXR runtime correctness. Its purpose is to reconcile historical review-set statements with the current DXVK software-closure evidence so later automated runs do not reopen already-closed work.

> Post-validation reconciliation: this document was authored concurrently and landed as a docs-only child of source result `f5374416de2db3c77be7da787320cdae47de1a8e`. Its original "no renderer/runtime source change" conclusion applied only to this review note, not to the whole task. The actual selected work for `CONVERSION-DXVK-00095` is the bounded Set 04/F13 live adoption of the shared producer map for 15 exact `DispTimeAttack2D` callsites. The child changes only this review document, so the source blobs are unchanged and were validated through the exact descendant.

## Five-lens review

### 1. Provider provenance and runtime-version lens

Set 06 was correct at review time to carry F24, F08/F09 and F12 as open. Those software findings are now closed by later exact-SHA work:

- F24 requires an observed exact DXVK runtime version before stock-provider verification.
- F08/F09 pin and verify the stock DXVK release archive/cache/package provider.
- F12 re-attests provider/capability evidence after each successful device creation/recreation.

These are software/CI closures only. They do not establish HMD visual parity.

### 2. One-click identity and mutation lens

The current DXVK branch has software closure for target identity, package integrity, transactional selector rollback, post-selection root attestation and executable one-click behavioral coverage. Historical Set 10 text describing stale-slot precedence, missing rollback or absent root attestation is preserved as campaign-time evidence, not current branch status.

### 3. Transport and synchronization lens

The host DirectGPU path remains intentionally guarded at one left/right host-owned hold CopyResource pair, with producer/consumer generation and ACK ordering preserved. No evidence in the completed software closures justifies removing the hold pair or changing polling/Flush cadence without exact-build HMD FrameBudget evidence.

### 4. Performance-methodology lens

DXVK SAFE PERFORMANCE now has cadence/profile equivalence and reduced diagnostic instrumentation sufficient for a clean benchmark path. This closes the software methodology gap for DXVK SAFE, but no performance verdict is valid until the same exact build is measured in Quest 3/VDXR on a controlled scene.

### 5. Adversarial stale-status lens

The remaining stale statements are documentary/historical rather than live implementation blockers. The current index and completed task records supersede them for present status. Reopening F08/F09/F12/F24/F34/F35 without new contradictory evidence would duplicate completed work.

## Current DXVK status after reconciliation

Software/source-graph closures already established:
- F04 stereo facade structure debt: CLOSED at software/source-graph level by CONVERSION-DXVK-00093.
- F08/F09 provider provenance: CLOSED in software/CI.
- F12 recreation re-attestation: CLOSED in software/CI.
- F24 runtime-version verdict: CLOSED in software/CI.
- F25 selector transaction wording/contract: CLOSED.
- F27/F28/F29 DXVK SAFE performance-path methodology: CLOSED for DXVK SAFE.
- F30 DirectGPU copy amplification: GUARDED; runtime cost remains unmeasured.
- F34 package-wide integrity: CLOSED for DXVK one-click.
- F35 one-click behavioral CI: CLOSED for DXVK one-click.

## Remaining DXVK gates

The remaining DXVK lane gates are hardware/runtime evidence, not an invitation for speculative software tuning:

1. Exact-build Quest 3/VDXR stock DXVK SAFE two-pass visual parity through startup/menu/race/goal, stereo geometry/shadows, menu car, flare, arrows/HUD, world rank markers, Reset and recenter.
2. Same-scene PERFORMANCE frame-time evidence for the host-owned DirectGPU path, including whether the guarded hold-copy pair is materially costly on target hardware.
3. Only after SAFE/two-pass parity is established may custom multiview be considered for promotion.

## Decision

This concurrent review note itself makes no renderer, transport, selector, package or runtime-policy change. However, the task source result `f5374416de2db3c77be7da787320cdae47de1a8e` does make one bounded behavior-preserving source change: the 15 already-proven `DispTimeAttack2D` exact callsites now derive their existing `SCREEN_HUD` handoff from the centralized disassembly producer map. No producer range was widened.

The docs-only child `0a9471b603623e77ec51ac0a85d11341690b1d58` preserved those source blobs and passed Backend Conversion Gate `36639004847`, Build `36639011795`, OpenXR architecture `36639011760` (6/6 jobs), HUD Inspector `36639011771`, and hosted-package runs `36639011911`/`36639004952`. Therefore the original no-source-change conclusion is superseded. `RUNTIME_VALIDATION=UNTESTED` remains mandatory because no Quest 3/VDXR or in-game run was performed.
