# LOCALIZATION-LOCALIZATION_A-00483

TASK_ID=LOCALIZATION-LOCALIZATION_A-00483
LANE=LOCALIZATION_A
WAVE_ID=P00316
TARGET_BRANCH=korean-localization-clean

## Current-contract selection
- Current controller contract assigns producer A to odd numeric asset_queue.csv indices.
- Index 53 / 568D3696 is odd and is a direct C rework item for post-reset generation lineage.
- No pre-reset Korean candidate pixels or pre-reset localized mip payloads were used as construction input.

## Material result
- Rebuilt textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds from the exact canonical English HD source already present on the branch.
- Canonical source blob: 3d6bedf9c66d6c43c4ca16483a0f447137b39c3a.
- Canonical source SHA-256: 65bc5e88e7b01f8148bcbbb2dc4b2225bf53c8501801e329c51ecb274e8cd813.
- Source/candidate DDS identity: 4096x4096, DXT5, 13 mips, 22,369,776 bytes.
- Fresh candidate SHA-256: 25600c9081b311fcc887dc146bd28dfc5dd8d3627de9a516d94a872f15668b64.
- All 14 localized elements were freshly typeset from canonical translation strings after exact-source text removal.
- Mip 0-12 localized regions were rebuilt from exact English source mip data plus the fresh localized edit mask; no prior localized lower-mip bytes were reused.

## Self-QA
- Clean-plate change outside semantic source-removal mask: 0 pixels.
- Candidate header matches source header exactly.
- All decoded Korean effect bboxes are contained inside 2px-inset candidate-safe bboxes.
- English-left / Korean-right decoded DDS comparison: PASS.
- English residue observed: none.
- Clipping / overlap / opaque boxes: none observed.
- Protected non-text linework/artwork: retained.
- Machine-readable report: localization/graphics/role_A/LOCALIZATION-LOCALIZATION_A-00483/LOCALIZATION-LOCALIZATION_A-00483_568D3696_SELF_QA.json.
- Comparison evidence: localization/graphics/role_A/LOCALIZATION-LOCALIZATION_A-00483/568D3696_english_vs_korean.png.
- Clean-plate evidence: localization/graphics/role_A/LOCALIZATION-LOCALIZATION_A-00483/568D3696_clean_plate_proof.png.

RESULT=SELF_QA_PASS_PENDING_C
AUTOMATION_VALIDATION=PENDING
VALIDATION_MODE=C_BATCH_GATE
RUNTIME_VALIDATION=UNTESTED
