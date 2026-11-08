# F50 Slot C native cockpit v22 — 2026-11-08 KST

Status: ACTIVE / PARTIAL_NEEDS_QA. Current active_by_slot.C=f50. 24h ownership starts 2026-11-08T04:35:52Z (earliest expiry 2026-11-09T04:35:52Z). Never advance without P0 dashboard/steering and photo gates. Same F50 workstream; score delta +0.

## Immutable native input provenance
- Original game PMT private readonly /home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz; SHA256 10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab; 439481 bytes.
- Original PMT imported Blender: work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend; SHA256 d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31.
- Exact input source-derived prior v21-r2 editable blend SHA256 5aec7398777dbec8c0fad9bc8fd2190474d929f992e9fed1e76cf566824eda6d.
- New independent versioned private editable F50_OriginalPMT_P0_DashboardSteering_v22.blend SHA256 cc4090261747c8c013011e68d1781f5aa6f75bca478ec5c2e9fb6fd3f1c5fcc7.
- Original PMT, original first Blender import and v21-r2 remain byte-identical.

## P0 authentic source-mesh geometry before -> after
Only 3 pre-existing imported source mesh objects of 42 modified. All original IDs, object transforms, cameras, UV layers, material slots, vertex/face topology preserved, and the OTHER 39 native meshes remain geometry-SHA identical.

| Original mesh object id | Source verts/faces before=after | Existing moved verts | Max displacement | Mesh SHA before -> after |
|---|---:|---:|---:|---|
| object00_group01_material028_a0, dashboard instrument visor | 5506/7552 | 1868 | 1.250029 mm | 85fe94355dd228489b18571cbed01901612387094e478d3427d317f485eda2ae -> eafae91ec88b7959dfe87fba29937817a3cb60c035c37fc7dfb98ad833793864 |
| object21_group01_material002_a0, original three-spoke steering rim | 13552/26496 | 5131 | 1.037111 mm | e0efcd1a6814319ffe3c30e322d76fbcc0f6db7282ca1c1569d580b6ef68d1c5 -> 47fdc4ec9819f2ff4fb5635f7e9ba396be653830786887838909c439cb5f81c7 |
| object21_group00_material000_a0, original six-bolt steering hub | 2738/4464 | 526 | 1.150000 mm | 352eef9090c34cc852734d3f90d71dc8c29ad84f0c689109119c8ac23bf37d99 -> 0c8d859b1076c1b91ef5f08ddd6b3be9b1516918ee91022dff02bef05ec294bb |

Source cowl: bounded, normal-consistent existing-vertex surface curvature fitting of original F50 instrument eyebrow. Wheel: small symmetric existing-grip contours and lower spoke transition. Hub: bounded existing-six-bolt front plate fairing preserving screw islands/center badge. No disconnected substitute, new mesh, faces, new texture, game exports or body work.

## Actual Blender, photos and output evidence
- Public geometry-only source: tools/car_modeling/slot_c/f50_p0_source_mesh_v22.py; N100 copy SHA256 76a02730ba91e13d0ab6a965e39ad7e38d37d3cdcccdd319e57f9d9f47cb99ef.
- Actual N100 official Blender 4.5.15 LTS opened private native-derived v21-r2, saved private v22, a SECOND new Blender process opened v22 -> v21-r2 -> v22, checked 42 real original mesh sources/IDs/hashes/matrices/UVs/materials/cameras and rendered independent steering detail. PASS_F50_V22_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER. Private receipt: F50_SlotC_P0_v22_Independent_Reopen_Audit.json.
- Independent reopened actual steering PNG SHA256 1f0d7e1ad6e64473c36125ca7d978d2296831492dc9845b0d354c108ec96781d.
- Before/after actual source-blend diagnostic camera 800x560 views each: GAUGE pixels RGB max-channel delta>3 = 1381, STEERING = 9766. Private compare: F50_SlotC_P0_v22_SOURCE_BEFORE_AFTER.jpg SHA256 8d2b87125bc9b381f923bbf0138707e6f97b1c6b8508630a083142f4d08cd507; hash/metrics JSON: F50_P0_DashboardSteering_MeshDelta_v22.json.
- F50 private source photos from N100 MANIFEST/COVERAGE verified: 03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg SHA256 6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961; 03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg SHA256 cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2. No private photo/PMT/blend committed publicly.

## Gates still unpassed / exclusions
- Original F50 source steering mesh retains 624 factory open/non-manifold edges. No blind closure.
- Source original game driver-eye calibration, steering pivot gameplay correctness and seven F50-photo-matched perspective views UNVERIFIED/INCOMPLETE; visual fidelity P0 still PARTIAL. The before/after render is diagnostic non-game camera.
- GitHub hosted official Blender real ORIGINAL private source scene = BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED. A source-only smoke CI PASS, if any, cannot validate private scene. Never claim hosted real-scene PASS.
- Keep active_by_slot.C=f50; Daytona slot A, Dino 246 already completed, Model2, UW2, VR/DX branches untouched; no OVC/OVC3/PMT/GLB conversion, public private asset upload, game packaging, exterior geometry, DDS/PBR/normal textures.
