# DX9Ex VR second deep visual review — 2026-10-09

Session start: **10:37 KST**. User requested one more hour of active review, not unattended/background work. Commit factual checkpoints when actually achieved, roughly every 5 minutes, and do not invent elapsed periods.

## Constraints
- GitHub source authority: thp32tt/OutRun2006Tweaks vr-d3d9ex-focus starting at ccf636ac68af4d473849a1b2a655748c002d88e4. Last DX9Ex game/material compile SHA 308bf647211f670974fb53ad7d60d398dea4667c.
- Prior C0–C6: docs/automation/reviews/AI2_ALL_VISUAL_RANK_30MIN_REASSESS_20261009.md. Original GOAL calls 0xBEA5A→0xBE020 and 0xBEA5F→0xBE150 both necessary, 4th+ rank sprites are intentional digits/suffix/marker.
- Preserve historically user HMD-working OutRun rival, car-selector DDS, R50 world/car stereo, mono TRYAGAIN, recenter, input. No blanket HUD/alpha promotion, no generic lens flattening.
- Static CI and Windows compile are not HMD optical PASS. Latest exact game SHA RUNTIME_VALIDATION=UNTESTED. No HUD 1000/5000 mechanical loops.

## C0 — 10:38–10:40 KST: source and renderer baseline
- Authenticated GitHub focus source HEAD ccf636ac (unchanged from 09:25 report). Last game/host/packaging material 308bf was validated in DX9Ex Active run 37859508332, inspector 37859508345, Domain 37859508246. No new Quest3 visual report has been supplied here.
- Live src/vr/game/render_semantics.hpp: SelectSpriteQueueNode at canonical 0x2D762 lazily opens queue, resets old marker, reads exact producer/scope tags into thread-local CurrentQueueProducer. EndSpriteQueueRender cleans only tags whose serial <= queue-start cutoff; 0x2D734 direct entry hook is prohibited because two crashes were observed.
- Active DrawIndexedPrimitiveDestR30 calls external F11 indexed ImGui -> exact fixed-function R62 D3DXSprite FVF0x142 -> XYZRHW indexed fallback -> shader guard. Original rank producer/tag alone cannot prove which GPU route accepted.
- **NEW SOURCE-PROVEN DIAGNOSTIC LIMITATION**: R62TryFixedFunctionSpriteIndexed increments 'VR R62 FIXEDFN KIND0 hits' after R30ExecuteXyzrhwStereo even if the right-eye draw failed. The shared stereo function returns leftHr and records FrameRightDrawFailed on right-eye failure. Hence R62 hits means attempts / owner reached, NOT two-eye acceptance. Prior review wording implying accepted binocular output from hits alone must be corrected.
- R30TracePreRestartHudDrawForm fires as a first-per-state/producer/candidate branch trace for shader/XYZRHW/FVF142, not at definitive successful L/R Present. R30TracePreRestartHudEligibility similarly logs before full eligibility resolution. Do not call these optical verdicts.

## Pending
1. Prove exact right-eye successful draw and restore vs attempted R62 for rank and GOAL.
2. Compare original per-node queue/parent tags, batch Flush timing and shader raw c64 epoch.
3. Reconcile old user HMD counters and latest compiled source without extrapolation.
4. Consider narrow telemetry/guard material only after proving source deficiency, with one targeted negative test and Windows gates.

## C1 — 10:43 KST: independently traced render outcomes
- Source src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30ExecuteXyzrhwStereo draws L then R with a temporary right-eye RT/depth switch. If right draw fails it sets FrameRightDrawFailed, R9Poison and safe fallback but **returns the left-eye HRESULT**. Likewise, R30/F11 and generic XYZRHW counts increment after the right attempt, not a guarantee of a committed two-eye picture.
- R62TryFixedFunctionSpriteIndexed increments projectedDraws/hudDraws and logs hits unconditionally after that helper, even if right failed or the original D3D projection restore failed. Thus the existing apparently positive HUD/4–5 count is a false-positive success indicator. The frame is correctly failclosed for host, but the log is ambiguous.
- src/hooks_uiscaling.cpp::VRProjectedD3DXSpriteIsolationR64 increments Flushes after vtable[10] regardless of HRESULT and only logs at count powers of two. It tracks Failures but does not emit per-producer first-success or first-failure. A 6th/6 glyph batch can thus be present but absent from the logs; a counted flush might be failed.
- Validated src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp has existing c64 source/draw fingerprints, so adding another generic c64 logger would be duplication. Focus review material only on proven outcome telemetry gaps R62/R64, without changing sprite ownership or matrices.
- Source code candidate branch vr-d3d9ex-candidate/AI2-R62-R64-EYE-ACCEPTANCE-20261009 created at current focus. Only a code+negative verifier commit and exact Win32 CI should make any new candidate eligible. No Quest3 optical claim.

## C2 — 10:48 KST: bounded source instrumentation implemented, first CI failure corrected
- New candidate **2b774facfbd272de4561ca01f6a569a650d022a7**, draft PR #112: changed only src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp (R62), src/hooks_uiscaling.cpp (R64), tools/verify_vr_visual_composition_p0.py. No matrices, Draw, Flush invocation, GOAL helpers, callsite maps or ownership changed; output pixels should be identical. Log only count/outcome, RUNTIME_VALIDATION=UNTESTED.
- R62 real binocular success requires SUCCEEDED(leftHr), original projection restored, !FrameRightDrawFailed, !FrameStereoIncomplete. Existing hits retained as **attempts**, with separate accepted/rejected counters by projected vs ScreenHud owner and first-per-producer success/failure logs. Note FrameRightDrawFailed is a frame-level signal, not proof of individual isolated rank if prior frame damage already occurred.
- R64 logs and atomics separate attempted Flush from SUCCEEDED(vtable[10]) and emit first success/failure for exact RankMarkerSprani/ClipSprite and DispRankFirst/ClipSprite. Does not widen Draw→Flush to menu/GOAL/rival or change optical content.
- Added **three distinct** destructive test mutations: remove right-eye rejection, remove projection restoration criterion, treat failed Flush as success. No unchanged 1000/5000 loop.
- GitHub PR #112 https://github.com/thp32tt/OutRun2006Tweaks/pull/112 triggers actual Windows CI. Initial DX9Ex Active 37871341630 policy **FAILED** on an **obsolete verifier exact-string** expectation for old `VR R62 FIXEDFN KIND0 ... hits={}`; not a compiler or GPU failure. Corrected that expected signature (preserving checks of original token and new stereoAccepted fields) in test-only commit **5f09e0816efa94450d2c648fe961f984a245866b**. New exact-SHA CI launched runs Active 37871437259, Inspector 37871437277, Domain 37871437479, Build 37871437400 and architecture 37871437555. Status at this checkpoint in progress, DO NOT mark PASS.
- The original independent decomp source calls 0xBE020 banners and 0xBE150 per-sector split rows; this verifies different producer purposes at source level, without proving exact user GOAL clock pixel identity. Preserve both and current mono TRYAGAIN.
