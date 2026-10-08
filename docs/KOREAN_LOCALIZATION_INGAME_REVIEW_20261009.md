# User in-game review: 2026-10-09 19 screenshots

- Build: `OutRun2-Korean-USER_REVIEW_NOT_APPROVED-cc8f9dd6ba7163b12451f192e80d7f417aa8548a.zip`
- Exact source commit: `cc8f9dd6ba7163b12451f192e80d7f417aa8548a`.
- Source evidence: user's **19 game screenshots** submitted in ChatGPT conversation, filenames below; marked rectangles locate review areas, they are **NOT automatically game-rendered black boxes**. No unmarked originals were supplied in this review. The user's narrative also independently reports genuine plate/box residues.
- State: **all 19 screenshots are new real-game FAIL reports**; no retest/closure is implied. A displayed C3 row is historical, not final approval. Actual new in-game accepted assets: 0 from this report.
- Reopening rule: `EXACT` source-family mappings -> active queue REWORK; `SUSPECTED`/`RUNTIME` remain active mapping work, and already REWORK assets keep status rather than incrementing counters.

| Screenshot | Screen and observed problem | Mapping | Primary q | Owner | P |
|---|---|---|---:|:---:|:---:|
| 스크린샷(173)(1).png | OPTIONS header top clipping/low-res/incorrect original title style; small menu remains English | EXACT from prior IGR-023 main title; English menu may be separate runtime/stock | 205 | B | P0 |
| 스크린샷(174)(1).png | RANKING header low-res/right-italic and family mismatch | EXACT from prior IGR-022 | 205 | B | P0 |
| 스크린샷(177)(1).png | SINGLE PLAYER mode/header hierarchy failure, large English mixed with small Hangul subtitle | EXACT shared main-title atlas; mixed runtime/source text remains to map | 205 | B | P1 |
| 스크린샷(179).png | OutRun subtitle underfills source/title and scene fonts inconsistent; upper header reused | SUSPECTED common mode-intro family, verify q212 cell and runtime | 212 | B | P1 |
| 스크린샷(181)(1).png | CAR SELECT title partly clipped/overlapped, small info ghost/box intrusion indicated | EXACT title from IGR-018; unmarked small cells need own source map | 121 | A | P0 |
| 스크린샷(182)(1).png | Same car selection info overlay has English underlay/poor small-glyph placement | EXACT common title atlas q121; info cells MIXED mapping open | 121 | A | P0 |
| 스크린샷(183)(1).png | SINGLE PLAYER metallic native title family visibly inconsistent with small Korean | EXACT established chrome family q175, already REWORK | 175 | A | P1 |
| 스크린샷(184)(1).png | SHOWROOM main small labels/selection English-Korean typography inconsistent | EXACT established showroom/menu family q193 | 193 | A | P1 |
| 스크린샷(186)(1).png | 328 GTS car detail tiny cyan Korean label illegible/box trace suspected | SUSPECTED showroom metadata q227, already REWORK | 227 | A | P1 |
| 스크린샷(187)(1).png | F40 class title `프로` low-resolution and visually out of hierarchy | EXACT keyword-linked existing q227 producer family, already REWORK | 227 | A | P1 |
| 스크린샷(188)(1).png | 365 GTS/4 small `아웃런` label does not match native size/color source family | SUSPECTED q227; confirm row mapping before new image bytes | 227 | A | P1 |
| 스크린샷(189)(1).png | GOAL select tiny upper label, contaminated/misaligned small row, English mixed | EXACT IGR-004 goal selection family q201; q219 chrome header separately already REWORK | 201 | B | P1 |
| 스크린샷(190)(1).png | COAST 2 COAST large header style/spacing/slant/size mismatch | EXACT prior IGR-013 q228 top title; stage labels may belong q173 | 228 | B | P1 |
| 스크린샷(191)(1).png | CLARISSA/name panel unlocalized big title, rank/help texture degradation, portrait row opaque silhouettes appear ambiguous | SUSPECTED q57 shared rank/text atlas; inspect which lock silhouettes are intentional BEFORE altering | 57 | A | P1 |
| 스크린샷(192)(1).png | Car select header style, Dino protected model mark appears mirrored; only title map exact | EXACT title q121; protected logo source DDS mapping remains unresolved, do not edit vehicle logo blindly | 121 | A | P0 |
| 스크린샷(193)(1).png | Transmission selector tiny text/box and rough Korean overlay on actual composed modal | EXACT previous IGR-005 q137 | 137 | B | P0 |
| 스크린샷(197)(1).png | HUD `총 시간`/`시간`/`하트` low-res, letter-edge/heart-neighbor box-trace reported, dynamic glyph readability | UNINDEXED RUNTIME_TEXT vs separate HUD DDS mapping; do NOT blindly edit q60 or font atlas | — | B | P0 |
| 스크린샷(202)(1).png | STAGE 2 overlay collides, rank label duplicates/blocks original geometry; damaged central rank visual | SUSPECTED rank popup q49 + separate unindexed runtime stage label; split ownership | 49 | A | P0 |
| 스크린샷(203)(1).png | OUTRUN MILES red in-game banner slant/letter residue/plate edge/overlay mismatch | EXACT previous IGR-010/012 OUTRUN MILES q60; q63 only if independent mapping proves badge glyph | 60 | B | P0 |

## Remediation rules immediately actionable

1. Keep every report `OPEN_USER_INGAME_FAIL`; link each screenshot to its own row `IGR-026`–`IGR-044`.
2. New exact primary graphics reopened: **q49, q60, q121, q137, q193, q201, q205, q228**; q212 is also reopened provisionally for a user-visible mode-intro family with explicit mapping check. Previously failed **q175/q227/q219** remain REWORK, do not produce duplicates. q57 remains mapping-first, not blindly reopened. Do not modify preserved songs, Ferrari/model/logo source art or unrelated DDS.
3. The real **HUD / stage-2 / overlapping UI** may be rendered via runtime hooks or baked DDS or both. Inspect `src/hooks_localization.cpp`, `localization/text/runtime_ko.tsv` and exact HUD/rank sprite mappings before selecting the source domain. A runtime fix needs Windows Win32 Release and a fresh user gameplay retest.
4. Producer A/B: native English SHA -> per-segment masked CLEAN-only QA -> source-family typography/lean anchors -> transparent glyph-only composite -> CLEAN/FINAL contamination check -> persisted DDS native/RAW/mips/75/50 -> actual-composited game crop. ANY confirmed visual failure is HARD FAIL independent of bbox PASS.
5. C1/C2 first-look calibrate representative bad slant, clipping, residue, boxes, too-thick/small glyph; independent region evidence, source-vs-CLEAN and CLEAN-vs-FINAL and native presentation. Stage-2 and title overlap is zero tolerance; new REWORK bytes require separate C3 and user retest.
6. **Preview builds must exclude active real-game failures** (even if older queue claims C3). Excluded file receipt should be `USER_REVIEW_EXCLUDED_INGAME.csv`. Keep untouched old DDS and original source for comparison, no false QA PASS, no automatic closure.

Work order: P0 HUD/heart/stage-2 and top clipped title -> P0 transmission/car title -> P1 showroom/car label and secondary controls -> source-family C3 retest. Priority is user-visible impact, not guessed number of DDS.
