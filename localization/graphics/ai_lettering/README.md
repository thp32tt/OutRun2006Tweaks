# AI-generated Korean lettering extraction: 37759842

**Status: EXTRACTED_ONLY / NO DDS CANDIDATE / RUNTIME_VALIDATION=UNTESTED**

The 2026-10-13 input is a 1254×1254 reference UI collage, **not** the
canonical 4096×4096 HD DDS. We extracted only standalone Korean lettering
`튜닝`, `수동`, and `참가자를 기다리는 중입니다.`; no blue panels,
icons, logos, or English-only tiles are transplanted.

- Canonical semantic binding: `localization/graphics/transcriptions.jsonl`
  entry 95, original `37759842_1024x1024.dds`.
- Exact crop rectangles + input SHA-256:
  [37759842_manifest.json](37759842_manifest.json).
- Local extraction QA + blockers:
  [37759842_extraction_review_20261013.json](37759842_extraction_review_20261013.json).
- Reusable tool:
  [extract_ai_korean_lettering.py](../../../tools/localization/extract_ai_korean_lettering.py).

## Reproduce using the two 2026-10-13 chat input images

```shell
python tools/localization/extract_ai_korean_lettering.py \
  --manifest localization/graphics/ai_lettering/37759842_manifest.json \
  --ai-sheet ai_korean_ui_1254.png \
  --reference-sheet user_reference_ui_1254.png \
  --extract-dir work/37759842_layers
```

The extracted layer files are produced locally; they are **not** in GitHub.
Their exact SHA-256 values are in the QA JSON. Do not substitute a
different AI image under the same name: the extractor verifies both SHA-256
identities.

## Clean-plate composition (currently blocked)

```shell
python tools/localization/extract_ai_korean_lettering.py \
  --manifest localization/graphics/ai_lettering/37759842_manifest.json \
  --extract-dir work/37759842_layers \
  --clean-plate VERIFIED_EXACT_HD_CLEAN_PLATE.png \
  --clean-plate-qa VERIFIED_CLEAN_PLATE_QA.json \
  --compose-png work/37759842_lettered_proof.png
```

The script fails closed without an independently verified clean-plate
QA binding, exact canvas, or with low-resolution AI glyphs requiring
upscaling. The current uploaded 1254-pixel collage is **too low-resolution
to qualify as native-HD artwork**. Therefore **no real source clean-plate
has been composited and no DDS has been approved**.

The older Batch 41-51 `37759842` candidates were rejected due to
icon/background damage, so they cannot be recycled as plates. Recover or
rebuild the canonical HD English-source clean plate and redo the lettering
at source-native size before committing any candidate DDS. Keep the original
DDS unchanged until the strict v2 pipeline and independent C QA pass.
