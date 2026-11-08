# Ferrari F50 — Slot C authentic original PMT cockpit v21-r2 (2026-11-08 KST)

**State:** `ACTIVE / PARTIAL_NEEDS_QA`; no car transition. Original 24-hour window begins `2026-11-08T04:35:52Z` (13:35:52 KST) and may not advance even after elapsed time without quality PASS. This is the same F50 P0 feature; score delta **+0**.

## Non-negotiable original source provenance

- Read-only original native OutRun 2006 resource: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`; SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Actual original PMT directly imported .blend: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`; SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Exact immutable v20 source-derived input: SHA256 `e4b82bf586ac8459960b61117d4fb68b8a0e5fa22beae2006fb18b1edc0f47bc`.
- **New private, editable real original-derived Blender scene:** `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v21_r2.blend`; SHA256 **`5aec7398777dbec8c0fad9bc8fd2190474d929f992e9fed1e76cf566824eda6d`**; 1,539,191 bytes; source import and previous checkpoint not overwritten. Licensed game asset not uploaded to the public GitHub repository.

## Real in-place source geometry changes

Only 3 pre-existing original PMT-derived F50 cockpit mesh IDs out of 42 changed. Original vertex/face topology and object IDs/coordinate transforms/UVs/materials/cameras remain unchanged. **39 remaining original source meshes retain identical geometry SHA hashes**.

| Original object name / region | v20 → v21-r2 verts/faces | Existing vertices displaced | Max displacement | Original-object mesh SHA before → after |
|---|---:|---:|---:|---|
| `object00_group01_material028_a0` gauge visor/cowl | 5506/7552 → 5506/7552 | 2,015 | 4.200 mm | `2beef9bfedd70361f8be1d55c58d95959e0eaf185493c6eb2fa6b352f082ee16` → `85fe94355dd228489b18571cbed01901612387094e478d3427d317f485eda2ae` |
| `object21_group01_material002_a0` authentic F50 three-spoke rim | 13552/26496 → 13552/26496 | 6,054 | 1.985 mm | `ff0d50d358343794daef0183a0e0f4c1456859932e9609df1af2e55beb1d90db` → `e0efcd1a6814319ffe3c30e322d76fbcc0f6db7282ca1c1569d580b6ef68d1c5` |
| `object21_group00_material000_a0` original wheel horn cup and hub | 2738/4464 → 2738/4464 | 562 | 2.300 mm | `ff4f9ced8d5d6873ebf57922ecf6da3efd1519eaf5f16342f0b32c04895f6a31` → `352eef9090c34cc852734d3f90d71dc8c29ad84f0c689109119c8ac23bf37d99` |

Dashboard P0: restored a smoother visor/cluster cowl arc by **normal-side-preserving, two-pass local quadratic curvature fitting over the existing PMT-derived surface**. Original mesh boundaries/corners retained. F50 wheel P0: upper rim grip cross section/three-spoke shoulder positions adjusted in native source mesh. Original hub P0: limited front-surface smoothing while retaining original source six-fastener positions. No detached component or fabricated substitute car.

**Rejected and not promoted:** first `v21` trial directly averaged connected triangulation vertices, which visibly amplified fan-shaped gauge cowl ridges. `v21-r2` was rebuilt directly from independently SHA-confirmed v20, not layered on rejected trial; comparative render inspection shows materially smoother gauge visor, though some original edge creases remain. No credit for trial/retry.

## Actual Blender/photo verification

- Official **Blender 4.5.15 LTS** opened v20, modified existing source mesh, saved separate private v21-r2, then **a new independent Blender process** opened v21-r2, v20 and v21-r2 again; all 42 original IDs/geometry source provenance, unchanged 39 mesh SHAs, input/output metadata and cameras checked. Independent render passed. Private receipt: `F50_SlotC_P0_v21_r2_Independent_Reopen_Audit.json`, status `PASS_INDEPENDENT_F50_V21_R2_TRUE_ORIGINAL_BLENDER_4_5_15_REOPEN_RENDER`.
- Real native-source before/after diagnostic comparison `F50_SlotC_P0_v21_r2_BEFORE_AFTER.jpg` SHA256 `f6b19f80b6d16c473f23e29943526be2dca279ca7ee65b0f6a008b5d8c997216`. Independent reopened steering render SHA256 `34f5d6086df1ada1158e1976a79ba05028ac2b41bde3ca6c1d1352d8d90fd305`.
- **Matched non-game diagnostic camera**: RGB max-channel delta >3: gauge 24,065 / 448,000 pixels; wheel 21,737 / 448,000 pixels. Private receipt `F50_SlotC_P0_v21_r2_Compare_Metadata.json` SHA256 `ca4d816271c7bb1795993e03c1b5c60b9af50308267ec49cabccd939adfd39fb`. This is evidence of real geometry revision, not game camera calibration or authentic likeness PASS.
- N100 existing F50 photo library and `MANIFEST.json`/`COVERAGE_MATRIX_16x8.csv` checked. Two private exact-model photo references: `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` (PistonHeads source; photo SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`) and `03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg` (Mecum 1995 F50; SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`). Private photo+actual scene comparison `F50_SlotC_P0_v21_r2_PRIVATE_PHOTO_GEOMETRY.jpg` SHA256 `0d08c3f46264f624b6974a5cd5dc284cb94773d04837d45156dcb8214e7c98b5`; no third-party image redistribution or texture usage.

## Incomplete gates / prohibited scope

- **Host GitHub Actions real-scene verification = `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`**. Hosted runner has no permission-cleared original F50 private .blend; source-only workflow is not a replacement for true native real-scene QA. Only N100 official Blender local actual-scene test is verified.
- Native original game driver-eye camera and steering pivot placement in game, full seven photo-matched viewpoints, complete 24-hour window and human-authenticity approval **not confirmed**. **P0 PARTIAL**, car stays `ACTIVE`; the factory wheel's 624 open/nonmanifold edges are preserved and unresolved.
- **No OVC3/OVC/PMT conversion/export, GLB substitute, game modification/integration, public game asset upload, exterior wheels/body, texture/normal/PBR work, slot A Daytona, finished Dino, Model2 or VR/DX branch changes.**
- Public code only: `tools/car_modeling/slot_c/f50_p0_source_mesh_v21_r2.py` and `tools/car_modeling/slot_c/f50_v21_r2_independent_reopen.py`; no repeated AI2 points for retries/CI/reopens.
