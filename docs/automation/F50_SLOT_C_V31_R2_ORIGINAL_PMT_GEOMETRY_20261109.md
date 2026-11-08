# Ferrari F50 slot C: genuine original PMT cockpit v31-r2 (2026-11-09 KST)

**Ownership, no handoff:** GitHub master queue `active_by_slot.C=f50`, `ACTIVE / PARTIAL_NEEDS_QA`. Slot A Daytona remains untouched; Dino 246 is completed by user, not revisited. This is an original-native cockpit 3D mesh rework only, **not** a new car or third-party GLB.

## Read-only original provenance

- Original game file `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`, SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`. Protected unchanged.
- Verified first true F50 original PMT-derived Blender import `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Immutable direct edit input `F50_OriginalPMT_P0_DashboardSteering_v30.blend` SHA256 `undefined`. Original local object identities and matrices verified before modifying.
- **Accepted private editable output:** `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v31_r2.blend`, SHA256 `b0d70a7a984098ede5be9494e62a227aa989fe4ccacd6cdd0b9f013cbfa15814`.
- **Public non-proprietary source script only:** `tools/car_modeling/slot_c/f50_p0_source_mesh_v31_r2.py` (source commit `d7434329ebec6bdbaf289ca135a026c7114e82bf`). No proprietary `.blend`, PMT or photo embedded in public GitHub.

## Actually changed existing original mesh topology coordinates

| Native PMT original imported object | v30 vertices/faces | v31-r2 vertices/faces | Existing vertices moved | Max distance (mm) | SHA256 before → after |
|---|---:|---:|---:|---:|---|
| `PMT_F50_object00_group01_material028_a0` | 5506/7552 | 5506/7552 | 947 | 1.649976 | `9e1aa3dbffd87c93d9e2a3c3c0e7be2ed7faf927ad103dcd06cea727146044ef` → `0b7fcfb54288fb1e577fc872c6fe1f315fa340cb2d237547c00f177b824c141c` |
| `PMT_F50_object21_group01_material002_a0` | 13552/26496 | 13552/26496 | 5134 | 2.4 | `add2710c720cf6fa805fc91ae1f4f1658950ea6c6dab5f3dc5115516c96989aa` → `12145eaf2b444b504047c0b632436ac54b562d2b682e37db128f9269b79d9200` |
| `PMT_F50_object21_group00_material000_a0` | 2738/4464 | 2738/4464 | 541 | 2.099998 | `63c6ed1108733286bee22058b8318a4a0c25d8c53699c2b7706656629205a9c3` → `b15e7e8756a3f9bf174e4945897ed343f9f51ad942a2dcaa839d72b3f0b33b68` |

Total **6622 existing PMT-derived vertices modified** across the native instrument pod surface, original three-spoke ring/shoulder and real six-bolt steering hub wings. No replacement object, procedural car, new external model, retopology outside cockpit, animation pivot edit, imported GLB, new material, UV/texture, normal map/PBR. Preserve the original source top silhouette and all X/Y coordinates for the gauge cowl, while smoothing only its existing Z surface. The v31 test candidate with artificial bumpy cowl top was **rejected** and was NOT used as the accepted baseline or recorded as a new result.

Native object IDs, camera matrices, object world transforms, mesh UV/material counts, vertex/face counts remain unchanged. All **39/42 other original meshes** untouched by exact SHA content, including exterior. **624 existing steering-wheel nonmanifold/open edges unchanged, NOT repaired**; no claim of physical weld or complete spoke-to-rim perfection.

## Verified original F50 photos

Original local photo library `/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv` referenced without copy/publishing.
- Genuine F50 cockpit photograph: [1995 Ferrari F50](https://www.mecum.com/lots/1158440/1995-ferrari-f50/) `03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg`, private image SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`.
- Genuine F50 wheel/gauges/dashboard closeup: [Ferrari F50 30th-anniversary dashboard](https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812) `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg`, private image SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`.
- These photos show the F50 3-spoke wheel and broad smooth instrument hood; they guided bounded geometry edits to source objects only. **Photo/model perspective and real game eye are not calibrated**. F50 seven independent matched genuine photo views not complete; only the F50 center-shifter category currently tagged PASS_VISUAL in local coverage matrix, no false seven-view PASS.

## Actual Blender and comparison

- **Official locally installed Blender 4.5.15 LTS** opened the genuine private v30 original-derived cockpit scene and directly modified only 3 objects. Saved private v31-r2 file, then a **separate Blender process** reopened `v31-r2 → v30 → v31-r2` and validated source SHA, per-object SHA and camera identities, and rendered actual F50 source wheel. `PASS_PRIVATE_F50_V31_R2_ORIGINAL_GAME_BLENDER_4_5_15_FRESH_REOPEN_RENDER` (local QA).
- Private previous-vs-new real mesh rendering: `F50_SlotC_P0_v31_r2_ORIGINAL_BEFORE_AFTER.jpg`, SHA256 `77d854ae87a48bb3ecc47c2c42b31fb7c91a4158d42d56ec7289e3a99b03c40f`. Same non-game diagnostic camera, two 800×560 images per subject. RGB>3 changed pixels: gauge **2393**, steering **20420**. This is a geometrical difference test, NOT human visual fidelity approval.
- Independent reopen wheel render SHA256 `43dbb56a50750da8f30eaddb311a4f38da4d682e1074b7179763eb1a863f932c`. Local native SHA, first import and original v30 source all matched after production.

**Still BLOCKED/PARTIAL:** hosted GitHub Actions real private source .blend never transferred to a secure runner: `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`. Hosted smoke tests would not prove an original F50 scene. Exact original-game driver-eye/FOV/steering animation validation, matched seven F50 photos, inherited open edges, human P0 dash/wheel quality and full 24h QA gate remain unresolved. **No transition to next car, no vehicle COMPLETE**, leave slot C F50 ACTIVE / PARTIAL_NEEDS_QA. **No PMT/OVC/OVC3 conversions, no runtime/game/VR/Model2 source edits**, no exterior body/wheels/tires, textures, PBR, or other slot changes.

**AI2 unchanged:** same running F50 feature, no new independent scored achievement, no retry/QA double count. Latest scoreboard confirmed 2782 + 0 = **2782**.
