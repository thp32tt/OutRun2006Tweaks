# Slot C — Ferrari F50 original OutRun 2006 source-only Blender P0 checkpoint

**Status:** ACTIVE / P0 PARTIAL NEEDS DRIVER-EYE & 24H QA; NOT COMPLETE.
**Slot owner:** C = f50. Slot A = daytona365, Dino246 = SKIPPED_DONE_BY_USER.
**Task:** FERRARI16-SLOTC-F50-ORIGINAL-PMT-DASH-WHEEL-20261108
**Scope:** Original game cockpit dashboard/gauge/steering geometry ONLY; no vehicle reconstruction, other GLB, OVC/OVC3/PMT output, original-game patch or new texture/PBR/normal map.

## Verified immutable original input

Read-only user-owned original game installation:
`/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`
- Compressed source SHA256: `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`
- Decompressed PMT data SHA256 (computed only in RAM): `a080d3b5853063f9decdc92097b03148a1bee77c00340dd0d24f820ba17b07a7`.
- Additional F50-specific variants located but NOT imported into the editable candidate:
  - `obj_plcar_f50_t_pmt.sz` SHA256 `ab70f7dcc26a59112a6cf50c848f6449dc049bcd2d3ed67e89d94c1553977c72`
  - `obj_rc_f50_pmt.sz` SHA256 `2e667e691647e3212af1bbd42c5cc698e68d0716011bdc85b342ef7efd853d9f`
  - `obj_rc_f50_t_pmt.sz` SHA256 `4a2c4349be85048c0e71177362c076405e9cb3a6537d3b123fe5fe815cfd4c69`

## Private original-derived Blender files (never commit binary)
N100 folder: `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/`.

