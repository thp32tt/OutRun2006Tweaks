# Graphics Orientation & Preserve Policy

Updated: 2026-09-26 22:46 KST
Branch: `korean-localization-recovery-20260928`

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

Stage-name spelling and song-title handling are additionally governed by `TRANSLATION_NAMING_POLICY.md`. Stage names use phonetic Hangul transliteration only. Song titles/music credits stay as original English pixels and must be included in protected masks.

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

The canonical localization branch for this recovery workflow is **`korean-localization-recovery-20260928`**.

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
5. Reject the candidate if any glyph is clipped, overlaps another element, or crosses the source region boundary. **Any 1-pixel text-to-text, localized-to-preserved-text, localized-to-icon/decorative/protected-artwork overlap is FAIL.** Source text visible beneath or behind localized lettering is treated as overlap/residue and is also FAIL.
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


## Zero-tolerance pixel boundary gate

Effective 2026-09-28:

- The allowed overflow is **0 pixels**. If any Korean glyph/text pixel extends even **1 pixel** outside the original source text region or sprite cell, classify the asset as **REWORK_REQUIRED**.
- A candidate bbox must be a subset of the exact original source glyph/effect bbox on all four sides. In addition, localized bbox width and height must each be less than or equal to the exact source text bbox width and height. **Any 1-pixel growth in width or height is FAIL**, even if a surrounding plate/cell has unused room.
- `changed_pixels_outside_source_region` must be `0` and `introduced_alpha_outside_source_region` must be `0`.
- A zero-margin edge touch is not an automatic failure, but must be recorded as a high-risk condition and checked at high zoom and in game. Any clipping or escape fails the gate.
- For DXT5/BC3 assets, 4x4 block confinement alone is not sufficient for final approval when exact decoded-pixel evidence is unavailable. Keep such evidence on hold/recheck; never infer PASS from compression-block containment alone.
- Missing or ambiguous source-region evidence is **HOLD_STRICT_RECHECK**, not PASS.
- Static containment PASS does not override the mandatory isolated `DDS_ONLY` in-game validation gate.
- Canonical audit record: `localization/graphics/FULL_PIXEL_BOUNDARY_AUDIT_20260928.json`.


## Production extension: plate-only + composition-only protection (2026-10-08)

The mandatory production **10-stage** and retained original **eight ordered**
checks are specified in `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md`.
They apply per sprite and do **not** change the RAW orientation rules below.

- Review exact-source **SOURCE vs CLEAN** with Korean hidden. An English
  outline/glow ghost, donor patch, alpha edge or rectangular erasure trace
  invalidates the plate, regardless of later text coverage.
- Composite only transparent Hangul glyph/effect alpha onto approved CLEAN.
  Review **CLEAN vs FINAL** independently and reject any visible foreign box,
  patch intrusion or rectangular composite seam. Ordinary editing selection
  boxes are allowed if they leave no unintended pixels.
- Review persisted decoded DDS at RAW/readable native and practical/mip sizes.
  Source-size bbox, 1px protected overlap, per-sprite transform and no
  source residue continue to be absolute gates.
- Record the five distinct plate/composition failure codes defined by the
  quality pipeline. A/B must not claim producer PASS for an identified visual
  defect or hand that failed candidate to C as a success.

## Recovery quality pipeline: clean plate before lettering

This section imports image-quality techniques without importing later controller/automation machinery. It applies to newly produced or materially reworked localized graphics.

### 1. Glyph-footprint removal, not rectangle erasure
- Build the removal mask from the complete source glyph/effect footprint: fill, outline, shadow, glow and antialias fringe.
- Never erase a whole OCR/text rectangle merely because text was detected there.
- Keep sprite borders, panel borders, separator lines, icons, logos, preserve-original labels and neighboring cells in an explicit protected mask.
- Mask dilation may include source antialias/shadow/glow residue, but must be clipped by protected artwork.

### 2. Background-aware reconstruction
Before removing source text, classify the underlying background:
- flat/near-flat -> reconstruct from verified neighboring source pixels;
- smooth gradient -> reconstruct a continuous source-faithful gradient;
- patterned/textured/artwork -> use source-constrained reconstruction/inpainting or faithful redraw;
- transparent/semitransparent -> reconstruct RGB and alpha together; never insert an opaque backing.

Perform removal/reconstruction at the exact HD source resolution. Downscale/inpaint/upscale is forbidden for final artwork.

### 3. Mandatory clean-plate gate
For every translated image element use:

`EXACT_HD_SOURCE -> SOURCE_TEXT_MASK -> PROTECTED_MASK -> CLEAN_PLATE -> KOREAN_LETTERING -> DDS_CANDIDATE`

Retain the source mask, protected mask, clean plate and final candidate as separate QA evidence.

Do not place Korean lettering until the clean plate has:
- no source-script/old-Korean residue;
- no rectangular patch, seam or erasure halo;
- no damaged border, icon, logo or unrelated artwork;
- no gradient/texture discontinuity;
- no unintended alpha discontinuity.

### 4. Fit and font gate before pixels are committed
- Verify that the selected font contains every required Hangul/symbol glyph; tofu/fallback mixing is FAIL.
- Measure source typography height, scale, alignment and effects first.
- Measure multi-line source styling per line. Equal source-line styles require equal Korean-line font/weight/fill/outline/shadow/slant/scale; intentional source-line differences must be mapped to the corresponding Korean lines.
- Treat the exact source glyph/effect bbox as the maximum render dimensions, not the plate or sprite-cell bounds.
- Measure the Korean glyph/effect footprint before final rendering.
- If it does not fit, try source-faithful spacing/line break, then smaller source-faithful size, then an approved shorter translation.
- Do not distort glyphs or add generic outline/shadow/glow merely to make text readable.
- If source-faithful quality cannot be achieved automatically, mark `MANUAL_RECONSTRUCTION_REQUIRED`.

### 5. Two-stage validation
Validate twice:
1. CLEAN_PLATE vs exact source — removal/reconstruction defects only.
2. FINAL KOREAN CANDIDATE vs exact source — containment, overlap, clipping, residue, protected-artwork changes, alpha and DDS properties.

For multi-element atlases, translated masks must not newly overlap each other or protected artwork.

### 6. Fail closed
Ambiguous detection, masks, reconstruction, orientation, font coverage or fit never becomes an automatic PASS. Preserve the exact source and use `HOLD_STRICT_RECHECK` or `MANUAL_RECONSTRUCTION_REQUIRED`.

### 7. Evidence and runtime separation
Record source identity/hash and static QA evidence for new/reworked candidates. Upscaled previews are human-inspection aids only; pixel decisions use exact decoded source resolution.

Static validation does not claim an in-game pass. Until the game was actually tested, record `RUNTIME_VALIDATION=UNTESTED`.

Tool support:
- `tools/localization/validate_clean_plate.py` checks changes against allowed/protected masks and fails closed.
- `tools/localization/render_artwork.py` is proof-overlay only and must never be treated as a final DDS renderer.
