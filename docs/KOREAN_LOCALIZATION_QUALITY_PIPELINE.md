# Korean Localization Quality Pipeline

This document is a quality-only layer for `korean-localization-recovery-20260928`. It intentionally does not define controller scheduling, retries, rollovers, task IDs or orchestration.

## User screenshots: 14 hard-stop presentation observations — 2026-10-09

Add these to, **not instead of**, the existing 10-stage construction and
eight ordered rework checks. Require PASS/FAIL/HOLD with actual native
evidence per affected label: 1. English glyph/effects fully removed on
CLEAN without Korean; 2. plate/gradient/alpha continuity; 3. no added
rectangular composite trace; 4. native Hangul contour/counter-space and
no prior low-res raster upscale/font fallback; 5. persisted DDS codec,
block, mip and glyph-edge integrity; 6. readability at 100/75/50%;
7. original source family stroke, width/height and *per-line* hierarchy;
8. readable top-minus-bottom slant and perspective from measured anchors;
9. source effect-bbox ceiling and positive separation where possible;
10. zero clipping or overlap between letters, dynamic Stage 2, rank,
HUD numbers/icons and protected artwork; 11. RAW/FLIP-Y orientation and
source-equivalent transforms; 12. exact preservation of Ferrari names,
model marks, songs and logos; 13. composited in-game UI at true display
scale, including HUD animation/foreground; 14. region-by-region review
of the user's annotated screenshot against unobscured game pixels.

A single visible defect HARD FAILS producer/C/C3 regardless of scalar
outside-mask zero or past C3 PASS. The black screenshot rectangles are
user review outlines, NOT automatically composited artifacts; distinguish
them from actually visible plate/crop remnants. Missing exact mapping,
plate evidence or unmarked comparison is HOLD/MAPPING_REQUIRED, never
an invented pixel FAIL or PASS.

Separate reference renderer families for tiny HUD, small gray menu,
italic selector, silver-techno header, showroom metadata and rank/stage
overlay. Approve ONE exact saved-DDS example against canonical original
before propagating its method; reject generic stretched/blurred Korean
rasters, wrong italics, overthick shadows and too-small-to-read results.
No additional automatic scaling bypasses native source bbox ceiling.
Qualify text-free SOURCE-vs-CLEAN before lettering and CLEAN-vs-FINAL
after. Keep runtime stack-order/screen-scale as a required new user
regression retest; static PASS does not close an actual-game failure.

## Repeat-defect convergence selection (2026-10-08)

For A/B/C selection, apply `docs/KOREAN_LOCALIZATION_REWORK_CONVERGENCE.md` and the read-only `tools/localization/rework_triage.py` to the current queue before DDS reconstruction. Missing-only evidence remains HOLD for fresh evidence; confirmed repeat source-family failures require a changed rendering method. Neither state is a PASS. Existing independent C/C3 evidence and actual-game acceptance requirements still apply.

## Evidence enforcement update — 2026-10-08

Follow `docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md`. It supersedes historical
string-token C3 approval: calibration, per-region lossless evidence, separate C/C3
observations and exact source/candidate binding are mandatory for current export.
The evidence validator does not replace visual judgment or actual game testing.

## Mandatory 10-stage production and artifact-contamination gate (2026-10-08)

This is the **required A/B construction sequence** for each new or materially
reworked Korean graphics asset. It expands the existing eight *ordered rework
visual checks* below; **all eight remain mandatory**. This sequence changes
image production and evidence, not A/B/C1/C2 scheduling or approval semantics.

1. **Exact English source / DDS provenance:** pin canonical English source SHA,
   native decoded width/height, format, alpha, authored MIPs, source glyph/effect
   bboxes and per-sprite RAW/readable orientation. Never upscale a prior Korean
   candidate to manufacture a source.
2. **Segment inventory / protected masks:** account for every visible localizable
   label; distinguish deliberately preserved names, icons, song titles and art.
   Derive source glyph/effect masks including outline, shadow, glow, fringe and
   protected foreground; OCR rectangles are hints, not erase/insert masks.
3. **Source lettering removal / CLEAN_PLATE construction:** restore plate and
   background from source-faithful flat/gradient/textured/translucent layers.
   Remove source glyphs *and their effects*, not only bright letter interiors.
   Korean lettering cannot be used as a cover for incomplete restoration.
