# Ferrari F50 slot C: genuine native PMT cockpit geometry v26-r2 (2026-11-09)

**Checkpoint:** private original-based editable Blender scene **SAVED; Blender 4.5.15 fresh-process reopen and genuine scene render PASS; F50 remains ACTIVE / P0 PARTIAL.** Do not consider this a complete car or a 24-hour finished cycle.

## Provenance / protected inputs

- Slot owner `active_by_slot.C=f50`. Slot A Daytona and completed Dino 246 untouched; no Model2VR/DX11/DX9Ex/DXVK/game changes.
- Read-only OutRun 2006 Ferrari F50 original native compressed PMT: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz`, SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Original direct PMT import `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend`, SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Exact immutable input original-derived `F50_OriginalPMT_P0_DashboardSteering_v25_r2.blend`, SHA256 `bfa8becc5d2bbd0258b135fbc8b3478b2725f8e5f5b8da9c95397cf5908e6da4`.
- Accepted versioned private native-derived edit **`F50_OriginalPMT_P0_DashboardSteering_v26_r2.blend`**, SHA256 **`e6309fb522a76d9f7a1ee5fa3e3398389631067743a889e8d210cbf6982bf9b9`**, 1,539,547 bytes; N100 folder `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/`.
- Failed visual trial `v26` SHA256 `5022282083294d259b818e07eb7dd62e32f8fe31e715aaf76c3c6912fda4f831` had excessive wheel surface grooves despite programmatic PASS. **Rejected**. `v26-r2` starts directly from immutable `v25-r2`, never from this rejected candidate. Both are preserved without overwrite.

## Exact native PMT imported mesh edits (in-place original vertices only)

| Original object ID | Previous → current vertex/face totals | Moved source vertices | Max displacement | Previous → current geometry SHA256 |
| --- | --- | ---: | ---: | --- |
| `object00_group01_material028_a0` instrument hood | 5506/7552 → 5506/7552 | 1,992 | 1.495600 mm | `1bf41eb343e0d2e656230418d91a82b95bc54b32c9b7d8899cd4713a67151be5` → `aef5bac35948624d33bef92070c34ca1c667e6669c0f7f37a11697544c12598b` |
| `object21_group01_material002_a0` genuine 3-spoke rim | 13552/26496 → 13552/26496 | 10,901 | 1.019726 mm | `4643c224d88913fe1af2e2d5042d13f17824768249763169f1b6f57eb8c20fc0` → `01b3ae52baecf6852264478fc7e13e286755a027f31b1b6d9135bf4104e89784` |
| `object21_group00_material000_a0` original six-bolt hub | 2738/4464 → 2738/4464 | 500 | 0.976261 mm | `32f68dcf0721c0785d3c8ec1398a05579a94ad2181de5d65fc524ea1a379e055` → `357c35a82d25146cc49dcac5983976126108639263fe1d3b6cafbb64316f8857` |

Original IDs, object transforms, indices, UVs, camera metadata, material slots, animation pivot unchanged; other **39/42** original meshes byte-signature identical. No new object/mesh or texture. Source steering rim's inherited **624 non-manifold/open edges remain**; no false claim of closing them. V26-r2 uses original hood normal-gated arch, low-amplitude native wheel grip rounding and protected six-bolt original hub face smoothing.

## Genuine private QA and photographs

- Public source-edit Blender Python script: `tools/car_modeling/slot_c/f50_p0_source_mesh_v26_r2.py` (N100 same source SHA256 `05108a5045e9096f78d032cfc5cf0cce65f330addf07b91c2ab73d10998292e7`).
- Private non-proprietary driver: `f50_v26_r2_private_runner.py`, Blender official Linux 4.5.15, separate build/reopen/render Blender processes.
- Independent receipt: `F50_SlotC_P0_v26_r2_Independent_Reopen_Audit.json` status **`PASS_F50_V26_R2_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER`**, independent steering render SHA `ebf7c43d5e6d8ffc0d0934a98e24589a0111097b1af11998120287bb8391b730`.
- Authentic before/after Workbench **non-game camera** 2×2 image `F50_SlotC_P0_v26_r2_SOURCE_BEFORE_AFTER.jpg`, SHA256 `7beef318e84027de6d512a84a1c2c953bc0abe1b0730d6d88176ce4d22bd1063`. Matched 800×560 camera pixels with channel delta >3: instrument 1,008; steering 21,935. Not a game-eye confirmation.
- Reference source: actual Ferrari F50 cockpit photos in private N100 `03_F50/`: `REF2_dashboard_closeup_dad64db8c0a5.jpg`, SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`, and `REF5_mecum_interior_01_f8afa7e2a.jpg`, SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`. Copyright photos kept private.
- **Outstanding:** exact original game driver-eye FOV/camera verification, authentic seven photo-view comparison, 624 inherited steering open edges, human P0 quality approval, uninterrupted 24h time gate. First car allocation 2026-11-08 04:35:52Z; earliest 24h 2026-11-09 04:35:52Z (13:35:52 KST). Completion and car advancement prohibited without all gates.
- **GitHub hosted official Blender 4.5.15 genuine model QA = `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`**. Current hosted workflows install Blender and run queue/smoke tests but *have not received the private copyrighted original-derived .blend*. Do not equate smoke QA with this genuine private F50 result. No confidential assets in public repository.

No OVC3/OVC/PMT export/conversion, GLB, game install/package or runtime/VR validation; no external body, wheels, tyres, texture, normals, PBR. This is continuation of F50 P0 feature; AI2 scoring **+0**, retries and rejection do not count.
