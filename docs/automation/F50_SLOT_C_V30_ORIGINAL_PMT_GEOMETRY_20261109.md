# Ferrari F50 cockpit original-native PMT slot C v30 — 2026-11-09 KST

Only active queue slot C `f50`. This is a **genuine original OutRun 2006 F50 cockpit mesh continuation**, **NOT** a remade car, imported third-party GLB, or game-export package. Slot A Daytona and completed Dino 246 remain untouched.

## Source provenance, immutable

- Native original game: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`, read-only SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- First true PMT original import: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Previous edited source, reverified before processing: `F50_OriginalPMT_P0_DashboardSteering_v29.blend` SHA256 `44e33004a37a8a6ef2729e1680cda4f013d56559334987fcdd2978c2423b0c4e`.
- New **PRIVATE editable F50 source scene**, saved without replacing original: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v30.blend`, SHA256 `acd9e92e3456ff90cf3837383d56739b35d0cc93a5c9b95f0c522f3b73bb99ec`, 1539846 bytes.
- **Public non-proprietary geometry editing script:** `tools/car_modeling/slot_c/f50_p0_source_mesh_v30.py` SHA256 `f1e19aafa5114a3bd1e2767fcd926bf2f89b9819a1b27b3ca48924519366ad24` (GitHub code only; no original meshes/photos).
- Native source original object IDs are preserved, not renamed or replaced. Original game resource not written, PMT/OVC/OVC3/GLB exports not invoked.

## Physically edited original mesh, not texture shading

| Original PMT object | Before vertices/faces | After vertices/faces | Moved existing vertices | Max displacement (mm) | Strict mesh content SHA256 before → after |
|---|---:|---:|---:|---:|---|
| `PMT_F50_object00_group01_material028_a0` | 5506/7552 | 5506/7552 | 980 | 1.450002 | `0d269c730df489e26bc6d6f6243a912d5daa1ce0f203019528e48f05d87468ec` → `9e1aa3dbffd87c93d9e2a3c3c0e7be2ed7faf927ad103dcd06cea727146044ef` |
| `PMT_F50_object21_group01_material002_a0` | 13552/26496 | 13552/26496 | 4751 | 1.45 | `cf27f11b8ce8bb7b814a16d894a6922402a6cccdcb142f4360c4079cc9766ffc` → `add2710c720cf6fa805fc91ae1f4f1658950ea6c6dab5f3dc5115516c96989aa` |
| `PMT_F50_object21_group00_material000_a0` | 2738/4464 | 2738/4464 | 402 | 0.573214 | `bcf5e7567b2e03e06f48dfde9de01fe56ca45e8eed47b422fd4cbe4b3f14d29f` → `63c6ed1108733286bee22058b8318a4a0c25d8c53699c2b7706656629205a9c3` |

**Source-only total:** 6133 existing vertices physically moved across 3 original objects. Smooth source instrument-cowl arch, source three-spoke/hub junction and upper rim shoulder without synthetic rim bars, bolt placeholders or topology grafts. 42 original source meshes retained; 39 unrelated source-mesh SHA signatures unchanged. Same object identity, original matrix, UV layer count, materials, vertices and face counts, camera snapshot; previous **624** wheel non-manifold edges remain (**NOT repaired**). Scene metadata increments source-edit stage only. No external body/tires or textures, normal maps, PBR, ORM, game, VR/Model2 runtime.

## Private photos and honest coverage

N100 reference library `/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv` reviewed for F50, including:
- [Ferrari F50 dashboard photograph](https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812): `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg`, SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`.
- [1995 Ferrari F50 interior photograph](https://www.mecum.com/lots/1158440/1995-ferrari-f50/): `03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg`, SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`.
- These are PRIVATE source-holder photos, not redistributed and not published in this repository. Original matching LHD and precise viewing rays require further QA; available 16x8 matrix has no separately confirmed F50 driver-eye or steering-closeup tags, center-shifter marked PASS_VISUAL, other angles incomplete.

## Actual Blender 4.5.15 LTS audit and before/after evidence

- Official Blender **4.5.15 LTS** locally accessed PRIVATE original scene; separate process reopened **v30 → v29 → v30**, compared all original mesh signatures, and executed an independent real-scene render: `PASS_PRIVATE_F50_V30_ORIGINAL_GAME_BLENDER_4_5_15_FRESH_REOPEN_RENDER`.
- Saved original-model same-diagnostic-camera (not actual game-eye) rendered side-by-side: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_SlotC_P0_v30_ORIGINAL_BEFORE_AFTER.jpg`, SHA256 `f286b4678847ba039405dabdffcc58186d9626136aa416dbe93051b6c2fcaa80`.
- Real native-model view changed RGB>3 pixels: gauge **2595**, steering **11314**, both 800×560 pixels per view; difference proves rendering changed, **not** that the game cockpit is visually approved.
- Private v30 after-wheel image `F50_SlotC_P0_v30_AFTER_STEERING.png`, SHA256 `e5dd21ecfecbbd5a9d0196154c566e8766ddef078ef23682a713728e7a00d24c`. Separate-process reopened actual v30 independent wheel image `F50_SlotC_P0_v30_FRESH_REOPEN_WHEEL.png`, SHA256 `1de36b30fe01f7119fd104e3c4d3110c163a9d1f40a3248a369bcdca6a35d143`.
- Private reports: `F50_P0_DashboardSteering_MeshDelta_v30.json` and `F50_SlotC_P0_v30_Independent_Reopen_Audit.json`.

**Unmet gates:** original OutRun 2006 driver-eye/FOV and wheel pivot rig not calibrated; true matched seven genuine F50 photo-angle renders, human cockpit acceptance, wheel source inherited open-edge repair, and 24-hour quality gate all unresolved. **GitHub Actions hosted full source scene is `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`; no production Ferrari source/scene hosted CI PASS claim**. Local official Blender verification is not hosted GitHub Actions certification. **F50 remains `ACTIVE / PARTIAL_NEEDS_QA`; do not advance.**

**AI2 score:** latest GitHub scoreboard confirmed prior **2782 + 0** for same ongoing F50 P0 feature and uncompleted hosted source scene = **2782 cumulative**, no duplicate RUN_KEY credit. No AI1 impact.
