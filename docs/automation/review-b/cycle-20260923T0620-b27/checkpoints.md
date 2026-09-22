# B27 checkpoints
Target integration: `539fecf218d39cea103da6ccc23f59eb7498185f`
USER_RUNTIME baseline: `17ad376bfdf7939f0851c0c629e4fa094a84f28a`
Merge-base: `4ff3a3f98a000e0e19f4ba065066d5f81e9d5417`

CP10 10/150
CP20 20/150
CP30 30/150
CP40 40/150
CP50 50/150
CP60 60/150
CP70 70/150
CP80 80/150
CP90 90/150
CP100 100/150
CP110 110/150
CP120 120/150
CP130 130/150
CP140 140/150
CP150 150/150 COMPLETE

Accounting: fresh=75, carry=75. Fresh categories: cross=15, adversarial=15, path=15, regression=15, performance=15. Distinct reviewed paths=15 with five independent lenses each. Cross/adversarial minimum is met by explicit categories plus cross-boundary objectives embedded in path/regression/performance rows. Existing-finding revalidation <=30. Protected runtime baseline remains authoritative; BUILD_VERIFIED does not supersede it.

Findings/handoff: reuse `VR-R51-WHITE-HUD-DIPLOPIA-001`, `VR-R51-VEHICLE-RANK-ANCHOR-001`, and protected world/frame invariants. Current HEAD lacks R51 ScreenOverlay2D/ScreenHud and SpriteNode semantic registry. READY_FOR_C remains bounded restoration on an isolated candidate with BASELINE_DELTA; preserve SkyGlowFactor=1 and TargetRefreshRateHz=0. Runtime-visible result remains NEED_HMD_TEST.