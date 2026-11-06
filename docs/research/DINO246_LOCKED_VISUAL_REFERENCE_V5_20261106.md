# Dino 246 Cockpit — LOCKED PRIMARY VISUAL REFERENCE (v5)

Date: 2026-11-06 KST
Status: AUTHORING TARGET LOCK; NO NEW MODEL CLAIM
Latest actual baseline: `feature/dino-hd-cockpit-detail-v4-20261106` (v4 GLB/OVC).

## Canonical reference — DO NOT SWITCH

- **Primary image:** user-uploaded `페라리 디노 246 클래식 콕핏(1).png` in 2026-11-06 conversation.
- **Exact reference SHA-256:** `0c4d19980684571b283dd1070954c92f5a0ef236849a04db48b027fcb1cca53e`
- Resolution: 1448 x 1086 px.
- **Image nature:** concept-generated illustration supplied by the user, not measured OEM photography. Use as **visual design target**, not unquestionable manufacturing geometry or a newly generated AI variant. Use genuine Dino 246 photos, original game PMT mesh, and Quest APK for unseen geometry, part ownership, driving position, and realistic 3D dimensions.
- **Critical**: v4's newly added rectangular air vents + vintage radio layout are *NOT* the canonical target and MUST NOT be treated as the new master. Do not change the target based on previously AI-generated alternate images.
- The image remains supplied in the chat. This Markdown locks its identity by exact content hash; image binary is not embedded or committed in this docs-only change. Future collaborators need the actual uploaded file alongside this spec.

## Required visible objects / appearance

1. **Instrument cluster:** **two large round dials** side by side at driver eye-height, **four smaller round dials** in left/right pairs; dark recessed surround, raised metal circular rings, legible radial ticks and orange/red needle accents. All dials arranged by match-projection to the canonical target image; current arbitrary 3+2 gauge layout is not a pass.
2. **Steering wheel:** round black leather rim with prominent stitched grain and correct hub location. Brushed aluminum three-spoke design with rounded perforations and a small central **yellow Dino emblem**; visible **single** angled steering-column shroud exiting below, not through, the gauges. Check real wall/shaft cross-sections.
3. **Dashboard:** continuous deep black padded/stitched fascia with rounded integrated instrument binnacle, properly contoured glovebox, and **two round recessed vents high on the top of the dashboard** (near windscreen). No generic rectangular vent bank and no radio substituted from unrelated reference art.
4. **Passenger controls:** narrow metal **three-control switch/toggle module** on the right side, cursive Dino 246 passenger badge.
5. **Center tunnel:** correct chrome gated manual shifter plate / long stalk / black spherical knob, small accessory/ashtray and black trim. Avoid floating objects and giant tiles.
6. **Cabin:** deep black leather bucket seats with rounded ribbed padded cushions and piping; matching sidebolsters, physically plausible material roughness and normal detail. Door panels with manual winders, armrests, chrome trim, and carpet.
7. **Pedals:** three correctly positioned hanging or floor-mounted metal pedals with perforations/texture consistent with the canonical image.
8. **Body context:** front screen rim, windshield frame/wiper geometry and red exterior from the original game when runtime owner permits; do not fabricate unrelated red body panels into the cockpit-sidecar model.

## Why v4 failed visual fidelity

- v4 `tools/dino_cockpit_concept_detail_v4.py` constructs components with hard-coded `surface / tube / box / disc` parametrics; source game PMT is used chiefly for scale/bounds verification, **not** one-to-one restoration of exact original mesh topology.
- v4 adds the wrong rectangular vents and radio, a wrong count/placement of gauges, synthetic flat seat pads and very simple materials.
- v4's software triangle preview is not a photo-real PBR rasterizer, but its severe layout mismatch is actual geometry, not solely a lighting problem.
- Increasing triangle/mesh counts is **NOT** a fidelity acceptance criterion.
- 2K procedural noise textures and normal-from-albedo are insufficient to reach reference-grade leather, metal, embossed gauge text and cushions.

## Required authoring shift and acceptance gates

- **Replace the generator-first strategy with Blender-focused photo/mesh matching**: import the original car topology + v4 meshes as alignment aids; create carefully art-directed submeshes with measured proportional relationships and consistent transforms. Use geometry for shape, authored 2K-4K PBR maps for surface details (albedo/normal/roughness/metallic), and baked normal/ambient occlusion when appropriate.
- Match the reference's 2D silhouette in **one canonical projected camera**, then validate multi-view 3D from actual game/A PK geometry. A single picture cannot determine unseen back/underside geometry, so supplement only those unknowns with vetted real photos, not alternative designs.
- Independent screenshots: original concept (do not reinterpret), actual GLB same-pose render, optional diagnostic overlaid feature-point guides. No generated illustrative image may be mislabelled as an actual model render.
- Checklist gate: (i) gauge family and layout, (ii) correct top round vents and 3-switch panel / no radio, (iii) steering column gauge clearance, (iv) seat depth and rounded ribbed shape, (v) proper color/material/lighting, (vi) original vehicle/camera dimensions, (vii) source/runtime integrity and 2-eye visibility.
- Before any R26 deploy: verify original-model draw owner suppression to avoid double wheels, stable launcher exact source SHA, crash on car select/return to menu, original game files unchanged, Quest 3 HMD A/B + performance. **RUNTIME_VALIDATION=UNTESTED** until device proof.

## Current outcome

This is **reference-lock documentation only**: no new GLB, OVC, Windows VR binary or photo-faithful model delivered by this commit. Do not award a new AI performance/competition point for this note. Continue modeling only against the *primary SHA-256 matched image*.