4. **Independent PLATE_ONLY_GATE:** examine SOURCE vs CLEAN **with no Korean text
   present**, at native, high zoom and practical 100/75/50-percent sizes on
   neutral/contrasting backdrops. Inspect RAW and readable orientation. Reject
   source-script silhouettes, edge ghosts, glow, smears, color bands, alpha
   discontinuities, BC blocks, donor boundaries, rectangular patch seams and
   lost plate detail even when a scalar residue or bbox check reads zero.
   Store the stage decision/evidence separately from final-candidate QA.
5. **Original-family type/effect profile and method selection:** measure source
   line hierarchy, readable top-minus-bottom slant, baseline, shape/counter
   space, height/width, weight, stroke, fill, highlight, edge, extrusion and
   shadow. Select source-faithful technique by family (flat UI/help, tilted
   selection, metallic/chrome/beveled text). Generic flat fonts with arbitrary
   width stretch, shear or bevel overlays are *not* acceptable substitutes for
   a visibly different native source family. Record representative source PNG,
   measurements and approved renderer-method reference before batch reuse.
6. **Native-size Korean glyph production:** draw each Hangul syllable from a
   suitable native-resolution glyph or source-conditioned/vector reconstruction.
   Match the measured family and per-line hierarchy; retain a legible Korean
   counter-space and strict original effect-bbox width/height ceiling. Do not
   add outlines, shadows, boxes or embossed layers absent from the English.
7. **GLYPH_ONLY_COMPOSITE_GATE:** apply only the transparent Korean glyph plus
   *explicitly source-justified effect alpha* to the independently qualified
   CLEAN plate. Never paste an opaque/semopaque rectangular text crop with
   its own background pixels. A rectangular **selection region** is allowed as
   an editing aid only if every resulting changed pixel and edge is justified
   by plate reconstruction or intended glyph/effect masks.
8. **Independent COMPOSITE_CONTAMINATION_GATE:** inspect CLEAN vs FINAL separately
   from SOURCE vs CLEAN. Every changed pixel must be attributable to approved
   glyph/effect masks; classify unwanted halos, non-glyph background deltas,
   square blocks, box-edge seams, foreign artwork or source-script redraw as
   hard failures. Compute outside-mask/protected-art/overlap/alpha deltas and
   examine lossless contact crops; a machine zero cannot overrule a visible
   defect. Do not silently widen the allowed mask to absorb an artifact.
9. **Persisted DDS decode/mipmap presentation gate:** encode with the required
   original native dimensions, format, alpha, MIPs and RAW sprite orientation;
   re-decode **the actual saved DDS bytes**. Verify no BC/DXT block pinholes or
   damaged strokes, glyph clipping, 1-pixel intrusion, bad slant, plate residue,
   patch artifacts or readability loss at native, high zoom, 100/75/50-percent
   practical display and authored MIP levels. Record exact source and candidate
   SHA-256.
10. **Independent C/C3 and user-preview handoff:** submit only candidates with
    both plate-only and composite gates PASS (or stop as REWORK/MANUAL required).
    Independent C then C3 inspect the exact bytes. Provide a distinctly labeled
    **USER_REVIEW_NOT_APPROVED** in-game preview when eligible, *before* user
    acceptance, without claiming current evidence-backed final approval.
    Final approved export remains guarded by `qa_evidence_gate.py` and actual
    game-validation requirements; neither historic C3 status nor preview
    packaging can promote an asset.

**Mandatory explicit defect codes** (write in per-asset producer QA findings,
C findings and queue/backlog evidence when observed; never fabricate a count):

- `SOURCE_RESIDUE_UNDER_KOREAN`: any English/source glyph, outline or
  source-style shadow/glow ghost beneath or beside Korean text.
- `INCOMPLETE_CLEAN_PLATE`: source lettering/background restoration leaves
  visible smear, erased detail, brightness/alpha discontinuity or residue.
- `FOREIGN_BOX_ARTIFACT`: a foreign UI/image chunk or extraneous graphic box
  has been composited with the lettering.
- `BACKGROUND_PATCH_INTRUSION`: copied/painted background patch changes
  adjoining original/protected artwork, palette, alpha or plate continuity.
- `RECTANGULAR_COMPOSITE_TRACE`: visible rectangular edge, luminance/alpha
  block or crop boundary introduced by composition.

