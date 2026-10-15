# Q051 five-label ImageGen batch sheet — manual pilot (2026-10-16)

**Status: STATIC SHEET PASS / IMAGEGEN EXPERIMENT FAIL FOR EDIT/ALPHA / TEST_ONLY.**

- New isolated GitHub branch: `experiment/q051-hud-five-label-sheet-20261016`; asset/controller branches are untouched.
- N100 original 5 individually cropped Q051 readable HD English PNG files from `work/c_salvage_text_roi/original_hd_phrase_crops_20261016/DELIVERABLE_V3_20261016/`.
- A1 TOTAL TIME → 총 시간 (480×127); A2 LAP TIME → 랩 타임 (516×123); B1 HEARTS → 하트 (299×115); B2 SCORE → 점수 (280×115); C1 TIME → 시간 (250×119).
- `sheet_reference.png` 1280×768 RGBA: paste exactly at original scale, no resizing/rotation/masking/CLEAN, individual source RGBA pixels byte-for-byte equal within each sheet slot.
- `sheet_review.png` contains tracking labels in the background, NOT the generator reference.
- `manifest.json` stores source SHA256 and source image rectangles, review/generation HOLD.
- `Q051_HUD_YELLOW_5_TEST_ONLY.zip` contains both sheets + prompt + manifest.
- Image generation attempted once in ChatGPT, generation id `4ad91fc3-5e78-4b41-9e0b-725b90743ca4`, `edit_op=null`. Generated a new 1536×1024 RGB image with five Hangul phrases, **NOT** source-bound editing. It includes an RGB checkered background (not alpha transparency), did not preserve 2×3 slot positions and was not normalized to original UI. Therefore not acceptable as a real Korean glyph or DDS composite; generated image stored only in the user conversation/local artifact, not inferred to be on N100.
- No original A/B/C/C1 controller restarted. No DDS or game patches. No legacy 986 tiles used. No original source output overwritten or deleted. `RUNTIME_VALIDATION=UNTESTED`.

The batch optimization concept remains open for further tests using real source attachment binding and native slot mapping; this pilot is not an authorized production reroute.
