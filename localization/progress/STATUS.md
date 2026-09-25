# Korean Localization Status

Updated: 2026-09-26 00:34 KST

## Active branch
`korean-localization-clean`

Base: `emoose/OutRun2006Tweaks@08e5efb4deea4066c440307ec009c868a30562d3`

## Isolation
- VR source: **absent**
- VR/FFB source merge/cherry-pick: **forbidden**
- Shared cross-project data: reverse-engineering knowledge only

## Text
- txet IDs: 1,356
- non-null: 1,355
- Korean draft: **1,355/1,355 (100%)**
- reviewed/finalized: **1,351/1,355 (99.7%)**
- context-sensitive IDs: **96, 97, 279, 280**

## Graphics
- DDS inventory/visual review: **243/243 (100%)**
- direct Korean artwork targets: **79**
- graphics transcription: **79/79 (100%)**
- translated graphics segments: **674/674**
- FULL-DRAFT DDS candidates: **79/79 (100%)**
- final in-game validated: **0/79**
- package: `OutRun2_Korean_GFX_FULL_DRAFT_Test.zip`
- package SHA-256: `5512dad798a4ddb4872e4aa3e69438537f75f488f439317d7b95c0eb372b6c78`
- report: `localization/graphics/FULL_DRAFT_REPORT.json`

The full draft intentionally uses exact/OCR/manual/atlas-alpha placement evidence. Large atlases require screenshot validation before release promotion.

### Graphics QA reset
- Mandatory policy: `localization/graphics/ORIENTATION_POLICY.md`
- Original game DDS from the original analysis archive is the source of truth.
- Previous generated draft art must not be used to infer orientation.
- Per-sprite mirror/rotation must match the original raw DDS.
- Vehicle/model/brand/song/legal artwork is preserve-original unless explicitly approved.
- `841E796B_512x128.dds`: vehicle/model cards preserved as original; do not translate vehicle/model names.
- `EBEF6D20_512x512.dds`: Korean route/loading text must inherit the original raw DDS transforms.
- 1st/2nd/early-3rd batch generated images are visual drafts pending source-faithful rework.

### Source-faithful batches
- Batch3: 10 assets, report `BATCH3_SOURCEFAITHFUL_REPORT.json`
- Batch4: 5 assets, package SHA-256 `cfddc6c758bfdc8313dd624bbe9211ce6d2221bd04985ee6856d449e66cffb95`
- Batch5: 5 assets, package SHA-256 `1d5de3dcc55caefba4e904e3d0030b6ae5fbd70f479546641add3d967cf3459f`
- Source-faithful reviewed since QA reset: **20**
- Retained/rebuilt localized candidates: **17**
- Reset to original pending safe rework: **3**
- Pending special case: `49BB5FE5_128x32.dds` DXT5 compression-safe rewrite

## Runtime/font
- K0 txet roundtrip: **PASS**
- K1 clean trace package: **ready**
- K2 ASCII resolver proof: **ready**
- K3 trace build/package: **ready**
- unique Hangul syllables: **505**
- two-page 1024x1024 Hangul atlas proof: **ready**
- final Hangul runtime render: **pending in-game proof**

## Resume
Read:
1. `localization/progress/progress.json`
2. `localization/resume_state.json`
3. `localization/WORKLOG.md`
4. `localization/graphics/ORIENTATION_POLICY.md`
5. `localization/graphics/BATCH3_SOURCEFAITHFUL_REPORT.json`
6. `localization/graphics/BATCH4_SOURCEFAITHFUL_REPORT.json`
7. `localization/graphics/BATCH5_SOURCEFAITHFUL_REPORT.json`
8. `localization/graphics/FULL_DRAFT_REPORT.json`

Next gate: continue remaining assets from original DDS first; handle DXT5 safely; keep vehicle/model/brand/song/legal text preserved; in-game validate source-faithful candidates.
