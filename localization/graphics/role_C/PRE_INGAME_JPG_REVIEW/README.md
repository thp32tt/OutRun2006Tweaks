# C QA PASS - English original vs Korean pre-in-game review

- Numbered C-pass rows: 12
- High-risk candidates blocked pending exact-SHA C3_STRICT_PASS: 10
- Primary English source: Sonic-TV/OR2006Sprites pinned at 3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6
- Exact stock-original fallback: localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip
- Every JPG contains the English original and current Korean candidate side-by-side.
- Top: FLIP-Y review comparison. Bottom: RAW DDS comparison.
- English source SHA-256, native dimensions, origin, and any review-only display scale are recorded in the manifests.
- Lower-resolution English originals may be nearest-neighbor scaled only for human display; the English source bytes are never modified or treated as pixel-QA equivalents.
- If no proven English source can be aligned to the candidate, export fails closed.
- User visual rejection overrides prior C static PASS and reopens the asset for A/B rework before in-game testing.
- High-risk candidates are omitted until their current candidate SHA is explicitly recorded with C3_STRICT_PASS. See manifest.json mandatory_c3_blocked.
- C visual checklist: clean plate/source-footprint restoration; source-direction slant; source-relative scale/hierarchy; readable weight/effects; zero clipping; zero protected-art intrusion; no untranslated visible localizable labels.
- Report defects by the leading JPG number.
