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
- side-by-side static visual comparison against the exact English HD source completed.
- no untranslated English residue remains in any region classified for translation.
- Korean glyphs, outlines, shadows and effects do not clip, escape the original text region, or intrude into icons/artwork.
- in-game screenshot validation is deferred to the user's final integrated test and is NOT a production/static-QA completion gate.

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


## Zero-tolerance pixel boundary gate

Effective 2026-09-28:

- The allowed overflow is **0 pixels**. If any Korean glyph/text pixel extends even **1 pixel** outside the original source text region or sprite cell, classify the asset as **REWORK_REQUIRED**.
- A candidate bbox must be a subset of the original source bbox/cell on all four sides. Width/height growth is allowed only when the result still remains fully contained in the original source region.
- `changed_pixels_outside_source_region` must be `0` and `introduced_alpha_outside_source_region` must be `0`.
- A zero-margin edge touch is not an automatic failure, but must be recorded as a high-risk condition and checked at high zoom in the English-source vs Korean-candidate comparison. Any clipping or escape fails the static gate.
- For DXT5/BC3 assets, 4x4 block confinement alone is not sufficient for final approval when exact decoded-pixel evidence is unavailable. Keep such evidence on hold/recheck; never infer PASS from compression-block containment alone.
- Missing or ambiguous source-region evidence is **HOLD_STRICT_RECHECK**, not PASS.
- Production/static QA does not require isolated `DDS_ONLY` in-game validation. Runtime validation is deferred to the user's final integrated test; until user evidence exists, record `RUNTIME_VALIDATION=UNTESTED` and never claim runtime success.
- Canonical audit record: `localization/graphics/FULL_PIXEL_BOUNDARY_AUDIT_20260928.json`.


## Mandatory English-source side-by-side visual QA

Effective 2026-09-29:

- Every newly created or materially reworked Korean DDS MUST have a comparison proof using the exact English HD source DDS as the left/reference image and the current Korean candidate as the right image.
- Use identical crop coordinates, orientation, zoom and scale for both sides. Label them clearly `ENGLISH SOURCE` and `KOREAN CANDIDATE`.
- Do not use an older Korean candidate as the left-side baseline. Before/after-Korean-only comparisons may be supplementary evidence but never replace the English-source comparison.
- Inspect the full atlas and every translated sprite at readable zoom. Any untranslated English residue in a region classified for translation is `REWORK_REQUIRED`.
- Any clipped Korean glyph/effect, pixel outside the permitted source text region, overlap with an icon/artwork/neighbor sprite, or accidental modification of preserved artwork is `REWORK_REQUIRED`.
- Comparison proof PNGs must be retained with lane QA evidence so the user can visually review the same source-vs-candidate pair.
- In-game testing is intentionally deferred during production. The user will perform the final integrated game test and return screenshots/files for defects. Such later runtime defects become rework inputs; until then use `RUNTIME_VALIDATION=UNTESTED`.

## Generation reset and zero-artifact reconstruction contract

Effective 2026-09-29 after user visual QA:

### Generation reset

- All previously generated Korean graphics candidates are **SUPERSEDED / NOT REUSABLE AS ARTWORK**. They may remain only as historical failure/QA evidence.
- No pixel, cleaned background, glyph, mask, patch, crop, or composited region from an older Korean candidate may be used as construction input.
- Every localized graphic must restart from the exact English HD source DDS. Stock original may be used only when the HD source has no corresponding asset and that fallback is explicitly recorded.
- Existing PASS/DONE/static-pass labels from pre-reset candidates do not grant approval. New-generation assets must pass this contract from scratch.

### No-overlay / no-box rule

- Never place Korean text on top of visible English text.
- Never hide English using a black/white/solid/semitransparent rectangle, badge, strip, blur, flood fill, or arbitrary opaque patch.
- Never introduce a rectangular background that is absent from the exact English source, even if it makes Korean easier to read.
- The localized result must preserve the original background/artwork continuously through the former English glyph area.
- Any visible English stroke, shadow, outline, antialias fringe, glow, underline, or previous-letter silhouette is an automatic **REWORK_REQUIRED**.
- Any new box, seam, flat-color patch, halo, edge, mismatched gradient, or transparency discontinuity is an automatic **REWORK_REQUIRED**.

### Reconstruct-before-typeset rule

For each translatable text element:

1. Start from the exact English HD source.
2. Identify the complete English glyph footprint including outline, shadow, glow, antialiasing and effects.
3. Reconstruct the background under that complete footprint so it visually continues the surrounding original artwork.
4. Only after the English text and all effects are fully removed may Korean be rendered.
5. Render Korean within the original permitted sprite/text region, reproducing the source orientation and source-faithful typography/effects.
6. Composite only the minimum required text/effect pixels. Preserve all unrelated source pixels bit-for-bit whenever technically possible.
7. Produce full-atlas and per-sprite ENGLISH SOURCE vs KOREAN CANDIDATE proof images.

### Redraw-if-clean-removal-is-not-possible rule

- If the original background cannot be cleanly recovered by deterministic pixel reconstruction, do **not** cover the defect.
- Redraw/reconstruct the affected background or UI element from the exact source's surrounding visual language before adding Korean.
- A redraw must match the source geometry, gradient, border, texture, transparency and neighboring pixels; it must not invent a replacement panel style.
- If faithful reconstruction is not achievable automatically, stop the asset as **MANUAL_RECONSTRUCTION_REQUIRED**. Do not emit a compromised candidate.

### Hard automatic rejection gates

