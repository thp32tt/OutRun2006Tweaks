> **2026-10-19 최신 후속 작업:** 당시 보류했던 2개(Q062 HARD, Q201 CONIFEROUS FOREST)는 **원본 PNG 네이티브 픽셀 Q201 1건**과 **검증된 상위 PSD 독립 레이어 Q062 1건**의 서로 다른 방식으로 검토용 후보를 생성했습니다. 재크롭 후보 46/46건 확보(이 중 45건 원본 픽셀 일치, 1건 PSD 레이어 기반으로 평탄화 원본과 픽셀 차이 존재). **새 전체 결과 및 범위 제한은 [OUTRUN_C_NATIVE_ENGLISH_46_FINAL_20261019.md](OUTRUN_C_NATIVE_ENGLISH_46_FINAL_20261019.md)를 우선 적용**합니다. C 결과는 여전히 TEST_ONLY, 실게임 검증 및 최종 승인 미실시. 기존 A/B·DDS·255건 마스터 미변경.

# OutRun 2006 native-HD source English crop: last four, 2026-10-19

## Scope
Existing GitOps C slot: `thp32tt/OutRun2006Tweaks` branch
`localization-controller-recovery-20260928`, service `outrun-c-english-native-crop`.

Input is SHA-pinned, original, unsplit N100 full HD PNG. This handoff runs
**no OCR redo, no ImageGen, no PSD import/compositing, no DDS write** and makes
no C1/C3 or game success claim. The active GitOps C container needs no redeploy
for these **separately generated QA artifacts**.

## Final four outcomes
| QA index | Original phrase | Resolution |
|:---|:---|:---|
| 012 | Leader! (official transcription) | Re-cropped native pixels at [3145,870,3604,977]. Adjacent left-side black UI rule excluded; original glyph and punctuation preserved. **Visual punctuation resembles colon rather than official exclamation; semantic approval pending.** |
| 049 | SELECT LICENSE | Re-cropped at [1955,548,3520,674]. Previous top duplicated text and lower UI bar excluded. |
| 036 | HARD | **HOLD.** Original word outline shares the white/green plate edge. A tighter rectangle removes glyph/outline pixels; cannot crop away backing art while preserving all original text pixels. |
| 059 | CONIFEROUS FOREST | **HOLD.** Neighboring STAGES sprite abuts the final T; moving the right edge cuts the glyph. |

The two new test-only native crops were verified against the original atlas
SHA256 and original region RGBA byte-for-byte. Their N100 location:
`qa_review_20261018/reworked_last4_20261019_test_only/`.

All four old and alternative preview images:
`LAST4_VISUAL_PROTOTYPE_012.jpg`,
`LAST4_VISUAL_PROTOTYPE_036.jpg`,
`LAST4_VISUAL_PROTOTYPE_049.jpg`,
`LAST4_VISUAL_PROTOTYPE_059.jpg`.

Two remaining HOLD items: `REWORK_REMAINING_2_20261019.json`.
All metadata: `LAST4_20261019_SUMMARY.json` and `FINAL_LAST4_20261019_QA.json`.

## Downstream safe next actions
- HARD: upstream `Sonic-TV/OR2006Sprites` PSD index reports
  `OutRun2SP Mode UI/spr_sprani_loading_cvt_Exst/33491F83_512x256.psd`,
  revision `3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6`; index states PSD
  is **not copied into the branch**. Examine original separate editable
  layers only with a new approved workflow. It is not part of these C outputs.
- CONIFEROUS FOREST: distinct Q147 original atlas also has a recorded
  phrase, but **font/style/assets are different**, so its crop is not a
  pixel-faithful substitute for Q201. Original layer separation is needed.
- Neither HOLD item may be auto-approved or have its source pixels/mask
  silently edited.

## Verified cumulative state
- Original full HD PNGs: **108/108**.
- Existing original C pixel crops: **242/242**, untouched.
- Rework test-only native crops: **44/44** manifest+SHA-checked, including
  two from this pass.
- Historic `MASTER_255` crop archive: **255 items**, untouched.
- Need separate visual/semantic review before Korean generation or
  game acceptance. A/B, controller scheduling, DDS and game files untouched.