# B19 summary

Status: COMPLETE subject to persisted ledger/checkpoint reread.
Target integration SHA: `c4dd697e2b1f33d3b8af6ab254f378a1cc421248`.
Review branch only; no production runtime source or integration changes.

## Accounting
- review_units_completed: 150
- evidence-bearing rows: 150
- fresh_units: 150
- carried_forward_units: 0
- outside_latest_delta: 145
- cross_subsystem: 60
- adversarial_falsification: 30
- distinct_functions_or_paths: 30
- existing_finding_revalidation: 5
- CP10..CP150: accounted for

## Result
B19 rotated away from B18 DirectGPU/ACK and reviewed graphics post-process/state restoration plus D3D9Ex compatibility reset/resource-shadow boundaries.

Existing finding `VR-REFLECTION-RATE-ACTIVE-GATE-001` (Issue #6 comment 5761987578) is revalidated, not duplicated. Current `ReflectionUpdateRate::FaceCount_dest` still uses `Settings::VREnabled && Settings::VRNormalizeReflectionRate` for QPC elapsed-time normalization. It does not use `RuntimeEligibility::MayInjectStereo()` or equivalent active-runtime authority and only clears the QPC epoch when the config gate becomes false. This matches the stored falsifiable hypothesis: configured-but-runtime-ineligible menu/fallback/recovery intervals can still receive the VR elapsed-time reflection policy. Exact nextAction for C/D remains the existing finding's deterministic runtime-eligibility verifier and minimal active-gate correction; B does not implement it.

The current near-plane path is contrary evidence for the older near-plane recurrence: `CalcCameraMatrix_dest` now requires `VRPositionalTracking && VRStereo && RuntimeEligibility::MayInjectStereo()` in GAME/GOAL before applying `VRNearPlane`; B19 therefore does not reopen `VR-NEARPLANE-ACTIVE-GATE-001`.

Reset compatibility was traced from fresh-device `CaptureClassicBaseline` through successful `ResetEx` into `RestoreClassicResetState`. Render states, texture-stage states and sampler states are replayed; textures/streams/indices/shaders are neutralized and viewport/scissor are rebuilt from the new backbuffer. A broader classic-reset-state completeness question (transforms/material/lights/clip planes/palette/shader constants) remains NEEDS_EVIDENCE rather than a promoted defect because B19 did not establish an active post-reset visual failure or prove those categories are not deterministically re-primed by the game/VR caches.

R14 shadow ownership remains fail-closed under device replacement and external GPU writes: locked shadows defer retirement, external writes invalidate/retire CPU authority, and the 384 MiB budget bounds shadow allocation. No new bounded P0/P1 rendering/performance defect was promoted from that cluster.

Regression registry `VR-STARTUP-WHITE-001` remains `INTEGRATED_BUILD_VERIFIED_NEED_HMD_TEST`; B19 produced no matching runtime recurrence evidence and does not mark it DONE.

Exact nextAction: C should consume the revalidation of `VR-REFLECTION-RATE-ACTIVE-GATE-001` as EVIDENCE_AUGMENT, avoid a duplicate finding, and keep the existing deterministic verifier/fix intent. Next B should rotate away from this reset/R14 cluster unless a candidate or runtime evidence invalidates it.
