# Q051 F0 DDS no-op + TIME CLEAN static pilot (2026-10-16)

**Status: NOOP_STATIC_PASS, TIME_CLEAN_STATIC_CANDIDATE, F0_OVERALL=HOLD_UNTIL_USER_GAME_BASELINE.**

Basis: Astra v2 `OUTRUN-KR-PLAN-REVIEW-20261016-094508`; asset branch `korean-localization-recovery-20260928`; no A/B/C/C1 restart. No DDS was deployed into the game.

## Native original and verified readable PNG
- DDS key: `FF2462BB`; mapped source `textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds`, *actual* header dimensions **4096x2048** (filename suffix is not literal).
- Local verified N100 original DDS: `/home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012/q051_FF2462BB_GITHUB_HD_SOURCE_20261015.dds`.
- DDS sha256 `5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67`, **33,554,560** bytes.
- Readable full PNG: `q051_FF2462BB_FLIPY_CHECK_ORIENTATION.png`, sha256 `2da1b6f01219356ddc6ea925bd8fcd4afd37d9040eb48081a40861cc649da6f0`.
- The original DDS flip-Y image matches the full 4096x2048 readable PNG byte-for-byte in decoded RGBA pixels: **8,388,608/8,388,608 pixels match**, 0 mismatch.
- Header: `DDS `, size 124 bytes, total header 128, RGB+alpha 32bpp, RGB masks `0x000000ff/0x0000ff00/0x00ff0000`, alpha `0xff000000`, pitch 16384, mipcount 1, no FourCC, DDS length exactly header+pixel payload.

## No-op round trip
- Decode source DDS to native RGBA, re-encode full RGBA payload under its unchanged header (not merely filesystem copy), write isolated `Q051_FF2462BB_F0_NOOP_RGBA32_TEST_ONLY.dds` on N100.
- Source and no-op DDS are **byte identical**; sha256 both `5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67`. Independent persisted DDS re-decode matches native pixels.
- This proves only this source's **uncompressed, one-mip RGBA32 no-op path**, NOT block-compressed DDS/multiple mip support nor actual in-game loading.

## One-phrase CLEAN static candidate: Q051 TIME
- Input readable phrase bbox (half-open XYXY) `[1595,608,1845,727)`; inverted RAW DDS bbox `[1595,1321,1845,1440)`.
- The source `TIME` glyph+effects constitute one contiguous positive-alpha group in this ROI, 12,376 pixels; outside text shape the cropped source already has zero alpha. We remove **only** that exact positive-alpha mask, transparent alpha=0, replacing hidden RGB within allowed pixels with `(0,10,57)`.
- Isolated test DDS `Q051_TIME_ONLY_CLEAN_F0_TEST_ONLY.dds`, SHA256 `7c1a81b1570ffc910d71ea25d05819d93c8ed0a80be7d2c0437fce6b43fbdd43`; original header and byte count preserved.
- Persisted CLEAN DDS re-decode confirms precisely **12,376 modified pixels**, no modifications outside the mask/target rectangle, and `TIME` ROI alpha nonzero count **0**. Nearby text kept in original source (other glyph ROIs not edited).
- Important crop overlap: `Q051-TIME_HUD_2` is explicitly excluded as duplicate; `Q051-YOU` broad reference crop includes the neighboring TIME tail (1,157 selected TIME alpha pixels). Pixel investigation in overlap found 0 opaque white YOU pixels and 0 red arrow pixels. Inspect the attached before/after preview; keep **independent visual QA required** due to overlapping reference rectangles. Source sprite/UV actual bounds and in-game sampling remain untested.
- Source has text pixels on a transparent native layer; this **does not imply other opaque-plate assets can use alpha removal**.

## Artifacts and production boundaries
- Native N100 isolated outputs: `/home/chatgpt-runner2/work/c_salvage_text_roi/F0_Q051_NATIVE_DDS_20261016/`.
- This GitHub experiment directory contains original source analysis scripts, test reports, a **preview**, test CLEAN native PNG and removal mask. Large 32MiB DDS files stay on N100, SHA pinned. They are **TEST_ONLY**, never copied into the game.
- **F0 NOT PASS** until baseline DDS game loading, actual shared-sprite sampling, clean/restore and independent review are recorded. F1 (Korean ONE glyph persisted DDS + real game) is not started. Unicode runtime also not claimed.
- Auto generation/compose/deploy remains off, legacy 986 tiles unused, VR project untouched, C continues native English crop only.

## Suggested next acceptance
1. Independent inspection of `Q051_TIME_CLEAN_SIDE_BY_SIDE_TEST_ONLY.png` and `Q051_TIME_REMOVAL_MASK_TEST_ONLY.png`.
2. Verify original/no-op DDS same visual result in game plus rollback, with actual SHA and screenshot.
3. If CLEAN does not harm shared atlas use, acquire exact generated Hangul TIME PNG and move to independently gated F1.
