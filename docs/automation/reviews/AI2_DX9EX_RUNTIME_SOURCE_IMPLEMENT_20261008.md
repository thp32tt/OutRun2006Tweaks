# AI2 DX9Ex runtime source correction — 2026-10-08

TASK_ID: DX9EX-AI2-P0-SKYGLOW-PREHUD-SNAPSHOT-20261008
Branch: vr-d3d9ex-focus
Status: C2_SOURCE_PATCH_COMMITTED_C3_BUILD_PENDING
RUNTIME_VALIDATION: UNTESTED

## C0 / C1 reviewed
- Research authority: docs/automation/reviews/AI2_DX9EX_RUNTIME_EVIDENCE_DEEP_RESEARCH_20261008.md; AGENTS.md and P0 convergence policy.
- Source-reproduced risk (not a proven headset optical cause): R30CaptureSkyGlowSceneBeforeHud() is called only after several HUD ownership/preparation checks. R30ApplyStereoSkyGlow() copies the *current* backbuffer into the bloom source when R30SkyGlowSceneCaptureEpoch != PresentEpoch. This includes previously drawn +TIME/results/menu/F11 HUD if capture failed or that HUD was delegated to the fallback draw owner.
- The current 00558 source already contains original SceneEffect znear, glyph all-node tags, replay mask deep copy, F11 XYZ owner, R57 clip-W guard. DO NOT reapply those fixes.
- Minimal intended patch: detect the first exact ScreenHud/ScreenOverlay2D draw for a frame **at the four R30 draw dispatch entrypoints before trying any optional stereo owner**; attempt the per-eye pre-HUD scene capture immediately; record an epoch. If no clean capture was made after HUD was seen, skip *only the additive SkyGlow pass* for that frame. Preserve present-time fallback capture if no HUD has been drawn; reset the epoch with device reset. No changes to light position, lens classification, source tick, per-eye projection, or user SkyGlowFactor.
- Validation target: exact changed SHA DX9Ex Active, HUD Inspector, Source Impact, Domain Isolation. Add source-order/negative mutation contract once, no 1000/5000 loops. Hardware remains untested.

## C2 implementation — committed in bounded revisions
- `e65555c57712822cf8953f78b7d76ceb3d5a8ecb`: save pre-HUD SkyGlow scene at four draw-dispatch entrypoints (before R30/R29 decisions), fail closed on missing clean scene rather than blooming text/UI.
- `cf79069b7b7b7e226b440097b55087b1484bdca2`: exact ScreenHud 6th/6, +TIME, checkpoint, goal/result recovers last original *raw* game WVP for age 13..128 and same shader identity/serial; no potentially head-injected live c64 re-use. WorldBillboard/rival paths unchanged.
- `a00cef8aaa26decdbddab1b4531928e2c1050da3`: same bounded original raw WVP proof only for exact original-mod Clr_SceneEffect or EXE+0xCABE projected lens; keep both flat/PerspectiveHud and spatial/WorldBillboard lens paths eligible without generic alpha promotion.
- `tools/verify_vr_visual_composition_p0.py`: 4 independent SkyGlow, 3 HUD raw c64, 3 lens/SceneEffect fault mutations and precise source-order/ownership assertions. Source/test snapshot for exact final CI: `9d01dd3eb871be4a439457247596a60cb5c8f74b`.
- First source verifier code `ada0f75d` caused **one false positive** from searching an unrelated earlier `return false`. Corrected assertion range at `d3a91a13`; second SceneEffect assertion's ambiguous `else` search corrected at `9d01dd3e`.
- Change scope: `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` and `tools/verify_vr_visual_composition_p0.py`. No code changes to original EXE semantics, original near-plane/extension-time timers, textures, host, DX11, DXVK, or Quest runtime.


## C3 CI — exact source SHA `9d01dd3e` (partial proof)
- OutRun EXE HUD Inspector `37766111701` / job `113274066092` static-exe-analysis **SUCCESS**: 71 exact HUD CALLs, deliberate input mutations, new source verifiers; Win32 build job `113274066511` running at C2 checkpoint.
- DX9Ex Active `37766111828` policy job `113274138615` **SUCCESS**; Win32 game, host, R33 chain, package jobs pending/running.
- Full Source Impact `37766111648`: source-cross-domain job `113274065879` **SUCCESS**; Win32/x64 MSVC analyzer jobs running.
- Domain Isolation `37766111726` / job `113274068297` **SUCCESS**.
- No final all-green claim, package digest, or Quest3 acceptance until those jobs complete. `RUNTIME_VALIDATION=UNTESTED`.


## C4/C6 committed handoff — OPEN UNTIL FINAL CI
- User-requested progress checkpoints are additionally recorded in [Issue #14](https://github.com/thp32tt/OutRun2006Tweaks/issues/14) comment `6058245101` and [Issue #13](https://github.com/thp32tt/OutRun2006Tweaks/issues/13) comment `6058245975`.
- Next: determine exact-source all-green/compile failures; if pass, record material SHA, artifact/CI proof and a single targeted Quest3/VDXR session for lens, +TIME, goal, F11, world/rival, shadow, pacing. Do not claim HMD PASS before user test.

