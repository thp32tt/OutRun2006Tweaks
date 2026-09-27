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


## S3 — FrameContext introduction
- Branch: `vr-d3d9ex-candidate/r69-clean-s3`
- Parent: S2 `f504705ad8b2650790dbd2d07991a100a9b1820c`
- Change: introduced `src/vr/d3d9/frame_context.hpp` and moved the R67/R68 stage-transition identity/hold state into `FrameContext`.
- Stage-transition behavior remains unchanged: three-present hold, last-good projection reuse, SkyGlow capture epoch reset.
- This is the first migration step; unrelated long-lived telemetry/state remains untouched.
- Build gate: DX9Ex Active Validation triggered from this final stage head.


## S4 — remove R57 production mode matrix
- Branch: `vr-d3d9ex-candidate/r69-clean-s4`
- Parent: S3 `6b6debb0a153a881e8a6e408a8bf5dadb55e4978`
- Production renderer: removed `R57Mode()` and `OUTRUN_VR_R57_MODE`; projected rival markers now always use the R69 HMD-proven head-inverse path.
- HUD producer ownership: removed the second R57 mode selector in `src/hooks_uiscaling.cpp`; rank markers are fixed to `ProjectedWorldMarker2D` and DispRank/POSITION nodes are fixed to exact `ScreenHud` ownership.
- Test launcher: numbered R57 GUI variants are removed from the selector; `R69_FIXPACK` is the visible production variant. Legacy variant names remain runner aliases but no longer alter renderer ownership.
- Validation policy: proven-baseline and launcher-policy gates now reject reintroduction of `OUTRUN_VR_R57_MODE`.
- Visual policy intentionally preserved from R69: projected rank head inverse, centre-eye fused flare, stock PC shadow behavior, exact option-arrow ownership.
- Build gate: DX9Ex Active Validation triggered from this final stage head.


## S5 — canonical render-policy boundary
- Branch: `vr-d3d9ex-candidate/r69-clean-s5`
- Parent: S4 `5942ea9445da5d5e18d8ba0abf72eb9ab677fb13`.
- Added `src/vr/d3d9/render_policy.hpp` as the single RenderScope -> render-route mapping boundary.
- The production screen-space classifier now consumes the canonical route instead of independently re-deriving HUD/world/projected booleans.
- Visual behavior is intentionally unchanged; this stage reduces duplicated classification logic before further renderer separation.
- Build gate: DX9Ex Active Validation on the candidate branch.


## S6 — screen-space policy extraction
- Branch: `vr-d3d9ex-candidate/r69-clean-s6`
- Parent: S5 `fc2b0de8cf78ec757d35efdaa83ddbcd744e3d0e`.
- Added `src/vr/d3d9/screen_space_policy.hpp` and moved the screen-space kind definition plus exact producer-route dispatch out of the 4k-line renderer body.
- Exact ScreenOverlay2D / ProjectedWorld / ProjectedScreenEffect semantics now resolve through a small policy module before projection/WVP classification.
- HUD and world paths still use the existing proven projection/WVP gates, so visual policy remains R69-equivalent.
- Build gate: DX9Ex Active Validation on the candidate branch.


## S7 — unified stereo safety policy
- Branch: `vr-d3d9ex-candidate/r69-clean-s7`
- Parent: S6 `d46e8c55335a8360b2a9d62a606160b02e6503b3`.
- Added `src/vr/d3d9/safety_policy.hpp` with one fail-closed `StereoReplayState -> CanReplayStereo` predicate.
- The R30 production owner now gathers live D3D9/runtime state and delegates the decision to this policy instead of maintaining a second nested boolean gate.
- Existing R9/R13 mono-shadow fallback behavior is preserved; this stage changes ownership of the decision, not its conditions.
- This is checkpoint build B2 for limited HMD testing.
- Build gate: DX9Ex Active Validation on the candidate branch.


## S8 — hot-path telemetry/branch cleanup
- Branch: `vr-d3d9ex-candidate/r69-clean-s8`
- Parent: S7 `b98155535d5ccbea2fd06e7ae55a8c5cadfb9670`.
- Removed redundant projected/overlay semantic booleans after the new direct screen-route dispatch; HUD/world are the only routes that continue into projection/WVP classification.
- Projected-marker atomic counter and first-event log now run only when VR telemetry is enabled.
- No projection, eye transform, safety, HUD-scale, flare, shadow or stage-transition policy changed.
- Build gate: DX9Ex Active Validation on the candidate branch.