Each code is **hard producer FAIL** for confirmed visual defects, even with
zero changed pixels outside a coarse bbox. Use `HOLD_STRICT_RECHECK` when exact
source/clean/effect-mask evidence is unavailable rather than inventing a PASS.
The presence of a legitimate rectangular editing window alone is *not* a
defect if persisted pixels are visually correct and remain within justified
source-derived restoration and glyph masks.

**Mandatory evidence handoff:** retain separate SOURCE/CLEAN and CLEAN/FINAL
lossless comparisons, SOURCE/FINAL for style/hierarchy, source glyph mask,
protected mask, justified final effect mask, actual saved DDS decoded views,
RAW/readable and practical size/mip views, SHA hashes, concrete per-stage
PASS/FAIL/HOLD and the defect code(s). A/B must reject and correct any bad
CLEAN plate *before* trying new Hangul styles. C should reproduce the two
independent comparisons, not accept producer-PASS prose as visual proof.

**Source-family propagation / repeat rejection:** validate one representative
persisted-DDS candidate against its native English family before batch-producing
the same UI style. Two independently recorded C rejections with the **same
visual root-cause family** require `METHOD_CHANGE_REQUIRED` under
`docs/KOREAN_LOCALIZATION_REWORK_CONVERGENCE.md`: stop same-method rerenders
and explicitly record a different source-conditioned or manual/vector approach.
Do not rerender a currently held, unchanged good DDS merely to migrate QA
evidence. When a rerender is blocked, A/B may select another ready, independent
asset according to their existing shard rules.

**Production metric priority:** report (a) new/materially revised candidate
DDS with current SHA, (b) independent current-byte C/C3 reviews and passes,
(c) defect recurrence by root cause, (d) current evidence-approved export,
(e) preview DDS included and user feedback, (f) actual in-game closures.
DDS file count, repeated rerender attempts, previews and historical C3 labels
must never be reported as final approval or completed runtime validation.

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

### Ordered rework generation gate

For every REWORK asset, enforce the following checks **in this order while regenerating the asset**, not only as post-hoc QA. A failed step sends the asset back to the corresponding construction step before a producer PASS can be recorded.

1. **English removal / plate restoration:** after removing the English/source lettering and its effects, the plate/background must be fully reconstructed before any Korean lettering is drawn. Source-shaped residue, blur, patch boxes, seams, donor boundaries, damaged artwork or alpha discontinuities are FAIL.
2. **Source-matching slant direction:** at readable orientation, the Korean lettering must lean in the same visual direction as the English source. Preserve the source raw-DDS transform separately; do not infer visual lean from a shear-sign variable.
3. **No undersized lettering:** within the hard source-bbox size ceiling, use a source-faithful scale that remains immediately readable and is not unnecessarily smaller than the English source. A materially undersized Korean result is FAIL even when containment passes. Never enlarge beyond the exact source glyph/effect bbox to solve readability.
4. **Source-faithful weight/effects:** stroke weight, outline, shadow/glow and related effects must match the source family and must not be excessive. Heavy outline/shadow that harms legibility or changes the source style is FAIL.
5. **No clipped pixels:** no Hangul stroke, outline, shadow, glow, antialias fringe or transformed glyph pixel may be cut off or truncated.
6. **Protected-art clearance:** Korean glyph/effect pixels must not intrude into protected graphics, vehicles, vehicle/model names, icons, frames, boxes, numbers, portraits, neighboring atlas content or other preserved artwork.
7. **Both FLIP-Y and RAW must be clean:** inspect the FLIP-Y/readable review and the actual RAW DDS view. Both must have correct orientation/transform and be free of clipping, residue, overlap, intrusion and other visible anomalies.
8. **Immediate readability against the source:** compare the final Korean result directly against the English original at the same practical display scale. If the Korean text is not immediately readable, or is materially harder to read because of scale, weight, effects, damage or contrast, it is FAIL and must be regenerated.

Numeric containment/protected-mask PASS never overrides a failure in this ordered gate.

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

The export is a human visual gate: numbered JPGs, queue-index ordering, a machine-readable manifest, and English original vs current Korean candidate shown side-by-side. Each localized candidate must include both FLIP-Y review and RAW DDS comparisons. The manifest must pin/hash the English source and record its native dimensions. Prefer same-resolution source; a proven lower-resolution English original may be integer nearest-neighbor scaled only for human display when the Korean candidate was intentionally rebuilt at higher native resolution. That display scaling never counts as pixel-QA evidence. Missing/ambiguous provenance or a non-alignable source is FAIL/HOLD.

