# Quest 3 lens / +TIME / checkpoint / goal deep audit — durable handoff (2026-10-08 KST)

## User request
Deep review of **all available** original emoose hooks, fork historical sources, disassembly/pinned EXE evidence, live renderer and every reported lens flare / +TIME / goal/result regressions. Implement real fixes today where source-proven; persist GitHub checkpoints during execution so the work survives chat timeouts. No repetitive HUD 1000/5000 source checks.

## C0 recovery at 2026-10-08 17:19 KST
- Production branch `vr-d3d9ex-focus`; recovered HEAD `03fb00c687434e7947bffbfbb33055fe14b95cee`.
- **Already landed before this turn**: deep lens/+TIME/goal exact-owner source repair material `5011d1e7ca53d73b2cffc7e841dc39e5a57aa6c1`, original-mod/EXE deep report `docs/automation/reviews/AI2_QUEST3_LENS_TIME_GOAL_SOURCE_REPAIR_20261008.md`. Prior exact-material workflows: DX9Ex Active `37745084656` SUCCESS; HUD Inspector `37745084596` SUCCESS; Domain Isolation `37745084546` SUCCESS; Full Source Impact `37745084597` SUCCESS; package `11535334283`, digest `sha256:a78b81a36332b0300e1f6bb7208c39529a7c1cdb052f1e5835d832cedf5d1169`. **Never double count or reimplement these changes.**
- Concurrent/newer branch work after that material: `0f349f4b6b62` nested SceneEffect near-plane fix, `a869acfca72b` pinned out-of-window 0xCABE lens and in-window 0xCF4E Calc3D2D disassembly CALL target correction, `611755d6ee7b` bounded deep-copy of Sumo `SPRARGS2::child_B4` mask replay chain, `3ae95aaf2492` preserve legacy semantic layout verification around new Sumo mask change. At recovered HEAD CI outcome for this newest chain **not yet verified**; do not claim success.
- Original visual HMD evidence `CONVERSION-DX9EX-00519` source `9a3e08cc62b6a36a8196936eacead8cc08fcc756`: lens/+TIME/goal/rank/menu etc doubled or head-following, textures missing. **RUNTIME_VALIDATION=UNTESTED** for all newer builds; source-build success never closes HMD failure.
- Current priority: assess the unclosed issue **lens 0xCF4E projected-anchor per-light lifetime and original `Clr_SceneEffect` camera override ownership**, plus time/goal glyph `TextGlyph_putSprite` and underlying Sumo zero-tick replay, c64 shader-order and fixed XYZRHW. Preserve known original x86 CALL targets, avoid generic alpha/FVF heuristics, avoid new forced stereo transformations without exact ownership.

## C1 source-evidence plan (resume cursor)
1. Read `AGENTS.md`, `docs/VR_P0_VISUAL_COMPOSITION_CONVERGENCE.md`, `docs/VR_PROBLEM_HISTORY.md`, `docs/VR_BINARY_CONTRACT.json`, original emoose `src/hooks_graphics.cpp` and `src/hooks_uiscaling.cpp`, canonical `tools/analyze_outrun_exe.py` and exact HUD Inspector disassembly.
2. Review actual active `src/hooks_graphics.cpp::VRLensFlareProjected2D, Clr_SceneEffect_dest`, `src/hooks_uiscaling.cpp::TextGlyph_putSprite`, `src/hooks_framerate.cpp::SumoUISpriteReplay` and `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30ClassifyScreenSpacePass, R30ConfigureXyzrhwWorldEffect, R30TryScreenSpaceFovDraw`; trace per-node scopes, c64 provenance, mono stereo fallback.
3. Inspect most recent 00557/00558 change's CI and logs **before editing**; other workers may be changing the same files. Prefer independent source-deterministic fault finding over colliding with a pending rewrite. Re-fetch current HEAD before each write.
4. Commit distinct new source fix only if binary + original hook + current ownership jointly prove it; attach a specific regression guard and exact material SHA GitHub Actions outcome. Update this file after each material result.

## Current truth
This is an initial **GitHub-persisted recovery checkpoint**, not a claim that all visual symptoms have passed. See previous exact-material `5011d1...` report for already-completed implementation; do not repeat completed work.
