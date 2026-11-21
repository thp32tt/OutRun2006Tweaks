# OutRun 2006 HD Korean localization — HOLD recovery execution plan
Date: 2026-11-21 KST. Scope: 954 HD DDS-origin ROI, A/B existing ImageGen PNG, GitHub-hosted CPU processing. No general font rendering, no paid image API, no VR/FFB modifications.

## Verified starting evidence (not a release)
- Native atlas GitHub run: https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/44767911427 ; asset commit `b158c51d94adc58a1167205e5925bae535931c10`.
- Exact native source: `qa_report.json.zip_sha256=2a0bab7d3046ce482314f775fa448b14fe4fa483b1a4e5e3ffd4c9976f0167dc`.
- 954 ROI: 343 TEST_ONLY painted; 611 HOLD; 74 native test DDS; 0 accepted C1/C3 release approvals.
- Current strict HOLD breakdown: ROI_OVERLAP_NEEDS_MANUAL_QA 402; QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT 75; QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE 49; COARSE_ROI_CONTAINS_OTHER_TEXT_HOLD 36; all other reasons total 49.
- 402 overlap HOLDs span 73 native overlap clusters; latest evidence says 252 source-ambiguous and 126 partial-owner diagnostic rows, 0 full-owner C1-ready candidates. Source-protected pixel edits total 57 (45 cleaned previews + 12 protected-collision HOLDS); those edits are **not** integrated into strict approved DDS.
- Historical fallback queue referenced source `13c30301198c4588b5bc07a4c7194dcad42c94c8c9b453f42c501e9963ff16e2` and 640 HOLD, while all its 8 unclaimed ROIs are now geometry overlap on the current source. Never regenerate fonts for geometry-only HOLDS or fake pass counts.

## Implemented now
1. Audit always uses latest successful `outrun-ab-multi-atlas.yml` run, QA/masks/auto-edits from the **same** artifact and SHA; dynamic source HOLD/overlap counts, never frozen 640/450. Code commit `b336f84e`, tests `9c6d8bd8`, master workflow `05aa1738`. Independent CI 44902489066 SUCCESS, 9 tests PASS, current 611/402 audited. This produces diagnosis, not native DDS release approval.
2. ImageGen fallback now compares stale unclaimed task ROI IDs and reasons against latest strict report. If **any** old task remains genuinely ImageGen-eligible, hold prior queue; if **all** are no longer eligible, retain immutable historical refs/task IDs, mark all superseded with exact new reasons and update active queue to the latest SHA. Source `88937d70`, regression tests `2162a55d`, workflow trigger `ab7423fb`. Existing browser dispatch interval and N100 Docker memory limits unchanged.
3. GitHub Action logs, not green checkmarks alone, establish actual work completion: `source SHA`, `painted`, `HOLD reason deltas`, `new queue`, `C1/C3`, `runtime validation`.

## Next repair rounds (in measurable priority order)
1. **Overlap 402 / 73 clusters.** Partition by native DDS SHA, geometry and real alpha connected components. In each cluster, split only exact *source-owned original glyph* pixels from protected sprites/foreign text; where source ownership remains ambiguous, use a group-level CLEAN + group-level composite test **only if every original text pixel in the group is accounted for and all foreign alpha remains byte-identical**. If not provable, keep HOLD and attach one contact-sheet preview + precise ambiguous coordinates. Never use mere rectangular ROI intersection to infer ownership. Evaluate batches of 4–8 clusters and record per-reason strict HOLD delta.
2. **Opaque/non-isolated 75.** Separate text and protected art by original alpha/pixel signatures; require `protected-pixel delta=0` on source, CLEAN and final native DDS. Unisolatable art stays HOLD for independent C1.
3. **Edge 49 and coarse 36.** Reuse bounded native-source component expansion only when another ROI is not entered; for coarse parents containing multiple labels, prefer verified disjoint children; count the parent as a genuine HOLD unless the full English label has a proven removal mask. No cropping or non-native upscaling.
4. **Remaining 49 (including BC3 4-mip, line-count and color loss).** Route by exact reasons: preserve original BC3 mip chain and protected DDS blocks; reuse original-size A/B glyph pixels for line reflow; only isolated unresolved **glyph-shape** problems enter free browser ImageGen. Hard-stop on missing source SHA, game pixel/art collisions, incorrect line count or corrupted DDS.
5. **C1/C3/game acceptance.** Queue newly verified cleaned DDS and reference/evidence pairs in batches of 4–8 for independent visual C1, then native C3 and user-game tests. Keep `release_approved=false`, `runtime_validation=UNTESTED` unless specifically evidenced. No automatic final release.

## Execution gates and measurement
- Always report `954 = painted_test_only + HOLD`, per-reason counts, source native run ID/SHA, imported SHA-pinned PNGs, C1/C3 passes, generated DDS and exact new native SHA.
- A repeat GitHub Action success with no decrease in native HOLD, no new SHA-approved C1 candidate or repaired backend defect is **not** another progress achievement.
- Keep free ChatGPT browser schedule unchanged; monitoring or recovery may refresh or reopen an unresponsive tab, not increase polling frequency.
- No N100-intensive rebuild; use hosted GitHub Ubuntu Actions for full DDS and QA; N100 only for lightweight operational checks or existing Docker browser transport.
- TARGET for next iteration: at least one actual **strict native** HOLD-to-TEST_ONLY transition without protected-art difference, verified in a new exact-SHA native run. Do **not** report hypothetical 402/75/49 progress as implemented.
