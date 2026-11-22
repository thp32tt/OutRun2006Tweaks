# OutRun 2006 HD — GPT 104-DD​​S one-by-one visual atlas QA
Date: **2026-11-23 KST**

## Input and method
- Source: GitHub Actions successful coverage-first HD build [44977233106](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/44977233106), artifact `14737602774`, 104 native-orientation DDS and 954 registered ROI.
- Actual full build artifact downloaded and parsed as 104 uncompressed RGBA DDS. Each atlas decoded with its authoritative orientation (all shown native readable-side, respecting FLIPY) and inspected **individually** using GPT visual reading at the full atlas preview level.
- 104 unique full-atlas JPG evidence files and **212 additional ROI-crop sheets** were generated for focused evidence. ROI pages were sampled, not independently approved for all 954 source ROI.
- Individual DDS results saved to `qa_status.csv` and a Korean full 104-row table in `qa_report.md` in the ChatGPT conversation output bundle `OutRun2006_HD_GPT_Visual_QA_104DDS_20261123.zip` (sha256 `c753af5fe33afcff0d9ad98e425456338602fe7232bffe1216f514a3aeb6f236`). The bundle was created locally, not deployed to a public repository.

## Confirmed aggregate results (atlas-level, NOT gameplay approval)

| Model vision screening | DDS files | Sum of ROI belonging to these DDS |
|---|---:|---:|
| VISUAL_FAIL / corrective work required | **49** | **620** |
| VISUAL_REVIEW / zoom, original comparison | **36** | **296** |
| VISUAL_PASS_PROVISIONAL / no evident major issue | **19** | **38** |
| **Total** | **104** | **954** |

Defects (nonexclusive, counted **per DDS**): source-English remnants **53**, Korean/English and/or Korean/Korean overlaps **33**, protected-art intrusion/block evidence **31**, low-contrast text **16**, edge clipping **11**, duplicate text **3**, demonstrable translation mapping mismatches **2**.

The counts of ROIs in these classes **are not 620 independently failed individual phrases**. They indicate membership in atlases that had at least one issue.

## High-priority model-visible evidence
- `FA7BBB13_1024x512.dds` (Keyboard, PlayStation, Switch, Xbox, general sprite) retains English mission cues such as `Keep control!` / `Run through green!`, interleaved Korean, and oversized overlays. Clear rework.
- `4D38BBB0_1024x256.dds`: `SINGLE PLAYER` and `CREATE NEW LICENSE` original red words and oversized Korean `라이선스 선택` / `새 라이선스 만들기` visibly overlap and obscure vehicle art.
- `9CE4E175_256x32.dds`: one `NOT AVAILABLE` region shows both small and large `사용할 수 없음`, a distinct double-render/relocation problem.
- `EBFC709F_512x256.dds`: `CREATE GAME` remains in English with a large `게임 참가` beneath; create/join text mapping must be checked against the original ROI semantics.
- `FF514CEB_512x512.dds`: `QUICK GAME` red English remains beneath Korean `게임 만들기`; the separate `빠른 게임` wording makes the mapping problematic.
- `9F060EC1_512x512.dds`: Korean licensing/ranking labels on solid background patches cover the original white license-card UI.
- `75C3586A_512x512.dds` contains readable Korean character names but proximity to illustration does not by itself prove runtime collision; only source ownership/diff can verify.
- Low-risk 104/104 screen: clear text assets include indices 019, 035, 037, 044, 045, 049, 050, 053, 055, 059, 060, 070, 077, 079, 085, 089, 091, 092, 104.

## Interpretation limits
A DDS atlas is a sheet of separate UV sprite elements; two adjacent text sprites in the 2D atlas may never overlap during game execution. Label collisions which are only atlas adjacency are classified REVIEW rather than certain gameplay collisions. However persistent English letters and unmasked solid background patches within a source ROI are visually real concerns.

**DO NOT infer C1/C3 PASS, game runtime approval, final gameplay usability, source-art restoration QA, or independently per-ROI 954/954 approval from the prior mechanically completed 104-DDS build.** The present evidence is ChatGPT GPT visual screening, not third-party OCR, in-game testing, or a formal individual 954-ROI C1 pass.

## Recommended next order
1. Build a **diff of original DDS and all 49 failing DDS**, constrained to the registered source ROI, so protected art and existing English letter remnants can be distinguished.
2. Fix mapping and duplicate IDs first (e.g. `9CE4E175`, `EBFC709F`, `FF514CEB`), then safely clean English original ink and place resized Korean **without a solid rectangle**.
3. Cluster common sprites with near-duplicate platform variants and repair each source-family only once where possible, then port changes to variants via SHA-verified geometry.
4. Re-run model visual QA only on changed atlas+ROI pages, compare before/after, retain individual SHA, and require representative actual game screenshots before announcing release.

**QA action:** production branch is **untouched** by this visual screening; this file documents the screening. Existing strict quality pipeline and browser polling schedule were not changed.
