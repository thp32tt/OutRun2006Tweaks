# Ferrari F50 Slot C original OutRun 2006 cockpit geometry v13 — 2026-11-08 KST

**State: ACTIVE / P0 PARTIAL_NEEDS_QA / NOT COMPLETE.** Do not advance F50 slot C before the minimum dedicated window ends at **2026-11-09 04:35:52 UTC (13:35:52 KST)** AND authentic original model driver-eye / photo seven view / P0 wheel+dash QA passes. Slot A = Daytona365 independently; Dino246 SKIPPED_DONE_BY_USER.

## Immutable ORIGINAL native game provenance
- Exact real OutRun 2006 **Ferrari F50** `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`; **read only**, rechecked and retained.
- Genuine original-native imported `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`; **read only**, retained.
- Source-derived original 42-mesh `F50_OriginalPMT_P0_DashboardSteering_v12.blend` SHA256 `0cb722eea1d78640d74c7f2dee740bdc024e9623073936f752cb1cb7fb3e03e8` rechecked, not modified.
- NEW separate, editable real **original source derived Blender 4.5.15** `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v13.blend` **1,539,625 bytes**, SHA256 `ef53e2b4be0e80237eb44bdd01695e1bb785e4654abba4bf9f936559ebc3180d`. NO new car, no GLB substitute, no external body/wheels/tires, textures/PBR/normal maps, exports/native output/game modifications.
- Previous checkpoint source and queue confirmed fresh before editing. All proprietary `.blend`, PMT/native and photos remain on N100 private storage, **not** published to GitHub.
- Reproducible public nonproprietary scripts: `tools/car_modeling/slot_c/f50_p0_source_mesh_v13.py` and `tools/car_modeling/slot_c/f50_v13_independent_reopen.py`. Former uses exact source PMT SHA, imported source SHA, v12 SHA, 42 native object guards; latter opens v13 in a separate official Blender 4.5.15 process and reopens source v12 and v13 for independent SHA checks.

## Actual in-place original Blender mesh geometry edits (v12 → v13)

| Exact original PMT mesh ID | Vertices/faces BEFORE → AFTER | Existing source-derived vertices moved | Max local vertex delta | Mesh geometry SHA256 before → after | Nonmanifold |
|---|---|---:|---:|---|---|
| `object00_group01_material028_a0` (F50 original molded dashboard/instrument visor) | 5,506/7,552 → 5,506/7,552 | **3,389** | **1.23781 mm** | `47426218...` → `a0d6213d...` | 0 → 0 |
| `object21_group01_material002_a0` (F50 original 3-spoke wheel/rim) | 13,552/26,496 → same | **10,034** | **4.06665 mm** | `d1cc557d...` → `c4294f4a...` | **624 → 624** |
| `object21_group00_material000_a0` (F50 original hub/column-facing cup) | 2,738/4,464 → same | **2,490** | **1.88615 mm** | `f8b3ea07...` → `5a143c5d...` | 0 → 0 |

Native/source object names, identities and pivot matrices held; 39 other original parts SHA-identical, original UV/material assignments and cameras retained. No additions/removals of meshes/geometry objects, no native resource writes. Native steering mesh retains 624 pre-existing open/nonmanifold edges, **not claimed fixed**.

Photo-guided P0 actual mesh changes: original F50 hood overhang/lip, twin physical gauge recesses, crown/fascia seam, subtle interior smoothing on existing source vertices; 10-and-2 grip inner/outer roll on existing wheel rim, lateral three-spoke shoulder fold and lower spoke fork; existing original hub cup/counterbore step, no invented badge/texture.

## Independent native Blender evidence
- Official Blender **4.5.15 LTS** real private editable PMT-derived v12 loaded, the three original source-named meshes sculpted, saved as new v13, actual BEFORE/AFTER matched `QA_*_NON_GAME` Workbench renders (800×560).
- Separate official Blender 4.5.15 process actually opened v13, re-opened v12 and v13, compared **all 42 original mesh IDs, 3 changed hash signatures, 39 unchanged mesh signatures, matrices, topology and cameras**, and rendered v13 steering independently: **PASS**, independent PNG SHA256 `caf6647d2ec9ccd1d49cec5a4df3e1dd94baae443dfbf2d601e62496b2a708c3`.
- Exact per-object SHA and metrics private: `F50_P0_DashboardSteering_MeshDelta_v13.json`; second Blender `F50_SlotC_P0_v13_Independent_Reopen_Audit.json`.
- Private baseline-vs-updated Blender comparison `F50_SlotC_P0_v13_SOURCE_BEFORE_AFTER_2x2.jpg` SHA256 `8503a0428154953d52ed95f7c6a47be4993081725aae15d86da383e76d475348`. Private exact-F50 reference photos and before/after Blender comparison `F50_SlotC_P0_v13_PRIVATE_F50_PHOTO_BEFORE_AFTER.jpg` SHA256 `3e9cf657f6b1d0a9a279109774bf74b6f0d2a7fe4eeff9ac9c683c3a74fc1049`. Photo source N100 `outrun2_vr_refs/20261104_16car_cockpit/MANIFEST.json` SHA `a4645b3bcc98443026951f4aba845bd8561aad85b8cd58a8c289be02d194225e`; `COVERAGE_MATRIX_16x8.csv` SHA `1f16c1dddbd436954fdfc486807382ad75a97adc0fe3c70f902d9c3307cfaac3`. Qualitative reference PistonHeads F50 dashboard `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` SHA `6d2a6655...`, Mecum F50 interior `03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg` SHA `cd313031...`; photos held private. These independent diagnostic cameras are **NON_GAME**, not exact driver-eye validation.

## Strict incomplete gates & score
- Genuine original game's seated driver-eye camera/FOV and live animation pivot placement **UNVERIFIED**; seven exact full photo viewpoints **INCOMPLETE**; F50 P0 cosmetic match **PARTIAL**.
- Hosted GitHub Actions runner includes official Blender 4.5.15 but does not contain private original .blend/native PMT, so **BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED** specifically for hosted full scene QA. Source-only workflow smoke success cannot be called original F50 model host audit.
- No OVC3/OVC/PMT conversion/output; no game install/mod package, Model2, VR backend, DX11, DX9Ex, DXVK, Dynamo, Daytona slot A, Dino246, exterior or textures changed.
- AI2 original F50 PMT P0 task already uniquely scored in scoreboard. Baseline **2780 + this same-feature continuation 0 = 2780** pending latest SSOT recheck; no retry/render/CI duplicate award.
