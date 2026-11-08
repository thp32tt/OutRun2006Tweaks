# Ferrari F50 — slot C, original OutRun 2006 cockpit native geometry v19 (2026-11-08 KST)

**State:** `ACTIVE / PARTIAL_NEEDS_QA`; same existing F50 P0 source feature continuation, AI2 score +0 (no duplicate). No vehicle advance, no other slots.

## Exact immutable source lineage

- Read-only original native resource: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`, SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Verified directly imported original F50 source scene: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`, SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Input original PMT-derived v18 immutable `.blend`: SHA256 `c9c2156c21754a3982f8a2f0f602b45834f0f789010717fbc858053638b5f86d`.
- **New private Blender v19 editable model:** `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v19.blend`, SHA256 `fc37c4682aee385fab9d06fdf6abec8fc0325faa14996ed371b730a805d928bd`. The private licensed game .blend is not uploaded to the public repository.

## In-place existing original cockpit source-mesh edits

| Original PMT object ID | v18 vertices/faces → v19 vertices/faces | Moved existing vertices | Peak mm | Source mesh SHA256 v18 → v19 |
|---|---|---:|---:|---|
| `object00_group01_material028_a0` | 5506/7552 → 5506/7552 | 1424 | 6.221 | `ecb2bf25ce53fbc881a7db9790400786a76b4342f74fcefdc61303445fbd2cce` → `248992cd049a29c2c69b026979d863ef6c5f5a516167cb37e4455131c31f0c67` |
| `object21_group01_material002_a0` | 13552/26496 → 13552/26496 | 11236 | 1.080 | `69f0e5f9f0186e7696e2a329e0bea6fd4f6e63099c32101900dc15c5e950b832` → `328077c4d14747258f1fe67f9be344428add117a677c31a3cc04aef57af7e3a6` |
| `object21_group00_material000_a0` | 2738/4464 → 2738/4464 | 2207 | 0.889 | `8aea7b7d1f1ea6b44034d7cd50a9b7a9fb7263646aaf17f3689ddad3503a526e` → `b53b248f0301fe1c23ff05959ba2d116640fbcd8e9b7a7aa66d8b8d7d643c580` |

- Dashboard instrument cowl: local source-surface quadratic-fit smoothing of existing top/bottom mesh layers with native normal-orientation separation, reducing prominent radial fan wrinkles. Bounds and native triangulated silhouette retained; faint lower/side creases remain and **P0 is not final PASS**.
- Steering: refine only original 3-spoke rim grip sections/shoulder transitions. Hub: source center cup, ring, and six inherited fastener-seat relief.
- All **39 other original source meshes have identical geometry SHA**; no added mesh, object, GLB, new texture or materials. All native object IDs, original transforms/cameras, UV/material counts and polygon counts preserved. Existing native wheel **624 boundary/nonmanifold edges remain**; not blindly patched.

## Real Blender and photo QA

- Official Blender **4.5.15 LTS** opened actual private v18 and saved v19; separate fresh official Blender process reopened v19, v18 and v19, verified authentic source hashes of 42 meshes, cameras/object transforms/UV/material counts and rendered a genuine real-scene steering view: `PASS_INDEPENDENT_F50_V19_TRUE_ORIGINAL_BLENDER_4_5_15_REOPEN_RENDER`. QA audit saved privately at `F50_SlotC_P0_v19_Independent_Reopen_Audit.json`.
- Private matched diagnostic before/after comparison `F50_SlotC_P0_v19_TRUE_SOURCE_BEFORE_AFTER.jpg`, SHA256 `faa3d373c2f7288a42b73273562b677598635465a4f5db5adb2ee6fa74aeecb1`. Non-game diagnostic view counts, difference threshold RGB >3: **gauge 18,284 px**, **steering 10,975 px**. Pixel differences prove actual visible revision only, not photo-perfect likeness.
- Private existing F50 photo + v19 actual game-source scene comparison `F50_SlotC_P0_v19_PRIVATE_REAL_PHOTO_COMPARE.jpg`, SHA256 `31ceb8f8b58fdfac2c0b7715a12cd70f4c5874d1ea19709acab84b269b2b6a74`. Reference `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` is a real F50 dashboard/steering photograph indexed in the existing N100 MANIFEST, proprietary/private reference only. No image upload.
- The game-native driver-eye camera, true seven photo-matched viewpoints and human visual sign-off are **UNVERIFIED/INCOMPLETE**. GitHub-hosted Actions runner lacks the licensed private scene: `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`; source-only Blender 4.5.15 workflow does **not** prove hosted real F50 scene QA.
- Slot C minimum 24h from `2026-11-08T04:35:52Z` to `2026-11-09T04:35:52Z` (13:35:52 KST); retain F50 until all quality gates pass, even after that instant.

## Public scripts only

- `tools/car_modeling/slot_c/f50_p0_source_mesh_v19.py` (fail-closed exact PMT and source `.blend` hashes; original existing mesh editing, separate private `.blend` save).
- `tools/car_modeling/slot_c/f50_v19_independent_reopen.py` (independent actual scene verification).
- **Forbidden output count zero:** OVC3/OVC/PMT conversion or export, game mod/install/build, textures, normal/PBR, exterior/body/wheels/tires, Model2, Dino, VR, slot A and alternative GLB assets. Completed vehicle claim **false**, score **+0**.
