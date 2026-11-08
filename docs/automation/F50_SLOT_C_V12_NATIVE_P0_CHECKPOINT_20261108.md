# Ferrari F50 / Slot C / original native PMT cockpit P0 v12 — 2026-11-08 KST

**Status:** ACTIVE / PARTIAL_NEEDS_QA. User's 24h dedicated F50 slot started 2026-11-08T04:35:52Z and is NOT eligible for transition before 2026-11-09T04:35:52Z. Slot A remains Daytona365; user-done Dino246 never modified.

## Immutable original game provenance
- Game source (private, read-only): `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`; SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Authentic first F50 PMT import scene (private): `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`; SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Copied/unchanged prior true original-derived edit (private): `F50_OriginalPMT_P0_DashboardSteering_v11.blend`; SHA256 `33edb2a2b3673847569c9bc321f8442148478e6a996d606fbd3f1bca27a69b9f`.
- **New true source-geometry edited Blender scene:** `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v12.blend`; size **1,539,744 bytes**, SHA256 **`0cb722eea1d78640d74c7f2dee740bdc024e9623073936f752cb1cb7fb3e03e8`**. The native game file and v11 baseline retained intact; proprietary binaries/photos remain private N100 only, NOT committed/uploaded to public GitHub.
- Source code (nonproprietary): `tools/car_modeling/slot_c/f50_p0_source_mesh_v12.py` and `tools/car_modeling/slot_c/f50_v12_independent_reopen.py` @ `0a6591ca91bcd13fa5827125a7ca990b9dbbf054`.

## Actual original-mesh in-place geometric editing (official Blender 4.5.15 LTS)
| Exact original OutRun PMT object ID | Original derived v11 vertices/faces | Edited v12 vertices/faces | Existing vertices moved | Max deformation | Before mesh SHA256 → after |
|---|---|---|---:|---:|---|
| `object00_group01_material028_a0` (dashboard gauge shroud) | 5,506 / 7,552 | 5,506 / 7,552 | **3,426** | 3.659 mm | `9ac1da17…` → `47426218…` |
| `object21_group01_material002_a0` (3-spoke wheel/rim) | 13,552 / 26,496 | 13,552 / 26,496 | **10,029** | 3.604 mm | `39425354…` → `d1cc557d…` |
| `object21_group00_material000_a0` (hub backing/collar) | 2,738 / 4,464 | 2,738 / 4,464 | **2,494** | 1.677 mm | `ee41fbb2…` → `f8b3ea07…` |

**Physical sculpt:** formed source dashboard's overhanging instrument eyebrow, twin recessed pockets and lower fascia; altered native three-spoke lateral metal arm shoulder/return, leather rim shoulder/grip and bottom spoke lip; adjusted actual hub cup, concentric relief and six shallow bolt-seat impressions. There are zero added car/mesh objects and no complete cockpit reconstruction.

Before/after detailed exact object mesh hashes, polygon and transforms, native-source identities, topology, cameras/UV/materials/other 39 meshes unchanged are stored in the **private** `F50_P0_DashboardSteering_MeshDelta_v12.json` and `F50_SlotC_P0_v12_Independent_Reopen_Audit.json`.

## Real Blender evidence (local original private scene, not hosted source smoke)
- Blender 4.5.15 LTS process #1 opened verified v11 and imported source provenance; physically edited the 3 existing source-named meshes, saved v12 and rendered matched `QA_F50_GAUGE_DETAIL_NON_GAME` and `QA_F50_STEERING_LOCAL_NON_GAME` original before/after (800×560 each).
- Independent Blender 4.5.15 process #2 opened v12, reopened v11, compared all 42 native object IDs/geometric SHA, transforms and cameras, reopened v12 anew, and rendered `F50_SlotC_P0_v12_INDEPENDENT_AFTER_STEERING.png`, SHA256 `e09e0b50f1fdcb4f003616428b7cf5b1425fdf4bb05c047860a2be79228f2f45`: **PASS**.
- 39 other source objects hash-identical; 624 **pre-existing** native steering boundary/nonmanifold edges retained 624 (not yet quality PASS; intentionally not blindly sealed). Object matrices/UV/materials and source game assets unchanged.
- Proprietary-free private original-source 2×2 **before/after**: `F50_SlotC_P0_v12_REAL_SOURCE_BEFORE_AFTER_2x2.jpg` SHA256 `6f52a3db69c4bdd6f40254b1f99a65cbb19c891d5f80500297fce3c69c76f050`.
- Private photos+actual Blender 6-frame comparative view `F50_SlotC_P0_v12_PRIVATE_PHOTO_V11_V12_COMPARE.jpg` SHA256 `12a0af9470deef32b13c8273faa1f50a7eacc1d404e9925cef37a1aef8590bb5`. N100 reference library `MANIFEST.json` SHA256 `a4645b3bcc98443026951f4aba845bd8561aad85b8cd58a8c289be02d194225e`, `COVERAGE_MATRIX_16x8.csv`; exact F50 reference photos remain private, F50 7-view matrix remains INCOMPLETE (only shifter marked VISUALLY_VERIFIED).

## Explicitly incomplete / forbidden
- Calibrated original game driver-eye/steering animation pivot: **UNVERIFIED**. Same-camera test above is an intentionally NON_GAME diagnostic scene view, not gameplay proof.
- Seven F50 photo matching viewpoints, P0 subjective fit and full 24h vehicle QA: **INCOMPLETE**; therefore `vehicle_complete=false`, no slot advance.
- GitHub Actions 4.5.15 hosted runner has **NOT** been provided the authorized proprietary native .blend / photos; actual private-scene hosted QA is `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`. A toolchain smoke or static source CI is NOT a hosted F50 original-scene proof.
- No OVC3/OVC/PMT output/conversion, game integration, VR/runtime changes, third-party GLB, exterior, textures/normal/PBR, other slot, Dino, or Model2.
- **AI2 score:** GitHub SSOT already awarded the original F50 P0 task once: previous confirmed **2780** + this continuing same-feature geometry checkpoint **0** = **2780 cumulative**. No repeat counting.
