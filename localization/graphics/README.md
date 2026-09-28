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

## Controller work-scope rule
The automation/controller MUST derive graphics scope from `asset_queue.csv`, not from the number of DDS files currently committed.

Current sanity baseline (2026-09-28):
- total queue: 137 rows
- direct `localize_text`: 79
- `zoom_review`: 47
- direct containment/review scope: 126 rows
- `font_pipeline`: 9
- `hangul_name_entry`: 1
- preserve-only: 1

The controller must recompute these counts every run. The existing committed DDS set is only a partial working set.

For every localized texture element, compare the localized non-transparent pixel bbox to the original/HD source permitted bbox/cell. A 1-pixel escape in any direction is `REWORK_REQUIRED` and blocks approval. Missing or ambiguous evidence is `HOLD_STRICT_RECHECK`, not PASS. BC/DXT/DXT5 block-only evidence cannot substitute for decoded-pixel containment at final approval when exact evidence is unavailable.

## Current visual review
Reviewed: `game_ui`, `common_ui`, `ranking`, `font`.

The reviewed atlases clearly contain embedded English labels suitable for direct texture localization. The font atlases contain Latin/digit/symbol glyphs and require a separate Hangul strategy.

Machine-readable summary: `inventory_summary.json`.


## Mandatory original-orientation policy

Before editing any DDS, read and apply `localization/graphics/ORIENTATION_POLICY.md`.

Key requirements:
- inspect the original game DDS, not a previous Korean FULL-DRAFT;
- classify vehicle/model/brand/song/legal text as preserve-original where applicable;
- preserve per-sprite mirror/rotation exactly as stored in the original raw DDS;
- apply the same raw transform to Korean replacements when the original text is mirrored/rotated;
- never normalize an entire atlas simply to make it upright in an image viewer.
