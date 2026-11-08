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
