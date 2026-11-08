# F50 slot C — original PMT-derived v28 cockpit source geometry (2026-11-09 KST)

**Scope:** ONLY `active_by_slot.C=f50`, driver-visible P0 dashboard and steering, immutable original source. Native game driver-eye is unverified. Vehicle remains `ACTIVE / PARTIAL_NEEDS_QA`; no advance to another car.

## Read-only source provenance

- Original compressed OutRun 2006 Ferrari F50 native game PMT: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`, SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Verified first genuine PMT-imported editable scene: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`, SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Immutable prior cockpit source v27-r2: `F50_OriginalPMT_P0_DashboardSteering_v27_r2.blend`, SHA256 `45393c348358214c4332d449fcdb1c5a47d38b1958e4e1a043efd59eebe92faf`.
- **New private editable source-derived v28**: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v28.blend`, SHA256 **`2134440787a2777daaaa555c73a0a748b299863828f270931afa0363645592ac`**, 1540391 bytes.
- Public non-proprietary Blender editing script: `tools/car_modeling/slot_c/f50_p0_source_mesh_v28.py`; depends on existing source-check helper `f50_p0_source_mesh_v27_r2.py` and makes NO exports.
- These private original files and F50 photos are **not** committed to the public GitHub repository.

## Genuine existing source object IDs, original vs changed geometry

| Original mesh ID | Before v/f | After v/f | Source vertices physically moved | Max move (mm) | Geometry SHA256 before → after |
|---|---:|---:|---:|---:|---|
| `PMT_F50_object00_group01_material028_a0` (Native instrument cowl) | 5506/7552 | 5506/7552 | 1592 | 0.899971 | `90ac6661da38cdd20b579ba514a0d2e970e5e8719c35cd130fb980c2a5e9bfa3` → `628e9201abeb01a96c57ce71b11c2b8e725db440adb148ae102fe99dc8b6df54` |
| `PMT_F50_object21_group01_material002_a0` (Native three-spoke/rim) | 13552/26496 | 13552/26496 | 3404 | 0.800002 | `9b338c040d659a1260a975494fe067b083435dfc7b93f56ea42e222931404d6b` → `92d40d14b0f285c34814548e8fb8bb08c3640b037f4345e45ed83c9ce7b4fb3d` |
| `PMT_F50_object21_group00_material000_a0` (Native six-bolt hub) | 2738/4464 | 2738/4464 | 395 | 0.474197 | `977c7c00dc32eb272983e9b9bae0ed3c3f75aa32fd763cd73b996cf0dd52ceab` → `6f9293228d9c1346d9067b935b2d980f8777fb0fa407fca2b42a989f9995d4e2` |

Source-derived cowl upper arch normal-gated fairing, inherited rim shoulder radial contour correction near the two top corners (bounded 0.8mm), and original 6-bolt hub face annulus local smoothing. All geometry edits are on the original **existing** mesh vertices; no replacement wheel/vehicle/mesh, no new topology outside the inherited PMT.

**Preservation invariants:** exactly 42 original source mesh objects, 39 other original mesh object SHA/matrix signatures identical; all source vertex/face counts and object IDs unchanged; camera transforms, UV and material counts unchanged. Original source steering wheel 624 nonmanifold/boundary edges **unresolved**, not claimed fixed. Source original game PMT, first imported .blend, and v27-r2 file SHA readback unchanged.

## Actual Blender 4.5.15 and model-render evidence

- Official installed **Blender 4.5.15 LTS** performed real v27-r2 source file build to v28 private .blend.
- A **separate fresh Blender process** opened actual v28 → immutable v27-r2 → v28; checked original mesh hashes, all original object IDs/matrices, camera transforms and independently rendered the real F50 steering mesh.
- Independent audit: `PASS_PRIVATE_F50_V28_BLENDER_4_5_15_FRESH_REOPEN_RENDER`. Fresh separate-process steering image SHA256 `e96ff950fea2a8191c4c47024d5eeff5453668eca1da88f50a7d1d4f22b8e622`.
- Same diagnostic, **non-game camera** before/after source comparison: `F50_SlotC_P0_v28_ORIGINAL_BEFORE_AFTER.jpg`, SHA256 `14f796ff683e01698eda8c75077831ef6314e330b6d5e255a3db3d2e17d32a88`. RGB>3 changes gauge **1735** / steering **3489** pixels at 800×560. These are real source renders, not synthetic concept images or a certified game-camera view.
- N100 F50 reference photos checked against `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv`, including `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` and `REF5_mecum_interior_01_f8afa7e2a.jpg`. Authentic exact F50 photos, but **not** seven independently verified game-eye-aligned views. Source photo licensing remains private.

## Explicit unfinished QA / blocked host gate

- **GitHub Actions native F50 scene check: `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`**. The public GitHub-hosted Blender smoke job can confirm toolchain and script/queue tests, NOT actual proprietary F50 .blend rendering because the authorized private scene is not available to the runner. Do not misreport hosted smoke as genuine native model validation.
- Exact original driver-eye FOV and animation pivot, seven authentic F50 photo views, and 624 inherited wheel boundary edges remain unverified/unresolved. No vehicle `COMPLETE`, no forced 24h handover.
- AI 2 score: +0, same F50 ongoing model-quality continuation (no repeated credit for build/QA/checkpoint).
- **Strict exclusions respected:** no PMT/OVC3/OVC/GLB conversion or output, no game/VR change, no exterior/body/tire, no new textures, DDS, normal maps, ORM or PBR, no slot A, Dino, Model2 or DX branch changes.
