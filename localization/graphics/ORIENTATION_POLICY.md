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

## Additional safeguards from further open-source pipeline review

Effective 2026-09-29:

- **Mask dilation is source-effect aware:** the removal mask must expand enough to include antialias/shadow/glow residue, but expansion is clipped by protected artwork masks. Blind rectangular dilation is forbidden.
- **High-resolution removal:** perform source-text removal/reconstruction at the exact HD source resolution. Do not downscale for inpainting and upscale the result back into the DDS.
- **Intermediate preservation:** retain source mask, protected mask, clean plate and final lettering as separate QA artifacts. A flattened final image alone is insufficient evidence.
- **Typography measurement:** estimate source text height/scale/alignment first; Korean font sizing begins from measured source typography rather than an arbitrary maximum box size.
- **Confidence/fail-closed threshold:** uncertain text detection, ambiguous masks, uncertain reconstruction or missing glyph coverage must stop automatic promotion rather than guessing.
- **Two-stage residue detection:** scan once immediately after source-text removal and again after final Korean lettering. The first scan must not be confused by Korean glyphs.
- **Protected-boundary masks:** panel outlines, sprite boundaries, separators, icons, logos, preserve-original labels and neighboring cells are protected masks. Any changed pixel inside a protected mask fails.
- **No generic readability effects:** do not add a white/black stroke, shadow, backing, glow or border merely for legibility. Effects are reproduced only when present in the exact source element.
- **No artificial upscaling as evidence:** upscaled views may be used for human inspection only; containment and artifact decisions are made against exact decoded source-resolution pixels.
- **Retry limit:** automatic reconstruction may retry with alternate source-constrained methods, but repeated failure ends in `MANUAL_RECONSTRUCTION_REQUIRED` rather than progressively destructive edits.

Tool enforcement:
- `tools/localization/render_artwork.py` is PROOF-ONLY and requires explicit acknowledgement; its transparent lettering output is forbidden as final DDS artwork.
- `tools/localization/validate_clean_plate.py` provides a fail-closed source/candidate edit-mask gate and rejects changed pixels outside the permitted edit mask, protected-mask changes and alpha changes outside the permitted mask.

## Broad-source automated-development safeguards

Effective 2026-09-29 after additional review of open-source scene-text translation, inpainting, visual-regression and DDS texture workflows.

### Detection geometry is not an edit mask

- OCR/text detector rectangles are localization hints only. They must never be used directly as erase/fill rectangles.
- Derive a pixel-level glyph/effect mask inside the detected region.
- Track detection confidence separately from mask confidence. Low confidence in either blocks automatic promotion.
- When text is rotated/mirrored in raw DDS, perform mask derivation in a normalized temporary view but map the exact mask back to the original raw transform before editing.

### Bounded mask dilation

- Expand glyph masks only enough to include source antialias, outline, shadow and glow residue.
- Dilation radius must be recorded per element and clipped by protected masks/cell boundaries.
- If residue requires dilation that would touch protected artwork, automatic removal stops; do not sacrifice artwork to erase text.

### Exact-resolution reconstruction

- Detection may use temporary scaled views, but reconstruction and final compositing occur at exact source DDS resolution.
- Neural/upscaled/inpainted intermediate images are never accepted as final pixels merely because they look clean at preview scale.
- Any reconstruction method must be constrained to the approved mask and validated at native resolution.

### Source-style measurement before lettering

Record before Korean rendering:
- source text/effect bbox;
- baseline/center/alignment;
- approximate cap/text height;
- foreground/effect colors sampled from source;
- outline/shadow direction and extent;
- line spacing and inter-line alignment;
- raw orientation.

Do not apply generic renderer defaults when source measurements are available.

### Compression round-trip QA

For BC/DXT/compressed candidates:
1. construct and validate the uncompressed working image;
2. encode to the exact required DDS compression/mipmap policy;
3. decode the produced DDS again;
4. run containment, protected-mask, alpha, residue and visual checks on the **decoded final DDS**, not only on the pre-compression PNG;
5. compare DDS metadata against the exact source.

Compression artifacts that create visible residue, alpha damage, edge contamination or protected-region changes are `REWORK_REQUIRED`.

### Multi-scale visual regression

Human QA evidence must include:
- full atlas at native aspect;
- native-resolution translated-region crop;
- nearest-neighbor enlarged crop for pixel-edge inspection;
- source/candidate/diff view;
- alpha-channel comparison when alpha is used.

Smooth/bilinear preview scaling must not be used as the sole evidence for 1-pixel decisions.

### Candidate determinism and provenance

Each automatic candidate records:
- generator/tool version or commit;
- generation rule version;
- exact source SHA-256;
- translation/spec identifier;
- mask/protected-mask hashes when retained;
- font identifier (not redistributed font bytes);
- deterministic parameters affecting layout/reconstruction;
- candidate SHA-256.

Regenerating with identical inputs should produce identical pre-compression pixels where the method is deterministic. Nondeterministic reconstruction must record its method/seed or be treated as manual-review evidence.

