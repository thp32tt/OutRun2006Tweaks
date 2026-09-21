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

**Status:** REOPENED / NEEDS_RECONSTRUCTION  
**Observed again:** 2026-09-21 KST  
**Severity:** runtime-blocking

### Symptom fingerprint

The game reaches or passes the logo, then remains on a white screen instead of progressing into normal menu/game flow. Input/recenter may still react, so this is treated as a presentation/progression regression rather than a simple process crash until logs prove otherwise.

### Current durable knowledge

A similar symptom was reported as fixed on 2026-09-20, but the exact prior root cause and fix SHA are not currently encoded in durable repository state. They must be reconstructed from the 2026-09-20 candidate, runtime logs, scheduled history and commits. No root cause should be invented.

### Risk surface

Startup/device creation/reset/Present flow, stereo transport/shared-frame eligibility, host first-frame/fallback state, and launch/profile configuration are all revalidation triggers.

### Required recovery sequence

1. Search prior runtime bundles/history for the same symptom fingerprint.
2. Identify the last known-good and first known-bad SHA/config pair.
3. Recover the prior root cause and exact fix commit if it existed.
4. Reapply or adapt that fix only after checking why the protection was lost.
5. Add a deterministic smoke/static guard when feasible.
6. Keep one mandatory HMD startup transition check: **logo -> menu/game, no persistent white frame**.
7. Append the recurrence/fix/validation event to Issue #13 and update the JSON case instead of creating a duplicate finding.
