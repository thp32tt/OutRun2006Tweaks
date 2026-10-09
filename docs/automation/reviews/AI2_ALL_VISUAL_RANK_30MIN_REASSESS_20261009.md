# AI2 — DX9Ex rank/HUD whole-visual reassessment, 2026-10-09 KST

## Authority, scope, status
- GitHub SSOT: `thp32tt/OutRun2006Tweaks` `vr-d3d9ex-focus` baseline `cbec81ef9f35f95d4a20225b892d8733da83394c`. This audit branch is **documentation-only**, not automatically integrated.
- Explicit request: re-examine rank 1–5, 6th/6/HudScale, white text/GOAL/time/+TIME, F11, menu arrows, result, rival, car DDS, flare, scene/shadows, OpenXR output, and historical sources. Prefer user HMD evidence, not CI green.
- **No HMD optical test performed in this session**; RUNTIME_VALIDATION=UNTESTED until exact Quest3/VDXR observation. No 1000/5000 repetitive static audits.
- Preserve 2 original GOAL calls `0xBEA5A→0xBE020`, `0xBEA5F→0xBE150`. Semantic assignment course/time still conjectural. Separate correct mono TRYAGAIN and race-end pre-restart GOAL.
- Active C++ game build is Win32 R26+R30 HUD; x64 host entry is `vrhost/src/main_r23.cpp`; R33 comparison is not active runtime.
- A checkpoint is logged only after concrete source/evidence review, not speculative time passage. Do not assume asynchronous work after conversation.

## C0 — initial source/historical gate (08:56–08:58 KST)
1. **Prior PR #111 does NOT repair rank**. It edits only `src/vr/game/outrun_renderer.cpp::ResetFrameState` and P0 verifier for original shader WVP cache; no rank draw code.
2. **CROSS-PRESENT HYPOTHESIS DISPROVED**. Current base already calls `InvalidateGameWvpWrite()` unconditionally from `NotifyGamePresent()` (renderer ~1846–1851), and active `src/vr/d3d9/stereo_renderer_r7.inc::PresentDest` calls `NotifyGamePresent()` before incrementing `PresentEpoch` (~1572). Existing deep review `docs/automation/reviews/AI2_DX9EX_P0_ALL_SCREEN_REVIEW_20261008_1957KST.md` explicitly reached this conclusion in C2-A. PR #111 is therefore unsupported and may interrupt no-tick HUD; **closed WITHOUT MERGE**, with correction GitHub PR comment 6071399385. Only same-Present WVP/queue association remains a live hypothesis. Earlier affirmative interpretation is superseded.
3. **Historical HMD anchors are category-specific**: R57_06 rank 1–3 car-follow, R62 source `945e4471` rank 4/5 single+attached but 6th/6 then broken, R64 source `10c73daa` 6th/6 single, HudScale and menu text functional but lens/option arrows/final records then broken; later user reports all except transient +TIME once working. No exact single all-pass ZIP SHA attested. See `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md` and `docs/automation/reviews/AI2_DX9EX_HMD_HISTORICAL_REGRESSION_20261009.md`.
4. **Current rank source repairs ALREADY present**: exact `Calc3D2D_dest` at rank return `0xBAEE7` with input/finite fallback and no optional R84 parent-depth prerequisite; `RankMarkerSub_dest` clears state per car; exact 1–3 `sprani` and 4+ `put_clip_sprite` tags **all priority siblings**, preserves frac offsets and projected point; R62 `FVF=0x142` indexed fixed-function source and dispatch restored; R64 D3DXSprite Draw→Flush hook restored only for rank and DispRank. This is code parity, not a user headset PASS.
5. **Last tested bad 6e800 is genuine user FAIL**: logs rank producer CALLs yet `projected[semantic=0,buildAttempts=0]`; analyzer `status=OK` cannot certify rank. Launcher `SOURCE_SHA` alone did not attest loaded game DLL at that time. Protect OutRun rival and vehicle selector DDS that user confirmed working.
6. **PR #111 exact CI distinction**: EXE HUD inspector, Domain, Win32 default Build succeeded, DX9Ex Active policy succeeded; architecture `game-x86` failed preexisting `stereo_renderer_r33.cpp :: R31OwnedResult R33TryFastWorld` guard. Unmerged status is based on disproven root cause, not an assertion that CI failed everywhere.

### C0 links
- Review baseline: https://github.com/thp32tt/OutRun2006Tweaks/tree/vr-d3d9ex-focus
- Closed wrong-attribution PR: https://github.com/thp32tt/OutRun2006Tweaks/pull/111
- Historical good snippets: `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`
- HMD fail source: `docs/automation/reviews/AI2_DX9EX_HMD_HISTORICAL_REGRESSION_20261009.md`

