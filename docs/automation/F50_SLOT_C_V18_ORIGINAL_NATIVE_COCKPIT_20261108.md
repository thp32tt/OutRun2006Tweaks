# Ferrari F50 — Slot C original PMT cockpit geometry v18 (2026-11-08 KST)

**State:** ACTIVE / PARTIAL_NEEDS_QA; continuation of the already-counted F50 P0 geometry feature, **score +0**. No vehicle advancement. Do not touch slot A Daytona or completed Dino 246.

## Provenance, immutable exact hashes

- Protected original game resource: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`, SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Native-resource-derived authentic imported `.blend`: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`, SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Read-only input original-derived v17 `.blend`: SHA256 `418574c3d9075495a0695bc8c625c4c0d5fb12b6d106ce2069cdf3b36b2c040d`.
- **New private editable output (not committed to public GitHub)**: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v18.blend`, size **1,538,715 bytes**, SHA256 `c9c2156c21754a3982f8a2f0f602b45834f0f789010717fbc858053638b5f86d`.
- Real Blender 4.5.15 LTS used in private source environment; independent **separate Blender process** reopened v18, v17 and v18, verified all 42 original mesh IDs and cameras and rendered a new steering view: **PASS**. Hosted GitHub Actions cannot claim private original-scene verification: **BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED**.

## Three genuine existing PMT-derived cockpit source mesh changes

| Original imported object ID | v17 vertices/faces → v18 vertices/faces | Actual moved existing vertices | Max offset | Original mesh SHA → candidate SHA |
|---|---|---:|---:|---|
| `object00_group01_material028_a0` | 5506/7552 → 5506/7552 | 2441 | 6.000 mm | `91a0c1136fda7b0ec79d07f7e0834db12896d829392056d3ca8a4e05d5eb7561` → `ecb2bf25ce53fbc881a7db9790400786a76b4342f74fcefdc61303445fbd2cce` |
| `object21_group01_material002_a0` | 13552/26496 → 13552/26496 | 11350 | 0.912 mm | `d9662cf9cf72c72c853e36b884bdb3a24d76abb5f0c0c8070cea8fe6bf54fd57` → `69f0e5f9f0186e7696e2a329e0bea6fd4f6e63099c32101900dc15c5e950b832` |
| `object21_group00_material000_a0` | 2738/4464 → 2738/4464 | 2274 | 1.419 mm | `b2f4d4ecac0d7ffc82663d2add358351f13210f83aab343536b4d986282b1e33` → `8aea7b7d1f1ea6b44034d7cd50a9b7a9fb7263646aaf17f3689ddad3503a526e` |

Edits are native-cowl **normal-aware neighborhood surface relaxation** to reduce radial fan wrinkles; 3-spoke steering rim/grip/shoulder relief; existing hub and six original fastener-seat lip. **No new objects**. Other **39 source meshes unchanged in mesh SHA**; object/camera transforms, material slots, UV layers, all original source IDs intact; wheel native **624 nonmanifold/open edges unchanged** (not blindly patched). No exterior/tires, new textures/PBR/normal maps, GLB, PMT/OVC3/OVC exports, game modifications or VR/Model2/other-slot changes.

## Actual output QA and photo scope

- Private original v17/v18 Blender before/after 2×2 comparison: `F50_SlotC_P0_v18_TRUE_SOURCE_BEFORE_AFTER.jpg`, SHA256 `58ff344a79afc85f6f04e1710e5d8ed609587a8c5414ba3b60462228c007e94a`. Matched non-game diagnostic cameras, 800×560 views; measured RGB change threshold >3: **gauge 35,072 px**, **wheel 12,801 px**.
- Private side-by-side exact F50 dashboard photo + real scene: `F50_SlotC_P0_v18_PRIVATE_REAL_PHOTO_COMPARE.jpg`, SHA256 `c37db14e88ff4a557ec17a24e114c5b0619675640b62fa8579febb0bc233f078`. Photo not redistributed. Verified existing reference `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` from PistonHeads (original protected content).
- Independent freshly reopened v18 render: `F50_SlotC_P0_v18_INDEPENDENT_AFTER_STEERING.png`, SHA256 `caf9daefe33169c344e2119f160de5269c0fb006ba47af7b78c1c33e7e31d828`. Private QA result: `F50_SlotC_P0_v18_Independent_Reopen_Audit.json`.
- Real-scene geometry still **PARTIAL_NEEDS_QA**, because dashboard fan ripples remain in diagnostic views and native game driver-eye coordinates, seven photo-aligned viewpoints, wheel boundary topology and hosted private-scene Actions evidence are incomplete. Diagnostic non-game cameras do not prove game-eye alignment.
- Earliest 24h window end is `2026-11-09T04:35:52Z` (**2026-11-09 13:35:52 KST**), and quality gate can extend the assignment. Dino stays skipped.

## Reproducible public scripts (no proprietary assets)

- `tools/car_modeling/slot_c/f50_p0_source_mesh_v18.py` (strict source SHA guard, real native vertex edits, private output).
- `tools/car_modeling/slot_c/f50_v18_independent_reopen.py` (separate-process source-scene mesh SHA, transform, camera and render QA).
- Both scripts require genuine private game input. GitHub-hosted Actions with missing .blend must report **BLOCKED_INPUT**, not a false F50 PASS or a synthetic smoke-car substitution.