1. **Real source import:** `F50_OriginalPMT_CockpitSource_v1.blend`, SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`, 292667 bytes.
2. **Real P0 edited copy:** `F50_OriginalPMT_P0_DashboardSteering_v1.blend`, SHA256 `b7289f9ec1d772f9beca1c785f63c3536e8c501aee8a9a5710b2b086b7152e6d`, 349724 bytes.
3. **Real Blender diagnostic before/after comparison:** `F50_OriginalPMT_P0_BeforeAfter_Comparison.png`, SHA256 `efd580284a0f8b9340192159bac967c6484e7387834f15924c2f69a87ee320bd`.

Actual official **Blender 4.5.15 LTS**, verified official downloaded archive SHA256 `0d2b8bb2efe97e6c8eb57de6b7322f8800e1984e3125b60decca5f6771e4773e`. In-place edit saved, two actual preview views rendered, *independent fresh process* reopened with source SHA, object identity, modified mesh SHA/count, unchanged other objects and pivot matrices. Verified **42 original imported mesh parts; exactly three original meshes changed; 39 untouched**.

| Source PMT object/part identity (derived from native indices; original resource has no authored Blender name) | Before vertices/faces | After vertices/faces | Actual geometry |
|---|---:|---:|---|
| `object00_group01_material028_a0` | 10 / 8 | 346 / 472 | Source F50 instrument-binnacle face physical contour/recess/thickness |
| `object21_group01_material002_a0` | 110 / 184 | 898 / 1656 | Original 3-spoke steering wheel rim curvature/spoke relief |
| `object21_group00_material000_a0` | 14 / 12 | 78 / 124 | Original hub backing physical thickness |

Reference photos from N100 03_F50 private gallery; exact F50 dashboard photograph source [PistonHeads](https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812) and original F50 interior photo from [Mecum](https://www.mecum.com/lots/1182048/1995-ferrari-f50/). Private image contents not published.

**QA pending / not claimed:** real OutRun game driver-eye camera and source steering-wheel placement/animation transforms, photo-calibrated spatial matching/occlusion, seven viewpoints and required 24h dedicated window. Current views are explicitly `QA_*_NON_GAME`. Local official Blender real-scene PASS is **not** a GitHub hosted Actions real-scene PASS: private source .blend never uploaded to hosted runner. No gameplay/runtime proof. Do NOT advance slot C or score duplicate/retry checks. Public files contain only parser/import/rework/reopen scripts and this provenance memo; proprietary original PMT/.blend/photos never committed.

## Slot C original-source v8 geometry checkpoint — 2026-11-08

- **State:** `ACTIVE / PARTIAL_NEEDS_QA`, original F50 only; 24-hour minimum window started 2026-11-08 04:35:52 UTC and cannot end before 2026-11-09 04:35:52 UTC. No automatic advance. Driver-eye/steering animation placement and exact 7-photo view QA remain unverified.
- **Source:** immutable OutRun 2006 `obj_plcar_f50_pmt.sz` SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`. Verified original import `F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- **Input:** private F50 source-derived v7 `F50_OriginalPMT_P0_DashboardSteering_v7.blend` SHA256 `3ef39db64ac0464309db1e42902e514a20caeef07ca12f6fb017aec6c7d49b3b`.
- **Output:** private, separate original-derived `F50_OriginalPMT_P0_DashboardSteering_v8.blend` SHA256 **`6895c0e155a823000303b8da4262d4539e131b07cf47e377a82c9316a97e4cea`**, 1,539,087 bytes. Exact folder `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/`.
- **Source code:** `tools/car_modeling/slot_c/f50_p0_source_mesh_v8.py`, commit `bb22d979bd17897de7ec43650cd627a45bc6f87d`; independent verification `tools/car_modeling/slot_c/f50_v8_independent_reopen.py`, commit `cd9090a00662e00540c1a13095316f0428085a74`.
- **Native PMT object `object00_group01_material028_a0`:** existing dashboard/instrument visor 5,506 vertices / 7,552 faces unchanged count; 3,364 existing vertices shifted (peak 3.87617 mm). Mesh SHA `88c0937509649343e3fec1047967e0fa287bf1edc9cd810a3a70c55740e8568d` → `074a723b0e2229f798f35e5c3c579f79461967d9e75312e8ba32f9508dbeaeb1`; nonmanifold 0 → 0.
- **Native PMT object `object21_group01_material002_a0`:** existing native 3-spoke/steering rim 13,552 vertices / 26,496 faces; 8,929 existing vertices shifted (peak 2.54912 mm), thumb/grip and original arm shoulder contours, source rim/pivot retained. Mesh SHA `37721220f2dbe45825a6d408e5d2a7f5c74b7af2d26c4a05b6a35001f5204fcd` → `9315df69e58229abb81756b5746f3eca6500aaa86d8ab4f9805786b5fc25dcaa`; 624 pre-existing nonmanifold edges remain 624.
- **Native PMT object `object21_group00_material000_a0`:** existing hub 2,738 vertices / 4,464 faces; 2,146 existing vertices shifted (peak 1.14042 mm), existing metal cup/collar/bolt-seat surface relief. Mesh SHA `9b00233497a86957195031a49f2ea4c63b8510e5002e0c42e009244ee62fb5cd` → `ec15f701fcdf2c2756437c37416ce33d0507af07de08dd74bd1f41b45b28c05c`; nonmanifold 0 → 0.
- **Verification:** official private Blender **4.5.15 LTS** opened v7, edited the three existing original-derived meshes in place, saved v8, rendered two original-source v7/v8 camera-locked Workbench comparisons (gauge and steering), and **a fresh independent Blender process reopened v7 and v8, compared all 42 object hashes and rendered a separate v8 steering image: PASS**. All 39 other source meshes byte-signature-identical; mesh names/source IDs, transforms, UV, materials, cameras and read-only native PMT hashes preserved.
- **Private evidence:** `F50_P0_DashboardSteering_MeshDelta_v8.json`, `F50_SlotC_P0_v8_Independent_Reopen_Audit.json`, `F50_SlotC_P0_v8_*_GAUGE.png`, `F50_SlotC_P0_v8_*_STEERING.png`, `F50_SlotC_P0_v8_INDEPENDENT_AFTER_STEERING.png`; private F50 photo + before/after diagnostic sheet `F50_SlotC_P0_v8_PRIVATE_photo_source_after_dashboard_steering.jpg` SHA256 `a34fce0be01eb7661c1b24a1e995032b9906329cc1c89753bbe1d3a57270db13`. Image/photo is **not** licensed for publication and model QA cameras are **NON_GAME**.
- **GitHub Actions:** source-only workflow smoke cannot validate N100 private scene or true native model; hosted real-scene gate remains `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED` until an authorized secure scene transfer is supplied. This does **not** qualify as vehicle COMPLETE.
- **Scope respected:** no other vehicle, no Model2/Dino/slot A/VR branch, no original game modification, no OVC/OVC3/PMT output, no new car/third-party GLB, no exterior, no textures/normal/PBR. Same already-counted F50 P0 workflow continued; duplicate competition score **+0**.

## Slot C F50 v9 — source-backed in-place cockpit sculpt (2026-11-08, follow-up session)

**State:** `ACTIVE / PARTIAL_NEEDS_QA`. F50 remains in slot C; Daytona remains isolated in A; Dino 246 already complete, no changes. First 24h ownership started 2026-11-08T04:35:52Z and is not eligible for completion before 2026-11-09T04:35:52Z. Never auto-advance while P0/photo/camera QA unresolved.

**Read-only provenance (SHA256 rechecked on N100):**
- Original OutRun 2006 actual `rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`: `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- True initial native imported `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`: `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- v8 immutable starting editable `F50_OriginalPMT_P0_DashboardSteering_v8.blend`: `6895c0e155a823000303b8da4262d4539e131b07cf47e377a82c9316a97e4cea`.
- **NEW v9 original derivative** `F50_OriginalPMT_P0_DashboardSteering_v9.blend`: `54a559ec42e9d119d2151f1c5798b6249cc1477736e21ec4276d9479bdd7a22e`, 1,539,653 bytes. Private path `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/`. This private proprietary scene is not in GitHub.

**Precisely changed, existing PMT source-named meshes (no whole-car substitute, zero new objects):**

| Original source ID | Before/after vertices/faces | Moved existing verts | max local mm | v8 mesh SHA256 → v9 mesh SHA256 |
|---|---|---:|---:|---|
| `object00_group01_material028_a0` — instrument visor and dashboard | 5,506 / 7,552 → 5,506 / 7,552 | 3,613 | 2.45965 | `074a723b0e2229f798f35e5c3c579f79461967d9e75312e8ba32f9508dbeaeb1` → `7cc160bd2679264180429eb644450704b3ab117ac9a0d9230b17e744db301db3` |
| `object21_group01_material002_a0` — factory 3-spoke/steering rim | 13,552 / 26,496 → same | 8,354 | 2.88299 | `9315df69e58229abb81756b5746f3eca6500aaa86d8ab4f9805786b5fc25dcaa` → `9003b74d88700d7d27e6cf0d04ec321031d51411a13a6c587a789d063d2eddb7` |
| `object21_group00_material000_a0` — native steering hub | 2,738 / 4,464 → same | 2,652 | 1.29173 | `ec15f701fcdf2c2756437c37416ce33d0507af07de08dd74bd1f41b45b28c05c` → `43eaf739dd457d30b8e257a9a96c0405beee4fbaae37d630db81c0b8bd7aca19` |

**Actual Blender QA:** official private Blender 4.5.15 LTS reopened the verified v8 binary, sculpted only the three existing source meshes, saved v9, rendered matched `QA_*_NON_GAME` before/after gauge and steering images, and **separate Blender process** reopened v9 and v8, compared mesh/object/camera/UV/material/matrix signatures and saved `F50_SlotC_P0_v9_INDEPENDENT_AFTER_STEERING.png`: **PASS**. Exactly 39 other original imported source object geometry hashes remain identical. Original PMT and first imported blend original SHA unchanged. Factory 3-spoke wheel's **624 pre-existing boundary/nonmanifold edges remain 624**; topology was intentionally not closed without exact source-loop QA.

**Private photo-to-geometry evidence:** `F50_SlotC_P0_v9_PRIVATE_F50_photos_source_after.jpg`, SHA256 `e0be3fa2677e027b7a58025bee94762a9e9f0d9ff21ef0119502a0ce8ab28a49`; includes private actual F50 interior `03_F50/01_interior.jpg` and exact-model PistonHeads dashboard `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` alongside two actual original-source before/after Blender views. Reference sources must remain private; exact driver-eye calibration and seven-view matching remain **NOT VERIFIED**.

**Public source/verification commits:** `tools/car_modeling/slot_c/f50_p0_source_mesh_v9.py` @ `25be5c703ab23805ae7b25d0532960ae59e356e3`; `tools/car_modeling/slot_c/f50_v9_independent_reopen.py` @ `66cb13786c57e9091f575c413d925bf965f6b850`. No OVC3/OVC/PMT conversion/output, no game application, no extra exterior wheels/body, no textures/PBR/normal, no Dino/Model2/VR source, no slot A geometry.

**Limitations:** GitHub Actions installs Blender 4.5.15 but hosted runner still lacks authorized private original .blend: `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`. Source-smoke workflow cannot be represented as real hosted original-scene audit. Native game driver-eye/steering animation pivot in actual runtime unknown. Full photo 7-view, 24h and P0 subjective quality gate remain outstanding; `vehicle_complete=false`. **Score +0**: continued same F50 P0 native geometry, no duplicate credit.

## Slot C F50 v10 — original PMT cockpit geometry (2026-11-08 KST)

**Task:** `FERRARI16-SLOTC-F50-P0-SOURCE-DASH-THREESPOKE-HUB-V10-20261108`. **Status:** `ACTIVE/PARTIAL_NEEDS_QA`; the 24h F50 assignment is preserved, earliest full-window end `2026-11-09T04:35:52Z` (13:35:52 KST). No change to slot A, Dino, Model2, game runtime, exterior or textures.

**Read-only source:** actual original OutRun 2006 `rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`. Verified genuine native import `F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`. Starting copied original-derived **v9** `F50_OriginalPMT_P0_DashboardSteering_v9.blend` SHA256 `54a559ec42e9d119d2151f1c5798b6249cc1477736e21ec4276d9479bdd7a22e` remained immutable.

**Actual new editable source-backed result:** private N100 `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v10.blend`, size **1,539,303 bytes**, SHA256 **`602f5628e658e29658378c4ae42e5010633fffd366deea7370f7764049e67bac`**. This binary contains original proprietary game scene and is **NOT publicly committed, nor transferred to hosted GitHub Actions**. Nonproprietary source script `tools/car_modeling/slot_c/f50_p0_source_mesh_v10.py` commit `0823aa30ae90a15abec6e4ae8b15f24a37d9efce`, independent reopen `tools/car_modeling/slot_c/f50_v10_independent_reopen.py` commit `91f3eb0f0f3a55fa5d55d8e02a016b94dd68fa72`.

Three **existing source-ID meshes**, all geometry modified in-place, original faces/vertices counts unchanged:

| Original PMT mesh ID | Before/after verts/faces | Source positions moved | Peak delta | Mesh SHA256 before -> after | Nonmanifold edges |
|---|---|---:|---:|---|---:|
| `object00_group01_material028_a0` (dash instrument cowl) | 5506/7552 -> 5506/7552 | 3,336 | 2.32565 mm | `7cc160bd2679264180429eb644450704b3ab117ac9a0d9230b17e744db301db3` -> `53e6fe791a97d71f32abd125a699a3531274b20172b443ff8fe1460b0ba348ce` | 0 -> 0 |
| `object21_group01_material002_a0` (original 3-spoke wheel/rim) | 13552/26496 -> same | 9,579 | 1.95724 mm | `9003b74d88700d7d27e6cf0d04ec321031d51411a13a6c587a789d063d2eddb7` -> `099543381308ee8eb155347b2b794e7fa820102e5b9deed137a2fe7f73682377` | 624 -> 624 |
| `object21_group00_material000_a0` (factory steering hub) | 2738/4464 -> same | 2,538 | 0.80986 mm | `43eaf739dd457d30b8e257a9a96c0405beee4fbaae37d630db81c0b8bd7aca19` -> `5d892685de7586d773009bed67aef8b09cd600ec42070650b0e0406cc194de23` | 0 -> 0 |

Actual modeling: sculpted original instrument visor upper continuous brow, lip, dual instrument inset, side shoulders; photo-guided 10/2 upper rim grip, existing two horizontal spoke stampings, native lower spoke, original hub six-bolt shallow seats. **No new objects, no from-scratch replica, no GLB, no texture/material/PBR/normal work, no game-format export or modification of original PMT.** Compared against private original F50 `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` (PistonHeads) and `03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg` (Mecum), purely qualitative; not licensed for publication.

**Independent real-scene QA:** official private Blender **4.5.15 LTS** opened v9, saved v10, rendered matched same non-game cameras for before/after gauge and steering. Fresh new Blender process reopened v10, reopened v9, compared all **42** source-ID meshes, then reopened v10 and separately rendered a steering view: **PASS**. All **39** unedited original import meshes are geometry-hash identical; original source PMT/initial import hashes unchanged; original object transforms, cameras, UV and material-slot counts preserved. `geometry_edit_count=30`. Private evidence `F50_P0_DashboardSteering_MeshDelta_v10.json`, `F50_SlotC_P0_v10_Independent_Reopen_Audit.json`, `F50_SlotC_P0_v10_BEFORE_GAUGE.png`, `F50_SlotC_P0_v10_AFTER_GAUGE.png`, `F50_SlotC_P0_v10_BEFORE_STEERING.png`, `F50_SlotC_P0_v10_AFTER_STEERING.png`, `F50_SlotC_P0_v10_INDEPENDENT_AFTER_STEERING.png` (independent render SHA256 `fd8466fd8b81155ae12111ef7bd4385f460e1f39e364a2d5981abe7792ff2523`).

**Outstanding:** actual in-game driver-eye alignment and steering rig pivot provenance `UNVERIFIED`; seven photo view QA `INCOMPLETE`; source wheel 624 open/nonmanifold edges not arbitrarily filled; visual matching remains `PARTIAL` (small geometric changes are not subjective completion). Github-hosted 4.5.15 real proprietary .blend audit `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`, not misreported as passed by CI smoke. Minimum 24h not elapsed, **vehicle_complete=false** and **slot_C_advance=false**. **AI score change +0**, continuation of same F50 P0 achievement / no duplicate scoring.
