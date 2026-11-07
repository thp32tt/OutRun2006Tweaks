# Ferrari 365 GTS/4 Daytona v8.13 — measured cushion geometry, aligned packed normal map

2026-11-08 KST. Scope: **only** `feature/daytona365-blender-v8-20261108`. No original game/OVC/Quest 3/VR/Model2 edits.

## Real original game reference and difference
- Original game PMT Cycles same-camera screenshot displays a pronounced segmented lower seat, while the v8.9–v8.12 editable candidate used five broader, quieter cushion crests. The exact number of physical PMT source mesh folds is **not recovered** from a screenshot. Seven narrower padded zones and six dividing channels are a working visual approximation, bounded by privately measured original PMT material017 envelope X±0.57464m, Y[-0.72863,-0.01985]m, Z[0.33179,0.85149]m.
- No AI-generated illustration or stand-in model was used as proof.

## Existing Blender mesh physically reshaped in place
- Script `tools/blender_daytona365_v8_13_pmt_seven_pleat_packed_normals.py` accepts **immutable original v8.12 private .blend** SHA256 `03c7e288fad4ecb36952ca2f871e132ee079d9888dea4664d9a97923cd6945c6`.
- Both pre-existing `V8_L/R_CLASSIC_PADDED_CUSHION` objects retain **7,738 vertices, 7,736 faces**, original object identity/pivots, material indices and contiguous 49mm rear return. **3,067** front-surface vertices changed **per cushion**. v8.9 five-broad-crest geometry was compensated, and now has seven narrower 6.6mm-peak relief rolls separated by six ~1.8mm trough depressions.
- Original UV retained, new post-sculpt metric length `V8_13_Geodesic_Seat_Leather_UV` and 0..1 aligned `V8_13_Seven_Pleat_Aligned_Normal_UV` added. Existing 12 original seam/welt curves per cushion are physically conformed to new mesh without duplicate objects. Top bounds X within ±0.554m, Y[-.600,-.046]m, Z[.3895,.468336]m.

## Genuine new packed tangent normal plus original source PBR
- Deterministically generated 512×512 tangent-space PNG `Daytona365_v8_13_Cushion_Seven_Pleat_Tangent_Normal.png`, SHA256 `8a826b702bdf191dc3a76249e4d6fa1cc2fb894f8ea6288f08eeca62e0815ae8`, aligned to 7 physical padded regions and 6 channels.
- Generated normal image is **packed into the editable private Blender .blend**, not borrowed from proprietary game. Shader node `V8_13_SOURCE_PLUS_PLEAT_TANGENT_NORMAL` mixes it at 36% with the **still-linked genuine pre-existing packed source tangent normal**, then passes through pre-existing `NormalMap` and restrained Height bump. Original packed source BaseColor, Normal, ORM-green→roughness, Height remain preserved and texture colorspaces checked Non-Color.
- Rebased cushion PBR charcoal saturation/value and ORM roughness. Old v8.12 source V5 backrest correction and all protected original gauge, chrome H-gate, switchbank, wheel, doors, console and headrest geometry preserved.

## Official Blender save / independent verification / genuine Cycles evidence
- Blender 4.5.15 LTS actual new private `Daytona365_Cockpit_Blender_PBR_v8_13.blend`, **6,447,652 bytes**, SHA256 `130accf3db850df025c836c0364d5a8dfebcf6001a88e61d19135b4331499cc7`. Fresh reopen independently PASS: **106 meshes / 92 curves**, normal map packed, source PBR links, texture UV, originals preserved.
- Genuine same reference camera `V7_Camera_Reference_ThreeQuarter` Cycles preview `docs/images/daytona365-v8/Daytona365_v8_13_ACTUAL_CYCLES_PREVIEW.png` 480×320, 4 spp, 2 CPU threads, denoise, exposure -0.52, SHA256 `525ba2720fe6c64d35f59c4cd4165455ac028679982d1c31017ba6f86998c4cd`.
- True PMT original/v8.9/v8.12/v8.13 four-way comparison `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_9_V8_12_V8_13_ACTUAL_CYCLES_COMPARE.png` SHA256 `ed043eb53bc9484f4647bda4b083dc82d5ae0fb7b3cc43340647cb80c8ae3fd5`. Candidate v8.12→v8.13 mean RGB absolute delta [0.7585, 0.7137, 0.6925] only measures changed pixels, **not** optical improvement. Original PMT is 960×640/10 spp downsampled vs candidate 480×320/4 spp, so equal-sample photometric equivalence NOT established.
- 34 source/AST/compile contract guards locally PASS. GitHub Actions source contract is **not** real Blender render validation.
- **PREVIEW_ONLY**. Full matched 960x640/10spp source and actual game/OVC/Quest3 **UNTESTED**. Original PMT/OVC/private blend stay on private host, not uploaded.

## Next distinct scope
v8.14 source-measured original left/right seat side bolster and lower apron silhouette + packed source PBR vs real PMT; no double-count of v8.13 or prior milestones.
