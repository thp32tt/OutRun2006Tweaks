# F50 slot C — original OutRun 2006 PMT-derived source cockpit v29 (2026-11-09 KST)

**SLOT C only:** GitHub queue `active_by_slot.C=f50` remains `ACTIVE / PARTIAL_NEEDS_QA`; Daytona slot A and completed Dino are unchanged. No 24-hour forced handoff, vehicle COMPLETE or new-car creation.

## Immutable source proof

- Original OutRun 2006 Ferrari F50 native compressed resource: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`, SHA256 **`10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`**.
- True original PMT-imported Blender first scene: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`, SHA256 **`d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`**.
- Prior original-mesh-derived editable input: `F50_OriginalPMT_P0_DashboardSteering_v28.blend`, SHA256 **`2134440787a2777daaaa555c73a0a748b299863828f270931afa0363645592ac`**; its 42 native object IDs still anchor this change.
- **New private source-derived editable scene:** `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v29.blend`, SHA256 **`44e33004a37a8a6ef2729e1680cda4f013d56559334987fcdd2978c2423b0c4e`**, 1,539,699 bytes.
- Non-proprietary editing script: `tools/car_modeling/slot_c/f50_p0_source_mesh_v29.py`. Nothing imports third-party GLB or replaces the native wheel/car.

## Three original cockpit meshes — genuine in-place vertex changes

| Original resource object ID | v28 vertices/faces | v29 vertices/faces | Original-derived vertices moved | Max movement (mm) | Mesh SHA256 before → after |
|---|---:|---:|---:|---:|---|
| `PMT_F50_object00_group01_material028_a0` (F50 original instrument binnacle shell) | 5506/7552 | 5506/7552 | 966 | 1.850009 | `628e9201abeb01a96c57ce71b11c2b8e725db440adb148ae102fe99dc8b6df54` → `0d269c730df489e26bc6d6f6243a912d5daa1ce0f203019528e48f05d87468ec` |
| `PMT_F50_object21_group01_material002_a0` (F50 original wheel/rim/three spokes) | 13552/26496 | 13552/26496 | 4691 | 2.699601 | `92d40d14b0f285c34814548e8fb8bb08c3640b037f4345e45ed83c9ce7b4fb3d` → `cf27f11b8ce8bb7b814a16d894a6922402a6cccdcb142f4360c4079cc9766ffc` |
| `PMT_F50_object21_group00_material000_a0` (F50 original six-bolt central hub) | 2738/4464 | 2738/4464 | 383 | 0.339381 | `6f9293228d9c1346d9067b935b2d980f8777fb0fa407fca2b42a989f9995d4e2` → `bcf5e7567b2e03e06f48dfde9de01fe56ca45e8eed47b422fd4cbe4b3f14d29f` |

Visually guided by two **private existing real F50 photographs** (verified image SHA: dashboard `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`, full F50 cockpit `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`). Source: `outrun2_vr_refs/20261104_16car_cockpit/03_F50/`. The real car's smooth black gauge arch and round top rim inform bounded adjustments on **existing original PMT geometry**, including radial shoulder-lobe relief and source-spoke face/hub fairing. The photo camera and diagnostic 3D camera are **not calibrated matched**; no claim of exact replica approval.

**Preservation proof:** 42 native source mesh objects; exactly 3 changed; the other **39 exact original object mesh signatures** match v28. All native mesh names/IDs, vertices/faces, 624 pre-existing nonmanifold steering edges, UV/material counts, original scene cameras/world transforms and steering object local matrices unchanged. 624 edges are still a known unsolved issue, not claimed fixed. Native original game PMT and all original/import/prior versions kept read-only.

## Real Blender source geometry and independent validation

- Official Blender **4.5.15 LTS** opened the actual protected v28 source scene, saved native F50 cockpit v29 `.blend`, then a **separate second Blender process** reopened v29 → v28 → v29 and confirmed all changed/unchanged source object SHA and cameras before rendering.
- Independent readback status: `PASS_PRIVATE_F50_V29_ORIGINAL_GAME_BLENDER_4_5_15_FRESH_REOPEN_RENDER`. Independent steering render SHA256 `e5f0fab97df2068d44bbf31637b45d001d732f016e81ccaffbb70254167827fc`.
- Genuine rendered source model v28/v29 same **non-game diagnostic** camera comparison: `F50_SlotC_P0_v29_ORIGINAL_BEFORE_AFTER.jpg`, SHA256 `24efbfa05a4c6881cb2d0fb5623ececd370aa6e7e802dfceaae84813533e7085`. RGB>3 changed pixels **3685 gauge** and **16629 steering** (each 800×560).
- Private Blender output v29 SHA256 verified again after saved independent QA.

## Remaining gate: do not advance or score

- **Hosted GitHub Actions real confidential PMT-derived F50 .blend:** `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED` until an authorized protected private scene transfer and appropriate runner verification; any public CI on script/queue or Blender installation is **smoke only**, not proof of a real F50 hosted source model.
- True game driver-eye/FOV and steering animation pivot are **UNVERIFIED**; seven independent authentic F50 photo matched angles and human P0 acceptance are **INCOMPLETE**; inherited 624 wheel boundary defects remain.
- F50 stays `active_by_slot.C=f50` `ACTIVE`, `PARTIAL_NEEDS_QA`. Prior F50 feature already has one adjudicated point; this continuation gets **AI2 +0** (no CI/rollover/delivery double-count).
- **Excluded and untouched:** Daytona slot A, Dino 246, all other cars, exterior, external wheels/tires, materials/textures/normal/PBR, game/VR/Model2/DX sources, OVC3/OVC/PMT/GLB conversions/outputs/installers.
