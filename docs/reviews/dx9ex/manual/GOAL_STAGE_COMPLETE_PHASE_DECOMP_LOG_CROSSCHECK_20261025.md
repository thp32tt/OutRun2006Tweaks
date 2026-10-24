# GOAL stage-complete phase: decompiled game, review logs and R26 A/B (2026-10-25 KST)

Scope: manual investigation only, docs only, isolated candidate `vr-d3d9ex-candidate/20261025-b7ca-correctness`. Baseline `b7ca566b0098dba8b7a4746c7950c65a7309006b` MUST remain the source of truth. `vr-d3d9ex-focus` untouched. Runtime fix NOT claimed.

## New user HMD observation (higher authority than earlier reports)
- 2026-10-24 review/test-branch Quest3: **the progress graph looked correct while climbing; only the final/result screen was doubled.**
- Previous evidence text in `docs/evidence/DX9EX_FOUR_LOG_SCREEN_REGRESSION_20261024.md` described animated time as normal but static graph as doubled. Treat the newest user clarification as the test observation. Do NOT conflate progress-fill, static completed rows, final separate time/score and end transition.

## High-confidence decomp source callgraph, independent code
`r4dius/outrun2-decomp/src/platform/race_end_modes.cpp`:
- Original `gad_goal_498670`, EXE RVA `0x98670`, orchestrates GOAL mode 19/22 for variants 0/1/7/8/9.
- It calls `gad_stage_table_4979e0` (RVA `0x979E0`) while frame counter `0x8366E8` animates the bars; the stage-table function returns `frames > end_frames` once the cleared rows finish.
- In that GOAL function, `if (!gad_stage_table_4979e0(c)) { wait(); return; }`; **only after the table returns true**, it calls new `0x429530` title sprite and `gad_time_4973c0`, and for variants 1/9 additionally `gad_score_4974e0` plus `anim_497220`.
- The original exact E8 RVAs `0x9898E/0x98A36` (sprani) and `0x989AD/0x98A10/0x98A89` (time/score print) are **inside the 0x498670 GOAL function**, after the stage-table gate. This is an overlooked provenance mismatch: `src/hooks_uiscaling.cpp` labels them `StageExtensionTime` and documents them as mid-course `+TIME`. They are GOAL post-table summary output, not established evidence of course-change +TIME source. A previously asserted +TIME fix covering these exact parents MUST be reclassified as GOAL-summary classification until original in-race +TIME callers are separately found.
- `text_4b9200` emits glyphs per character. The test branch `test/dx9ex-final-screen-20261024` adds one function-entry inline hook at `0xB9200` with a 19-original-parent exact-return whitelist, but the post-table `0x989xx` parents have a separate `StageExtensionTime` owner. Prior CALL+5 midhooks at `0x97C57/0x97E6D` crashed and must not return.
- Thus it is plausible that animated table is now stable while a distinct GOAL completed-summary group is doubled by phase-inconsistent producer/queue/eye semantics. Exact GPU draw responsible is NOT confirmed.

## Comparison of last tested baseline b7ca vs experimental test branch
- Experimental `hooks_uiscaling.cpp`: B9200 entry hook + direct D3DX pre/post flush for canonical 0x97xxx callers (absent in b7ca).
- Experimental R26-safe stereo renderer: removes exact-result `BuildStageEyePoses` eye-local extra rotation and returns to shared head-inverse + identity eye orientation for the finite HUD (both XYZRHW and shader paths).
- Experimental lens C993 screen family and second 0x570008 removal MUST NOT be imported as a GOAL repair.
- These changes were combined, NOT individually A/B isolated; do not assign observed progress improvement exclusively to either.

## Observed logs and limitations
- Baseline attached 20261024T152651909Z-f66e48fc ZIP: `HUD_GOAL_TIME=NOT_OBSERVED_THIS_SESSION`; no specific result-progress L/R physical receipt. It **does** show `INI read failed` and default fallback.
- Existing GitHub `docs/evidence/DX9EX_FOUR_LOG_SCREEN_REGRESSION_20261024.md` ties user uploaded 225618/225917/230322/230620 ZIPs to a confirmed duplicate `DriverSeatCarSpaceBasis` in shipped INI; these builds ran defaults (not intended INI). ALL crashes in one all-review variant are unrelated to proving GOAL optical path.
- Raw bytes of 20261024 REVIEW_COMBINED/FINAL_DEBUG ZIPs are not available in the current container: only indexed filenames and existing GitHub evidence were accessible. DO NOT claim new raw GPU trace analysis from those archives.
- Stronger GPU counters or a B9200 producer entry log are not evidence of two eye draws and a correct xrEndFrame.

## Focused repair design: no broad promotion
1. Separate GOAL phases via state machine **without changing game time**: `GOAL_PROGRESS` while `4979E0` returns false; `GOAL_SUMMARY_POST_TABLE` on first true and subsequent summary; `GOAL_STATIC_END` if further transition identified. Capture variant `0x780258`, phase `0x836698`, table ticks `0x8366E8`, GOAL state and exact original callsite.
2. Correct original producer identity for the five `0x989xx` calls. They should have a distinct `GoalPostTableTimeScore` owner (or proven exact `ScreenHud` equivalent), **not** misleading `StageExtensionTime` +TIME. Guard the 0x98670 native-call lifetime and preserve animation, use no global all-2D promotion.
3. Correlate each post-table `0x989xx` call with exact appended SpriteNode priority/epoch, direct D3DX Draw/Flush/End, physical FVF/VS/c64 and render scope, 2 eye Draw HRESULT/viewport/projection restoration, and actual XR frame id. Flush only a proven homogeneous owner, not every glyph/texture. Log failure and negative cases.
4. Compare the same source+scene in **2x2** isolated experiments on b7ca: A B9200 function-entry exact-parent only, B finite-result extra-eye-pose rollback only, AB both, unchanged R26 control; additionally a separate phase-labeled post-table producer test. Protect main menu 4:3, rival/rank, culling default 8, HUD scale 0.55, game resolution policy and FPS.
5. Fix duplicate INI key and assert parse success before comparing optics; do not import portrait `UnifiedEyeMenuSource` or disabling `FollowGameResolution` from test branch. Keep TEST/DEBUG packages independent, normal Windows GitHub Actions only and include START_HERE launcher + x86 game/x64 host.
6. First fix should be **GOAL-summary producer ownership and physical draw correlation**. The user did not authorize a global rendering rewrite. HMD `RUNTIME_VALIDATION=UNTESTED`.

Sources:
- https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/race_end_modes.cpp
- https://github.com/thp32tt/OutRun2006Tweaks/blob/test/dx9ex-final-screen-20261024/src/hooks_uiscaling.cpp
- https://github.com/thp32tt/OutRun2006Tweaks/blob/test/dx9ex-final-screen-20261024/docs/evidence/DX9EX_FOUR_LOG_SCREEN_REGRESSION_20261024.md
