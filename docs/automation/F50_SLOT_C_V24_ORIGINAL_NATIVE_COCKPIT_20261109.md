# Ferrari F50 — Slot C original-game cockpit P0 v24 (2026-11-09 KST)

**Status: ACTIVE / PARTIAL_NEEDS_QA; owner `active_by_slot.C=f50` unchanged.** Dedicated 24h window began 2026-11-08T04:35:52Z; earliest eligibility for completion is 2026-11-09T04:35:52Z, subject to real P0 and photo QA. This is continuation of the same F50 feature: **AI2 score +0**.

## Authenticated original OutRun 2006 asset, all immutable

- Ferrari F50 original compressed game PMT, private read-only `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` (439481 bytes), SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Genuine original PMT-imported editable baseline `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`, SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Exact previous source-derived v23 `.blend` SHA256 `92ef962e65686faef64877b3540b4311f103220fad659ab483bbc5c3ba816f0b`, not modified.
- **New private editable output** `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v24.blend`, **SHA256 `eda7f5a5ac489b93227b58456e51d02eec993672904f4467a79cb5b0fe2df086`**, 1539739 bytes. Official Blender **4.5.15 LTS** saved actual native-derived source data.

## Actual source-object geometry (v23 -> v24)

No new car/cockpit mesh/object. Exactly **3 of 42** original imported source-ID objects have physically changed source vertex coordinates; same vertex/face counts and source IDs/matrices/UV/materials/cameras, 39 other original meshes SHA-identical.

| Source PMT object ID | Vertices/faces before and after | Existing vertices moved | Max distance | Verified v23 object mesh SHA |
|---|---|---:|---:|---|
| `object00_group01_material028_a0` — instrument cowl | 5506/7552 -> 5506/7552 | 1882 | 0.979662 mm | `c9ad46902db240eeefa667fe8f1beb5cb8377e862669ee445f30cceb327e1e64` |
| `object21_group01_material002_a0` — genuine three-spoke rim | 13552/26496 -> 13552/26496 | 12514 | 1.853884 mm | `a4e6388ebbed7da582c1f23f3ee860bc27d6b9ba7a2aa84d3563e192137ccd36` |
| `object21_group00_material000_a0` — six-bolt hub | 2738/4464 -> 2738/4464 | 522 | 0.972710 mm | `490dfb71323e1a72d53fa2af6ac75f7912eb8b1f1e06a2c314d8530f205cb896` |

Photo-guided adjustments use existing source geometry only: low and continuous gauge eyebrow/cowl crest, top arc and symmetric F50 rim grip contour fairing, restrained front hub-plate relief away from six fasteners and badge island. Original wheel's **624 pre-existing non-manifold/open edges** have **not** been silently repaired. This is controlled contour editing, **not** a new instrument cluster, separate detail mesh or a fully photo-matched replacement.

## Mesh hash before -> after (same original object IDs and faces)

- Instrument cowl `object00_group01_material028_a0`: `c9ad46902db240eeefa667fe8f1beb5cb8377e862669ee445f30cceb327e1e64` -> `e07aaae7f2b8552328ea2384071dc1ca8e290b17715272ffccfcbc3a6f1138ea`.
- Original three-spoke rim `object21_group01_material002_a0`: `a4e6388ebbed7da582c1f23f3ee860bc27d6b9ba7a2aa84d3563e192137ccd36` -> `798fad5bea06c7922992d8e37e5ea70a3c971f17a13de034eee5c431528672e3`.
- Factory six-bolt hub `object21_group00_material000_a0`: `490dfb71323e1a72d53fa2af6ac75f7912eb8b1f1e06a2c314d8530f205cb896` -> `385dbcbfb715d4caddbdaec44ab5c4e7140e9b49a3e7d00ed987c65c46944d5a`.

## Verified Blender original-source QA

- Public geometry script: `tools/car_modeling/slot_c/f50_p0_source_mesh_v24.py`, file SHA256 `571fbe05f5754c2955ce3b33b45720822b9ab88030486f5efef459b2a4e00caf`.
- N100 private Blender 4.5.15 build opened exact v23 and saved v24. Separate fresh Blender process reopened v24 and v23, compared all 42 original mesh identities and geometry SHA plus cameras, then reopened v24 independently and rendered genuine steering source; `PASS_F50_V24_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER`.
- Matched non-game 800×560 Workbench before/after for real PMT-derived parts: GAUGE **744** pixels changed and STEERING **22326** pixels changed with max RGB delta >3. Private comparison: `F50_SlotC_P0_v24_SOURCE_BEFORE_AFTER.jpg` SHA256 `fac6981b2f722289c3fc89b702137b005920c30002ecde625b1ba828f8e2b4d4`.
- Private evidence `F50_P0_DashboardSteering_MeshDelta_v24.json`, `F50_SlotC_P0_v24_Independent_Reopen_Audit.json`, and paired genuine before/after renders. **The first audit attempt failed** a stale v23 stage-number assertion; patched the v24-only audit guard from 69 to 72 without modifying saved source v24; independent audit then passed. Retried QA is +0.
- Reference source library `outrun2_vr_refs/20261104_16car_cockpit/03_F50/`; exact F50 photos reviewed privately: `REF2_dashboard_closeup_dad64db8c0a5.jpg` (SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`) and `REF5_mecum_interior_01_f8afa7e2a.jpg` (SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`). Full seven authentic views and matched driver-eye still incomplete.

## Explicit BLOCKED and exclusion report

**GitHub-hosted real private .blend QA = `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`**. The public GitHub Actions workflow can validate the official Blender installation, queue guard and code-only smoke, but cannot authenticate or render the N100 private proprietary original scene without permission-cleared transfer. Do **not** interpret a hosted smoke PASS as genuine F50 scene QA. Exact game driver-eye, real animated steering pivot, seven calibrated photographs and final visual P0 quality remain **UNVERIFIED / INCOMPLETE**, so do not set COMPLETE or advance slot C.

No OVC3/OVC/PMT exports, game integration, packaging, GLB replacement, exterior/wheels/tires, new textures/PBR/normal maps, or Model2/VR/DX11/DX9Ex/DXVK/UW2/slot A/Dino 246 source changes. Original private PMT/photos/.blend remain off public GitHub.
