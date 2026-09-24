# Translation Workflow

1. Generate a local catalog from the owned game file:

```bash
python tools/localization/build_text_catalog.py \
  "Text/English_Korean.bin" localization_work/strings.csv
```

2. Keep human draft decisions in:

`localization/translations/ko_draft.json`

3. Expand exact duplicate source strings automatically:

```bash
python tools/localization/propagate_translations.py \
  localization_work/strings.csv \
  localization/translations/ko_draft.json \
  localization_work/ko_expanded.json
```

The propagation step only reuses a Korean translation when the English source string is byte-for-byte the same after txet decoding. It aborts if two explicit IDs assign different Korean text to the same source string.

Current measured result from the analyzed archive:

- explicit draft IDs: 180
- exact-match expanded IDs: 361
- effective coverage: 26.6%
- total IDs: 1,356

Context-sensitive review remains required before release.
