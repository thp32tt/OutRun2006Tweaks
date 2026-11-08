# Slot A Ferrari 365 GTS/4 Daytona — native PMT cockpit P0 r6 (2026-11-08 KST)

**Scope:** ONLY `active_by_slot["A"] == "daytona365"`; Ferrari F50 belongs to C; Dino246 already complete. This is an **ACTUAL** edit of pre-existing original-game-derived Blender cockpit meshes, **NOT** a car finished or game mod. Native resource/import and actual private Blender scene present on authorized N100; none distributed through this public repository.

## Immutable source identity
- Native read-only original OutRun 2006 `rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Verified original PMT import: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Source marker `object00_group01_material012_a0` 13v/12f; original steering `object22_group00_material000_a0` 61v/31f. The current editable scene uses original-derived object names and real geometric provenance, not an unrelated GLB.
- Exact read-only immediate input: N100 `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v3_r5.blend`, SHA256 `163e48fe83c4555d45e18ba33b574854bc871fa5794b2c91a71a1d57d568696b`.
- Exact Spider/LHD cockpit photo: `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg`, SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. The library's seven matched interior view categories are **not** all verified; a GTB/4 coupe shot does not qualify as an exact GTS/4 Spider.
- Output ONLY private editable `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v4_r6.blend`, size **7,487,945 bytes**, SHA256 **`cb220cd75eb09c84fe722a14b5d4bc268a8cf1d9af23c77aba56a97c38b19ea9`**.

## Original-derived mesh geometry actually modified

Vertex/face counts are retained in r6; **positions actually changed**, not merely material colors. Before/after Blender coordinates retain the exact original object world matrices/steering anchor, scene camera, UVs and prior packed materials. Signatures are SHA256 of seven-decimal vertex coordinates + original face index/material topology.

| Existing original-derived object | Before → After V/F | Moved vertices | Max displacement | Before → After geometry SHA256 |
| --- | --- | ---: | ---: | --- |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 → 9720/17285 | 4077 | 1.250mm | `3c3034e7` → `adaa606a` |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 1536/1536 → 1536/1536 | 456 | 1.619mm | `ef8bed9b` → `0c310bc4` |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224/210 → 224/210 | 128 | 1.662mm | `367465f4` → `67a9e1c7` |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 908/1344 → 908/1344 | 811 | 1.045mm | `24d6f650` → `e47529c7` |
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 284 | 1.298mm | `2cad99a7` → `8c290e3e` |

**Total moved existing mesh vertices: 5,756.** Original metal 8 physical steering perforations still all verified via center-ray miss / surrounding metal-hit in a fresh Blender instance. All **108 other pre-existing mesh objects** geometry-signature identical; no new objects/materials/images/curves; original world transforms and scene camera unchanged.

## Actually executed real-scene QA
- Official Blender **4.5.15 LTS** in N100 private runtime: source r5 opened, r6 geometry saved, SHA rehashed; a completely new Blender process reopened the r6 output. Independent verifier: `DAYTONA_SLOT_A_R6_FRESH_REAL_ORIGINAL_SCENE_REOPEN_PASS`. Original PMT and exact original import rehashed independently. No test cube was accepted.
- Actual original-derived r5 **and** r6 Cycles CPU renders, **720×480, 3 spp**, identical **approximate** camera, Blender processes independent. Before PNG SHA256 `d00d8a7e47e52ecb02c9c4aadb895543da445d52708da6229dad398d63aaac7e`; after PNG SHA256 `6625b10fc5cd7895e0e8ea7a86548704039cd656d0a87a474f13e400fa9dc2cb`.
- N100 private photograph + r5 + r6 comparison: `SLOTA_DAYTONA_R6_EXACT_SPIDER_PHOTO_VS_R5_R6_PRIVATE.jpg` SHA256 `fe7bf89aa2650c981a2813f18a6bb8317da52c0040cf587affc5f244d5292859`. Pixel fraction above delta 8 approximately 0.85%; modifications are real and visible only subtly at this distance, **not** a claim that real-life shapes now match.
- QA caveat: steering spoke non-manifold edges remain **1597**; original-derived gauge bezel **466**, dash **184**. These inherited/open surface defects require targeted real source-mesh/topology QA. Original driver's actual calibrated game camera and seven matched photographs remain **incomplete**.
- GitHub-hosted Actions cannot receive/access this private original `.blend` by default. Existing hosted 4.5.15 toolchain smoke **does not** validate this proprietary original scene; hosted real-source test = `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`. Neither smoke success nor local test implies hosted real-scene PASS.

## Public scripts vs private artifacts
- Actual geometric editor: `tools/car_modeling/slotA_daytona_p0_r6_original_mesh_contours.py`.
- Independent fresh-process validator: `tools/car_modeling/slotA_daytona_r6_independent_private_scene_verify.py`.
- Same-camera real-scene render script: `tools/car_modeling/slotA_daytona_r6_real_scene_cycles_compare.py`.
- Actual proprietary edited `.blend`, photo, renders and JSON audit stay on private N100 under `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/`; none copied to public GitHub.
- **Forbidden operations NOT performed:** PMT/OVC/OVC3/game output, game integration, VR source changes, exterior body/wheels/tires, new texture/normal/PBR, third-party GLB, slot C, Dino or Model2 changes.

## Continuation hold
`active_by_slot.A=daytona365`, `status=ACTIVE`, `geometry_gate=PARTIAL_NEEDS_QA`, `reference_gate=PARTIAL_NEEDS_7_VIEWS`, `photo_view_qa=NEEDS_REWORK`; starting 2026-11-08 04:13:41 UTC, earliest 24h end **2026-11-09 04:13:41 UTC**. Keep same vehicle until actual P0, correct calibrated driver eye, photo 7-view and 24h QA all pass. **Do not mark COMPLETE or switch car.** No fresh point for repeat P0 source/wheel feature, render, CI smoke or documentation; SSOT has already scored original Daytona P0 achievement once.