### Fail-closed CI semantics

A changed DDS is not accepted merely because a QA JSON exists. Automation must parse machine-readable QA and require:
- a PASS-class status;
- zero changed pixels outside permitted source/edit region;
- zero changed pixels in protected masks;
- zero introduced/changed alpha outside the permitted region;
- post-compression decoded-final validation for compressed DDS where applicable.

A missing metric is not assumed to be zero; missing mandatory post-reset evidence blocks promotion.

## First-pass image-generation prompt contract

Effective 2026-09-29. The goal is to prevent defects during generation, not to depend on QA to repair them later.

Every image-generation/reconstruction request must be assembled from this contract plus asset-specific measured facts. Free-form prompts that merely say "translate this image to Korean" are forbidden.

### Prompt priority

The generator must understand the task in this order:

1. **EDIT, DO NOT REDESIGN.** The exact supplied HD source is authoritative.
2. Preserve every pixel/shape outside the explicitly identified source-text/effect footprint.
3. Remove the complete specified English/source text and its own outline/shadow/glow only.
4. Reconstruct the exposed background so it is a seamless continuation of the exact surrounding source.
5. Render only the supplied approved Korean wording in the cleared region.
6. Match the measured source typography/layout/effects as closely as Korean glyph geometry permits.
7. If faithful reconstruction or fitting is uncertain, return no production candidate and flag manual reconstruction.

### Mandatory positive instructions

Each asset prompt must explicitly state:
- exact source image dimensions and raw orientation;
- exact text element(s) to replace;
- exact approved Korean string for each element;
- measured source bbox and permitted edit region;
- protected regions/elements that must remain unchanged;
- source alignment, baseline/center, approximate text height and line count;
- sampled source text/effect colors;
- outline/shadow/glow direction and extent when present;
- alpha/transparency behavior;
- whether background under the text is flat, gradient, patterned, illustrated or transparent;
- required output dimensions and alpha behavior;
- "the result must look as though the Korean text was part of the original game artwork, not pasted on later."

### Mandatory negative instructions

Every generation prompt must explicitly forbid:
- Korean text drawn over visible English;
- black, white, gray, colored or semitransparent cover rectangles;
- new panels, labels, plaques, ribbons, boxes or backing shapes;
- blur/smudge patches used to conceal source text;
- visible English/source glyph fragments, shadows, outlines, glow or antialias residue;
- modification of icons, logos, borders, separators, neighboring sprites or unrelated text;
- redesigning, restyling, recoloring or re-composing the UI;
- replacing the original background with a newly invented background;
- cropping, padding, resizing or changing aspect ratio;
- arbitrary font fallback, missing-glyph boxes or mixed fallback fonts;
- adding outlines/shadows/glows that are absent from the source;
- generic "improved readability" effects;
- low-resolution reconstruction followed by upscale;
- changing alpha outside the permitted edit mask;
- hallucinating additional Korean/English words, punctuation, icons or decoration.

### Background-specific generation instruction

The prompt must name the reconstruction strategy:
- flat background: continue exact neighboring color/texture;
- gradient: continue gradient direction, stops and local luminance without a seam;
- pattern/artwork: reconstruct only masked source-text pixels from surrounding/source structure;
- transparent/semitransparent: preserve alpha structure and reconstruct RGB+alpha together;
- complex unrecoverable art: redraw only the affected element from source evidence, never invent a covering panel.

### Typography-first fitting instruction

Before committing Korean lettering, the generation step must conceptually fit the approved string inside the measured permitted region. Prefer:
1. source-faithful tracking/spacing;
2. source-faithful line breaking;
3. modest font-size reduction;
4. approved shorter translation.

Never solve fit by stretching/squashing glyphs, clipping, escaping the source region, covering neighboring art, or adding a new background.

### Single-pass self-check instruction

The final paragraph of every generation prompt must require an internal pre-output check:

"Before producing the candidate, verify that no source-language text or effect remains; no cover box, patch, seam or invented panel exists; all protected artwork is unchanged; Korean text is fully inside the permitted region and unclipped; canvas, orientation and transparency are unchanged. If any condition cannot be satisfied, do not produce a production candidate."

### Prompt provenance

The exact final prompt text (or structured prompt JSON) used for each production candidate must be saved with the QA artifacts and hashed. This makes prompt regressions auditable and allows a successful first-pass recipe to be reused for visually equivalent source families.

## Mandatory orientation and source-letterform generation gate

Effective 2026-09-29 after first post-reset sample review. Orientation and letterform style are generation inputs, not optional visual-QA observations.

### Orientation must be proven from source pixels

- Never trust filename conventions, historical notes, previous candidates, or a transcription note such as `raw normal` by itself. When exact-source pixel inspection contradicts metadata/notes, exact-source pixels win and the stale orientation record must be corrected before production.
- Before generation, inspect the exact HD source DDS in raw pixel order and in the game's expected display transform when known.
- Record a discrete `source_text_transform`: `normal`, `flip_x`, `flip_y`, `rotate_180`, `rotate_90_cw`, `rotate_90_ccw`, or an explicitly documented composition.
- Record the observed source reading direction and baseline vector in raw coordinates.
- The Korean candidate must use the **same raw-coordinate transform/baseline direction** as the source element. Do not render upright first and assume the DDS/game will fix it.
- If source orientation cannot be proven, generation is blocked as `ORIENTATION_UNRESOLVED`.

