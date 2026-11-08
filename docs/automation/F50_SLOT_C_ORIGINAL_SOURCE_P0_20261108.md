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
