# OutRun 2006 — F3 15-label / two family input-preflight (2026-10-16)
 
TASK_ID: OUTRUN-KR-Q053-Q060-F3-20261016

## Result: SOURCE INPUTS PREPARED; F3 STATIC **HOLD / NOT PASS**

- Two genuinely different atlas families, **15 native English ROI**: Q053 mission yellow/navy 8, Q060 metallic menu/results 7. All 15 PNG input crops were byte-SHA-pinned against the authoritative native crop manifest and independently **pixel-exact** against the verified full original readable PNG.
- The provided Korean mapping is **DRAFT UNAPPROVED**, not a verified translation SSOT. All exact text and context must be reviewed before any sprite is accepted.
- Q053 original DDS SHA-256 `65bc5e88e7b01f8148bcbbb2dc4b2225bf53c8501801e329c51ecb274e8cd813` is **DXT5, 4096×4096, 13 mips**. Preserve all original blocks/mips and test block-level changes or HOLD; cannot use F2's raw RGBA writer.
- Q060 original DDS SHA-256 `6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc` is **uncompressed RGBA32, 4096×2048, 1 mip**. A compatible format alone does not prove safe CLEAN.
- Among 15 source crop rectangles, 14 touch an alpha/nontransparent border; these ROI crops mix other scene/background elements. **Their whole alpha mask is NOT an approved text-removal mask.**
- The image-generation attempts in this session returned **status infographics that claimed nonexistent F3 success**, not the requested independent transparent Korean word layers. These images are **REJECTED / DO_NOT_USE**. Claims, example hashes, and DDS paths appearing within them are fictional.
- `KOREAN_SPRITES=0/15 ACCEPTED`, `CLEAN=0/15 APPROVED`, `DDS_F3=NOT_CREATED`, `F3_STATIC=HOLD`, `C1_C3=NOT_RUN`, `RUNTIME_VALIDATION=WAIVED_BY_USER_FOR_THIS_TEST_UNTESTED_NOT_PASS` (not PASS).
- Nothing was deleted/replaced; legacy 986 tile images, F0/F1/F2, source HD DDS, A/B/C/C1 state, VR and Portainer unchanged. No Docker restart.

## Contents

- `F3_INPUT_PREFLIGHT.json`: per asset source SHA, native crop bbox, proposed text, alpha-border diagnostic, original DDS format and status.
- `Q053_MISSION_YELLOW_NAVY_NATIVE_CROPS.zip`, `Q060_METALLIC_GRADIENT_NATIVE_CROPS.zip`: 8+7 **original exact English crops**, NOT generated Korean. Both include proposed translation mapping for review.
- `Q053_MISSION_YELLOW_NAVY_EN_NATIVE_REFERENCE.jpg`, `Q060_METALLIC_GRADIENT_EN_NATIVE_REFERENCE.jpg`: human visual review only; preview scales differ from native source (the original PNGs are in ZIP files).
- `build_f3_source_sheets.py`: reproducible preflight preparation, no DDS writer.

## Next actionable steps

1. Verify official Korean wording against approved mapping; update only unapproved draft lines.
2. Generate **actual** phrase-per-slot alpha PNG for these two distinct styles from exact source files (not fake status sheet, not old 986 tiles). Keep each raw output SHA; text, slant and alpha QA independently.
3. Mark per-label English glyph/effect mask and protected neighboring scene content. Clean plate and no-residue check; current crops are NOT masks.
4. For Q060, compose a separate `Q060_F3_TEST_ONLY.dds` preserving source 128-byte header, size, native orientation, RGBA32 and all outside protected pixels. For Q053, first implement validated DXT5 per-mip, block-preserving candidate; do not overwrite compressed original.
5. Decode the **saved** candidate(s), verify each phrase and protected areas; record hard errors and only then count F3 static PASS. User-waived in-game test remains UNTESTED; do not promote to release.