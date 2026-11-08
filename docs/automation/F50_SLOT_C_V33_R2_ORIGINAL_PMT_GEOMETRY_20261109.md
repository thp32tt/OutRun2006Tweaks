# Ferrari F50 slot C v33-r2 — original PMT cockpit-only geometry (2026-11-09 KST)

**State:** native F50 Blender 4.5.15 saved / separate-process reopened / original model renders PASS. Vehicle ACTIVE / PARTIAL_NEEDS_QA. Not a finished car. This is a rework of the original imported scene, not third-party GLB, synthetic mesh or a new vehicle.

## Immutable original source lineage

- Original read-only game PMT: /home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz — SHA256 10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab
- Verified original native PMT imported editable Blender baseline: work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend — SHA256 d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31
- Immutable accepted parent v32: work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v32.blend — SHA256 16e2a9e17d83b8e77dd9c2636aeab8bfb60b19b850926f1641b26947382df193
- **Accepted source-derived editable output v33-r2**: work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v33_r2.blend — SHA256 **40a555a8d265b87d6ad7fc109672ceb339629a8311c1f5c0ca96a717916b19df** (1,540,157 bytes). License-protected .blend and PMT are private N100 artifacts, not checked into public GitHub.

## Actual original object edits

All operations directly relocate vertices of three existing original PMT-imported Blender mesh objects (no added model/object, unchanged faces, original camera, transforms, material/UV slots, animation positions, 39 other original meshes SHA-identical):

| Original imported native object | Vertex/face count before and after | Existing moved vertices | Max displacement | Geometry SHA256 before -> after |
| --- | --- | ---: | ---: | --- |
| PMT_F50_object00_group01_material028_a0 (instrument hood) | 5506/7552 -> 5506/7552 | 995 | 0.980020 mm | 133a00c89864613ba299ab39dd39c2d6dff422af07b551389fc393bd75995436 -> 0ca34ebe2d609fce82c8305c1bb06126b0daf5a7d9a239174fa7fb8885f7ebcd |
| PMT_F50_object21_group01_material002_a0 (original 3-spoke plate) | 13552/26496 -> 13552/26496 | 987 | 2.349822 mm | d3afbebcd59d994418db21ee4a045b7f718333f0ede5bc7538f2714552741444 -> 3ac53bfb2b001d5955425fe5269138341a77e6d79d49d90b9d4ed87f8624e7d4 |
| PMT_F50_object21_group00_material000_a0 (original six-bolt hub) | 2738/4464 -> 2738/4464 | 579 | 1.900000 mm | 618d3ed1f513b1bed124a5dc684e674ea98f5d3c0d13e5352d617a41df0919a8 -> 36650b8054aafcbaf63ef9f0ae880440a1e0b3a8243e3d3859412c10c22d8b00 |

Total 2,561 original source vertices edited. Hood XY silhouette maintained while smoothing shoulder topography; original 3-spoke sheet face fairing with protected open-loop vertices; original hub bolt islands/medallion protected while locally smoothing center plate. Source original eight boundary loops, sized [48,48,72,72,72,96,96,120], remain identical: 624 inherited open/nonmanifold edges; physical spoke/rim weld NOT proven and not falsely claimed.

## Rejected trial and original-scene QA

A preliminary v33 sample (SHA256 ddcb7727f9acc629a95044249b695f017a12be15c7826d282b89febfe7312401) passed automated geometry tests but **failed visual inspection due new upper-rim scar/crease artifacts**. It was rejected, not promoted and never used as v33-r2 input. Accepted v33-r2 was rebuilt *directly from immutable v32*, without that radial outer-rim correction.

- Script: tools/car_modeling/slot_c/f50_p0_source_mesh_v33_r2.py — local SHA256 22ab81e4b787fb54be8a272f568f5fa7ab02367237f44784437c7d2c49caf7c3, material source commit 6643815d967a8e3de3b2bd640bb984e0ef71e6fd
- Real official **Blender 4.5.15 LTS** opened authenticated native F50 v32, saved v33-r2, then independent fresh Blender reopened v33-r2, v32 and v33-r2 and rendered genuine source wheel. Receipt F50_SlotC_P0_v33_r2_Independent_Reopen_Audit.json: PASS_NATIVE_F50_V33_R2_BLENDER_4_5_15_FRESH_REOPEN_COMPARE_RENDER. Independent wheel render SHA256 2182465d3316e625edb012914e881a5b55e4c42b0e989cdf125e83f9e020c7e8.
- Genuine Blender matched non-game camera 2x2 v32 vs accepted v33-r2 geometry render: F50_SlotC_P0_v33_r2_ORIGINAL_BEFORE_AFTER.jpg, SHA256 891ff6438fc4fc3be605d1ae44fa2205a838767035fc31fe950d4b9cf277bde1; changed pixels RGB delta greater than 3: instrument hood 1,937, steering 8,765. No claimed exact original game driver-eye angle.
- N100 private photo source documents MANIFEST.json (17 F50 records; 16 downloaded) and COVERAGE_MATRIX_16x8.csv checked. F50 original photo examples: https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812 and https://www.mecum.com/lots/1158440/1995-ferrari-f50/. Known PistonHeads F50 photo is RHD; no claim of matching exact game-eye calibration, while the matrix only approves center shifter.

## Incomplete quality gates / invariants

Current native game driver-eye/FOV is UNVERIFIED; 7 authentic photo/model views incomplete; inherited 624 open wheel edges still present. GitHub-hosted Actions Blender real original source scene is BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED because proprietary .blend is not in the hosted runner. Do not promote hosted smoke to genuine scene PASS. Real private Blender 4.5.15 independent QA is PASS but vehicle is **NOT COMPLETE**. The first original F50 geometry window began 2026-11-08T04:35:52Z, earliest 24h end 2026-11-09T04:35:52Z. **Do not advance active_by_slot.C=f50.**

No Dino, Daytona/slot A, Model2/VR, game source, exterior body/wheels/tires, textures/normals/PBR, OVC3/OVC/PMT conversion or package. No scoreboard entry: AI2 score delta +0 for ongoing same feature, rejected trial/retry/render do not count.
