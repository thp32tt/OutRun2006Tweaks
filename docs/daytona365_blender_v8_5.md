# Ferrari 365 GTS/4 Daytona — real Blender v8.5 refinement

Date: 2026-11-08 KST. Production branch: feature/daytona365-blender-v8-20261108.

## Source and deliverables
Previous private v8.4: blender_v8/Daytona365_Cockpit_Blender_PBR_v8_4.blend; SHA-256 97ff8618a4a16ac837e90e8aa9dd4434f41172c0b54c6894ec680aefa93025d4.
New private v8.5: blender_v8/Daytona365_Cockpit_Blender_PBR_v8_5.blend; size 6,440,350 bytes, SHA-256 bac28640d88c745b5f276b1ecb5c2ae730e54660fb9526432aeb8c09be390ef8.
Private root: /home/chatgpt-runner/work_handoff/daytona365_rework_20261107.

Editable scripts:
- tools/blender_daytona365_v8_5_geometry_uv_pbr.py
- tools/verify_daytona365_v8_5_blender.py
- tools/render_daytona365_v8_5_actual.py
- tools/make_daytona365_v8_5_actual_compare.py
- tools/test_daytona365_v8_5_source_contract.py

## Real changes
1. Refit all four original v8.4 seat-shell objects without changing their names/topology. Upright backrest skins now offset rearward approximately 54 mm in Y, instead of making the previous incorrect ~47 mm downward Z offset. Cushions have softer front horn/center padding.
2. Active V8_5_METRIC_UPHOLSTERY_UV on all four shells: 2.2× cross-seat, 2.75–2.9× seat-length repeat; resampled leather welts and seams trace new vertices, old floating curves hidden.
3. Rebuilt the lower center tunnel as a contiguous 5-station, 30-vertex loft with sculpted shoulder edges; compacted shifter deck/armrest, retained the original gate/shifter.
4. Replaced oversized straight steering column cowl with source-positioned four-ring curved cowl and slender three-ring shaft. Original steering wheel/emblem/gauges untouched.
5. Narrowed door top caps and adjusted their bevels.
6. Retained packed user-reference-derived BaseColor, tangent Normal, ORM, HeightOffline; connected ORM green to physically restrained material-specific roughness ranges and retained microbump, brushed-metal normal.

## Actual verification
- Official Blender 4.5.15 LTS save and fresh reopen PASS.
- Verified 101 meshes / 53 curves; four seat shells, Y-thickness, active UVs, original gate/wheel and packed PBR normal, ORM, height PASS.
- Static source contract PASS (16 checks).
- Actual low-load N100 Blender Cycles PREVIEW ONLY: 480×320, 4 samples, 2 CPU threads, denoising, exposure -0.52, camera V7_Camera_Reference_ThreeQuarter.
- docs/images/daytona365-v8/Daytona365_v8_5_ACTUAL_CYCLES_PREVIEW.png: SHA-256 3124bad4835bc0a64c785b9545ca3e9a45766ff0407bb9477dc38f188bc1ab92; 252443 bytes.
- docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_5_ACTUAL_PREVIEW_COMPARE.png: SHA-256 338d8820c0fca15bc0df00045916ac1e58cbf77dca9c1bd071873eb655a627d0; 350691 bytes.
- Comparison is genuine original-game PMT Cycles (previously rendered 960×640 then downsampled) against freshly rendered v8.5 preview (480×320 4 samples). Identical camera framing, NOT identical samples/resolution.
- Original Cycles render SHA-256 d214f07ac3922921557d4981c8e3b3360ffbdd781197081bef6d7426817292b3.

RENDER_VALIDATION=PREVIEW_ONLY.
FULL_RESOLUTION_CYCLES=UNTESTED.
GAME_RUNTIME/OVC/QUEST3=UNTESTED.
No original-game binaries, private .blend, PMT, DDS or OVC uploaded to public GitHub; no game/VR branch modifications.

## Next high-value defect
The original-game dashboard's dark lower center-panel silhouette is still far from the v8.5 source-backed new model. For v8.6, map the lower dash, console and footwell against measured original object bounds/pivots before replacing further shapes. Inspect seat side supports and side-door trim afterward. Preserve the v8.5 .blend and rendered images.
