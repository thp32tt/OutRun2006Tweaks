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


## 2026-09-23 — R50/R51 protected visual/performance cases normalized

The following already-recorded runtime cases were normalized to the durable regression schema after CI exposed missing verifier metadata. This is a metadata/validation-contract repair only; it does not change prior HMD observations or claim any open visual defect fixed.

- `VR-R50-WORLD-STEREO-PRESERVE-001` — protected road/background/vehicle stereo invariant; HMD revalidation remains required for runtime-risking renderer changes.
- `VR-R50-FRAME-STABILITY-PRESERVE-001` — protected subjective frame-stability invariant; timing instrumentation and same-scene HMD comparison are required for risky performance changes.
- `VR-R50-WHITE-HUD-DIPLOPIA-001` — open white HUD/head-lock failure retained for historical continuity.
- `VR-R50-VEHICLE-RANK-ANCHOR-001` — open rank-marker world-anchor failure retained for historical continuity.
- `VR-R51-WHITE-HUD-DIPLOPIA-001` — current R51 white/fixed-function HUD correction target; no blanket queue-to-HUD widening allowed.
- `VR-R51-VEHICLE-RANK-ANCHOR-001` — current R51 world-billboard anchor target; preserve Calc3D2D vehicle/world anchor through per-eye projection.

## 2026-09-24 — R51 EXE-map HUD producer candidate failed, root-cause boundary narrowed

Candidate `8d21824f9502b3354fae679972a90868a0cce562` preserved the protected R51 world/road/vehicle stereo but failed both open R51 HUD regressions. White HUD/position-rank elements remained doubled and headset-following, and vehicle rank markers remained detached from their vehicles and headset-following.

The important new evidence is not merely another failed visual attempt: exact producer tagging was observed and `semanticHudAccepted` reached 93,681, while renderer `semanticOverlayBypass` remained zero for the entire session. The working hypothesis is now an ownership-lifetime/order gap: semantic selection is visible at R30 draw time but not at the earlier renderer c64/WVP injection boundary.

For the rank-marker case, exact callsite WORLD_BILLBOARD tags were also insufficient. Future work must preserve/recover the actual vehicle/world anchor from Calc3D2D/producer data through the queued SpriteNode and per-eye projection instead of relying on screen-space position plus scope alone.

Protected R51 baseline remains unchanged. The failed candidate is evidence only and must not be integrated.

