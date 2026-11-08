# Ferrari 365 GTS/4 Daytona Slot A — R42 native cockpit geometry (2026-11-09 KST)

**Status: ACTIVE / NEEDS_REWORK, not COMPLETE.** Active slot A is daytona365; slot C belongs to F50. Dino 246 is marked completed and never touched.

## Read-only source provenance
- OutRun 2006 genuine original car native resource: /home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz, SHA256 f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe.
- First genuinely PMT-derived Blender import: work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend, SHA256 92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3. Verified native import objects: object00_group01_material012_a0 = 13 vertices, object22_group00_material000_a0 = 61 vertices, official Blender 4.5.15 opening original.
- Immutable source-derived R41 actual previous scene: work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v39_r41.blend, SHA256 65320b1ac94990a1c187f9e92d06e290ef46e6c89e6f9b6843e777a10041a236.
- Reference: genuine 1971 Ferrari Daytona Spider LHD cockpit photograph 02_365_GTS4_Daytona/ADD_interior_LHD.jpg, SHA256 6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb. N100 MANIFEST.json and COVERAGE_MATRIX_16x8.csv checked; authentic complete seven matching-angle views are NOT available or validated. Private original and photo bytes NEVER published.

## Actual new R42 source geometry
Public, nonproprietary editing script: tools/car_modeling/slotA_daytona_r42_original_stamped_spoke_lip_and_dashboard.py, source commit 661a0d0d6aace599c8ae706a2b1b0e2fd9cb0a75, executed script SHA256 309298f2bc1a4cc685c5e5ad415540237cd3a633ca2ad427f6bb9b0037ee581c.

The real original PMT imported Blender scene R41 was opened, and only these EXISTING source-derived cockpit mesh vertex positions were changed, with photo-informed adjustment of thick metal hole lips, stamped factory steering spokes, steering grip and existing sheet bridge ends, dashboard pad, instrument cowl and metal gauge bezel. No new meshes/objects, materials, textures, UV edits or external geometry.

| Original-derived existing mesh | Vertices / faces unchanged | Moved | Geometry SHA256 before prefix -> after prefix |
|---|---:|---:|---|
| V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE | 1885 / 3584 | 318 | 167fd342 -> a4ac8db0 |
| V8_17_ORIGINAL_GUIDED_GAUGE_COWL | 2594 / 2592 | 2,077 | 3c683058 -> 77ee5675 |
| DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY | 3157 / 5376 | 1,997 | 4a4dbbaa -> bcefe2e8 |
| V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0 | 9732 / 17300 | 8,502 | d65ea513 -> d525dd19 |
| V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM | 6144 / 6144 | 3,297 | e3ac0408 -> 4f80bb14 |
| V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE | 20 / 18 | 20 | 6a802c89 -> 4d45e7aa |
| V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE | 20 / 18 | 20 | 85c08a6f -> 98972e48 |
| V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE | 20 / 18 | 20 | 34da9ce8 -> b9751ca4 |

**Total 16,251 moved original-derived vertex coordinates across 8 existing meshes; 105 other mesh geometry SHA signatures untouched**, scene inventory, camera, original object transforms, wheel pivot, original UV/material images unchanged. The original eight spoke holes are STILL open (BVH 8/8), despite user feedback about ugly bolt-like holes. **Full removal or photo-acceptable rework of the holes is NOT DONE.** Three bridge meshes are visually repositioned but **NOT topology-welded**, and source nonmanifold edges remain unchanged/unresolved.

One isolated private rejected R42 cap prototype filled six source boundary loops, but actual Cycles showed new button-like caps: it was rejected and is NOT the accepted R42 scene. No spurious claim of repaired holes or topology.

## Validated private editable output
- Genuine original-derived private editable R42: work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v40_r42.blend, SHA256 **55ffc5dd9c26448ffc3a076a3749319f6c1d082fd4d18ad165c6f3bcf22547f2**.
- Independent official Blender 4.5.15 fresh-process reopened R42 private source, audited eight after signatures, 105 protected other meshes, eight original wheel holes; real 720x480 Cycles 3spp CPU render PASS.
- Real R42 Cycles: SLOTA_DAYTONA_R42_AFTER_REAL_CYCLES_APPROX_EYE.png SHA256 cd1184a984d2037b88dd5b46fe6c731ab3b7f6ace3ad922f189f6e9e0ebb228b.
- Actual R41-R42 Cycles comparison: SLOTA_DAYTONA_R41_R42_REAL_CYCLES_BEFORE_AFTER.jpg SHA256 d2f7b33ac19c662c694e405499bb07939b3abc0a3492c8c53c62d0b464af14d3; 15,674 / 345,600 changed RGB>3 pixels, not photo authenticity proof.
- Per-object before/after complete SHA plus movement values: private SLOTA_R42_SOURCE_WHEEL_DASH_AUDIT.json. Separate-process result: private SLOTA_R42_FRESH_REOPEN_REAL_CYCLES.json.
- Actual original GAME driver-eye still uncalibrated. Authentic photo matched 7 views INCOMPLETE. Steering bridge weld / nonmanifold unresolved, user hole removal request unresolved. GitHub Actions hosted private genuine source scene: **BLOCKED_INPUT_NOT_TRANSFERRED**; a hosted Blender smoke job cannot claim real original model QA.
- Remain ACTIVE / NEEDS_REWORK, 24-hour allocation and cockpit P0 final QA INCOMPLETE, no automatic next vehicle. **Score +0**: same ongoing incomplete Daytona P0 outcome; previous AI2 2782 + 0 = confirmed 2782, no retries/CI/report scoring.
- Artifacts ONLY editable .blend model in private N100 plus comparison render, public editing script and audit text. No PMT/OVC/OVC3/GLB export, game installation or mod packaging, no Ferrari exterior, new texture/normal/PBR, Model2/Dino/VR runtime or slot C changes.
