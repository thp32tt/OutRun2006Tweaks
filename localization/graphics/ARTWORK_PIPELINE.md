# Korean artwork renderer

This tool creates deterministic PNG proof overlays from `artwork_specs.jsonl`.

It does **not** bundle game assets or fonts. Supply a Hangul-capable font you are licensed to use.

Example:

```bash
python tools/localization/render_artwork.py \
  localization/graphics/artwork_specs.jsonl \
  --font "/path/to/your/HangulFont.ttf" \
  --output-dir localization_work/rendered \
  --id 1
```

The first proof spec recreates the 256x64 `Continue?` label as `계속?`.
The source texture is stored horizontally mirrored, so the renderer mirrors the Korean proof to match the game's stored texture orientation.

PNG output is a review artifact only. Final DDS conversion must preserve the source DDS dimensions, pixel format/compression, alpha behavior and mipmap policy before an item can be marked `artwork_completed`.
