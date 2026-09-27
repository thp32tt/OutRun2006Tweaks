# R69 CLEAN structural simplification history

Baseline: R69 `e47fca96124566690eedeaf1c6e438dc67882e81`

Rules:
- Preserve a branch at every stage (S0..S4).
- Build/validate every stage before using it as the parent of the next stage.
- No visual-policy changes unless explicitly listed for that stage.
- R69 HMD-proven behavior is the regression baseline.
- vr-d3d9ex-focus is not modified by this cleanup series.

## S0 — frozen R69 baseline
- Branch: `vr-d3d9ex-candidate/r69-clean-s0`
- Purpose: immutable cleanup starting point plus build-history plumbing.
- Source behavior: identical to R69.
- Build gate: DX9Ex Active Validation.
- Status: branch created; validation trigger added in this stage.


## S1 — diagnostics/experiment separation
- Branch: `vr-d3d9ex-candidate/r69-clean-s1`
- Parent: S0 `5ee57a2585d5f2c9a8e48a8b028b479e39d5af8e`
- Change: moved R55 HUD coordinate mode, R56 HUD probe mode, and R57 projected-marker experiment environment parsing into `src/vr/debug/experiment_modes.hpp`.
- Production renderer now consumes those values through a debug-module boundary; render behavior and defaults are unchanged.
- Build gate: DX9Ex Active Validation triggered from this final stage head.


## S2 — semantic type unification
- Branch: `vr-d3d9ex-candidate/r69-clean-s2`
- Parent: S1 `5497f00f0183a3f99b3a56262b8160c8fd7f2bf7`
- Change: removed the duplicate HUD-only `SpacePolicy` enum from `src/vr/hud_semantics.hpp`.
- HUD reverse-engineering ranges and the HUD inspector now use `OutRunVR::GameSemantic::RenderScope` directly.
- Semantic outputs remain the same: unknown -> None, finite HUD -> ScreenHud, world-attached markers -> WorldBillboard.
- Build gate: DX9Ex Active Validation triggered from this final stage head.
