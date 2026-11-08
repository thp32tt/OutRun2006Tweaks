# Ferrari F50 slot C — original PMT cockpit geometry v25-r2, 2026-11-09

**Result: source-backed private .blend SAVED / independent Blender 4.5.15 fresh-reopen and Workbench comparison PASS; vehicle ACTIVE / P0 PARTIAL.** Slot C remains `f50`, not complete. This is a continuation of the same P0 dashboard and steering feature, **AI2 score +0**. Slot A Daytona365, Dino 246 and all runtime branches are excluded.

## Provenance: exact original game model and immutable input

- Read-only original OutRun 2006 **Ferrari F50** native compressed PMT: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` (439,481 bytes), SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`. Rehashed on 2026-11-09, unchanged.
- Verified authentic PMT-direct-import editable source scene: `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` (292,667 bytes), SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`. Rehashed, unchanged.
- Immutable previous original-derived geometry **v24** `F50_OriginalPMT_P0_DashboardSteering_v24.blend`, SHA256 `eda7f5a5ac489b93227b58456e51d02eec993672904f4467a79cb5b0fe2df086`. Rehashed, unchanged.
- **New accepted private editable source-derived v25-r2** `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v25_r2.blend`; **SHA256 `bfa8becc5d2bbd0258b135fbc8b3478b2725f8e5f5b8da9c95397cf5908e6da4`**, 1,540,124 bytes.
- First v25 `775fa517d197bda72edff3be51cf7781c044d01be7877a8a05f00badd76ac34d` was created as a *rejected trial* because its wheel/spoke interfaces might have excess sharpness; accepted v25-r2 was rebuilt **directly from v24**, not chained to rejected v25. Neither affects original/previous files.

## Existing original PMT mesh geometry only

No new vehicle/object/mesh added, no outside body, UV, texture or PBR changes. All 42 original source mesh object identities, vertex/face indices, world transforms and cameras retained. 39 untouched native imported objects identical by per-object mesh SHA.

| Original PMT object ID | Before → after vertex/face | Physically moved existing vertices | Max movement | Original geometry SHA before → after |
| --- | --- | ---: | ---: | --- |
| `object00_group01_material028_a0` instrument/dash cowl | 5506/7552 → 5506/7552 | 1691 | 0.749111 mm | `e07aaae7f2b8552328ea2384071dc1ca8e290b17715272ffccfcbc3a6f1138ea` → `1bf41eb343e0d2e656230418d91a82b95bc54b32c9b7d8899cd4713a67151be5` |
| `object21_group01_material002_a0` F50 original 3-spoke rim | 13552/26496 → 13552/26496 | 10627 | 1.241378 mm | `798fad5bea06c7922992d8e37e5ea70a3c971f17a13de034eee5c431528672e3` → `4643c224d88913fe1af2e2d5042d13f17824768249763169f1b6f57eb8c20fc0` |
| `object21_group00_material000_a0` original six-bolt hub | 2738/4464 → 2738/4464 | 493 | 0.663860 mm | `385dbcbfb715d4caddbdaec44ab5c4e7140e9b49a3e7d00ed987c65c46944d5a` → `32f68dcf0721c0785d3c8ec1398a05579a94ad2181de5d65fc524ea1a379e055` |

Changes retain native 3-spoke factory structure: upper visor normal-gated surface curvature fairing; existing rim local radius/depth smoothing with angular *spoke-root exclusion* to protect seam geometry; existing six-bolt hub plate fairing without changing logo island or fastener regions. The existing wheel's **624 non-manifold/open edges remain unchanged**; must be independently reviewed, not silently capped.

## Actual photos, Blender and limitations

- Existing N100 photo library `/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/03_F50/` and `MANIFEST.json` plus `COVERAGE_MATRIX_16x8.csv` reviewed. Genuine Ferrari F50 dashboard/steering `REF2_dashboard_closeup_dad64db8c0a5.jpg` SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`; full cockpit `REF5_mecum_interior_01_f8afa7e2a.jpg` SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`. Both rehashed; no private copyrighted photographs published to repo.
- Public non-proprietary geometry script `tools/car_modeling/slot_c/f50_p0_source_mesh_v25_r2.py`, private runner `f50_v25_r2_private_runner.py`. Build in authentic private original-derived scene using **official Blender 4.5.15 LTS**, then **independent fresh Blender process** reopens saved v25-r2 and previous v24, verifies original identities and 39 unchanged meshes, reopens v25-r2 and renders original geometry. Receipt `F50_SlotC_P0_v25_r2_Independent_Reopen_Audit.json`, **`PASS_F50_V25_R2_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER`**.
- Genuine private native-derived Workbench matched non-game before/after 800×560 views: gauge **227** pixels and wheel **16,893** pixels >3 RGB difference; `F50_SlotC_P0_v25_r2_SOURCE_BEFORE_AFTER.jpg` SHA256 `5b0ab6dee3e80424524625bb66c4386138edca6413e9e6f1d45f5b87a0017e5b`. Independent steering render SHA256 `9dcf8f9186379f4efd42c25cb8e05380f4a3583452541a675f1aac4c6e23691f`. Exact per-mesh metrics: private `F50_P0_DashboardSteering_MeshDelta_v25_r2.json`.
- This is **not yet original-game driver-eye QA**. True in-game camera eye/FOV and steering-animation pivot behavior are unverified; seven photograph-specific comparisons and high confidence photo match incomplete. Original wheel 624 open edges unresolved. **Hosted GitHub Actions genuine original .blend audit = `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`**: hosted runners do not have the private original scene; public Blender smoke cannot substitute for real model QA.
- First 24-hour allocation began `2026-11-08T04:35:52Z`; earliest 24-hour boundary `2026-11-09T04:35:52Z` (**13:35:52 KST**). Even after this time, completion and slot C advancement require source/photo/driver-eye/final P0 gates. Keep `ACTIVE / PARTIAL_NEEDS_QA`, no complete claim and score +0.

**Forbidden outputs:** no GLB substitute; no PMT/OVC/OVC3/game export or conversion, install, packaging, VR/DX/Model2/other branch edits, exterior body/wheels/tires, textures, normals, PBR, or Dino/Daytona changes. All private copyright-bearing game scenes and photos stay on N100 private storage.
