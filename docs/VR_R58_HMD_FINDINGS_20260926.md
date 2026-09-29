# R58 HMD Findings — 2026-09-26

Test source: nightly R57 unified package, merge SHA `593acb199bb1b6f31b94a4a15b7cf61e8bb0e3aa`.

## User-observed HMD results

1. R57_01_POSITION_KIND1_HUD35: HUD still split; no useful improvement.
2. R57_02_POSITION_KIND0_HUD35: HUD still split; no useful improvement.
3. R57_03_POSITION_ALL_WORLD35: ordinary HUD converged to one stationary image; other target defects unchanged.
4. R57_04_RANK_ALL_AS_HUD: 1st-3rd markers became smaller and stopped following the head, but no longer matched the vehicles exactly.
5. R57_05_RANK_PROJECTED_IPD: 1st-3rd markers followed vehicles only when facing forward; head motion introduced drift.
6. R57_06_RANK_PROJECTED_HEAD: 1st-3rd markers followed vehicles correctly, including head motion.
7. R57_07_RANK_PROJECTED_13: same head-follow defect as mode 5.
8. R57_08_RANK_PROJECTED_46: no target improvement.
9. R57_09_RANK_PROJECTED_ZERO: ordinary HUD converged, but 1st-3rd split again.
10. R57_10_RANK_PROJECTED_TRACE: ordinary HUD converged, 1st-3rd split, and vehicle-rank depth was absent as intended by trace-only mode.

## Runtime conclusions

- DirectGPU/D3D9Ex transport was stable in all final sessions; semantic registered/consumed counts balanced and no fence timeout/fallback explains the visual failures.
- Mode 6 proves that the projected vehicle marker reconstruction requires the latched common head inverse in addition to relative-eye IPD/FOV.
- Mode 8 produced no PROJECTED MARKER build telemetry. The 4th+ formula was not the immediate failure; the kind-0 clip SpriteNodes never arrived at final draw with projected-world ownership.
- Mode 2 likewise produced no accepted kind-0 exact HUD path, while kind-1/sprani ownership was observable in modes 1/3.
- Therefore the remaining POSITION and 4th+ vehicle-rank defects share one root cause: nested `put_clip_sprite -> put_sprite_ex` semantic propagation is not presentation-authoritative for these direct producer callsites.

## R58 fix

- Keep the proven mode-6 projected transform for vehicle-attached ranks.
- At each direct `put_clip_sprite` producer wrapper, capture the priority-list tail before the call and explicitly tag the actual appended SpriteNode after the call.
- DispRank clip nodes receive exact `SCREEN_HUD` ownership.
- 4th+ rival-rank clip nodes receive exact `PROJECTED_WORLD_MARKER_2D` plus the captured Calc3D2D view-space anchor.
- Mode 8 now uses the same head-inverse projection formula as mode 6 so it can isolate the corrected 4th+ path.
- Do not hook canonical queue entry RVA 0x2D734; ownership is still consumed at the safe per-node queue boundary.

## Next minimum HMD set

Only three runs are needed:
1. R57_03 on the R58 build — proves direct DispRank kind-0 tagging fixes POSITION.
2. R57_08 on the R58 build — proves isolated 4th+ projected ownership + head inverse.
3. R57_06 on the R58 build — final combined 1st-6th projected vehicle-rank candidate.

Do not repeat the previous 10-case matrix unless one of these three fails.
