# Ferrari F50 — SLOT C v41 windshield_frame source edit (2026-11-09 KST)

Requested `TARGET=driver_controls` remains **BLOCKED_UNIDENTIFIED_NATIVE_STALK_PEDAL**: native PMT pedal and column-stalk attribution not established among 42 original meshes. No synthetic replacement; per V3 breadth-first policy advanced to next `windshield_frame`. P0 dashboard and steering wheel remained untouched.

- Original read-only PMT: `obj_plcar_f50_pmt.sz`; SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Original direct-import .blend SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Input v40 .blend SHA256 `03b96b1eb2293c151c60133919380055fa8393372b0acbf18045edf25faa949a`.
- Edited **only** original `object00_group00_material000_a0` windshield upper black border/A-pillar frame, 68 vertices and 56 faces retained: existing indices 27,28,30,32,34,36,38,40,43,45,47,49,50; max actual displacement **21.0 mm**. No generated faces, meshes or objects. Other **41** PMT native mesh fingerprints unchanged including windshield glass `material005_a1`, dashboard, steering, seats, door, shifter and all UV/material/transform data.
- Photo reference (private N100, no republication): `REF16_interior_1_b0df0e6809.jpg` SHA256 `9a52450918bfa4a0cb22cf56c0bf373175b212dcb20fe1e6ee7c512114546dad`; black upper surround/A-pillar silhouette only, no calibrated in-game camera.
- N100 saved editable `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_Windshield_Header_Apillar_v41.blend` SHA256 **`016645f5fea43ef75c8e80479f49baaff2d3aa8d1647a058f732ac69080da08d`**.
- Official Blender 4.5.15 LTS `v41 -> v40 -> v41` independent **PASS**; private receipt, independent reopen JSON, same-camera BEFORE/AFTER Workbench PNG evidence retained on N100. Source-locked reproducible script `tools/car_modeling/slot_c/f50_windshield_native_header_v41.py`, commit `3693c9fc68b570b5e41e7a06156bebc19475efb8`.
- `windshield_frame=COVERED_PARTIAL_QA`; `driver_controls=BLOCKED`. **NOT** Ferrari F50 vehicle QA PASS. Glass-edge match, seven genuine photo views, calibrated driver-eye and existing topology findings require vehicle-level review. NEXT `visible_seat` (no polishing dashboard or wheel). 24h assignment started 2026-11-08T04:35:52Z unchanged.
- Zero OVC/OVC3/PMT export/game integration/new texture/PBR/Model2/Dino/other slot work.
