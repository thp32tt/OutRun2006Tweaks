# Ferrari F50 Slot C P0 v14 — original OutRun 2006 PMT cockpit geometry (2026-11-08 KST)

**State: ACTIVE / PARTIAL_NEEDS_QA / NOT COMPLETE.** Slot C remains F50 for its dedicated 24-hour window, first material commit 2026-11-08T04:35:52Z, earliest release 2026-11-09T04:35:52Z. Slot A Daytona and completed Dino 246 untouched.

## Protected true original source and editable lineage

- Read-only OutRun 2006 Ferrari F50 PMT: `rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Independent original native import with **42 original source-named meshes**: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Immutable genuine PMT-derived v13 input: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v13.blend` SHA256 `ef53e2b4be0e80237eb44bdd01695e1bb785e4654abba4bf9f936559ebc3180d`.
- **New genuine F50 original-derived editable v14**: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v14.blend` SHA256 `87cce97c87a15bb657599c5e2457a1c109658d58b65ec5488e8988b6e007c349`.
- New nonproprietary public geometry script `tools/car_modeling/slot_c/f50_p0_source_mesh_v14.py`, fresh-process QA `tools/car_modeling/slot_c/f50_v14_independent_reopen.py`. All source game files, original imports, private modified .blend and copyrighted photo references remain **private N100-only**; no proprietary geometry published to GitHub.

## Source ID geometry delta (native v13 -> v14)

| Real original PMT mesh ID | Vertices/faces before -> after | Changed existing vertex coordinates | Max local change | Geometry SHA256 before -> after | Nonmanifold before -> after |
| --- | --- | ---: | ---: | --- | --- |
| `object00_group01_material028_a0` | 5506/7552 -> 5506/7552 | 2804 | 1.84375 mm | `a0d6213dad3ca609eb074b7b2903c5aec2a3291845503bfc467fda7450826169` -> `be562487b4102326f55f022f30bbc534f456df6f3cc8356a6a7430bb352260a7` | 0 -> 0 |
| `object21_group01_material002_a0` | 13552/26496 -> 13552/26496 | 13551 | 4.07277 mm | `c4294f4adbedc292b9d08b820ca244027ffb92e80db6e4274e75a6996ec50478` -> `e240a908071264d40aa77e7756bd5c9e87b19742caf46dd1c6a0820ea30ac2f0` | 624 -> 624 |
| `object21_group00_material000_a0` | 2738/4464 -> 2738/4464 | 2279 | 1.11 mm | `5a143c5d7e077ee262b98dd15ed653583f06b7685230a89776b9438f49c586a3` -> `fcb6a75ea4785b1c5453d362ac64facc98b99a2c7069b09257f2f4396f6dc63c` | 0 -> 0 |

Only the genuine native **dashboard/instrument visor, source three-spoke MOMO-style steering rim/spoke mesh, original hub** were deformed. Photo-guided intervention on original topology: one-piece broad F50 gauge-hood crown with undercut and molded return; less angular steering ring, raised 10/2 grip and 9/3 spokes, six-o'clock web; existing hub circular horn-seat, stepped counterbore and six fastener lands. No invented horn emblem or new substitute vehicle, no new material/texture/normal/PBR/DDS, no new object.

All **39 other source meshes are signature-identical**. No source-object names/IDs, transforms, camera matrices, UV/materials, pivots, mesh vertex/face counts or original PMT changed. Native steering wheel's **624 nonmanifold edges remain 624**; not claimed healed.

## Actual official Blender 4.5.15 proof

- Downloaded Blender **4.5.15 LTS** from official release host, official archive SHA256 `0d2b8bb2efe97e6c8eb57de6b7322f8800e1984e3125b60decca5f6771e4773e` checked before extraction.
- Official real 4.5.15 locally on N100 opened the exact v13 source PMT-derived .blend, physically edited only original three mesh objects, saved new v14, independently launched a **second Blender process** that opened v14 -> v13 -> v14 and rechecked 42 source IDs, 3 changed vs 39 unchanged meshes, matrices/cameras/material/UV, original hashes and boundary counts.
- Real matched diagnostic original-scene Workbench images of gauge and steering: RGB max-channel difference >3 in **7493 / 42895** pixels out of 448,000 each; these are **not original game driver-eye captures**.
- Independent real steering image SHA256 `0408096a5ea990aafa20808ce9320a46fd7b4a012d8ebb7fe3c6761154740dda`. 2x2 private before/after `F50_SlotC_P0_v14_SOURCE_BEFORE_AFTER_2x2.jpg` SHA256 `4f478cadfdc1fd739750ea0cd722cd3798c75a2ee45e8e825cc23a5c75e0783f`; privately held genuine photo + model comparison `F50_SlotC_P0_v14_PRIVATE_REAL_F50_PHOTO_GEOMETRY_COMPARE.jpg` SHA256 `771d83a4ab53d2ca8b939dc99f51aed24e3f45f6812d9f360691ec0760bb2e82`. Private evidence: `F50_P0_DashboardSteering_MeshDelta_v14.json` and `F50_SlotC_P0_v14_Independent_Reopen_Audit.json`.
- N100 photo library `outrun2_vr_refs/20261104_16car_cockpit/MANIFEST.json` SHA256 `a4645b3bcc98443026951f4aba845bd8561aad85b8cd58a8c289be02d194225e`, F50 in `COVERAGE_MATRIX_16x8.csv` SHA256 `1f16c1dddbd436954fdfc486807382ad75a97adc0fe3c70f902d9c3307cfaac3`. Exact-model F50 reference sources: https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812 and https://www.mecum.com/lots/1158440/1995-ferrari-f50/ . Copyright photos are never committed, and LHD/full-seven-angle coverage is not certified.

## Blocking gate and scope

The GitHub Actions `ferrari-geometry-blender.yml` runner installs official Blender 4.5.15 but **does not have the private original import/edited .blend**. Therefore **`BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`** for **hosted production real-model + independent-render validation**. A smoke-only success never counts as authentic F50 completion. The **private N100 actual-scene** save/reopen/diagnostic render is PASS. Exact game calibrated driver-eye, all seven correct F50 reference viewpoints, remaining nonmanifold and minimum dedicated 24h gate are incomplete. Keep C=f50 ACTIVE P0 PARTIAL, no early advancement and no completion claim.

**No** OVC3/OVC/PMT output/conversion, game deployment, packages, GLB substitute, exterior/wheels/tires, textures/normal/PBR, VR/DX11/DX9Ex/DXVK/Model2/UW2, slot A, Dino changes. **AI2 score change = +0** (continuation of same original F50 feature; no duplicate for retry/CI/renders).