C must refresh this comparison set whenever C-PASS membership or candidate bytes change. tools/localization/export_c_pass_comparison.py is the persistent exporter and the active C execution path must invoke it when a refresh is required. Prefer the ChatGPT local execution environment for this exporter and related image/DDS QA when its inputs are available locally; use GitHub Actions only when the hosted runner itself is required for validation or an unavailable dependency. User-observed visual defects in this set are hard failures even when C numeric/static checks passed; the asset must return to A/B rework and receive a newer C pass before in-game validation. Reopened/pending-C assets must disappear from the current export. Preserve-original policy passes with no candidate remain numbered comparisons whose right side explicitly states that the original is intentionally preserved.

## User pre-in-game JPG rejection hard gates

The following checks are mandatory in producer self-QA and independent C readable-orientation review. They are hard FAIL conditions and override previous numeric/static PASS:

- **Plate/background source-footprint restoration:** wherever English/source text previously covered a plate, badge, speech bubble, gradient or textured UI surface, the reconstructed plate must be visually continuous. Haze, blur, dirty source-shaped residue, luminance patches, donor seams, softened plate detail, leftover outline/shadow silhouettes, or a visibly different patch are FAIL even when a residue counter is zero.
- **Readable slant direction:** compare source and Korean at readable orientation. If the source leans right, Korean must lean right. Left-leaning replacement of a right-italic source is FAIL. Direction is judged visually from top-vs-bottom horizontal displacement, not from a transform parameter sign.
- **Text scale and hierarchy:** Korean may not be visibly undersized relative to the corresponding source family. Fit as large as safely possible while staying strictly within the exact source glyph/effect bbox. Large rank/header labels must retain source-like visual hierarchy rather than becoming small captions.
- **Readable weight/effect ceiling:** excessive boldness, outline thickness, shadow, internal shading, glow or gradient that makes Hangul materially harder to read than the source is FAIL. Source fidelity does not justify reduced legibility.
- **No clipping:** fill, outline, shadow, glow and transformed glyph strokes must all remain intact. Any visible cutoff, including bottom-outline or italic-end clipping, is FAIL.
- **No protected-region intrusion:** Korean text/effects may not intrude into vehicle graphics, names, portraits, plates, icons, neighboring cells or other protected artwork. A text box that touches/overwrites protected content is FAIL even if the source bbox mask check was numerically permissive.
- **No untranslated visible UI labels:** source labels selected for localization must not remain English. User-confirmed omissions such as COURSE/LEFT/RIGHT/EASY/HARD-class navigation/difficulty labels are FAIL unless explicitly preserve-original by policy.
- **English-original side-by-side review:** C must compare English original vs Korean result for plate cleanliness, slant direction, scale, weight/effect strength, clipping, protected-art intrusion and untranslated labels. Numeric QA alone cannot close any of these gates.

A user rejection in PRE_INGAME_JPG_REVIEW immediately changes the affected row to REWORK_REQUIRED, invalidates the prior C visual PASS, removes it from the current C-pass export, and requires material A/B rework plus a newer independent C pass before in-game testing.



## Third-stage C strict visual audit (C3_STRICT_AUDIT)

This gate applies to candidates whose current bytes have already passed independent C static QA. It is an additional human/controller visual false-negative hunt used when higher-priority production/fresh-C work is exhausted; it does not replace producer QA, normal C QA, or in-game validation.

### Required comparison views
For the same candidate SHA, inspect:
- canonical English source vs verified CLEAN_PLATE vs Korean FINAL at matched decoded dimensions;
- FLIP-Y/readable orientation and RAW DDS orientation;
- practical display scale plus high-zoom detail;
- line/region crops where multiple typography families, protected artwork, or tight plate boundaries exist.

