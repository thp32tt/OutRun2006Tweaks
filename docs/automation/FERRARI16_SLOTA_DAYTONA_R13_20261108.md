# Ferrari 365 GTS/4 Daytona — slot A native original cockpit R13 (2026-11-08 KST)

**State:** SLOT_A_ONLY, `daytona365 ACTIVE / PARTIAL_NEEDS_QA`. Started 2026-11-08 04:13:41 UTC (13:13:41 KST). **NOT** a completed 24-hour allocation, not approved for vehicle rotation. Independent slot C `f50` and user-finished Dino 246 untouched.

## Source authenticity and immutable private scene chain

1. Exact read-only original OutRun 2006 compressed PMT: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA-256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
2. Verified direct game PMT-derived Blender original import: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA-256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Original root object identity `object00_group01_material012_a0` (native dash), `object22_group00_material000_a0` (native wheel metal pressing), retained in proven source-derived edit chain.
3. Immutable predecessor private original-derived Blender `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v10_r12.blend`, SHA-256 `2995c8b21e519d7e7da4de71bf3bd35186ef8f7159506d619c312083cf5fd518`.
4. **New genuinely edited original-derived private source Blender:** `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v11_r13.blend` SHA-256 **`e8c63f9a92529c2580bb92e8b511533ac9efab7e89116fc8e40e12d74e347a51`**, 7,792,013 bytes. Actual Blender 4.5.15 official binary saved the private scene and separate new Blender process independently reopened and Cycles-rendered it.

Source/script commits on the shared only-scope feature branch:

- Material Blender geometry editor `tools/car_modeling/slotA_daytona_r13_native_visor_rim_edge_loops.py` @ `742fc5f49c87ed981be3f62d751b78638d1d9ad6`.
- Independent genuine source scene QA and actual Cycles renderer `tools/car_modeling/slotA_daytona_r13_independent_native_reopen_cycles.py` @ `18327049dda5f210fd82337bfdac07dc900a9f85`.

## Real source-derived mesh edits, BEFORE/AFTER

Only six already-existing original-PMT-derived **cockpit** objects were changed in Blender; **13,120** actual vertex displacement operations across these objects. New geometry comes **only from subdivision of original-derived mesh edges**, not substitute objects:

| Original-derived existing object | Before vertices/faces | After vertices/faces | Physically moved vertices |
|---|---:|---:|---:|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1,885 / 3,584 | 1,885 / 3,584 | 480 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 650 / 648 | 2,594 / 2,592 | 2,125 |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 908 / 1,344 | 908 / 1,344 | 905 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9,720 / 17,285 | 9,720 / 17,285 | 8,222 |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 1,536 / 1,536 | 6,144 / 6,144 | 1,272 |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224 / 210 | 224 / 210 | 116 |

The existing dash instrument trough gained a curvature correction, the source-derived dashboard shroud acquired actual interpolated edge loops and rounded center/shoulder relief, and the existing native three-spoke metal got pressed relief around **eight original-derived physically open holes**. Wheel ring added real interpolated topology and shaped grip cross-section at upper thumb arcs. Existing metal bezel and native steering hub collar subtly reformed. No standalone new steering wheel or car. All six objects retain original local/world transforms and original UV-layer/material identity. All 107 other mesh geometry signatures and other camera/material/packed-image inventories unchanged. Existing original-derived non-manifold edges remain in dashboard (184), gauge bezel (466), and spoke metal (1597): unresolved geometry gate, **not** a quality PASS for shipping.

## Existing real Ferrari Spyder photos and actual private scene rendering

Private image source 1: exact 1971 LHD Daytona Spider, `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA-256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`, source https://www.wearecurated.com/inventory/1971-Ferrari-365-GTS4-Daytona .

Private image source 2: original Spider dash closeup, `REF2_dashboard_original_e91527ff82f3.jpg` SHA-256 `6c87cd360497eead51a8aba83c6c4e07986247c47f4dbd5a181fcecf81a1f004`, source https://www.octane-magazine.com/cars-for-sale/ferrari-365-gtb4-daytona-spider-1971-708126 .

Private image source 3: genuine 1972 Daytona Spider Mecum cockpit `REF5_mecum_interior_01_c37db04b5.jpg` SHA-256 `a021ba729a2275c6f73c349f6b2622d4ff42a6dcbd2b4791f6c57ca951b83754`, source https://www.mecum.com/lots/1132965/1972-ferrari-365-gts-4-daytona-spider/ .

Actual old R12 Cycles image SHA-256 `9154e6d1ac5025a6ff6672f628fee850fbe0a4287771d58d167da622eefc3b94`. New independently reopened official Blender 4.5.15 private **R13 actual Cycles** 720x480 3 samples SHA-256 `080e319e625c268c7956a36e8ca59b3e9bc648dd744443d9ce4afd3eccd9ec4a`; same transient *approximate* camera as R12. Actual RGB comparison: 13,747 / 345,600 pixels max-channel difference >3, and 5,495 >12. This proves a genuinely rendered visual change but **does not** validate real in-game camera or exact photo alignment.

- Private render R12/R13 comparison: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/SLOTA_R12_R13_PRIVATE_REAL_CYCLES_BEFORE_AFTER.jpg`, SHA-256 `286cc64a73d5e37a67aad66453b9903d638a96fa2df3ab662c18dd198c6f4fa5`.
- Private exact Spider dashboard photo/R12/R13 comparison: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/SLOTA_R13_PRIVATE_ACTUAL_SPIDER_PHOTO_R12_R13.jpg`, SHA-256 `37cfb36635f5804f7cd75937f2b390316772e322d03c6c1c26b99cb2673acb57`.
- Private audit source metrics: `SLOT_A_DAYTONA_P0_R13_ORIGINAL_VISOR_RIM_EDGELOOPS.json`, `SLOTA_R13_INDEPENDENT_NATIVE_CYCLES_AND_TOPOLOGY.json`, `SLOTA_R13_PRIVATE_SPIDER_R12_R13_PIXEL_AUDIT.json` in same private folder.

## Gating and safe boundary

- **PASS (local only):** real source SHA, original Blender provenance, official Blender 4.5.15 actual material .blend save, separate Blender process full genuine source reopen, 6 source-derived mesh edits, 107 unmodified meshes, 8 BVH-open spoke holes and genuine 720x480 Cycles image; no new car, external GLB, geometry outside cockpit, textures or runtime exports.
- **NOT COMPLETE / BLOCKED_INPUT:** Official hosted GitHub Action is smoke on public source, **not** actual privately licensed .blend/PMT QA; private licensed model not delivered to hosted runner. Do not describe hosted smoke SUCCESS as production source-scene audit.
- **NEEDS_QA:** actual original game driver-eye calibration, authentic exact Spider seven-angle matched photo/scene comparison, remaining inherited source nonmanifold, final dashboard and wheel human validation, and full 24h car window. Do not advance from `daytona365`.
- **Scoring:** R13 is another refinement of the same previously scored slot A original-derived Daytona P0 dashboard+steering achievement `FERRARI16-SLOTA-DAYTONA-P0-SOURCE-DASH-WHEEL-20261108-0D388F55`. No duplicate award; +0, independent AI1/slot C scores untouched.
- **Strict negative changes:** No original PMT write, no game vehicle export or conversion (OVC3/OVC/PMT/GLB), game packaging, actual runtime/VR build or test, exterior body/wheels/tires, material/PBR/normal creation, Model2, Dino, slot C or other branch change.
