# Graphics Orientation & Preserve Policy

Updated: 2026-09-26 22:46 KST
Branch: `korean-localization-clean`

This policy is mandatory for all Korean graphics localization work.

## Source-of-truth rule

1. **Primary construction source is now the user's installed high-resolution texture mod DDS.**
2. Identify an asset by its stable hexadecimal hash prefix (for example `EBEF6D20`), not by the old `_512x512` resolution suffix.
3. Read the actual DDS header for width/height/format/mips. A high-resolution mod may keep an old filename suffix, so filename dimensions are not authoritative.
4. The stock original DDS/archive remains a **fallback and reverse-engineering/orientation reference**, not the preferred artwork source when an HD replacement exists.
5. Do **not** upscale or reuse an old Korean DDS as the new base. Korean artwork must be reconstructed from the exact HD DDS.
6. Do **not** infer orientation from a previously generated Korean FULL-DRAFT DDS or from a generated preview.
7. Raw DDS may intentionally contain per-sprite mirroring, rotation, upside-down text, or mixed orientations because the runtime sprite/UV path corrects it in game.
8. Orientation is determined **per element / per sprite**.
9. Until the exact HD source package is imported and hashed, graphics promotion is held; stock-resolution candidates remain historical evidence only.

## Translation exclusion rule

The following embedded text is preserved exactly as original artwork and is excluded from Korean translation unless later explicitly approved:

- vehicle model names,
- vehicle variant names,
- manufacturer/brand marks,
- logos,
- song titles / music credits,
- legal/licensing marks,
- product/model codes where they identify the vehicle.

When a selector tile contains a vehicle picture plus vehicle/model name, preserve the original picture **and** original vehicle/model-name artwork, including its raw DDS orientation.

## Orientation rule

For every localizable text/image segment:

1. Inspect the corresponding segment in the **original raw DDS**.
2. Record its original orientation: normal / mirror-X / mirror-Y / rotate-180 / other atlas-specific transform.
3. If the original text is mirrored, rotated, or upside down in the raw DDS, the Korean replacement must be rendered with the **same raw-texture transform**.
4. If artwork and text use different transforms in the same DDS, preserve those transforms independently.
5. Never normalize the entire DDS to make it visually upright in an image viewer.
6. Never assume that a vehicle/icon and adjacent text share the same transform.
7. Game-view screenshots are validation evidence; raw DDS orientation is the construction reference.

## Confirmed examples

### `spr_sprani_selector_cvt_Exst/841E796B_512x128.dds`
- The top/bottom blue selector tiles are vehicle/model-name artwork.
- Vehicle/model names and their vehicle pictograms are **preserve-original** and are not translated.
- Preserve the raw texture orientation exactly.

### `spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds`
- Branch-road text and loading labels are intentionally stored with non-upright transforms in the original raw DDS.
- Korean replacements must reproduce each original element's raw transform rather than being made upright in the DDS.
- Existing non-text artwork should remain source-faithful unless localization requires replacing embedded text.

## QA gate before marking an asset ready

An asset cannot move to final candidate status until all are checked:

- original DDS inspected,
- preserve-vs-translate classification confirmed,
- per-element transform confirmed,
- Korean text rendered with matching raw transform,
- non-text original artwork preserved where possible,
- dimensions/alpha/DDS format/mip behavior preserved,
- in-game screenshot validation completed.

## Resume rule

On any future request such as **"이어서 작업해줘"**, read and apply this policy before producing or revising localization artwork.


## Style-fidelity rule

This gate is mandatory in addition to orientation correctness.

1. Korean replacement text must stay visually close to the original artwork:
   - similar stroke/outline weight,
   - similar fill color or gradient,
   - similar shadow/highlight behavior,
   - similar condensed/wide proportions,
   - similar alignment, scale, and spacing.
2. Do not use a generic white-outline Korean style when the original is flat gray, orange, red, yellow, or otherwise stylistically different.
3. Prefer preserving the original background/badge/panel artwork and replacing only the text layer/region.
4. If the translated text cannot yet be made source-faithful, keep/reset that asset to the original DDS and mark it pending rework.

## Artifact-cleanliness rule

Before an asset can be retained as a localized candidate, inspect the full alpha/color result for editing residue.

Reject or rework an asset if it contains:
- stray black horizontal/vertical lines,
- crop seams,
- underline-like remnants not present in the source,
- text-erasure residue,
- clipped glyphs,
- opaque boxes introduced accidentally,
- alpha halos or mismatched borders around replaced text.

The artifact check must be performed on both the raw DDS view and the readable/game-orientation preview.

## GitHub persistence rule

The canonical localization branch is **`korean-localization-clean`**.

For every completed graphics batch or QA-rule change:
- update this branch's localization progress/resume metadata,
- add/update the machine-readable batch report under `localization/graphics/`,
- update `localization/WORKLOG.md` and `localization/progress/STATUS.md`,
- do not merge VR or FFB source into the localization branch.


## Text-region containment rule

This gate is mandatory for every translated sprite or text segment.

1. Determine the original text region / sprite cell from the original DDS before drawing Korean.
2. All non-transparent pixels introduced by the Korean replacement must remain inside that original text region.
3. The replacement must not spill into neighboring sprite cells, artwork, icons, bars, or transparent padding used by another element.
4. If Korean text does not fit:
   - reduce horizontal scale,
   - reduce font size,
   - use a shorter translation/abbreviation,
   - or leave/reset to the original.
5. Reject the candidate if any glyph is clipped, overlaps another element, or crosses the source region boundary.
6. Check containment both in raw DDS orientation and in the readable/game-orientation preview.


## HD texture migration rule

Effective 2026-09-26 22:46 KST:

- Canonical artwork baseline: **user-installed high-resolution texture mod**.
- Collector: `tools/localization/collect_hd_localization_source.ps1`.
- The collector matches by hexadecimal asset key, reads dimensions directly from each DDS header, and records SHA-256 for every selected HD source.
- When the HD source contains a target, all Korean text bounds, masks, alpha checks, orientation checks, style checks and containment checks are recalculated against that HD DDS.
- If the HD mod does not contain a target, the stock original DDS is allowed only as an explicit fallback and must be recorded as such.
- Existing B3-B65 stock-resolution candidates and user approvals are preserved as history, but they are not automatically valid HD candidates.
- Never resize an already-localized low-resolution DDS to create the HD localization.
