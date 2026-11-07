# Ferrari 365 GTS/4 Daytona v8.10 — actual dark door, wheel, geodesic UV and PBR

Date: 2026-11-08 KST. Scope: `feature/daytona365-blender-v8-20261108` only. No original-game executable/OVC, other VR runtime branch, Model2VR or web-port edits.

## Authentic input and visible defect
- Immutable private input `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_9.blend` (SHA256 `bfd91e5e29d796e708918298678305172ec21fff958122d2eed72118303ca9c2`). v8.9 dark seats, headrests and 13-station PMT018-bounded console are **existing achievements**, not repeated.
- In the genuine original PMT same-camera Cycles reference (960x640, 10 spp), door cards and steering rim appear dark charcoal/black. v8.9 candidate retained highly saturated brown/orange door panels and walnut wheel. Fixing these surfaces is the independent v8.10 scope.

## Genuine editable Blender changes
- `tools/blender_daytona365_v8_10_pmt_dark_doors_wheel_normals.py` modifies original left/right `V5_*_LEATHER_SCULPTED_DOOR` source meshes **in-place**: each retains 465 vertices and 840 polygons and original pivot, with four low-relief upholstered bands (up to 3.3 mm projection), two physically conformal seam curves per door, recalculated normals and `V8_10_DOOR_GEODESIC_UV` measured along the updated surface.
- Door lower pads/pockets and stitching have independent charcoal PBR clones. Source texture-driven packed BaseColor remains linked through dark Hue/Saturation node, source tangent Normal and ORM green→roughness stay linked, original packed Height microbump retained. No invented replacement source image.
- Existing 1536-vertex high-resolution steering rim and 153-vertex original rim have original geometry/UV preserved, with source-walnut normal/ORM/Height PBR reused for dark ebony appearance. Central emblem, original three spokes, gauges, switchbank, H-shifter and camera untouched; the previous 4 seats/headrests and console also untouched.

## Official Blender validation and genuine Cycles render
- Official Blender 4.5.15 LTS saved NEW immutable private `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_10.blend`, 7,024,898 bytes, SHA256 `ab60744f37c93f4db079a9be79b7df09f3d99006fc332e4a9f98e21b92acbb74`; independent fresh-open `tools/verify_daytona365_v8_10_blender.py`: **PASS** (106 meshes / 92 curves, packed BaseColor/normal/ORM/Height, original controls and source-mesh conservation).
- Real Cycles image `docs/images/daytona365-v8/Daytona365_v8_10_ACTUAL_CYCLES_PREVIEW.png`: 480x320, 4 spp, 2 CPU threads, denoised, exposure -0.52, same `V7_Camera_Reference_ThreeQuarter`, SHA256 `3356d0a11376b423e80f4158131a4d7f9cf831f7d5ee0c60a40deb00adb18148` (240,649 bytes).
- Actual original PMT/v8.8/v8.9/v8.10 contact-sheet `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_8_V8_9_V8_10_ACTUAL_CYCLES_COMPARE.png`, SHA256 `b2dd1adeab65a9041b924c620d3549ef8fe0a46c2601c50ca5f1ae6001d509ab` (700,118 bytes). Source PMT is genuinely rendered 960x640 at 10 spp and downsampled; candidates are 480x320 at 4 spp. Camera and framing match; **sample conditions and photometric comparisons do NOT**.
- Local AST/py_compile/22 static `tools/test_daytona365_v8_10_source_contract.py` guards PASS; GitHub Actions runs source tests only, not Blender render.

## Remaining visible mismatch and next v8.11
Bright tan/cream piping around the near seat persists from original pre-v8.9 geometry and differs visibly from original PMT dark trim. Next distinct geometric/material task: physically reproject/darken the existing seat piping and refine headrest cap silhouette without making disconnected duplicate objects. Full matched 960x640/10 spp comparison on suitable authorized host remains untested.

`RENDER_VALIDATION=PREVIEW_ONLY`; `FULL_MATCHED_960x640_10SPP=UNTESTED`; `ORIGINAL_GAME_RUNTIME/OVC/QUEST3=UNTESTED`.