A candidate cannot be retained when any of the following is true:

- source width or height differs;
- DDS format/compression/mipmap/alpha behavior differs without an explicitly documented source-required reason;
- any translated pixel escapes its permitted source region by >= 1 pixel;
- any Korean glyph/effect is clipped;
- any translatable English residue remains;
- any old Korean-candidate residue is present;
- any solid/opaque/semitransparent cover box or artificial backing panel was introduced;
- preserved artwork outside the approved edit mask changed;
- background reconstruction leaves seams, halos, flat patches, mismatched gradients or transparency discontinuities;
- another glyph/icon/sprite was erased, shifted, covered or contaminated;
- raw DDS orientation differs from the corresponding source element;
- readable/game-orientation preview reveals an artifact not obvious in raw orientation.

A failure of any single gate is **REWORK_REQUIRED**, never PASS-with-warning.

### Mandatory clean-generation evidence

Every new candidate must record:

- exact source path + SHA-256;
- candidate SHA-256;
- source/candidate dimensions, DDS format and mip count;
- per-element edit mask/ROI;
- changed-pixel count inside ROI;
- changed-pixel count outside ROI (must be 0 except explicitly enumerated source-faithful reconstruction pixels belonging to the same element);
- introduced alpha outside ROI (must be 0);
- English-residue inspection result;
- box/seam/artifact inspection result;
- full-atlas ENGLISH SOURCE vs KOREAN CANDIDATE comparison;
- enlarged comparison for every translated element;
- raw-orientation and readable-orientation inspection result;
- RUNTIME_VALIDATION=UNTESTED until actual user in-game evidence exists.

### Promotion rule

Only candidates created after this reset and passing every clean-generation gate may enter the active HD candidate set. Historical candidates must never be copied forward merely because their dimensions/header/containment checks pass.

## Imported open-source image-localization safeguards

Effective 2026-09-29. These safeguards adapt useful practices observed in open-source image/game localization pipelines to OutRun's DDS/atlas constraints. OutRun's exact HD source, raw sprite transforms, DDS properties and zero-pixel containment remain authoritative.

### Glyph-footprint removal, never rectangle erasure

- Build the removal mask from the complete source glyph/effect footprint, not from the OCR/text bounding rectangle.
- The mask must include source glyph fill, outline, shadow, glow and antialias fringe, but must exclude surrounding borders, icons and unrelated artwork.
- Never erase/fill an entire OCR rectangle merely because text was detected there.
- Protect sprite borders, panel borders, separator lines, icons and neighboring glyphs as explicit no-edit masks.

### Background-class reconstruction

Classify the pixels beneath/around each source text element before removal:

- flat/near-flat background -> reconstruct from verified neighboring source pixels;
- smooth gradient -> reconstruct a continuous gradient from source-side samples;
- patterned/textured/artwork background -> use source-constrained reconstruction/inpainting or faithful redraw;
- transparent/semitransparent artwork -> reconstruct RGB and alpha together; never synthesize an opaque backing.

After reconstruction, re-inspect the cleaned region before Korean lettering. If the cleaned region still contains source-letter traces or a visible seam, do not proceed to lettering.

### Clean-plate intermediate gate

Every translated element must have a clean-plate intermediate state:

`EXACT_HD_SOURCE -> SOURCE_TEXT_MASK -> CLEAN_PLATE -> KOREAN_LETTERING -> DDS_CANDIDATE`

The CLEAN_PLATE must be retained as QA evidence. Korean lettering is forbidden until the clean plate passes:
- no English/source-script residue;
- no old Korean residue;
- no rectangular patch/box;
- no damaged border/icon/artwork;
- no gradient/texture discontinuity;
- no alpha discontinuity.

### Fit-before-render gate

- Measure the target Korean glyphs with the actual selected font/effects before committing pixels.
- Compare the rendered glyph/effect mask to the permitted sprite/text region.
- If it does not fit, retry in this order: tighter source-faithful tracking/line break -> smaller source-faithful font size -> approved shorter translation.
- Never horizontally/vertically distort glyphs beyond a source-faithful range merely to force a fit.
- If legibility or style would be lost before it fits, stop as `MANUAL_RECONSTRUCTION_REQUIRED`; do not render a bad candidate.

### Font coverage gate

Before rendering, verify that the chosen font contains every required Hangul/symbol glyph. Missing glyph boxes, fallback-font mixing, tofu, or silently substituted glyphs are automatic rejection.

### Post-clean and post-letter validation

Run validation twice:
1. on CLEAN_PLATE, before Korean text exists;
2. on final KOREAN_CANDIDATE.

The clean-plate validation detects removal/reconstruction defects independently from lettering defects. Final validation checks containment, overlap, clipping, source-script residue, protected-artwork changes, alpha and DDS properties.

### Pairwise overlap gate

For atlases containing multiple translated elements, compare all translated masks pairwise. Any overlap not present in the source layout is `REWORK_REQUIRED`. Also reject overlap with protected masks for icons, borders, neighboring sprites and preserve-original text.

### Fail-safe generation rule

When detection, removal, reconstruction, orientation, font coverage, fitting or validation is ambiguous, preserve the exact source and flag the element instead of emitting a guessed localized candidate. Automatic production must fail closed, not fail open.

### Immutable-source and candidate-lineage rule

- Keep exact source artifacts immutable and hash them.
- Write every newly generated candidate as a new generation with explicit source SHA-256 and generation ID.
- Record offline/static validation separately from runtime validation.
- A generated file is never equivalent to a completed/approved asset.

