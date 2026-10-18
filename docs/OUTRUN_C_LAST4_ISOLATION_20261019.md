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