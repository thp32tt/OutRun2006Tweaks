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

## Current recovery-branch production policy

The active K4 Korean text path does **not** replace the game's stock font DDS atlases. `src/hooks_localization.cpp` suppresses matched stock English glyph output and redraws the Korean UTF-8 string through the existing D3D9 ImGui overlay. `Overlay::rebuild_fonts()` loads a Korean-capable Windows system font (Malgun Gothic first, then other Windows fallbacks). Therefore stock `spr_font_xst` DDS files remain original and do not require Korean bitmap candidates for K4.

The 505-syllable/two-page atlas described below is retained as K3 research evidence only. It must not be packaged as a stock-font replacement unless the runtime architecture is intentionally changed and separately validated in-game. Name-entry input (`spr_name_entry_xst`) is a separate path and is **not** resolved by this policy.

A133 statically reconciled A-owned font-pipeline queue rows 15/17/19/21/23 to preserve-original/no-candidate. Runtime/in-game validation of the K4 overlay remains pending.

### A134 remaining stock-font reconciliation

After refreshing the branch, A's primary shard had no actionable production rows while B was actively producing index176. A therefore work-stole the remaining even `font_pipeline` rows 16/18/20/22 and applied the same K4 architecture decision as A133. All nine stock `spr_font_xst` queue rows 15-23 are now preserve-original/no-Korean-DDS-candidate for K4. The name-entry atlas at index24 remains a separate input-path problem and is not covered by the overlay-font decision.
