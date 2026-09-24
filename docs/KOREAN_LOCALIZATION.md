# OutRun 2006 Korean Localization

## Goal
Build a Korean localization as an independent distribution based on the clean upstream OutRun2006Tweaks source, without VR or FFB feature code.

## Source baseline
`emoose/OutRun2006Tweaks@08e5efb4deea4066c440307ec009c868a30562d3`

Active development branch: `korean-localization-clean`.

## Proven text format
The analyzed `Text/*.bin` files use a `txet` container:

```text
0x00  "txet"
0x04  uint32 total file size
0x08  uint32 entry offsets[]
...   UTF-16LE record payloads
```

The analyzed Korean-region file has 1,356 entries. A lossless extract/rebuild using `tools/localization/txet_tool.py` reproduced the original file byte-for-byte.

The stock executable later reduces UTF-16LE code units to a one-byte text path, so Korean text assets can be prepared in advance but require a Unicode-safe runtime/glyph path before they display correctly.

## Graphics
The supplied localization analysis archive contains 243 DDS textures. Work is split into:
1. inventory/classification,
2. text-bearing texture identification,
3. translated raster replacement,
4. DDS format/mipmap/alpha preservation,
5. in-game layout verification.

## Work order
1. Complete machine-readable string inventory.
2. Complete graphics inventory.
3. Draft Korean translation table.
4. Build translated texture candidates.
5. Add logging-only runtime trace on the clean branch.
6. Add a one-string Unicode-safe proof.
7. Add a minimal Hangul glyph proof.
8. Expand translation/font coverage.
9. Package independently.

All progress is checkpointed under `localization/progress/`.
