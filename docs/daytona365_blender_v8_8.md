# Ferrari 365 GTS/4 Daytona v8.8 — real PMT-bounded console and source PBR

Date: 2026-11-08 KST. Only branch `feature/daytona365-blender-v8-20261108` modified; no native game or VR runtime branch integration.

## Real input and material changes
- Immutable private input: `Daytona365_Cockpit_Blender_PBR_v8_7.blend` SHA-256 `e247abed67d15b5562daa5374163cc4c3a18de7dd059bfc42d94c9227e0e61a3`. Original group018 measurements used only as aggregate bounds (X ±0.10683m, Y -0.23555..0.20228m, Z max 0.51887m); original model vertices are not redistributed.
- `tools/blender_daytona365_v8_8_pmt_console_pbr.py`: rebuilt `V8_LOW_CENTER_TUNNEL` from 9 to **13 manually shaped stations / 78 vertices / 74 faces**, preserving physical shifter H gate clearance; new metric UV `V8_8_METRIC_CONSOLE_UV`, edge micro-bevel and weighted normals. Center stack fairing uses the same packed PBR but stays below original switchbank.
- Four original left/right seat cushion/backrest objects, front/back return polygons and `V8_7_GEODESIC_LEATHER_UV` retained exactly. Two source-linked seat PBR material variants use BaseColor texture attenuation, physically constrained ORM Green→roughness, true tangent Normal and small bump. Packed BaseColor/Normal/ORM/Height retained; no generated image masquerades as source.

## Real Blender and preview validation
- Blender 4.5.15 LTS, saved immutable `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_8.blend`: **6,743,949 bytes**, SHA-256 `6859ead3070525e9a55e7b6946ba10d0050ff85825ce1074f8e3a2255ef48c60`.
- Separate fresh-open `tools/verify_daytona365_v8_8_blender.py`: **PASS**, 104 meshes/82 curves, 13 console stations, seam continuity, four original seat mesh topologies, packed texture nodes and camera retained.
- Actual **Cycles** render `docs/images/daytona365-v8/Daytona365_v8_8_ACTUAL_CYCLES_PREVIEW.png`: 480×320, 4 spp, 2 CPU threads, denoise, exposure -0.52, camera `V7_Camera_Reference_ThreeQuarter`, SHA-256 `64906b9627a9d80e05862df9c32aaa6e6be437cf1f65d8d623810a5be8320ef2`.
- Genuine four-way original PMT / v8.6 / v8.7 / v8.8 comparison `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_6_V8_7_V8_8_ACTUAL_CYCLES_COMPARE.png`, SHA-256 `7ad2acb353f8bd4187a38319599f85620904c97540b9cb8f9d2a8d6c22f7c71c`. Original 960×640/10 spp downsampled; candidates 480×320/4 spp, same camera/framing. **NOT photometrically matched**.
- `tools/test_daytona365_v8_8_source_contract.py` source AST/py_compile/19 static material checks **PASS**; CI is source-only and **not a Blender render**.

## Remaining visible mismatch
The candidate seat leather remains substantially brighter/oranger than the PMT black/dark-gray cabin, despite more restrained PBR, and the original upper backrest contour and pleat layout differ. v8.9 should fix those against measured material017 silhouette, with an appropriately exposed reference crop and a matched-sample render on an authorized high-power host.

`RENDER_VALIDATION=PREVIEW_ONLY`. `FULL_RESOLUTION_MATCHED_CYCLES=UNTESTED`. `GAME_RUNTIME/OVC/QUEST3=UNTESTED`.
