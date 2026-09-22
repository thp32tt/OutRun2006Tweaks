# B21 rendering/performance review summary

- integration target: `c4dd697e2b1f33d3b8af6ab254f378a1cc421248`
- review units: 150/150, fresh 150, carry-forward 0
- coverage: SkyGlow/exposure shader path, reflection pacing/resolution, near-plane/SceneEffect restoration, car shadow, Xbox brightness combiner state, culling/LOD draw amplification, transparency supersampling/reset, checked-in graphics config identity
- diversity: cross=30, adversarial=30, perf=30, recovery=30, distinct surfaces=30, outside-delta=145

## READY_FOR_C — SKYGLOW-CONFIG-POLICY
Bounded root-cause hypothesis: production source default and checked-in INI both select `SkyGlowFactor=4`, while the canonical VR CORRECTNESS policy requires `SkyGlowFactor=1`; package/profile behavior can therefore diverge from the intended visual baseline unless packaging overrides it correctly. Evidence: `Settings::SkyGlowFactor` default is 4 and checked-in `OutRun2006Tweaks.ini` is 4. Target: `OutRun2006Tweaks.ini` and, if C finds package override logic, the owning profile/package verifier only. Deterministic verifier: assert CORRECTNESS package/config resolves exact `SkyGlowFactor=1`; assert `TargetRefreshRateHz=0` remains unchanged. TEST_LEVEL=LEVEL0 for config identity; final SkyGlow visual correctness remains NEED_HMD_TEST. Dependency/risk: preserve stock mono SkyGlow suppression while true stereo owns independent eye glow; avoid reintroducing the historical mono-resource lifecycle mismatch.

## EVIDENCE_AUGMENT — VR-REFLECTION-RATE-ACTIVE-GATE-001
Current `ReflectionUpdateRate::FaceCount_dest` still enables elapsed-time normalization on configured VR (`VREnabled && VRNormalizeReflectionRate`) rather than live stereo eligibility. Existing stable finding is reused, not duplicated. C should prefer reconstructing the already-reviewed fix intent on current integration HEAD rather than merging stale candidate history.

## Regression gate
`VR-STARTUP-WHITE-001` remains `INTEGRATED_BUILD_VERIFIED_NEED_HMD_TEST`. This review did not produce Quest3/VDXR evidence and does not close it.

## Next B
If no exact C candidate needs B post-review, rotate away from this SkyGlow/reflection block to under-covered billboard/SBS/diagnostic-overhead or renderer eye-state paths. Do not repeat B21 solely because HEAD is unchanged.