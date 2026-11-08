# Ferrari F50 slot C v35 — original OutRun 2006 cockpit-only native mesh modification (2026-11-09 KST)

**Status:** Actual F50 private Blender scene saved and official **Blender 4.5.15 LTS** separately reopened and rendered **PASS**, but vehicle **ACTIVE / PARTIAL_NEEDS_QA**; **do not advance**. No OVC, OVC3, PMT conversion, game deployment, textures/PBR/normal-map creation, GLB substitution, external car body/wheels/tires or Model2/VR/slot A/Dino changes.

## Original game provenance and guarded parent (verified by N100 SHA256 readback)

| Role | N100 path | SHA256 |
| --- | --- | --- |
| Original OutRun 2006 F50 read-only native PMT | `rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` | `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab` |
| Native PMT-derived first editable import | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` | `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31` |
| Accepted immutable source parent v34 | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v34.blend` | `3e5cc0f9d56f061d8c8c12a14ccc8aefdc0234dc4e845bd36c5a24ce8f66165a` |
| **Actual new editable original-source result v35** | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v35.blend` | **`0259f05b9f5b2ae3beeb25644f36de971e269b71000152fdb53d89fc7d6876ff`** |

New v35 private .blend is 1,540,005 bytes. The original compressed game PMT and earlier source .blend versions remain unchanged, no game-format output was produced. This is an existing original-imported scene's *direct vertex edit*, not a concept model or stock GLB.

## Native F50 P0 original mesh changes

| Original game imported object ID | Vertices/Faces before & after | Moved original vertices | Maximum displacement | Mesh SHA256 before -> after |
| --- | --- | ---: | ---: | --- |
| `object00_group01_material028_a0` — instrument/dash hood | 5506/7552 | 834 | 1.049995 mm | `2753414bdf45d2f0b46faf38d253cb874f74925046a81300cb724a7a819d3766` → `e095c91c9deba43fbc776ff481d40856ef754ee4d78736a3066f0838e7aa8612` |
| `object21_group01_material002_a0` — original 3-spoke sheet / lower leather ring | 13552/26496 | 1177 | 1.600000 mm | `c7845a16fe23503f837f9fe35234139744dfeeee75089720726c87f280b93a11` → `f17c90b11bdf696bf84092df60e480689e9844ceadd7a33d11ed326caa392d9f` |
| `object21_group00_material000_a0` — original six-bolt center hub | 2738/4464 | 557 | 1.450000 mm | `3932f604d521400c2b01467ee7d5e21288b65d93e9820c89638cf64b74c9defd` → `6f637af5c8dddd3e4ec1e0d40c57beca10bc5d42cd798cd75dcb701bf8d5488c` |

**Total 2,568 existing original vertices moved.** Exactly 39/42 other original source meshes have the same geometry/UV/material/matrix signatures, and both original QA cameras retain their matrices, lens and scale. All eight actual original steering boundary openings (48,48,72,72,72,96,96,120) and **624 open edges** retained in place, neither filled nor passed off as welded. Factory badge center, six-bolt islands, upper-rim area previously scarred in a rejected v33 trial and native object/steering coordinates protected.

## Existing F50 photo comparison — local N100 library (not public files)

Private references: `outrun2_vr_refs/20261104_16car_cockpit/MANIFEST.json` SHA256 `a4645b3bcc98443026951f4aba845bd8561aad85b8cd58a8c289be02d194225e` and `COVERAGE_MATRIX_16x8.csv`.

- Authentic F50 close-up from https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812 : `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`; RHD photo and cannot be assumed equivalent to a native game's driver-eye / LHD camera.
- Second original F50 cockpit photo `03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg` SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`.
- The existing coverage matrix only marks F50 center shifter as `PASS_VISUAL`; driver-eye, full dashboard, gauges, wheel, seats, inner door and windshield remain `UNTESTED_VISUAL`. Photo observation informs *local geometric smoothing*, not independently proven seven-view factory-correct modeling.

## Actual original Blender QA evidence

- New non-proprietary editing script `tools/car_modeling/slot_c/f50_p0_source_mesh_v35.py`, SHA256 `6b24c1546980e66b1671d46f3c826665e3e242982325f97220bc140b7cc6ae06`; source commit `04aa4729ddf386df8d5c2837c0ba713ce7427826`.
- N100 private `F50_P0_DashboardSteering_MeshDelta_v35.json` includes the source actual before/after object mesh stats and SHA256.
- N100 private `F50_SlotC_P0_v35_Independent_Reopen_Audit.json`: **PASS_F50_V35_OFFICIAL_4_5_15_FRESH_PROCESS_REOPEN_RENDER**: new process opens v35, reopens immutable v34 then v35, independently checks actual source identity, 42 original meshes, 39 untouched, exact source game PMT, original steering 624 boundary edges and camera/UV/matrix constraints. Independent steering render SHA256 `04ded2de15bbb6c3a20913c9780f3a2b381e2d09fdc4a5eaf595e6f3099bc22c`.
- Real original F50 model same-camera v34 BEFORE / v35 AFTER 2×2: `F50_SlotC_P0_v35_REAL_ORIGINAL_BEFORE_AFTER.jpg`, SHA256 **`4624a6b59fa50a5329cecaf2f5dea5712e86a47496884733ef0da378d8bbc176`** (151,039 bytes). 720×480 per view, Blender 4.5.15 Workbench non-game QA cameras. RGB difference >3 pixels: **hood 1,112; wheel/hub 5,870**. These quantify visible mesh changes, not full visual/photographic acceptance.

## Outstanding gates; do not promote

- Original game driver-eye/FOV exact orientation and seven authentic F50 photo-to-model matching views **not yet verified**.
- 624 inherited original open edges are preserved, not sealed; substantial hub surface irregularity still warrants human visual QA and targeted rework.
- GitHub Actions hosted runner lacks the proprietary genuine F50 .blend: **BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED** for *hosted real-scene* test; N100 actual official Blender 4.5.15 real-scene save/reopen already PASS. Do not call a smoke/test cube a car.
- F50 first material start `2026-11-08T04:35:52Z`; earliest 24h end `2026-11-09T04:35:52Z` (13:35:52 KST). Time alone cannot progress next vehicle. Keep `active_by_slot.C=f50`, `ACTIVE`, `geometry_gate=PARTIAL_NEEDS_QA`.
- **AI2 score change +0**, continuation of already-scored original F50 P0 feature. No duplicate score for new QA, render, retry or rollover.

Only editable private .blend, private before/after renders and non-proprietary Blender editing script/report retained. No PMT/OVC3/OVC output, no game integration, no unrelated branch changes.
