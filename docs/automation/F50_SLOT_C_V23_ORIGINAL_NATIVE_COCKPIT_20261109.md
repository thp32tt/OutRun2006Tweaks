# Ferrari F50 — Slot C native PMT-derived cockpit v23 (2026-11-09 KST)

**State:** `ACTIVE / PARTIAL_NEEDS_QA`; queue owner remains `active_by_slot.C=f50`. This is continued source geometry refinement of an existing F50 P0 feature, **not** 24h completion or a new scoring event. AI2 score delta +0.

## Input provenance and immutable original

- Game model: **Ferrari F50**, exact private read-only OutRun 2006 compressed native PMT: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` (439481 bytes), SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Direct original game PMT import into true editable Blender: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`, SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Exact native-derived prior source `.blend`: `F50_OriginalPMT_P0_DashboardSteering_v22.blend`, SHA256 `cc4090261747c8c013011e68d1781f5aa6f75bca478ec5c2e9fb6fd3f1c5fcc7`.
- **New saved private native-derived `.blend` v23:** `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v23.blend`, SHA256 **`92ef962e65686faef64877b3540b4311f103220fad659ab483bbc5c3ba816f0b`**, 1538961 bytes.
- All three input file hashes rechecked after saving. Never modified or published private PMT, photos, source import or earlier versions.

## Exact in-place original mesh edits (v22 -> v23)

Only three existing objects, named from original PMT object/group/material IDs, edited in Blender 4.5.15 LTS. All original mesh vertex/face topology preserved and other **39/42** source mesh geometry SHA identical; original cameras/transforms/UVs/material slots unchanged.

| Original source mesh object ID | v22 verts/faces -> v23 | Existing vertices moved | Max displacement | Exact source mesh SHA before -> after |
|---|---:|---:|---:|---|
| `object00_group01_material028_a0` instrument cowl and visor | 5506/7552 -> 5506/7552 | 1842 | 1.049995 mm | `eafae91ec88b7959dfe87fba29937817a3cb60c035c37fc7dfb98ad833793864` -> `c9ad46902db240eeefa667fe8f1beb5cb8377e862669ee445f30cceb327e1e64` |
| `object21_group01_material002_a0` original three-spoke wheel rim/grips | 13552/26496 -> 13552/26496 | 6084 | 0.905087 mm | `47fdc4ec9819f2ff4fb5635f7e9ba396be653830786887838909c439cb5f81c7` -> `a4e6388ebbed7da582c1f23f3ee860bc27d6b9ba7a2aa84d3563e192137ccd36` |
| `object21_group00_material000_a0` original six-bolt hub | 2738/4464 -> 2738/4464 | 513 | 0.900000 mm | `0c8d859b1076c1b91ef5f08ddd6b3be9b1516918ee91022dff02bef05ec294bb` -> `490dfb71323e1a72d53fa2af6ac75f7912eb8b1f1e06a2c314d8530f205cb896` |

Dashboard: smoothing existing source instrument-binnacle crown while retaining original sheet/edge seams. Steering: symmetric photographed upper hand-grip / lower rim transitions on existing three-spoke source vertices. Hub: bounded front face curvature, bolt seats/logo center excluded. No substitute GLB, from-scratch cockpit, additional mesh objects, textures or topology replacement.

## Direct proof and quality limitations

- Public source script only: `tools/car_modeling/slot_c/f50_p0_source_mesh_v23.py`; SHA256 of exact source text `5695e110db606608b288ede83273a340a188088ad6c4167a20759a6ddb0bb869`. Initial typo in input-guard V23 identifier was fixed before accepting an artifact; the first attempted run created NO `.blend` and counts +0.
- Private official Blender **4.5.15 LTS** opened source-derived v22, sculpted 3 original objects and saved new v23. Independent **second Blender process** reopened actual v23 -> verified v22 -> reopened actual v23 -> independently rendered. Receipt: `F50_SlotC_P0_v23_Independent_Reopen_Audit.json`, `PASS_F50_V23_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER`. Independent steering image SHA256 `a1cb8834351f0ac669b4db1166ffc218af57bc005de4fa7f2382c45f3cb3fb97`.
- Matched native source-diagnostic (not game driver-eye) before/after 800x560 Blender Workbench: gauge 525 and steering 7867 changed pixels (max RGB channel difference >3). Private comparison image `F50_SlotC_P0_v23_SOURCE_BEFORE_AFTER.jpg` SHA256 `f938d0edc4d4ffd7417b07502c0d21b69a8f55c54394909a5db9f653cf5c6491`. Actual visual improvement is modest; do **not** claim full photo authenticity.
- Verified local reference photos (private only): F50 `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`; `03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg` SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`. Existing COVERAGE_MATRIX_16x8 F50 dashboard still candidate needs verification, center shifter PASS, full seven-photo views incomplete.
- Original steering mesh retains **624 pre-existing non-manifold/open edges**; not blindly repaired. Original game eye/FOV and animated steering pivot behavior **UNVERIFIED**, full seven driver-visible views **INCOMPLETE**, hosted GitHub runner true private original `.blend` still **BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED**. Hosted workflow validates Blender toolchain/source only if SUCCESS, not native scene. **No vehicle COMPLETE claim**.

## Exclusions / ownership / score

No other car or slot touched. Daytona365 stays slot A, completed Dino246 excluded; no body/exterior wheels/tires, textures/PBR/normal/DDS, GLB/OVC3/OVC/PMT output, game packages, VR/DX/Model2/UW2 sources. First F50 allocation 2026-11-08T04:35:52Z, earliest full 24h 2026-11-09T04:35:52Z; further P0, camera, photo and official private scene QA needed before any queue advancement. Same-feature continuation score +0 (retry also +0).