### Fail-closed emphasis order
1. **Readable slant/perspective direction:** visually match the English source direction and approximate magnitude. Opposite-direction shear, accidental upright rendering, excessive shear, or inconsistent line directions FAIL.
2. **Clean plate integrity:** before judging Korean lettering, verify the English/source lettering was actually removed and the underlying plate/background was naturally reconstructed. Residue, ghosting, blur, smeared texture, patch rectangles, seams, damaged graphics, wrong donor texture or alpha discontinuity FAIL.
3. **Source typography similarity:** compare family impression, condensed/wide proportion, weight, stroke shape, round/square character, relative cap-height equivalent, alignment, baseline, per-line hierarchy, spacing, gradient/fill, outline, shadow/glow and depth. A visibly different generic font treatment FAIL even if every pixel is contained.
4. **Non-undersized readable scale:** the Korean result must be immediately readable and visually proportionate to the English source without exceeding the exact original glyph/effect bbox. Excessively small or weak lettering FAIL.
5. **Glyph quality:** broken Hangul, missing/clipped strokes, jagged nearest-neighbor enlargement, mixed-resolution text, malformed syllables, clipped outline/shadow/glow or damaged antialias fringes FAIL.
6. **Protected-art and neighbor clearance:** enforce the existing zero-overlap rule at pixel level. Any localized/effect pixel touching prohibited vehicle/character/name/icon/box/frame/neighbor/preserved-art content is FAIL.
7. **Placement and hierarchy:** source-faithful horizontal/vertical anchor, baseline, line spacing, line-size hierarchy and relationship to the plate are mandatory. A contained but visibly displaced composition FAILS.
8. **FLIP-Y + RAW parity:** both inspection orientations must remain clean, correctly transformed and semantically consistent.

### Result semantics
- Existing machine QA remains mandatory, but a visible failure in this C3 gate overrides numeric PASS.
- `C3_STRICT_PASS`: all existing machine gates and every ordered visual item above pass for the same current candidate bytes.
- `REWORK_REQUIRED`: any definite visual or numeric defect. The prior C PASS for those bytes is superseded and A/B must repair before a fresh independent C approval.
- `HOLD_STRICT_RECHECK`: exact-source/clean evidence is missing or ambiguous, or decoded evidence is insufficient for a safe decision.
- A previous C3 pass is invalidated when candidate bytes, source/clean provenance, user/JPG/in-game evidence, or this quality policy materially changes.
- C3 does not imply runtime/in-game validation. Keep runtime state unchanged unless the game was actually tested.
- Record candidate/source hashes, comparison evidence, the eight ordered findings, and final C3 result in role_C evidence/WORKLOG so unchanged assets are rotated rather than repeatedly rechecked.


## Post-encode and presentation hardening gate

This gate closes false negatives that survive source/CLEAN/FINAL static review but appear after DDS encoding, scaling, family comparison, or actual game composition. It applies to every new or materially reworked graphics candidate in addition to the existing containment, visual, C, C3 and in-game gates.

### Decoded-DDS authority
- The QA image for a deployable candidate MUST be decoded from the exact persisted DDS candidate bytes. A pre-encode PNG/render is construction evidence only and cannot be the final QA authority.
- Preserve and verify DDS dimensions, pixel format/compression, alpha semantics, mip count/order and raw orientation against the exact source.
- For uncompressed/lossless DDS paths, unexpected pixel differences between the intended pre-encode image and the decoded persisted DDS are FAIL.
- For BC/DXT or other lossy paths, inspect the decoded persisted pixels for broken Hangul strokes, ringing/block artifacts, alpha halos, outline/shadow loss, color shift and new edge contact. Numeric format/header success cannot override a visible decoded-pixel defect.

### Mip and practical-display-scale gate
- When the source/candidate uses authored mip levels, inspect every text-bearing mip that can be selected by the game. Missing decoded evidence for a text-bearing mip is `HOLD_STRICT_RECHECK`, not PASS.
- A mip is FAIL if a Hangul stroke/effect disappears, merges with a neighbor, becomes clipped, gains a block/halo artifact, loses required outline/shadow hierarchy, or becomes materially less readable than the corresponding source presentation.
- In addition to native/high-zoom review, inspect the decoded final at the known runtime render scale when known. When that scale is not known, retain practical-size review evidence at 100%, 75% and 50% as a proxy. Proxy scaling never substitutes for actual in-game validation.
- Practical-size review is judged on immediate readability, glyph integrity, color/contrast, outline/effect survival and separation from nearby/protected artwork.

### UI-family style-profile gate
- Every localized graphics asset MUST be assigned to a source UI family or explicitly marked standalone.
- For a shared family, record/reuse a source-derived style profile covering font-family impression, width/height proportion, weight, readable slant/perspective direction, baseline/alignment, fill/gradient family, outline thickness, shadow/glow direction and relative text hierarchy.
- C must compare each candidate against both its English source and already accepted members of the same family. A candidate that is individually contained but visibly looks like a different font/resolution/effect family is FAIL.
- Do not impose arbitrary global numeric tolerances where the source family intentionally varies; the source family is the reference.

