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

## Production visual QA gate

The following visual gates apply to **every newly produced or materially reworked Korean graphics asset**, not only to items already reported by an in-game screenshot.

A producer self-QA PASS requires all of the following:
- **Native-resolution source only:** never upscale a previous Korean bitmap or low-resolution localized font to create the final candidate. Mixed low-resolution/high-resolution Korean lettering in one UI family is FAIL.
- **No broken glyphs:** jagged, garbled, clipped, malformed, inconsistent-antialias or visibly damaged Hangul is FAIL.
- **No source residue or double drawing:** any visible English/source-script remnant behind or beside Korean, duplicate English/Korean layer, ghost silhouette, or source-shaped effect residue is FAIL.
- **No foreign-image intrusion:** Korean text/effects may not overwrite, cover, borrow from, or visually intrude into icons, cards, portraits, photos, logos, decorative foreground, neighboring atlas content or other UI images.
- **No layer collision:** text-to-text, text-to-icon, text-to-frame, text-to-number or text-to-image collision/touch is FAIL unless the exact source intentionally overlaps the same elements.
- **Source transform fidelity:** slant/italic angle, perspective/shear, baseline, alignment, relative scale, line spacing and rotation must follow the corresponding source. A visibly wrong tilt or perspective is FAIL even when bbox containment passes.
- **Readable-orientation slant direction gate:** compare the *direction* of the source and localized lean at readable orientation, not merely the absolute shear magnitude or a variable named `slant`/`shear`. A source right-italic row rendered left-leaning is FAIL. For Pillow/PIL affine transforms, remember that the matrix maps output coordinates back to input coordinates; do not infer visual direction from the sign by name. Evidence must include a high-zoom SOURCE/FINAL comparison where top-vs-bottom horizontal displacement can be visually verified.
- **Glyph-integrity gate after transform:** affine/perspective work must be performed from native-resolution glyphs with sufficient padding, then cropped from alpha. Any transform that clips the source canvas, truncates a Hangul stroke, produces staircase/broken edges, or relies on a transform-induced crop to satisfy a bbox is FAIL.
- **Clean-plate visual residue gate:** a zero numeric source-residue count is insufficient when the comparison still shows source-shaped dark/light silhouettes, rectangular luminance patches, donor boundaries or badge/text shadows. SOURCE/CLEAN/FINAL high-zoom visual inspection overrides the numeric gate.
- **Source style fidelity:** font weight/proportion, fill/gradient, outline, shadow/glow, edge softness and antialiasing must remain source-family consistent. A Korean label that visibly looks pasted-on or belongs to a different resolution/style family is FAIL.
- **Clean-plate integrity first:** lettering must never be used to hide a bad clean plate. Patch rectangles, donor boundaries, seams, smears, luminance blocks, halos and damaged background/artwork are FAIL.
- **Family consistency:** labels that share one source UI family must use consistent Korean rendering rules unless the source itself intentionally differs. One low-resolution or differently weighted member in an otherwise high-resolution family is FAIL.
- **Readable-orientation visual review is mandatory:** inspect SOURCE/CLEAN/FINAL at normal readable orientation and high zoom in addition to machine masks/bboxes. Numeric PASS alone is insufficient.
- **Raw/orientation review is mandatory:** verify the actual DDS raw/game orientation so mirrored/rotated atlas content is not accidentally approved.
- **Runtime presentation remains a separate gate:** when a produced asset has not yet been seen in-game, record `RUNTIME_VALIDATION=UNTESTED` or `*_PASS_PENDING_INGAME_RETEST`; never infer in-game correctness from static QA.

If any item above fails, the producer must keep the item as `REWORK_REQUIRED` (or `MANUAL_RECONSTRUCTION_REQUIRED` where appropriate) and repair it before handing it to C. A/B must not mark a candidate producer-PASS merely because pixel containment/protected-mask checks are zero.

## In-game regression QA

Actual in-game screenshots are a higher-level visual gate than static mask/bbox checks. If a user screenshot shows a concrete defect, reopen the affected asset/runtime path even when earlier static QA passed.

Hard in-game failures include:
- visibly mixed low-resolution/upscaled Korean fonts;
- broken glyphs, jagged/garbled lettering or inconsistent antialiasing;
- source English residue or duplicate English/Korean layers;
- text-to-text overlap, text-to-icon/art intrusion, or other-image intrusion;
- wrong slant, perspective, baseline, alignment, relative scale, line spacing or source-style transform;
- clean-plate seams, donor boundaries, ghost silhouettes or residual source-shaped effects;
- HUD text that becomes unreadable against normal game backgrounds because weight/outline/effect does not match the source family.

For a screenshot-confirmed failure:
1. record/reuse the row in `localization/graphics/INGAME_REWORK_BACKLOG.csv`;
2. map the exact DDS atlas cell and/or runtime text ID/draw path before modifying files;
3. re-render raster text from exact native-resolution/HD source; never upscale an old Korean bitmap;
4. preserve protected artwork and source transform;
5. run normal static QA again;
6. keep the result as `*_PASS_PENDING_INGAME_RETEST` until a newer actual game screenshot confirms the defect is gone.

Static numeric PASS does not overrule visible in-game residue, overlap, low-resolution mismatch, or transform/style defects. Record such cases as numeric false negatives and repair them.

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

## Pre-in-game consolidated English-original comparison JPG review

After independent C static QA passes a graphics candidate, but before actual game testing, export the current C-pass set to localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/.

The export is a human visual gate: numbered JPGs, queue-index ordering, a machine-readable manifest, and English original vs current Korean candidate shown side-by-side. Each localized candidate must include both FLIP-Y review and RAW DDS comparisons using the same decoded dimensions. The manifest must pin and hash the canonical English source; missing/ambiguous source or a source/candidate size mismatch is FAIL/HOLD, not a review pass.

C must refresh this comparison set whenever C-PASS membership or candidate bytes change. tools/localization/export_c_pass_comparison.py is the persistent exporter and the C hosted-worker path must invoke it when a refresh is required. User-observed visual defects in this set are hard failures even when C numeric/static checks passed; the asset must return to A/B rework and receive a newer C pass before in-game validation. Reopened/pending-C assets must disappear from the current export. Preserve-original policy passes with no candidate remain numbered comparisons whose right side explicitly states that the original is intentionally preserved.
