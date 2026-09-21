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

**Status:** REOPENED / PROTECTION_MISSING_ON_CURRENT_FOCUS  
**Observed again:** 2026-09-21 KST  
**Severity:** runtime-blocking

### Symptom fingerprint

The game reaches or passes the logo, then remains on a white screen instead of progressing into normal menu/game flow. Input/recenter may still react, so this is treated as a presentation/progression regression rather than a simple process crash until logs prove otherwise.

### Reconstructed durable knowledge (2026-09-22)

The prior failure was correlated to known-bad `1f2dcb9848a7142c295f371f0dc91663f174c442`. The bounded root cause was D3D9Ex synchronous CreateDevice-thread stereo installation calling `EnsureStereoResources` before the promoted device was returned to OutRun, allocating/mutating private render-target/depth resources before fresh-device initialization completed.

Primary protection was `986f0d5794476056ef4bea08c6ac3c0d1f5f01d2`, which kept synchronous hook ownership but deferred private stereo-resource creation until the first successful real game `Present`. Structural guard `ba402e98351fcf8d215bd7719b6ea56044566ead` protected that invariant. Known-good startup transition was observed on `a9abb85702925aaa09ca85581423eb9766c2adb3`; that build still had a separate theater-only VR follow-up defect.

Current `vr-d3d9ex-focus` diverged from that historical fix line and again contains the pre-fix resource initialization in `InstallStereoHooks`, while `PresentDest` lacks the deferred-init protection. This is a recurrence caused by missing protection, not a new bug key.

### Required recovery sequence

1. Reconstruct the `986f0d57` protection minimally on the latest focus branch while preserving current post-successful-Present ownership.
2. Restore a deterministic structural guard equivalent to `ba402e98`.
3. Build the active DX9Ex game DLL and x64 OpenXR host and run deterministic host/regression checks.
4. Keep one mandatory HMD startup transition check: **logo -> menu/game, no persistent white frame**.
5. Also confirm gameplay stereo opens after the deferred initialization.
6. Append candidate/integration/validation events to Issue #13; final DONE requires matching USER RUNTIME VERIFIED evidence.
