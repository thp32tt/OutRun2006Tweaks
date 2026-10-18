> **2026-10-19 후속 완료 현황(최신):** 이전 4건 중 2건(Q051 Leader!, Q154 SELECT LICENSE)은 원본 RGBA 좌표 재크롭 후보를 만들고 원본·출력 SHA 및 byte-perfect 픽셀 검증을 완료했습니다. 2건(Q062 HARD, Q201 CONIFEROUS FOREST)은 원본 아트/글자가 붙어 있어 본 C 작업의 직사각형 크롭 범위로는 분리할 수 없어 HOLD입니다. 재크롭 후보 누계는 **44/46**, 재작업 보류 **2/46**입니다. Q051 문장부호는 화면에서 콜론처럼 보여 공식 `Leader!` 번역 표기와의 일치 확인이 남았습니다. 상세 근거: [OUTRUN_C_LAST4_ISOLATION_20261019.md](OUTRUN_C_LAST4_ISOLATION_20261019.md). 44개 TEST_ONLY ZIP과 4개 비교 JPG는 N100 `work/c_salvage_text_roi/c_original_hd_crop_only/qa_review_20261018/`에 있습니다. 원본 108개·기존 242개·255건 마스터·A/B·DDS는 변경하지 않았습니다. 별도 GitOps C 재배포는 필요하지 않습니다.

# OutRun 2006 C GitOps — native HD English crop QA and source-only rework
Date: 2026-10-18 KST. **Do not treat any QA result below as a released Korean DDS.**

## Verified inputs and technical QA
- Native, unsplit source HD PNG: 108 originals across 5 SHA-pinned ZIPs; all 108 source-record scans finished.
- Existing original-native crop files: **242**. All crop SHA256, source SHA256, dimensions and original-region RGBA equality **242/242 PASS**.
- The original 242, 255 historic master, 108 full-source images, active C queue, A/B/C1/C3 state are **untouched**.
- Visual QA on 76 edge-flagged crops, with six N100 contact sheets; 10 legible candidates, 20 plate/underline-review cases, **39 obvious neighboring-art cases and 7 punctuation/truncation risk cases**.
- Thus 46/76 originally needed native rework; text completeness for index 041 is correct (contact sheet displayed only shortened label); corrected in the recorded triage.

## Performed: 42 non-destructive native rework candidates
1. Q057 five platforms x [SPECIAL REQUEST, Target, Technical Bonus]: **15** outputs. Preview `Q057_REWORK_15_CANDIDATES.jpg`.
2. Additional punctuation, stray graphics and UI-neighbor fixes: **12** outputs. Preview `MORE_REWORK_PROTOTYPES.jpg`.
3. More native crop bboxes from original atlas (Ranking, Sector4, FRIEND REQUEST, Rival, Start, Goal, INTERMEDIATE B, SELECT LICENSE, COMPLETE, DRIVE TIME, VS RANK, WIN RATIO, GIANT STATUES, SETUP): **15** outputs. Previews `FINAL_REWORK_PROTOTYPE_01.jpg` and `_02.jpg`.
- **42/42** original SHA and saved output SHA verified; every output copied from the exact native original RGBA bbox, no generated pixels, source modification, rescaling, or alpha redraw.
- Stored on N100 in `qa_review_20261018/reworked_q057_test_only/`, `reworked_12_test_only/`, `reworked_15_followup_test_only/`.
- Every output is **CROP_TEST_ONLY_VISUAL_QA_REQUIRED**, not automatic C1/C3/game PASS.

## Four still unresolved by rectangular native crop alone
- QA #012: **Leader!** (Q051_FF2462BB_BASE_READABLE_FLIPY.png) — Black vertical UI element included.
- QA #036: **HARD** (Q062_33491F83_BASE_READABLE_FLIPY.png) — White/green adjacent plate parts protrude from HARD crop.
- QA #049: **SELECT LICENSE** (Q154_4D38BBB0_BASE_READABLE_FLIPY.png) — Duplicated adjacent SELECT LICENSE text.
- QA #059: **CONIFEROUS FOREST** (Q201_A9ABD877_BASE_READABLE_FLIPY.png) — Coniferous Forest meets adjacent text at right edge.


Those cases need manual glyph isolation or carefully protected sprite/art separation.
Do not release or replace existing PNG/DDS while full visual QA or game proof is absent.

## Artifacts and handoff
N100 base: `/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/qa_review_20261018/`.
- `STAGE_COMPLETE_20261018.json` — deterministic final source/crop counts.
- `triage_for_github_76.csv` — every visual judgment and rework candidate state.
- `rework_remaining_4.json` — remaining highest-risk crops.
- `EDGE_REVIEW_CONTACT_01_of_06.jpg` through `06_of_06.jpg` — original crop/source context comparisons.
- `Q057_REWORK_15_CANDIDATES.jpg`, `MORE_REWORK_PROTOTYPES.jpg`,
  `FINAL_REWORK_PROTOTYPE_01.jpg`, `FINAL_REWORK_PROTOTYPE_02.jpg`.

**Next gate:** Native-size detailed QA for 42 candidates plus 10 text-legible and 20 text/plate candidates; isolate four unresolved title/UI sprites; never assume runtime game pass.