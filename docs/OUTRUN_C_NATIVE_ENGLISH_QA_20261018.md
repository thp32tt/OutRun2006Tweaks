# OutRun 2006 C-slot original HD English crop — QA & Q057 rework
As of 2026-10-18 KST. GitOps service: `outrun-c-english-native-crop`.
All changes below are QA/rework artifacts. **No A/B, no image generation, no DDS writes, no runtime PASS.**

## Input and evidence
- 108 unsplit native-HD source PNGs from 5 SHA256-pinned Library ZIPs; manifest 108/108.
- One-pass OCR v2 completed: 108/108 source records, 107 SCANNED, 1 NO_REVIEWED_OFFICIAL_PHRASES.
- Existing native original crops: 242, including 166 initial and 76 edge-warning candidates.
- Full crop pixel comparison with source original: **242/242 PASS**, crop SHA: **242/242 PASS**.
- Original source pixel integrity is not equal to glyph isolation approval. In-game validation **UNTESTED**.
- Six visual contact sheets inspected in N100: `qa_review_20261018/EDGE_REVIEW_CONTACT_01_of_06.jpg` through `06_of_06.jpg`.

## Visual triage of 76 edge-warning crops
- 9 visually legible candidate regions (not final PASS).
- 20 text with original plate/underline/decoration requiring further separation/approval.
- 39 original regions include unrelated neighboring sprite/vehicle/UI artwork.
- 8 have punctuation clipping or transcription/adjacent glyph risk.
- **47 require rework**; none is automatically promoted into game use.
- 23/76 candidate bboxes have neighboring crop collision if blindly expanded, so automatic edge expansion is not safe.

## Performed: 15 Q057 native-HD rework candidates
- 5 platform atlases × `SPECIAL REQUEST`, `Target`, `Technical Bonus` = **15 test-only corrected pixel crops**.
- Fixed native XYXY bboxes:
  - SPECIAL REQUEST: [2210,377,3215,485]
  - Target: [2631,541,2810,598]
  - Technical Bonus: [2400,118,3630,267]
- Old broad crops contained cars and UI. Test candidate contact sheet confirms reduced unrelated artwork.
- 15/15 source SHA pass, 15/15 original-region RGBA byte-identical and crop SHA verified.
- Original 242, 255 historic master, queue/checkpoints, translations, C1/C3 results all untouched.
- Alternative outputs are under N100 `qa_review_20261018/reworked_q057_test_only/`.
- Preview `qa_review_20261018/Q057_REWORK_15_CANDIDATES.jpg`.
- **32 rework items remain**, recorded in `rework_remaining_32.json`, with no automatic dispatch or guessed success.

## Next gate
Review the 15 Q057 candidates at full native resolution, evaluate remaining 32 rework requests,
and independently approve plate/underline candidates before downstream alpha/Korean stage.
Do not equate these TEST_ONLY QA steps with actual game acceptance.