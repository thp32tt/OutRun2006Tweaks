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
