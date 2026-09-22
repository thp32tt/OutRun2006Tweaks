# B27 summary

- role: B review-only
- integration: `539fecf218d39cea103da6ccc23f59eb7498185f`
- protected USER_RUNTIME baseline: R51 `17ad376bfdf7939f0851c0c629e4fa094a84f28a`
- topology: diverged, merge-base `4ff3a3f98a000e0e19f4ba065066d5f81e9d5417`; R51 ahead 53 / behind 14 relative to current HEAD
- review units: 150 physical rows; fresh 75; carry 75
- CP10..CP150: complete
- source writes: none

## Result
The current integration still does not contain R51's explicit `ScreenOverlay2D`, `ScreenHud`, `CorroboratesHud`, `CorroboratesScreenOverlay2D`, or SpriteNode semantic registry/queue ownership machinery. R51 contains those mechanisms and remains the protected USER_RUNTIME partial baseline. This is baseline-regression risk, not proof that every R51 mechanism should be copied wholesale.

The exact R51-vs-HEAD compare exposes runtime-rendering deltas in hooks_graphics/textures/uiscaling, ex-device upgrade, R26/R30/R30-safe/R31/R34, HUD inspector, outrun renderer, render semantics, HUD semantics and test-profile policy. These paths were reviewed through cross-boundary, adversarial, direct-path, regression and performance lenses. No new stable regression ID was created because the observed risks map to existing R51 world/HUD/rank/frame-pacing keys.

## C handoff
READY_FOR_C: construct an isolated candidate from exact current HEAD, compute both R51->candidate and HEAD->candidate BASELINE_DELTA, restore only evidence-backed HUD/rank semantic ownership needed for open defects, and preserve R51 world stereo/frame stability. Do not reintroduce blanket queue-to-HUD ownership. Preserve `SkyGlowFactor=1` and runtime-selected `TargetRefreshRateHz=0`. Hardware-visible correctness remains NEED_HMD_TEST until matching Quest3/VDXR evidence.
