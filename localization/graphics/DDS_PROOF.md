# Source-compatible DDS proof conversion

For simple uncompressed 32-bit BGRA assets, `replace_uncompressed_dds.py` preserves the original 128-byte DDS header exactly and replaces only the pixel payload.

The first target, `textures/load/spr_etc_xst/D6DC1380_256x64.dds`, was measured as:

- dimensions: 256x64
- pitch: 1024 bytes
- pixel format: uncompressed 32-bit BGRA
- masks: R=0x00FF0000, G=0x0000FF00, B=0x000000FF, A=0xFF000000
- payload: exactly one 256x64x4 pixel level

Example:

```bash
python tools/localization/render_artwork.py \
  localization/graphics/artwork_specs.jsonl \
  --font "/path/to/HangulFont.ttf" \
  --output-dir localization_work/rendered \
  --id 1

python tools/localization/replace_uncompressed_dds.py \
  "textures/load/spr_etc_xst/D6DC1380_256x64.dds" \
  localization_work/rendered/D6DC1380_256x64.ko.proof.png \
  localization_work/rendered/D6DC1380_256x64.ko.proof.dds
```

This is still a runtime test candidate, not release artwork. Mark an asset complete only after the game loads the replacement correctly and the Korean label is visually acceptable.
