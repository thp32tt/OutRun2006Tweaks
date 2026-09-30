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

## 2026-09-29 graphics generation reset

All pre-reset Korean graphics candidates are historical evidence only and must not be used as artwork inputs. Active production restarts from the exact English HD source under the mandatory zero-artifact reconstruction contract in `ORIENTATION_POLICY.md`.

Production must not cover English with boxes or render Korean over English. Remove the complete English glyph/effect footprint, faithfully reconstruct the original background, then typeset Korean. If clean reconstruction is not possible, redraw the affected source element faithfully or stop as `MANUAL_RECONSTRUCTION_REQUIRED`; never retain a visibly patched candidate.



## Mandatory first-pass generation v2

New/reworked Korean DDS candidates use `outrun-first-pass-edit-v2`.

Pipeline:
`EXACT_HD_SOURCE -> SOURCE_REMOVAL_MASK -> VERIFIED_CLEAN_PLATE -> DETERMINISTIC_KOREAN_LETTERING -> NATIVE_MEASURE -> REFIT/RE-RENDER -> DDS -> C QA`.

The removal mask and Korean lettering region are intentionally different: Hangul is not required to occupy the exact English glyph pixels. Clean-plate edits stay inside the source removal mask; Korean/effect pixels stay inside the measured permitted region and, by default, at least 2 px inside both the source full-effect bbox and permitted region. A 1 px inset is allowed only when explicitly justified by small geometry. A zero-margin first-pass target is forbidden.

Do not resize a flattened Korean raster after rendering. If measured Korean effects do not fit, re-render from font/effect parameters at a smaller size or adjusted position and measure again. Transparent/text-only atlases require deterministic lettering.

## Naming consistency policy — songs and stage/course names

- Song/music titles are protected titles: **do not translate or transliterate them**. Preserve the exact source title, including subtitle/remix/year suffixes and capitalization where the source artwork/text requires it.
- Stage/course proper names use **Korean transliteration consistently**, not semantic translation. Examples: `Coniferous Forest -> 코니퍼러스 포레스트`, `Ancient Ruins -> 에인션트 루인스`, `Desert -> 데저트`.
- Generic UI words such as `Stage`, `Next Stage`, `Course Select`, mission instructions, and descriptive prose remain normal Korean localization; this rule applies to proper stage/course names only.
- Producer and C QA must reject a candidate that translates/transliterates a protected song title or mixes semantic translation and transliteration for canonical stage/course proper names.

## Typography family consistency v19

Song-title and stage/course-name typography is family-locked.

- Within the same visual UI family, every song title uses the same native font size/effect geometry. A long song title MUST NOT receive a smaller per-title font size.
- Within the same visual UI family, every stage/course proper name uses the same native font size/effect geometry. A long stage name MUST NOT receive a smaller per-name font size.
- "Same family" means labels occupying the same UI role/style system (same selector/list/ranking/card family), not every occurrence across unrelated screens. Different UI families may have different fixed sizes when the English source itself uses different typography roles.
- Fit order for these families is: fixed family font size -> source-faithful alignment -> tracking adjustment within the source style -> canonical abbreviation only when that source family itself uses abbreviations. Do not shrink one label independently.
- If a label still cannot satisfy the safe bbox at the locked family size, return `REWORK_REQUIRED` and redesign the family/layout. Never silently reduce only that label's font size or rescale a flattened raster.
- Producer evidence must record a stable `typography_family_id` and native `font_size_px` for each affected element. C QA must compare all members available in that family and reject non-uniform font sizes.
- This does not relax zero-pixel containment, source-faithful effects, or any DDS/alpha/orientation rule.