## Remaining steps
- C1: verify source diff across R57/R62/R64 and exact original fork CALL owner; inspect rank math, installed active pipeline and tag liveness.
- C2: follow shader/FVF/XYZRHW per-eye sinks and actual parent/child memory ownership, counters and eligibility.
- C3: inspect F11/menu/GOAL/+TIME/lens/shadow/rival/DDS and no-tick replay vs historical known-good.
- C4: exact CI and package check; document per-category matrix, risk and HMD next-test criteria.


## C1 — 09:01 KST checkpoint: original fork, HMD-tested R57/R62/R64 vs current rank source

- **Original upstream read directly** from authenticated GitHub `emoose/OutRun2006Tweaks:src/hooks_uiscaling.cpp` blob `addd30830e5465491bd79005fc4052b16eb4e611`. Its `Calc3D2D`, `DispRank` eight right-scroll original midhooks, and numeric clip-draw positioning corroborate the fork's address lineage; current eight original E8 replacements implement original right spacing and explicit per-node `ScreenHud`. Adding original midhooks on top of current E8 patches would double-hook.
- **R57_06 HMD (historical document from R62 tree)**: test 1–3 car markers follow car under actual head yaw; R57_03 ordinary HUD single, but other defects. R57_08 4th+ test showed *no projected draw*, not a proven bad projection formula. The current `R57BuildProjectedMarkerDelta` uses head inverse and relative-eye IPD/FOV unconditionally (old R62 had a conditional mode6/8), preserving the tested mode6 intent.
- **R62 complete fixedfn function compared to HMD-tested blob** `31ab2c90ed20943bd563bccb7914c064ca92db7c`: 189 historical lines vs 192 modern; line-level LCS shows only (a) extra read-only `R30TracePreRestartHudDrawForm(device,2u)`, and (b) `VR R62 FIXEDFN KIND0` producer-token log format/argument, **no executable matrix/draw-path differences**. Current dispatch still calls this after isolated external F11 and before generic XYZRHW; exact `FVF=0x142`/null VS/projection restoration verified at source.
- **R64 HMD category** `10c73daa037b5cc521b42ce7fb3a7cc1820b1921`: vtable[9] D3DXSprite `Draw` then vtable[10] `Flush` originally only for projected rank or exact DispRank; current restored class `VRProjectedD3DXSpriteIsolationR64` deliberately requires modern exact queue producer `RankMarkerSprani|RankMarkerClipSprite|DispRankFirst|DispRankClipSprite` and valid marker. Extra `QueueRenderActive()` / token restrictions protect the user-working rival; no HMD observation yet shows they accept each intended Draw. Log `VR R64 D3DX ISOLATE RESTORED` and count are the immediate runtime gate.
- **Important false-positive prevented**: R64 `ConsumeForDraw()` already prioritized `NextDrawScope` ahead of mode2 `CurrentQueueExactScope`; modern source does the same (and modern `EffectiveScope()` prioritizes exact queue). Therefore the one-shot ordering alone is **not a new R64→R84 regression**, although a stale token after a no-draw original source path remains a conditional lifetime hazard. Do not 'fix' ordinal by blindly reversing it without a repro / regression guard.
- Default shipped `OutRun2006Tweaks.ini`: `UIScalingMode=1` and VR `HudScale=0.55`; VR source `UIScaling::validate()` requires `UIScalingMode > 0` for exact rank/hud hooks. **Runtime config must confirm >0**; source default alone does not prove the installed user's setting. Turning scaling off could bypass hooks. No user report currently pins that setting.
- Current evidence: source R62/R64/R57 pathways are restored but latest user fail package `6e800...` predates them; no newly matching Quest3/HMD optical verdict. No production code changed in C1.

### C1 source identities / test entrypoints
- `src/hooks_uiscaling.cpp` full source on current baseline; `src/vr/game/render_semantics.hpp`
- R62 SHA `945e4471d6463f757f38b4b39d3eb8e492b2254f`
- R64 SHA `10c73daa037b5cc521b42ce7fb3a7cc1820b1921`
- `docs/VR_R58_HMD_FINDINGS_20260926.md` from historical R62 tree
- `tools/verify_vr_hud_exact_callsite_contract.py --self-test`, `tools/verify_vr_projected_marker_anchor.py`, `tools/verify_vr_visual_composition_p0.py` are targeted gates; no duplicate execution yet.
