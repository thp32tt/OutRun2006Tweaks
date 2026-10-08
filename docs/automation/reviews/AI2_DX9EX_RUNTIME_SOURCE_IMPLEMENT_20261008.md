# AI2 DX9Ex runtime source correction — 2026-10-08

TASK_ID: DX9EX-AI2-P0-SKYGLOW-PREHUD-SNAPSHOT-20261008
Branch: vr-d3d9ex-focus
Status: C1_CONFIRMED_SOURCE_PATH; work in progress
RUNTIME_VALIDATION: UNTESTED

## C0 / C1 reviewed
- Research authority: docs/automation/reviews/AI2_DX9EX_RUNTIME_EVIDENCE_DEEP_RESEARCH_20261008.md; AGENTS.md and P0 convergence policy.
- Source-reproduced risk (not a proven headset optical cause): R30CaptureSkyGlowSceneBeforeHud() is called only after several HUD ownership/preparation checks. R30ApplyStereoSkyGlow() copies the *current* backbuffer into the bloom source when R30SkyGlowSceneCaptureEpoch != PresentEpoch. This includes previously drawn +TIME/results/menu/F11 HUD if capture failed or that HUD was delegated to the fallback draw owner.
- The current 00558 source already contains original SceneEffect znear, glyph all-node tags, replay mask deep copy, F11 XYZ owner, R57 clip-W guard. DO NOT reapply those fixes.
- Minimal intended patch: detect the first exact ScreenHud/ScreenOverlay2D draw for a frame **at the four R30 draw dispatch entrypoints before trying any optional stereo owner**; attempt the per-eye pre-HUD scene capture immediately; record an epoch. If no clean capture was made after HUD was seen, skip *only the additive SkyGlow pass* for that frame. Preserve present-time fallback capture if no HUD has been drawn; reset the epoch with device reset. No changes to light position, lens classification, source tick, per-eye projection, or user SkyGlowFactor.
- Validation target: exact changed SHA DX9Ex Active, HUD Inspector, Source Impact, Domain Isolation. Add source-order/negative mutation contract once, no 1000/5000 loops. Hardware remains untested.

## C2 implementation
PENDING

## C3 CI
PENDING

## C4/C6 commit + handoff
PENDING
