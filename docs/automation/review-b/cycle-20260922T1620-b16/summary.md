# B16 Deep Review — 2026-09-22 16:20 KST

- target: `c4dd697e2b1f33d3b8af6ab254f378a1cc421248`
- role: B review-only
- review_units_completed: 150
- fresh_units: 150
- carried_forward_units: 0
- outside_latest_delta: 144
- cross_subsystem_traces: 50
- adversarial_falsifications: 50
- distinct_functions_or_paths: 50
- existing_finding_revalidation: 9
- regression key consulted: `VR-STARTUP-WHITE-001`
- CP10..CP150: persisted in checkpoints.md
- production source modified: no
- integration modified: no

## Finding

`B-SKYGLOW-CONFIG-POLICY-001` — READY_FOR_C_ORGANIZATION.

The current integration tree defines `SkyGlowFactor` default 4 in both `src/hooks_graphics.cpp` and the checked-in `OutRun2006Tweaks.ini`, while the current project runtime policy requires preserving `SkyGlowFactor=1`. The render semantic path already treats SkyGlow specially (`ForceZeroDisparity`) and the graphics code documents suppression during true stereo, so this is a configuration/profile identity defect rather than evidence for changing the stereo render algorithm.

Bounded hypothesis: a package/profile that consumes the checked-in default without an explicit package override can run SkyGlow at factor 4, violating the intended VR correctness profile and making visual comparisons non-deterministic across packages.

Contrary evidence sought: runtime-selected refresh remains correctly auto-native (`TargetRefreshRateHz=0.0` in checked-in INI); DirectGPU is currently safe-default false in the checked-in INI; async pixel diagnostics use `D3D11_MAP_FLAG_DO_NOT_WAIT`; DirectGPU latest-frame-wins skips old unsampled ring frames and ACKs them without D3D11 copy/draw.

Recommended D intent (through C queue, not B): make the authoritative CORRECTNESS/package profile explicitly pin `SkyGlowFactor=1` and add a deterministic profile/config verifier; do not change production stereo behavior solely from this finding. Runtime visual closure remains NEED_HMD_TEST.

## Regression gate

`VR-STARTUP-WHITE-001` remains `INTEGRATED_BUILD_VERIFIED_NEED_HMD_TEST`. Its risk paths include `src/hooks_graphics.cpp`, `src/vr/**`, `vrhost/**`, INI and VR workflow. This B run does not mark it DONE.

## Performance observations

- `TargetRefreshRateHz=0.0` and `FrameCadenceTargetHz=0.0` preserve runtime-selected cadence.
- `R35CadenceHost` quantizes common runtime rates and debounces changes before updating active render Hz.
- DirectGPU selection is latest-frame-wins; skipped unsampled frames are ACKed immediately.
- Pixel diagnostics are rate-limited and use non-blocking staging maps, but still add periodic copy work; no evidence in this static review establishes a user-visible regression.
- Projection/theater paths preserve explicit acquire/render/release ordering in reviewed code.

## nextAction

C should deduplicate `B-SKYGLOW-CONFIG-POLICY-001` against the existing SkyGlow active-gate queue item and, if not duplicate, route the smallest config/profile verifier + correction to D. Quest3/VDXR remains required for visual/runtime closure.
