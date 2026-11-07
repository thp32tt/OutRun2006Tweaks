# Ferrari 365 GTS/4 Daytona — measured Blender v8.6 real refinement

Date: 2026-11-08 KST. Branch: `feature/daytona365-blender-v8-20261108`.
Scope: cockpit source asset only, no OutRun executable/OVC/VR integration.

## Baseline and measured original PMT
- Input verified private v8.5: `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_5.blend`; SHA-256 `bac28640d88c745b5f276b1ecb5c2ae730e54660fb9526432aeb8c09be390ef8`.
- Actual original-game-derived PMT Blender scene: `original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`.
- Blender 4.5.15 LTS bounds probe on original PMT meshes, reference only:
  - `object00_group01_material016_a0` lower center stack: X [-0.14203, +0.14203], Y [0.16707, 0.22873], Z [0.58656, 0.84731] m.
  - `object00_group01_material018_a0` console: X [-0.10683, +0.10683], Y [-0.23555, 0.20228], Z [0.33638, 0.51887] m.
- Private source geometry/PMT/texture files remain off GitHub. Only these measured bounds and true rendered PNG evidence are committed.

## Materially changed real Blender source
`tools/blender_daytona365_v8_6_source_contoured_console_seats.py`:
1. Reshaped `V8_LOW_CENTER_TUNNEL` from five-station v8.5 into nine continuous shoulder-shaped stations. Front rises toward the original PMT console height without displacing the genuine chrome H gate or gear knob. Added physically measured longitudinal/circumference UV for tangent normal.
2. Rebuilt the v8.2 lower dash lip into 15 stations with a curved knee-clearance underside. Added a small lower center stack fairing capped BELOW the PMT switchbank's 0.58656 m minimum height, without synthesizing original PMT mesh.
3. Sculpted side bolsters on the same four original v8.5 seat-shell grids; maintained 7,738-vertex cushions and 8,614-vertex backrests (both sides), 54 mm backrest rear-thickness axis, and existing active upholstery UV. Reprojected all tenured welts/horizontal seams; added 8 inset side seams.
4. Added physically repeating UV to both long door lower pads, preserving their pivots and surface objects.
5. Created independent console/door PBR variants preserving the packed source-derived BaseColor, tangent Normal, ORM and HeightOffline textures. ORM Green remains linked into physically bounded roughness, metal=0 for leather, microbump restrained; no AI-generated render substituted for Blender output.

## Verified checkpoint, real render and comparison
- Blender 4.5.15 LTS real save and fresh reopen: **PASS**. Model: `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_6.blend`, **6,444,492 bytes**, SHA-256 `cb0eba836a69b3154012bd755fafac92b92b223be0e9394a876c322123e1f2f4`.
- Reopened scene: **102 meshes, 61 curves**; tunnel 54 vertices, 9 stations with active metric UV; measured lower-stack fairing bounds; upholstery topology/thickness; door UV and packed PBR; original steering/gauges/gate unchanged.
- Actual low-load Blender **Cycles** preview at 480×320, 4 spp, CPU 2 threads, denoising, exposure -0.52, same calibrated reference camera `V7_Camera_Reference_ThreeQuarter`. PNG: `docs/images/daytona365-v8/Daytona365_v8_6_ACTUAL_CYCLES_PREVIEW.png`, SHA-256 `7fd6c2726896e71d3e3ca0c2e64df6f5fcd4629212ef4af0e5a88c180010481c`.
- Real side by side **ORIGINAL PMT / v8.5 / v8.6**: `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_5_vs_V8_6_ACTUAL_CYCLES_PREVIEW_COMPARE.png`, SHA-256 `99e0a29dbc4f2c71251f243ae314a3bf6265b654f616a4324e9b9a2ca9163012`.
- Comparison caveat: ORIGINAL PMT Cycles was 960×640 at 10 spp then downsampled to 480×320; v8.5 and v8.6 are 480×320 at 4 spp. **Camera/framing matched, image sampling NOT matched to the original.** Do not use this comparison for texture-accurate photometric equivalence.
- Private archive: `/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/Daytona365_BLENDER_REWORK_v8_6_PRIVATE.zip`, **7,178,526 bytes**, SHA-256 `0d13d742602c92c0f7fdd513d475dabbdc2026a8c5adc5d562b4915e61e9fe48`, 12 files, ZIP integrity checked. Includes actual editable blend and renders, excludes PMT/DDS/OVC/EXE.
- `tools/verify_daytona365_v8_6_blender.py`, `tools/render_daytona365_v8_6_actual.py`, `tools/make_daytona365_v8_6_actual_compare.py`, `tools/package_daytona365_v8_6_private.py`, `tools/test_daytona365_v8_6_source_contract.py` added. CI runs source AST/static only, **not Blender render**.

**RENDER_VALIDATION=PREVIEW_ONLY.**
**FULL_RESOLUTION_MATCHED_CYCLES=UNTESTED.**
**GAME_RUNTIME/OVC/QUEST3=UNTESTED.**

## Remaining issues and next increment
The real original PMT shows darker, less stylized upholstery and a different seat back/console segmentation than this tan reference-inspired candidate. The v8.6 lower fairing is more coherent but still visibly simpler than the original integrated console and footwell. For **v8.7**, map the original `object00_group01_material017_a0` seat and `material018_a0` console *visible projected silhouettes*, then split seat cushion/backrest side returns and manually modeled instrument/center-panel transitions without hiding real controls. Run a matched 960×640 10-spp comparison only on authorized Windows/GitHub runner where the private scene is actually available; N100 remains a light preview/provenance host.

No game binary, OVC, DX11/DX9Ex branch, Dino or Model2VR source was modified.
