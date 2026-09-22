# VR Runtime Problem / Regression History

GitHub event ledger: Issue #13 — **[VR] Runtime Problem / Regression Ledger**

This document is the human-readable companion to `docs/VR_REGRESSION_KNOWLEDGE.json`. The JSON file is the machine-readable source of truth used by autonomous review/fix/integration work.

## Rules

- Repeated symptoms reuse the same stable regression key; do not create a new finding just because a later SHA reproduces it.
- Every recurrence is recorded as a `REOPENED` event in Issue #13 and increments the registry recurrence count.
- A case cannot be considered permanently fixed without: root cause (or bounded cause), exact fix reference, affected/risk paths, a verifier/evidence recipe, and validation level.
- Runtime-visible failures may be statically/build verified, but final `DONE` requires matching runtime evidence.
- D must load this registry at C0 RECOVER and revalidate any case whose risk paths/triggers intersect the candidate change before integration.
- When a regression reappears, start from the stored prior root cause, fix SHA, affected paths, known-good/known-bad identities and verifier before exploring a new hypothesis.

## VR-STARTUP-WHITE-001 — logo -> persistent white screen

**Status:** INTEGRATED / BUILD_VERIFIED / NEED_HMD_TEST  
**Observed again:** 2026-09-21 KST  
**Integrated protection:** 2026-09-22 KST  
**Severity:** runtime-blocking

### Symptom fingerprint

The game reaches or passes the logo, then remains on a white screen instead of progressing into normal menu/game flow. Input/recenter may still react, so this is treated as a presentation/progression regression rather than a simple process crash until logs prove otherwise.

### Reconstructed durable knowledge

The prior failure was correlated to known-bad `1f2dcb9848a7142c295f371f0dc91663f174c442`. The bounded root cause was D3D9Ex synchronous CreateDevice-thread stereo installation calling `EnsureStereoResources` before the promoted device was returned to OutRun, allocating/mutating private render-target/depth resources before fresh-device initialization completed.

Historical protection was `986f0d5794476056ef4bea08c6ac3c0d1f5f01d2`, with structural guard `ba402e98351fcf8d215bd7719b6ea56044566ead`. Known-good startup transition was observed on `a9abb85702925aaa09ca85581423eb9766c2adb3`; that build still had a separate theater-only VR follow-up defect.

### Current-focus integration — 2026-09-22

Candidate `341bd8027b9595f43c89e31ae1f9cf8783751faa` reconstructed the protection on base `3de2e34c8f77b39a6a5f1f2a521e21ac2a82ef39`: synchronous `InstallStereoHooks` no longer initializes private stereo resources before CreateDeviceEx exposure, and final R23 `Present` initializes them only after a successful lower game Present. The deterministic architecture guard is included. DX9Ex Active Validation run `35647825229` succeeded. A domain review, B rendering-domain review, and C exact-SHA changeset sanity all passed with runtime validation explicitly remaining `NEED_HMD_TEST`.

The candidate was fast-forward integrated into `vr-d3d9ex-focus`. This is **not final DONE** because the failure is runtime-visible.

### Required remaining validation

1. Launch the CORRECTNESS package on Quest 3 / VDXR.
2. Confirm **logo -> menu/game** with no persistent white frame.
3. Confirm first gameplay stereo opens after deferred initialization.
4. If it passes, append USER_RUNTIME_VERIFIED/VALIDATED to Issue #13 and update the registry to DONE.
5. If it recurs, append REOPENED using `VR-STARTUP-WHITE-001`, increment recurrence, and preserve the full earlier history.


## VR-CRASH-HUDQUEUE-001 — SpriteNode queue-entry mid-hook startup crash

**Status:** FIX_CANDIDATE / NEED_HMD_TEST  
**First observed:** 2026-09-21 KST  
**Recurred:** 2026-09-22 KST  
**Severity:** runtime-blocking

### Symptom fingerprint

Immediate `0xC0000005` access violation inside the canonical SpriteNode queue-entry block after `VRHudQueueSemanticBridge` is installed. Real runtime faults were observed at `OR2006C2C.EXE+0x2D738` and `+0x2D73E`.

### Root cause

R47/R49 installed a production `SafetyHookMid` directly at canonical queue-entry RVA `0x2D734`. The entry consists of a short prologue plus a relative call and following memory-load instruction. Two independent runtime crashes resumed inside that relocated instruction sequence, proving the `0x2D734` mid-hook boundary unsafe even though the canonical EXE identity/opcodes were correct.

### Fix candidate

Branch `vr-d3d9ex-candidate/VR-HUDQUEUE-ENTRY-CRASH-559eb670` removes the `0x2D734` production hook completely. Semantic queue ownership now opens lazily at the first real per-node hook `0x2D762`, where EDI already identifies the `SpriteNode*`; the existing common epilogue `0x2DCB4` closes the semantic scope.

The visual-contract verifier forbids reintroducing `Module::exe_ptr(0x2D734)` into the production bridge. The stable crash signature is also stored in `docs/VR_CRASH_SIGNATURES.json`.

### Required remaining validation

1. Exact candidate policy/Win32/x64/package CI must pass.
2. Launch CORRECTNESS on Quest 3 / VDXR.
3. Confirm startup passes the prior `0x2D738/0x2D73E` crash boundary.
4. Confirm HUD semantic rendering becomes active without falling back to broad draw heuristics.
5. Only after matching user runtime evidence may this case move to DONE.