### Orientation preflight before expensive generation

Before background reconstruction or Korean rendering:
1. derive/confirm source text transform from exact HD source;
2. map source bbox, permitted region and protected masks into the same raw coordinate system;
3. generate a temporary orientation proof containing only geometry/baseline markers, not production artwork;
4. verify that the proof follows the same source baseline direction;
5. only then allow clean-plate/Korean generation.

A candidate produced without this preflight is not promotable.

### Orientation postflight

After candidate generation and after DDS round-trip decode:
- compare candidate text baseline/direction to recorded source transform;
- verify edit mask and candidate lettering were not accidentally flipped relative to one another;
- verify raw DDS view and intended display view separately;
- any mismatch is `REWORK_REQUIRED`, even when containment is 0px-clean.

### Source-letterform style is a hard generation input

Before rendering, record source visual traits:
- slant/italic angle or direction;
- condensed/normal/expanded width character;
- stroke weight;
- corner character (square, rounded, beveled);
- outline count, thickness and colors;
- shadow direction, distance, hardness and opacity;
- highlight/bevel/glow treatment;
- source text height and width occupancy;
- tracking and punctuation treatment.

The prompt must tell the generator to reproduce these traits for Korean as closely as Hangul geometry permits. A generic Korean system font is not acceptable merely because it fits.

### Style-fit hierarchy

Prefer:
1. a Korean-capable font with source-like slant/width/weight;
2. deterministic affine slant/width adjustment within measured source proportions;
3. source-faithful outline/shadow/effect construction;
4. custom/redrawn Korean lettering when no font can match adequately.

Do not accept a visibly upright, rounded, overly bold/thin or otherwise generic Korean word when the English source is distinctly angled, condensed, outlined or arcade-styled.

### First-pass rejection conditions

The generation step must reject its own candidate before DDS output when:
- text transform differs from the source;
- reading/baseline direction differs;
- source is slanted but Korean is visibly upright, or vice versa;
- width/weight/corner character is materially inconsistent;
- outline/shadow hierarchy is materially inconsistent;
- punctuation orientation/placement is inconsistent;
- the only way to fit is to violate source style or permitted geometry.

These checks are required even if pixel containment, alpha and protected-mask metrics are otherwise perfect.

## Signed slant and GitHub visual-review artifact contract

Effective 2026-09-29 after the second post-reset sample review.

### Slant direction is signed geometry

A description such as `italic`, `slanted` or `right-leaning` is not sufficient for production generation.

For every stylized source text element, measure and record in the **display/readable coordinate system**:
- `slant_dx_per_dy`: signed horizontal displacement of the top edge relative to the bottom edge per positive glyph height;
- `slant_angle_deg`: signed angle derived from that displacement;
- `slant_direction`: `left`, `none`, or `right`;
- the exact transform used to map this readable geometry back to raw DDS coordinates.

Sign convention: in readable display coordinates, positive X is right and positive Y is down. A glyph whose top is displaced to the right of its bottom is `right`; top displaced left is `left`.

The Korean candidate must match the source sign first, then the measured magnitude within the approved tolerance. Mirroring/flipping for DDS storage must happen **after** readable-space lettering construction and must not invert the intended displayed slant.

A candidate with the opposite displayed slant sign is an unconditional `REWORK_REQUIRED` even when orientation, containment and alpha gates pass.

### Slant preflight/postflight

Before production rendering:
1. normalize exact source to readable display coordinates;
2. measure source signed slant from at least two stable glyph stems/edges when possible;
3. render a geometry proof and measure its signed slant;
4. require matching sign before full Korean effects are applied.

After DDS round-trip:
1. decode raw DDS;
2. apply the recorded display transform;
3. measure candidate signed slant in readable coordinates;
4. require source/candidate sign equality and tolerance compliance.

Never compare slant sign directly in differently transformed raw/display coordinate systems.

### Mandatory GitHub PNG review set

Every newly generated production candidate must save human-review PNG artifacts under:
`localization/graphics/generated_png/<asset_id>/`

Required files:
- `source_display.png` — exact HD source normalized to readable display orientation;
- `clean_plate_display.png` — clean plate in the same readable orientation;
- `candidate_display.png` — Korean candidate in the same readable orientation;
- `comparison.png` — labeled side-by-side source / clean plate / candidate at native or nearest-neighbor integer scale;
- `generation_prompt.json` — exact strict prompt/spec used;
- `qa_report.json` — machine-readable QA including orientation and signed-slant fields.

These PNGs are review artifacts, not DDS construction inputs. They must be generated from the exact source/candidate lineage. A changed production DDS without this review set is not promotable.

