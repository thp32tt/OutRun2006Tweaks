# Hangul atlas generation

The repository does not ship a font file.

Generate raster pages locally from a Hangul-capable font you are licensed to use:

```bash
python tools/localization/render_hangul_atlas.py \
  localization/font/hangul_glyph_manifest.json \
  --font "/path/to/HangulFont.ttf" \
  --output-dir localization_work/hangul_atlas
```

Default output:

- `hangul_page_0.png` — 16x16 cells
- `hangul_page_1.png` — 16x16 cells
- `hangul_metrics.json` — stable glyph index, page/cell, advance and bounding box

Current corpus uses 505 Hangul syllables, so two pages are sufficient.

The raster pages are development candidates until K3 in-game rendering verifies baseline, size, spacing, outline and scaling.
