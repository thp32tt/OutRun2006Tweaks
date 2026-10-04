# Korean Localization Quality Pipeline

This document is a quality-only layer for `korean-localization-recovery-20260928`. It intentionally does not define controller scheduling, retries, rollovers, task IDs or orchestration.

## Required construction flow

For every newly localized or materially reworked graphics element:

`EXACT_HD_SOURCE -> SOURCE_TEXT_MASK -> PROTECTED_MASK -> CLEAN_PLATE -> KOREAN_LETTERING -> DDS_CANDIDATE -> STATIC_QA`

### Exact source
Use the exact HD source when available. Preserve dimensions, compression/format, alpha, mip behavior and raw per-sprite orientation. Do not create a final asset by upscaling an old Korean texture.

### Source-text mask
Mask the actual source glyph/effect footprint, including fill, outline, shadow/glow and antialias fringe. OCR rectangles are discovery hints only; rectangular erasure is not an acceptable reconstruction method.

### Protected mask
Explicitly protect borders, separators, icons, logos, neighboring cells, preserve-original labels and unrelated artwork. Any changed pixel in protected regions is a failure.

### Clean plate
Reconstruct the background before adding Korean text. Reconstruction must match the source background class: flat, gradient, textured/artwork, or transparent/semitransparent.

The clean plate must pass visual/static checks before lettering:
- no source text residue;
- no patch box or seam;
- no damaged unrelated artwork;
- no texture/gradient discontinuity;
- no unintended alpha discontinuity.

### Korean lettering
Measure source typography and target Korean glyphs before final rendering. Verify font coverage. Reproduce only effects that exist in the source. Fit without crossing the original permitted region.

Apply `localization/graphics/TRANSLATION_NAMING_POLICY.md` before rasterization: stage names use canonical phonetic transliteration, while song titles/music credits remain untouched original English artwork.

The exact source glyph/effect bbox is a hard size ceiling. The localized bbox must be contained and must satisfy `localized_width <= source_width` and `localized_height <= source_height`; a 1-pixel growth in either dimension is FAIL even when the larger sprite cell or empty plate has room. For multi-line labels, compare both the complete text block and each reliably separable corresponding line.

Measure source style per line: fill/gradient, weight, outline, shadow/glow, slant, baseline, alignment, line spacing and relative scale. If source lines share a style, Korean lines must share it too. If source lines intentionally differ, preserve those corresponding differences. Source-unjustified style differences between Korean lines are FAIL.

If a source-faithful result cannot be produced safely, stop as `MANUAL_RECONSTRUCTION_REQUIRED` rather than generating a weak candidate.

## QA

Run two independent gates:

1. **Clean-plate QA**: exact source vs clean plate.
2. **Final-candidate QA**: exact source vs localized candidate.

Final QA includes:
- zero-pixel containment;
- protected-mask integrity;
- alpha integrity;
- no clipping or new overlap;
- zero localized-text overlap: 0 pixels against every other localized label and against preserved source text/icon/decorative/protected foreground; source-script residue behind a localized glyph is also FAIL;
- no source-text residue;
- orientation correctness;
- style fidelity, including per-line multi-line consistency against the corresponding source lines;
- exact source-size ceiling (`localized_width <= source_width` and `localized_height <= source_height`, with 1-pixel growth = FAIL);
- canonical stage-name transliteration;
- byte/pixel preservation of song titles and music credits;
- DDS dimensions/format/mips preservation.

Use `tools/localization/validate_clean_plate.py` where decoded RGBA source/candidate/masks are available.

`tools/localization/render_artwork.py` is proof-only. Its transparent lettering output is never a deployable localized DDS by itself.

## Evidence

For newly produced or materially reworked assets retain enough evidence to reproduce the decision:
- exact source identity/hash;
- source-text mask;
- protected mask when relevant;
- clean plate;
- final candidate/comparison;
- machine-readable QA report.

This does not require reopening every historical approved asset. Existing assets are revisited when they are modified or when a concrete QA defect is discovered.

## Runtime

Static QA and in-game validation are distinct. Never infer runtime success from image checks. Use `RUNTIME_VALIDATION=UNTESTED` until actual game evidence exists.

## Automation boundary

Quality rules live here and in graphics QA tooling. They must not be copied into controller scheduling/state code. Do not add Production/Event ID layers, queue schemas, rollover state machines or C0-C6 orchestration merely to enforce this document.
