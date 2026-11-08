# Ferrari F50 slot C — original OutRun 2006 PMT in-place cockpit v27-r2 (2026-11-09)

**Only `active_by_slot.C=f50`. Checkpoint: SAVED / private Blender 4.5.15 independent reopen+render PASS; vehicle remains ACTIVE / P0 PARTIAL.** Slot A, completed Dino 246, Model2VR and all DX/game pipelines unchanged.

## Source-proof and privacy

- **Immutable original game Ferrari F50 compressed PMT**: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`; SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`; 439481 bytes. Read-only and rehashed before build.
- **First verified direct PMT import**: `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`; SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- **Immutable actual source-derived previous Blender**: `F50_OriginalPMT_P0_DashboardSteering_v26_r2.blend`; SHA256 `e6309fb522a76d9f7a1ee5fa3e3398389631067743a889e8d210cbf6982bf9b9`, rehashed before build and again after QA.
- **Accepted private editable Blender-only output**: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v27_r2.blend`; SHA256 **`45393c348358214c4332d449fcdb1c5a47d38b1958e4e1a043efd59eebe92faf`**, 1539966 bytes.
- Visual trial `v27` `60db9e5254a9e433b45503df188fb04643a957c99a51e22513d5caf606d6b397` was rejected after a new black groove appeared on the left inner steering rim. Final `v27-r2` was rebuilt **directly from `v26-r2`**, not the rejected `v27` or a substitute GLB.
- Public geometry edit script `tools/car_modeling/slot_c/f50_p0_source_mesh_v27_r2.py` is non-proprietary. Original/private game .blend, native PMT, rights-reserved photos never committed to this public repository.

## Original imported mesh IDs and actual geometry changes

| Source original mesh ID | Before / after vertices, faces | Moved existing source vertices | Maximum move, mm | Geometry SHA256 before -> after |
| --- | --- | ---: | ---: | --- |
| `object00_group01_material028_a0` — instrument hood | 5506/7552 -> 5506/7552 | 3882 | 2.026517 | `aef5bac35948624d33bef92070c34ca1c667e6669c0f7f37a11697544c12598b` -> `90ac6661da38cdd20b579ba514a0d2e970e5e8719c35cd130fb980c2a5e9bfa3` |
| `object21_group01_material002_a0` — original three-spoke/steering | 13552/26496 -> 13552/26496 | 546 | 0.550001 | `01b3ae52baecf6852264478fc7e13e286755a027f31b1b6d9135bf4104e89784` -> `9b338c040d659a1260a975494fe067b083435dfc7b93f56ea42e222931404d6b` |
| `object21_group00_material000_a0` — original six-bolt hub | 2738/4464 -> 2738/4464 | 497 | 0.990789 | `357c35a82d25146cc49dcac5983976126108639263fe1d3b6cafbb64316f8857` -> `977c7c00dc32eb272983e9b9bae0ed3c3f75aa32fd763cd73b996cf0dd52ceab` |

Only three of 42 original source mesh objects changed. All **other 39 source meshes**, original identities, faces/vertex indices, original UV/material slots, scene cameras/transforms and pivot positions hash/matrix-identical. The new dashboard hood upper silhouette is smoothed from the pre-existing genuine PMT contour: polynomial fitted to original 90-bin upper envelope, tapered to native corners and bounded 1.5mm in the local Y direction. Existing steering rim vertices remain unedited; a 546-vertex local surface fairing touches only the **three inherited spoke bridges**, masks the original nonmanifold boundary anchors and limits Z correction to 0.55mm. Original six-bolt hub's existing top face is subtly leveled with protected fastener/badge zones. No new entire steering wheel, car, mesh, materials or textures.

**Original inherited 624 open/nonmanifold steering edges are preserved**, not misreported as repaired. The game steering animation and native driver-eye camera correctness require runtime/source evidence and are unverified.

## Actual photographic comparison and Blender QA

- Private original F50 photo references in N100 `outrun2_vr_refs/20261104_16car_cockpit/03_F50/`, checked against `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv`: dashboard `REF2_dashboard_closeup_dad64db8c0a5.jpg` SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`; full F50 interior `REF5_mecum_interior_01_f8afa7e2a.jpg` SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`. The cropped photo evidence does not establish a seven-angle exact LHD audit. Photos remain private.
- Actual N100 Blender **4.5.15 LTS** source-backed build saved private scene, second independent Blender process loaded final -> old -> final, verified original 42 mesh identities, 39 unchanged mesh signatures and all camera/world transforms, and rendered real geometry.
- Receipt `F50_SlotC_P0_v27_r2_Independent_Reopen_Audit.json` **`PASS_F50_V27_R2_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER`**. Independent native-derived steering Workbench render SHA256 `8ec07e076a9852e3f8f5e46f9c485ee835dd660e5a79c43dfe3aaffef0cf37c3`.
- Same-camera **non-game diagnostic** 2×2 real source before/after `F50_SlotC_P0_v27_r2_SOURCE_BEFORE_AFTER.jpg`, SHA256 `ece1c05479513ae372b4a17cf03b6c4fd5ac8a06fba9aeb229d885bf8ef501f3`: 800x560 pixel differences RGB>3, dashboard 2264, steering 3023; **not** original game-eye verification.
- GitHub hosted Blender workflow remains only a source/queue and Blender smoke gate until the protected original-derived `.blend` is privately transferred with authorization. **`BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED` for actual hosted source-scene verification**; do not claim a hosted genuine F50 model test from smoke success.
- Remaining: authentic driver-eye/FOV/animation pivot proof; seven photo-view comparisons and QA; original steering boundary defects; human P0 dashboard/steering approval; first dedicated 24h start `2026-11-08T04:35:52Z`, earliest elapsed 24h `2026-11-09T04:35:52Z` (=13:35:52 KST). **No complete gate, car advancement or point credit.**

**Output restriction:** only updated source-derived editable .blend delivered; validation scripts/renders retained as private evidence. No OVC3/OVC/PMT conversion or game package/runtime source changes, no new car or GLB, no exterior/tire/wheel or texture/normal/PBR work. Slot C stays `f50`; AI2 scoring +0 (continuation of existing feature).
