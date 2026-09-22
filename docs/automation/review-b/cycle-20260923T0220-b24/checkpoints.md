# B24 checkpoints

Target integration: `539fecf218d39cea103da6ccc23f59eb7498185f`
USER_RUNTIME_VERIFIED working baseline: `17ad376bfdf7939f0851c0c629e4fa094a84f28a` / CORRECTNESS / package SHA256 `bf9f5b7c04520f1bf018764f54c1a915e019f4a21b18bf5fab061ce29790fbe7`.
Review role: B review-only. Production/candidate source modified: NO.
Coverage identity: USER_RUNTIME baseline anti-regression, R51 semantic ownership, R28 shader-epoch world continuation, R30 HUD/XYZRHW/scissor/state restoration, SkyGlow, refresh/pacing.

- CP10 rows=10 fresh=10 carry=0
- CP20 rows=20 fresh=20 carry=0
- CP30 rows=30 fresh=30 carry=0
- CP40 rows=40 fresh=40 carry=0
- CP50 rows=50 fresh=50 carry=0
- CP60 rows=60 fresh=60 carry=0
- CP70 rows=70 fresh=70 carry=0
- CP80 rows=80 fresh=80 carry=0
- CP90 rows=90 fresh=90 carry=0
- CP100 rows=100 fresh=100 carry=0
- CP110 rows=110 fresh=110 carry=0
- CP120 rows=120 fresh=120 carry=0
- CP130 rows=130 fresh=130 carry=0
- CP140 rows=140 fresh=140 carry=0
- CP150 rows=150 fresh=150 carry=0 COMPLETE

Diversity: cross-subsystem >=25, adversarial >=25, distinct named paths/functions >=30, regression/baseline checks >=30. Existing finding IDs reused; no duplicate regression IDs created.

## USER_RUNTIME_BASELINE REVIEW

Protected USER_RUNTIME_VERIFIED evidence is independent of moving integration HEAD. R51 `17ad376b` remains the continuation baseline for correct road/background/vehicle 3D stereo and improved frame stability, while white HUD/text diplopia and vehicle-rank anchoring remain explicitly open.

Current integration `539fecf` is not a safe behavioral substitute for R51 merely because it is newer. The current `src/vr/game/render_semantics.hpp` lacks R51's `ScreenOverlay2D`, `ScreenHud`, SpriteNode semantic registry and queue fallback ownership. Current `stereo_renderer_r26.cpp` also has the pre-R51 `R28RunWithVerifiedWorldEpoch` behavior that always fails closed on a changed shader epoch instead of restoring R51's strict verified world continuation. These are baseline-regression risks against `VR-R51-WORLD-STEREO-PRESERVE-001`, and they also remove machinery needed to fix `VR-R51-WHITE-HUD-DIPLOPIA-001` and `VR-R51-VEHICLE-RANK-ANCHOR-001` safely.

R51 also carries the explicit generic-HUD common-centre/no-per-eye-scissor-remap rule; current integration lacks that runtime-proven protection. C must not reconstruct a candidate solely from the newer integration tree and silently lose these R51 protections.

## READY_FOR_C

1. `VR-R51-WORLD-STEREO-PRESERVE-001` — BASELINE_REGRESSION_RISK. Bounded cause: current integration dropped the R51 semantic header/queue ownership and strict R28 verified shader-epoch world continuation. Targets: `src/vr/game/render_semantics.hpp`, `src/vr/d3d9/stereo_renderer_r26.cpp`, relevant R30 ownership callers. Deterministic verifier: LEVEL0/1 assert R51 semantic enum+queue registry and R28 strict WVP/projection/pose proof with ScreenOverlay2D/ScreenHud exclusions are present on prospective candidate. Risk: restoring broad ownership incorrectly could regress world geometry; preserve fail-closed unknown draws.

2. `VR-R51-WHITE-HUD-DIPLOPIA-001` — remains OPEN/READY_FOR_C. Exact white HUD producers still need `SCREEN_HUD`; do not widen generic SpriteNode ownership. LEVEL0 semantic-producer verifier plus LEVEL3 Quest3/VDXR truth.

3. `VR-R51-VEHICLE-RANK-ANCHOR-001` — remains OPEN/READY_FOR_C. Exact rank marker must use `WORLD_BILLBOARD`/vehicle anchor semantics, not generic HUD. LEVEL0 producer/semantic verifier plus LEVEL3 runtime truth.

4. Existing `B-SKYGLOW-CONFIG-POLICY-001` remains READY_FOR_C: code default and checked-in INI still resolve `SkyGlowFactor=4`, while canonical CORRECTNESS policy requires `1`. Prefer profile/package-scoped correction unless global policy intentionally changes. LEVEL0 resolved-config verifier.

Protected `TargetRefreshRateHz=0` remains intact. Frame-pacing equivalence on the moving HEAD is not inferred from static/build evidence and remains NEED_HMD_TEST.

## exact nextAction

C: recover R51 USER_RUNTIME baseline before authoring the next candidate; compute BASELINE_DELTA from `17ad376b` and current `539fecf`; preserve verified-good R51 world ownership/scissor/pacing behavior, then implement only bounded white-HUD/rank-marker/SkyGlow fixes. D must independently compare baseline -> prospective tree and current HEAD -> prospective tree before integration/package. Runtime-visible HUD/marker/pacing truth remains NEED_HMD_TEST.