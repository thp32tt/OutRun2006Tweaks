# Original HD phrase crop extension — 255 references (2026-10-16)

**Actual execution receipt:** N100 MCP ran direct-original decoding, 63 new English phrase crops, per-crop visual QA and original-pixel exact validation. No A/B queue was modified.

## Provenance

- Prior batch: 192 numbered original English PNG reference crops from 12 full-HD original atlas sources.
- New direct DDS inputs: Q116 (Heart Attack Mode), Q161 (country/zodiac names), Q197 (OutRun License), Q212 (menu and modes).
- All four DDS binary SHA-256 digests matched the expected original DDS SHA pinned in GitHub. All four were decoded to correct-orientation full-size English PNGs. Q116/Q161/Q197 also matched independent pre-existing original readable PNGs at the RGBA pixel level.
- New native English ROI count: **63** (Q116: 1, Q161: 38, Q197: 5, Q212: 19).
- Combined numbered native ROI count: **255** (192 previous + 63 new), verified **255/255 pixel-exact** against directly authenticated full-original readable PNG source.
- Q161 38 phrase row boundaries were corrected using exact measured source alpha-row runs. Q212 full `OUTRUN` was recropped wider to avoid losing the initial letter; adjacent original icon may still appear in its reference and remains HOLD, not isolated alpha lettering.
- Original names (e.g. character names) marked PROTECTED_ORIGINAL_NOT_FOR_TRANSLATION. Fully clipped/edge-touching/opaque or mixed UI crops remain reference-only, not direct ImageGen inputs.
- No legacy 986 reconstructed arbitrary tiles or Korean generated images reused.

## N100 delivered archive

- Path: `/home/chatgpt-runner2/work/c_salvage_text_roi/OUTRUN_ORIGINAL_HD_CROPS_255_WITH_BACKLOG_20261016.zip`
- Size: **13,094,308 bytes**.
- SHA-256: `03e4aae8d81e211ae5a991dd7fad2783eb75ab9171a9c197f97ad53c4dec3da4`.
- Archive verified: **278 entries**, including 255 PNG, 19 JPG QA references, combined manifest and unresolved-source backlog.
- `MASTER_CROP_MANIFEST_255.json` holds every input path/hash, original crop bounding box, ROI hash, state and per-asset provenance.
- `NEXT_ORIGINAL_SOURCE_BACKLOG_108.json` is a 108-row next-input index; 16 base source entries accounted for, **92** source/variant entries not yet independently verified as full original, including platform variants.

## Holds and validation limits

- Q055: native 512x64 source glyph effect touches original bottom boundary, cannot assert lossless unclipped HD crop.
- Q095: N100 1024x1024 DDS SHA and dimensions do not match the inventory-pinned 4096x4096 expected HD original; not accepted as canonical HD.
- Legacy tile-reassembly-only Q043/Q044/Q065 preview images have not been promoted as full-original sources.
- Source-only status: `IMAGEGEN=NOT_RUN`, `C1=NOT_RUN`, `C3=NOT_RUN`, `DDS=NOT_RUN`, `RUNTIME_VALIDATION=UNTESTED`.
- No approved Korean outputs, no production queue state transitions, no game patch/runtime validation, no Portainer deployment.

**Important:** 255 means native English crop references, not 255 translation-complete or ImageGen-approved glyph layers. Continue to verify direct original DDS/PSD provenance for other 92 records before expanding the crop set.
