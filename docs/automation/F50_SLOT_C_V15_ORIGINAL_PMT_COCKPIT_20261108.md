# Ferrari F50 Slot C — original PMT-derived cockpit v15 (2026-11-08 KST)

Status: ACTIVE / P0 PARTIAL_NEEDS_QA / NOT COMPLETE. Dedicated F50 slot C until at least 2026-11-09 13:35:52 KST, then only after complete human-verifiable QA. Slot A Daytona365 and completed Dino 246 untouched.

## Read-only original source and genuine Blender lineage

- Native OutRun 2006 F50 PMT path: rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz
- Native PMT SHA256: 10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab
- First original game native import .blend: work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend
- True original first import SHA256: d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31 (42 original PMT named meshes)
- Immutable source-derived v14 .blend SHA256: 87cce97c87a15bb657599c5e2457a1c109658d58b65ec5488e8988b6e007c349
- New separate private F50_OriginalPMT_P0_DashboardSteering_v15.blend SHA256: d6dd11d872105e94a5f7b5262c7aed8a327098f80c3645e907a2c9ba127d8302 (1540445 bytes).
- Private file path: /home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v15.blend
- All native game files, original import, private .blend and copyrighted F50 photos stay N100-only. Neither model bytes nor photos committed to public GitHub.

## Existing original mesh geometry changes (v14 to v15)

| Original PMT mesh ID | Vertices / faces before → after | Vertices moved | Largest local delta | Exact geometry SHA256 before → after | Nonmanifold edges |
| --- | --- | ---: | ---: | --- | --- |
| object00_group01_material028_a0 | 5506/7552 → 5506/7552 | 2766 | 3.13109 mm | be562487b4102326f55f022f30bbc534f456df6f3cc8356a6a7430bb352260a7 → 715967e7e9a4c9d6eab3b40d8a2776ea69889f3ca3da1160a4d8c97c09a6f6cd | 0 → 0 |
| object21_group01_material002_a0 | 13552/26496 → 13552/26496 | 11671 | 2.44091 mm | e240a908071264d40aa77e7756bd5c9e87b19742caf46dd1c6a0820ea30ac2f0 → b7e76a3f48218a4b5945a7e78a335843a07f52e40d9bdc24936d571d805da722 | 624 → 624 |
| object21_group00_material000_a0 | 2738/4464 → 2738/4464 | 2339 | 1.27 mm | fcb6a75ea4785b1c5453d362ac64facc98b99a2c7069b09257f2f4396f6dc63c → 0e72e23cbfb48973c6977e151a4cb1c534ae797ac61f1a9c5f1421792cb94225 | 0 → 0 |

Photo-guided original mesh physical rework (no new objects): molded single instrument brow, cowl return and selective original-triangle z smoothing; source steering rim upper circular contour, leather grip, original 3-spoke arm shoulder and 6-o'clock web; original metal hub seat and counterbore lands. All original 39 unrelated mesh signatures, original UV/material assignments, source object IDs, matrices, native animation pivot and camera matrices unchanged. Steering's original 624 nonmanifold edges remain; not claimed repaired.

## Actual official Blender 4.5.15 LTS private-scene QA

- Opened sha-pinned native source-derived v14 .blend, sculpted only the three source-named cockpit meshes, saved v15, then a separate Blender 4.5.15 process reopened v15/v14/v15 and checked all 42 source meshes and hashes: PASS.
- Actual original-source Workbench same NON-GAME camera before/after 800x560 panels; RGB max-channel difference >3 pixel counts: GAUGE 8865, STEERING 19773.
- Independent second-process PNG SHA256: 43aa5b9e64de922f68c4ffa4b108e3c26f523617c4467dee5825d63f90cd8fbc
- Private 2x2 before/after visual comparison SHA256: f16bc847e72913b6f3d00d09895e5ffd601b0ef142de6934ece3d239e77a2d79
- Private real F50 photograph vs actual Blender comparison SHA256: f6a1d0f317ae8be7af154d884d1872ac8172f3ef746b8527059f783945cef858
- Original F50 photo library MANIFEST.json SHA256: a4645b3bcc98443026951f4aba845bd8561aad85b8cd58a8c289be02d194225e
- N100 COVERAGE_MATRIX_16x8.csv SHA256: undefined
- Reference F50 dashboards/photo provenance: https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812 and https://www.mecum.com/lots/1158440/1995-ferrari-f50/ . Image handedness/year/7 precise camera angles not fully verified.
- Local private evidence: F50_P0_DashboardSteering_MeshDelta_v15.json, F50_SlotC_P0_v15_Independent_Reopen_Audit.json, F50_SlotC_P0_v15_SOURCE_BEFORE_AFTER_2x2.jpg, F50_SlotC_P0_v15_PRIVATE_REAL_F50_PHOTO_GEOMETRY_COMPARE.jpg.

## Blockers / restrictions

- GitHub hosted official Blender 4.5.15 workflow cannot audit actual private PMT-based .blend: BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED. A hosted smoke PASS is not a true original-F50 hosted render.
- Original game driver-eye and camera/FOV/pivot integration remains UNVERIFIED; seven real photo vs Blender cockpit views INCOMPLETE; true wheel nonmanifold edge correction UNRESOLVED; dedicated 24-hour slot requirement not yet passed. Keep F50 ACTIVE/PARTIAL and do not move queue.
- No OVC3/OVC/PMT conversion or output, no game integration/packaging, GLB substitute, external body/wheels/tires, new textures/PBR/normal maps/DDS, Model2, VR/DX11/DX9Ex/DXVK, Dino or slot A modifications.
- Same previously scored F50 P0 achievement continuation: previous AI2 SSOT 2781 + current 0 = cumulative 2781 as of score check (not a duplicate achievement).
