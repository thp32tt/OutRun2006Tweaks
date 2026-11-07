# Ferrari 365 GTS/4 Daytona — v8.9 actual seat headrest/pleat geometry and charcoal PBR

Date: 2026-11-08 KST. Work on `feature/daytona365-blender-v8-20261108` only; no original-game EXE/OVC/VR/Model2 changes.

## Baseline and real source measurements
- Input (private immutable) `Daytona365_Cockpit_Blender_PBR_v8_8.blend`: SHA256 `6859ead3070525e9a55e7b6946ba10d0050ff85825ce1074f8e3a2255ef48c60`.
- Original authentic PMT `object00_group01_material017_a0` **aggregate only**: two-seat combined X [-0.57464,+0.57464], Y [-0.72863,-0.01985], Z [0.33179,0.85149] metres; high band Z [0.75,0.87] approximately X ±0.548, Y [-0.72863,-0.65045]. These are constraints, not copied proprietary PMT vertices/textures.
- v8.8 native-aggregate constrained 13-station console and source instrument panel preserved.

## Real editable changes
- `tools/blender_daytona365_v8_9_headrest_charcoal_pleats.py` creates **two real 7-ring, 28-vertex, 26-face padded headrest meshes** and source-bound seams. Upper cap 0.853 m, X within ±0.575 m, Y > -0.75 m; direct existing backrest contour integration rather than unrelated external car models.
- Original 4 seats remain their own original Blender objects: existing left/right cushion and backrest front/rear topology and world pivots retained. Sculpted five cushion rib profiles plus four backrest relief panels; paired 49mm cushion thickness and 54mm rear-facing backrest depth maintained. Existing v8.5/v8.6/v8.7 trim curves reprojected. Resampled physical-geodesic UV on actual changed surfaces and metric tangent UV on headrests, keeping attached side-return material polygons.
- Independent source-linked charcoal seat, side and headrest PBR. Retained packed source-derived BaseColor image and tangent Normal, ORM Green→roughness, Height microbump; a Hue/Saturation attenuation node now reduces orange saturation while preserving image details. Metalness remains zero for leather; stronger gloss and invented normal maps NOT substituted.

## Verified real Blender operation
- Official Blender 4.5.15 LTS saved `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_9.blend` (**7,012,264 bytes**, SHA256 `bfd91e5e29d796e708918298678305172ec21fff958122d2eed72118303ca9c2`). Separate fresh-open audit `tools/verify_daytona365_v8_9_blender.py` **PASS**: 106 meshes, 88 curves, packed PBR maps, original gauges/H gate/steering/switchbank and 13-section console preserved.
- True Blender **Cycles** preview `docs/images/daytona365-v8/Daytona365_v8_9_ACTUAL_CYCLES_PREVIEW.png`: SHA256 `25c8038f0766b946905704b3ff7c0e8dcac972683e3dda81a9be82a3eb8eaaef`, 480×320, 4 spp, denoised, CPU 2 threads, exposure -0.52 and calibrated `V7_Camera_Reference_ThreeQuarter`.
- Actual original game PMT / v8.7 / v8.8 / v8.9 comparison `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_7_V8_8_V8_9_ACTUAL_CYCLES_COMPARE.png`: SHA256 `4fc7a3cad4317de0c63a9bf4abe7a54b3bf641c0510d31dd01ff199791b2ba38`. Actual original PMT scene was 960×640 at 10 spp and downsampled; reworks are 480×320 at 4 spp. Same calibrated camera/framing, **NOT** matched-sample photometric equivalence.
- `tools/test_daytona365_v8_9_source_contract.py` AST/compile/static PASS; this source-only gate does not render Blender by itself.

## Outstanding visible defect and truthful boundary
The darkened seats now visually approach original source charcoal/black upholstery much better than the orange v8.8 candidate. However, a light tan decorative piping line persists on the near front seat, and original PMT headrest upper contour/segmentation does not yet match exactly. **v8.10** should correct those source-visible differences without changing legitimate PMT controls, cabin framing or the 13-station console.

`RENDER_VALIDATION=PREVIEW_ONLY`. `MATCHED_960x640_10SPP=UNTESTED`. `GAME_RUNTIME/OVC/QUEST3=UNTESTED`.
