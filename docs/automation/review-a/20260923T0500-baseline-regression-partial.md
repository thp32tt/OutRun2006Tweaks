# A review evidence — 2026-09-23 05:00 KST

Status: PARTIAL_NOT_CP150
Integration target: `539fecf218d39cea103da6ccc23f59eb7498185f`
Protected USER_RUNTIME baseline: `17ad376bfdf7939f0851c0c629e4fa094a84f28a`
Stable key: `VR-R51-WORLD-STEREO-PRESERVE-001`
Classification: `BASELINE_REGRESSION_RISK / READY_FOR_C`
Issue #6 handoff: comment `5783167083`

## Evidence

1. `docs/VR_AUTODEV_PROTOCOL.md` defines USER_RUNTIME_VERIFIED baseline evidence as independent from moving integration HEAD and forbids BUILD_VERIFIED evidence from replacing it.
2. `docs/VR_REGRESSION_KNOWLEDGE.json` identifies R51 `17ad376b...` as the current partial accepted USER_RUNTIME baseline and protects road/background/vehicle 3D stereo, frame stability, and the prohibition on broad world-to-HUD ownership.
3. R51 `src/vr/d3d9/stereo_renderer_r26.cpp::R28RunWithVerifiedWorldEpoch()` rejects `ScreenOverlay2D` and `ScreenHud`, then calls `R28CanRebindVerifiedWorld()`.
4. `R28CanRebindVerifiedWorld()` requires a valid game/backbuffer/stereo state, no aux/query hazard, a positive perspective-world semantic, matching last verified WVP, matching pose sequence, matching live c64..c67 values, and matching projection/generation.
5. R51 temporarily substitutes the verified shader identity/serial only around the R9 per-eye draw and restores both using compare-exchange, limiting the synthetic epoch lifetime.
6. Current focus still contains the proof helper but `R28RunWithVerifiedWorldEpoch()` no longer calls it. A changed vertex-shader identity/serial increments the reject counter and returns `E_NOTIMPL`.
7. Therefore current focus does not structurally preserve the exact shader-epoch world-continuation path present in the USER_RUNTIME_VERIFIED R51 tree.
8. This is a baseline-applicability risk, not proof of an HMD-visible regression. Runtime truth remains NEED_HMD_TEST.
9. Bounded hypothesis: legitimate perspective world/billboard draws can retain the same WVP/projection/pose across a shader-epoch change; unconditional fail-close can demote them from the R51-proven per-eye world path.
10. LEVEL0 verifier: seed verified WVP/projection/pose; change shader epoch only; assert World/WorldBillboard reaches per-eye continuation; ScreenOverlay2D/ScreenHud and any WVP/projection/pose mismatch fail closed; verify temporary epoch restoration on success and failure.

## Required C baseline delta

- `VR-R51-WORLD-STEREO-PRESERVE-001`
- `VR-R51-FRAME-STABILITY-PRESERVE-001`
- `VR-STARTUP-WHITE-001`

## Completion accounting

This run deliberately does **not** claim CP150 or COMPLETE. The 150-unit / >=75-fresh gate was not honestly satisfied within this invocation. No previous CP150 rows were relabeled as fresh. The persisted result is a concrete actionable baseline-regression handoff only.
