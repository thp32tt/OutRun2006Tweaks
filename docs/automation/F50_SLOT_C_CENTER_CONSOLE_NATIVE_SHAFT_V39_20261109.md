# Ferrari F50 — SLOT=C center_console 2/2: native PMT shifter SHAFT v39
2026-11-09 KST. Original game F50 PMT only. **COVERED_PARTIAL_QA (knob+shaft), no car QA PASS**.

## Real, independent physical geometry
- Source object changed: `object20_group00_material001_a0` (PMT object20, group00, material001). Original segmented triangular-shaft panels are sourced from the authenticated PMT direct import; they have **12 vertices/6 faces** prior to this change. New source-derived same object is **108 vertices/150 faces** with 108 moved vertices, max **2.1878 mm**. Its triangular cross-section is reshaped to a narrow, approximately cylindrical shaft, preserving original axial extent, object identity, transform and materials.
- **Other 41 imported original PMT meshes unchanged** by independent per-object geometry, UV, material and matrix fingerprint; this includes already-completed v38 knob, dashboard/steering and rest of vehicle. No new mesh object.
- N100 private actual F50 photo: `outrun2_vr_refs/20261104_16car_cockpit/03_F50/REF12_1995_ferrari_f50_transmission_2_1c36328e4.jpg`, SHA256 `c3c72ecf754d5c764450c8e90b7a8f7faaf0214503ea18c1c0a9c3f4ce215022`; clearly shows the cylindrical lever shaft. Photo used privately for geometry comparison; seven-view game-eye QA still incomplete.
- Before and after matching Workbench views on the actual source geometry: `F50_CenterConsole_Shaft_v39_BEFORE.png` SHA256 `7af44ff207863585b2c1122f008f3d089e0a94d66640d2115eb30b80dcacdfe0`; `F50_CenterConsole_Shaft_v39_AFTER.png` SHA256 `a19af8ff8cd15c86b9651af80d36cff0ef2ed54593fc770ccffa74292a60799a`.

## SHA-gated original provenance and real scene
- Immutable original game `rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Original PMT imported Blender `F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Previous v38 source input `F50_OriginalPMT_CenterConsole_Shifter_v38.blend` SHA256 `8e9081c15a071e2b2edde4f44dc529470ac08d9f34a8e4516a93b8926e933ec2`.
- **New immutable editable scene** N100 `/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CenterConsole_Shaft_v39.blend` (1,544,197 bytes) SHA256 `724df8bcd079299e8781726b25888243dbdcab7368d7d758f81ba8236666072f`.
- Official Blender **4.5.15 LTS independent new process open v39 -> open v38 -> open v39** PASS, exact 41 unchanged mesh fingerprints, SHA of saved blend verified. Private `F50_CenterConsole_Shaft_v39_Receipt.json` and `F50_CenterConsole_Shaft_v39_IndependentReopen.json`.
- Source implementation committed at `tools/car_modeling/slot_c/f50_center_console_native_shaft_v39.py` commit `f67d0f1bde0ac3b4a74d0777ea6d85278d8a6405`. No GitHub-hosted proprietary scene CI claim.

## Scope, timebox and next region
- **center_console dispatch 2/2 consumed** (v38 original knob, v39 original shaft); **NO FURTHER console polishing** under this dispatch cycle. H-pattern gate, mounting plate and full tunnel trim are **BLOCKED_UNIDENTIFIED_NATIVE_SOURCE**: no confidently identified PMT submesh, hence no synthetic construction. Earlier source-only objects material013/020/025 were reviewed but not accepted as gate without geometry identity proof.
- Workpack current component remains **`driver_controls`**, where it was already advanced after v38. Do not reset dispatch index; next new work must be controls/pedals/stalks, not dashboard or steering.
- F50 remains `ACTIVE / PARTIAL_NEEDS_QA`. Existing 24h owner start `2026-11-08T04:35:52Z` unchanged. Original game driver-eye calibration, 7 authentic matching views and full-car QA **NOT COMPLETE**.
- No OVC/OVC3/PMT export, game integration, source texture/PBR/normal, new vehicle or model, exterior/wheel, Model2/Dino/slot A/DX11/DX9Ex edits.
