# Korean localization binary comparison

This directory contains binary material for source-vs-localized verification.

- `original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip`: original game DDS files matching every DDS path in the FULL_DRAFT package.
- `modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip`: reconstructed localization FULL_DRAFT binary package.
- `modified/OutRun2_Korean_GFX_Batch51_37759842_Rework_Test.zip`: latest Batch51 candidate package for 37759842.
- `pairs/37759842/original/37759842_1024x1024.dds`: direct original DDS.
- `pairs/37759842/modified_batch51/37759842_1024x1024.dds`: direct Batch51 modified DDS.
- `FULL_DRAFT_PAIR_COMPARISON.tsv`: per-DDS SHA-256, size, and SAME/CHANGED status.

The original and modified archives preserve identical relative texture paths for straightforward binary and image comparison.
