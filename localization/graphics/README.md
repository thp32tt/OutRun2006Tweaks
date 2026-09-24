# Graphics Localization

The game assets themselves are not committed here. Use the catalog generator against a locally owned game install.

## Inventory baseline
- 243 DDS textures in the analyzed localization sample
- 111 front-end
- 31 selector
- 19 common UI
- 15 ranking
- 9 font
- 9 loading
- 7 game UI
- 4 route
- 1 name-entry
- 37 other

## Rules
1. Preserve original texture dimensions.
2. Preserve alpha usage.
3. Preserve DDS compression/format when replacing a texture.
4. Preserve or regenerate mipmaps consistently with the source.
5. Do not alter non-text artwork unless required for legibility.
6. Keep Korean raster replacements separate from runtime font work.
7. Record each localized texture by SHA-256 and relative path before packaging.

## Current visual review
Reviewed: `game_ui`, `common_ui`, `ranking`, `font`.

The reviewed atlases clearly contain embedded English labels suitable for direct texture localization. The font atlases contain Latin/digit/symbol glyphs and require a separate Hangul strategy.

Machine-readable summary: `inventory_summary.json`.
