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
