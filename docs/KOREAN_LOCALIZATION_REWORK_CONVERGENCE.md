# Rework convergence rules (2026-10-08)

A/B selection should use `python tools/localization/rework_triage.py --index N` after refreshing Git. `EVIDENCE_ONLY_HOLD` means gather missing visual proof against unchanged DDS bytes; it does not require a new DDS. `FRESH_C_REVIEW` means independent C inspection. `VALIDATION_ONLY` means current evidence and actual in-game retest are still necessary. `MATERIAL_REWORK` means correct the failed construction stage.

`METHOD_CHANGE_REQUIRED` means two distinct recorded C rejections share a visual root-cause family. Do not repeat the previously rejected technique. First measure a source-derived profile (native reference, readable slant, proportions, stroke weight, plate continuity, outline, shadow, gradient, and RAW view), then materially change the renderer or use manual reconstruction. Re-run producer QA, independent C/C3 and real game retest. Record specific review evidence in `localization/graphics/REWORK_ESCALATIONS.json`; never invent past rejections.

`PRESERVE_ORIGINAL` is not a Korean DDS production target. This triage is read-only and cannot mark PASS, close an in-game defect, or change A/B/C1/C2 scheduling. Completion reports must distinguish produced DDS, current evidence-backed approval, remaining user-visible defect and actual game validation. Repeat inspection of unchanged SHA without new evidence is not additional completed work.

A/B/C controller entrypoints should read this document before choosing a rework item. Apply the triage against the latest branch queue, without bypassing the evidence gate.

## Root-cause-directed reconstruction and clean-plate failure taxonomy

Classify *where* the visual failure originates before choosing another DDS
render. Each code requires concrete pixel/source evidence in the existing
queue/role QA report; do not infer defects from historical text alone.

| Failure / explicit code | Reopen at | Required material change |
| --- | --- | --- |
| `SOURCE_RESIDUE_UNDER_KOREAN` | Source removal + PLATE_ONLY | Restore English glyph, outline and glow footprint; Korean cannot conceal ghosts |
| `INCOMPLETE_CLEAN_PLATE` | CLEAN_PLATE | Restore uninterrupted source plate/gradient/alpha/textured detail, not a flat patch rectangle |
| `FOREIGN_BOX_ARTIFACT` | Composition | Remove foreign image/UI pixels from crop; paste only justified transparent glyph/effect alpha |
| `BACKGROUND_PATCH_INTRUSION` | Plate/composition | Restore donor/target source relationship and protected pixel continuity |
| `RECTANGULAR_COMPOSITE_TRACE` | Composition | Eliminate visibly changed rectangular crop seam or luminance/alpha block |
| Flat/unsupported added shadow, outline or red bevel | Family renderer | Match source flat layers; remove arbitrary offset/shadow rather than increasing effects |
| Wrong font, width/height hierarchy, slant, chrome or gold bevel | Source family | Measure and validate a native English-derived family reference; reconstruct via new manual/vector/source-conditioned method |
| BC/DXT compression pinholes/dotted strokes | DDS encoding | Verify persisted decoded face/alpha and source format/MIPs before fresh C |

A producer may use a rectangular **selection tool** or mask bounds internally;
only its visible unauthorized changes are defects. Do not mark a correct image
as FAIL solely because the editor used a rectangular selection.

All new/materially reworked candidates must pass separately:
(1) **SOURCE vs CLEAN** with Korean hidden; (2) **CLEAN vs FINAL**
showing glyph/effect-only authorized differences; and (3) SOURCE vs
persisted decoded FINAL for family fidelity at native, 100/75/50 sizes,
RAW/readable and authored MIPs. If stage 1 fails, halt text rendering and
repair CLEAN first. If stage 2 fails, fix composition without rebuilding
a good glyph unless genuinely necessary.

Before propagating a generator to other members of one family, C must inspect
one representative persisted candidate. For evidenced repeat
`METHOD_CHANGE_REQUIRED`, the next attempt must cite the specific new
source-conditioned construction profile and describe how it differs from
the rejected technique. q172/q214 source metallic-bevel and q175/q219
chrome/UI-family problems must not become repeated flat/SDF/shear recolor
attempts. If original contour/profile cannot be matched safely, record
`MANUAL_RECONSTRUCTION_REQUIRED` and let the other A/B shard proceed on
unblocked work; do not pass a knowingly defective candidate downstream.

**No QA inflation:** `EVIDENCE_ONLY_HOLD` is not an A/B production task;
historical C3 remains historical. Report separately actual new DDS, new
independent C acceptance, active rework, repeated-cause failures,
evidence-backed approval, user test-build candidates and true in-game
acceptance. A `USER_REVIEW_NOT_APPROVED` package enables feedback before
final export and never upgrades current QA state by itself.
