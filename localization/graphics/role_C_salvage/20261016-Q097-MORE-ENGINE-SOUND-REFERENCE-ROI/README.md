# C-ROI-SOURCE Q097: More Engine Sound (2026-10-16)

- **TASK_ID:** OUTRUN-C-ROI-SOURCE-Q097-MORE-ENGINE-SOUND-20261016-0003
- **Only source:** direct GitHub pinned PC HD DDS `localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds` (actual decoded DDS 2048x2048); SHA256 `bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364`.
- Readable full RGBA English PNG (direct original DDS FLIP-Y, pixel-exact, *not* historic 986 tiles): SHA256 `2ecc253ac9db49a9c1189f1f814d562a45462b660af94877ce1f66737cfe58af`. Existing full source in sibling `20261015-Q097-AUTOMATIC-DIRECT-ROI/Q097_full_original_readable.png` (or prior N100 SHA-pinned source).
- Visual English: **More Engine Sound**; reviewed Q097 transcription uses **More Engine sound** (case only). Reviewed translation: **엔진음 크게**. No brand, car or song title edited.
- Native ROI xyxy `[1480,316,1928,432]`: 448x116 RGBA, SHA256 `6afcbf5de2bcac733a1405763833acf15c61b6f7302dd52d093c92ced4b6b6fb`; 4x 1792x464 RGBA SHA256 `597b56376152e04189783af3edfaef3b54ee1a9e5eba9301dc61a932d5f9fc6e`.
- `text_roi_source_pack.py` schema `outrun-hd-text-roi-v1`; validated pixel-exact direct original DDS→readable full PNG→native crop→Lanczos 4x. One *whole phrase*, no original grid/tile usage.
- **Reference-only HOLD**: orange opaque UI plate is inside this ROI, and source alpha edges include some non-text pixels (bottom/right). Do not label this isolated glyph alpha, clean plate, approved direct ImageGen input or production-ready source. Requires separately reviewed exact PSD/glyph mask, CLEAN and UI-cell/UV safe fit measurement; official mapping CSV should be cross-checked independently. Preserve aspect ratio for future Korean output; differing Hangul width alone is not rejection.
- ImageGen, Korean generation, DDS write, C1/C3 and user game were **NOT RUN**. QA **TEST_ONLY**; `RUNTIME_VALIDATION=UNTESTED`. Existing A/B batches, 986 legacy tiles and state/queue are untouched. No Portainer redeploy or production dispatch.

See `SOURCE_ROI_QA_TEST_ONLY.json` for exact checks, holds and SHA records.