### Rework blast-radius gate
- A material rework MUST pin the immediately preceding candidate bytes when they exist and define the intended rework mask/region.
- Compare previous candidate -> new candidate. Any changed pixel outside the declared rework mask is FAIL unless that extra region is explicitly documented as part of the same repair.
- This check is independent of source-vs-candidate edit containment: a pixel may be inside the historical source edit region yet still be an unintended collateral change for the current rework.
- Use `tools/localization/validate_clean_plate.py --baseline-candidate ... --rework-mask ...` where decoded RGBA evidence is available.

### Localization coverage / omission gate
- Every visible source segment classified as localizable must resolve to exactly one current outcome: localized Korean, explicit policy-approved preserve-original, or a fail-closed blocker/HOLD.
- An unaccounted English UI label is FAIL even when every rendered Korean segment passes. Preserve-brand/song/credit exceptions must remain explicit and traceable to policy.
- A/B/C must check the asset transcription/segment specification against the final candidate so a skipped cell/row cannot disappear from QA merely because no Korean pixels were produced there.

### Mandatory C3 for high-risk candidates
The following candidates MUST receive a fresh `C3_STRICT_AUDIT` for the same current candidate bytes before entering the current PRE_INGAME JPG set, even when normal C static QA passes:
- any asset previously rejected by actual in-game review or PRE_INGAME JPG review;
- BC/DXT-compressed text or text-bearing authored mip chains;
- textured/gradient/transparent clean-plate reconstruction;
- slanted, italic, perspective, rotated or multi-line typography;
- small text or text close to protected artwork/neighboring atlas content;
- any candidate whose font/style-family mismatch, low-resolution rendering, clipping, residue, color/effect mismatch or hierarchy has previously produced a false-negative;
- any asset whose correctness materially depends on final runtime composition rather than isolated DDS appearance.

If required C3 evidence is missing, the candidate remains `HOLD_STRICT_RECHECK` or pending C3 and MUST NOT be exported as current C-pass PRE_INGAME evidence. For machine-enforced export gating, a high-risk pass must record `C3_STRICT_PASS` together with the exact candidate SHA in the queue/status evidence; a C3 token without the current SHA is stale and does not authorize export.

### Runtime-composite and golden-screenshot regression
- Once a defect or approved state has actual in-game screenshot evidence, retain the relevant screen/region as regression evidence tied to the exact asset/runtime mapping and candidate hash.
- For later changes, compare the same UI region at equivalent game state/resolution when reproducible. Mask dynamic scenery/vehicles/timers only when necessary; never mask the localized label, its plate, or adjacent protected UI.
- New clipping, collision, residue, hierarchy change, contrast loss, wrong color/effect, or newly untranslated text relative to the accepted screen is FAIL.
- Golden screenshot regression supplements but does not replace a fresh human in-game review when candidate bytes or runtime draw behavior change.

## Runtime UI in-game visual parity gate — 2026-10-08

User in-game screenshots are authoritative for runtime Korean typography as well as DDS artwork.

- At native screenshot scale, Korean runtime text next to stock English UI must not look visibly lower-resolution, blurrier, more jagged, or materially heavier than the surrounding source UI.
- Main-menu/body/modal Korean uses the lightest source-faithful Korean-capable UI face available. On Windows the localization runtime prefers `malgunsl.ttf` before regular Malgun; fallback order is allowed only when Semilight is unavailable.
- HUD/speech-bubble readability reinforcement is **not** a global Korean-text effect. Menu/modal text must not inherit the compact HUD keyline merely because its logical cell height is small.
- Any runtime text with excessive outline/keyline, black fill clumping, stroke merge, or reduced counter-space is a visual FAIL even when the text rectangle and stock layout are numerically correct.
- Review runtime text at 1x final screenshot scale, not only zoomed crops. Compare Korean and nearby untouched English for perceived sharpness, weight, baseline, spacing and hierarchy.
- A user screenshot reporting low-resolution/dirty/heavy Korean invalidates earlier build/static PASS for that visual state. Reopen the regression and require a NEW in-game screenshot before closure.
- Sparse visible localization is a coverage signal, not permission to translate protected brands, vehicle/model names, song titles, product names or scene/environment artwork. Map every visible English item to runtime/DDS and protection policy before changing it.

