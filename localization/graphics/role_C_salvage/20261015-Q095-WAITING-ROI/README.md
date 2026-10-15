# C-ROI-SOURCE Q095 Waiting for entries. — TEST_ONLY

- TASK_ID: `OUTRUN-C-ROI-SOURCE-Q095-WAITING-20261015-2233`
- Scope: Korean localization, independent new single-phrase source ROI; no A/B old-986-tile input/reassembly, no new image generation.
- English / verified official Korean from `localization/graphics/transcriptions.jsonl` Q095: `Waiting for entries.` → `참가자를 기다리는 중입니다.`
- Original platform: PC. Original exact DDS: `localization/validation/binary_compare/pairs/37759842/original/37759842_1024x1024.dds`; SHA256 `ec69c95e638f6ba1ef2c23db173462adb26ad0d10caed28f1c83b7d1d15658f0`; Git blob `c888e9b1c87dabdc7a6f5ef47dd88498b95b2d83`.
- Actual full-original readable 1024×1024 RGBA PNG, **pixel-for-pixel equal to the original PC DDS after vertical flip**: `localization/graphics/reference_packs/full_dds_test/37759842_FULL_ENGLISH_ORIGINAL_FLIPY_1024x1024.png`; SHA256 `8b78a092b5ca82276076cc5d99b05afd0831651ae2d4afbbcf7486f4693fa7c9`.
- Extracted one complete phrase including visible outline/shadow: native xyxy `[0,180,395,236]` (395×56). Alpha extent `[2,184,388,233]`; transparent L/T/R/B margins `2/4/7/3` px; 2-pixel-edge contact counts all zero. Initial broader trial intersected other phrase alpha and was **rejected**; this reviewed crop excludes it.
- Native SHA256 `b96ca5b4a3afd90c34270d47efc7a920fa25fe847ab048dcbd713c97ab8e7bb0`; 4x upscale 1580×224 PNG SHA256 `322626bcb8548b0dfb44d43853d90e0d4da9d779b78875e2a35e798374388052`.
- Extractor: `tools/localization/text_roi_source_pack.py`; schema `outrun-hd-text-roi-v1`. Reproduce using `roi_spec.json` and a source-root directory holding the exact full original PNG. All 14 mechanically reproducible source checks PASSED in `SOURCE_ROI_QA_TEST_ONLY.json`.
- Native return: preserve aspect ratio to independently verified UI cell/UV safe area. Width difference alone is not failure; never guess source removal mask or CLEAN plate.
- This ROI is an **isolated ImageGen input candidate**, not a generated Korean output; no ImageGen call. No A/B state, queue, batches, old artifacts, production or Portainer altered. No C1/C3 or game approval. `QA=TEST_ONLY`; `RUNTIME_VALIDATION=UNTESTED`.
