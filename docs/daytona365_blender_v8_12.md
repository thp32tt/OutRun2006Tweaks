# Ferrari 365 GTS/4 Daytona v8.12 — native V5 reclining-back bright strip fix

2026-11-08 KST. Only `feature/daytona365-blender-v8-20261108` changed. Source PMT/DDS/OVC/EXE, original game, VR runtime branches, Model2 VR, webport unchanged.

## Measured diagnosis
- Source-model PMT vs v8.11 actual source-camera Cycles render showed a long bright strip over the near seat, even after four original piping curves had become dark and conformal.
- Scene probe found visible legacy `V5_L/R_SEAT_RECLINED_PADDED_BACK` meshes with old `TanLeather`, protruding up to z=.860m behind new v8.11 seat-back shells.
- An actual 480x320/4spp Blender diagnostic suppressed *only those two V5 objects at render time* without altering the saved input; the cream-colored strip vanished. This is a controlled source-visibility test, not an invented illustration or a pixel-level material ID.
- v8.12 corrects source geometry/material in place. Both V5 objects remain render-visible and editable, not deleted or hidden.

## Physical geometry and original source-linked PBR
- `tools/blender_daytona365_v8_12_original_shell_exposed_lip_pbr.py` reads the immutable v8.11 private Blender source SHA256 `f53ecaf68bea214831dd706baf79e12ab36d9c253febfe8b5bf367c1d13f9cb1`.
- Both retained V5 meshes preserve 1,617 vertices, 3,072 polygons, native UVMap and pivots. Upper crown physically tapers smoothly from Z=0.860000m to 0.850016m, under PMT group017 max Z=0.85149m; smooth face shading and normals are recalculated.
- Source-linked material `V8_12_Source_Charcoal_Original_V5_Back_Return_PBR` clones existing genuine packed BaseColor/tangent Normal/ORM green roughness/Height PBR, changing only shader tint, roughness and restrained bump. The corresponding original protected control meshes, 242-vertex headrest caps, 8,614-vertex seat-back meshes, 13-station tunnel, door and wheel preserved.

## Genuine save, reopen and image evidence
- Official Blender 4.5.15 LTS saved private new `Daytona365_Cockpit_Blender_PBR_v8_12.blend` SHA256 `03c7e288fad4ecb36952ca2f871e132ee079d9888dea4664d9a97923cd6945c6` (7,027,879 bytes). Independent Blender fresh-open check PASS, 106 meshes/92 curves.
- Actual Cycles `docs/images/daytona365-v8/Daytona365_v8_12_ACTUAL_CYCLES_PREVIEW.png`, SHA256 `11de66b30977b8d381166be0dfa25233edcbf2fa076e9e53cee506cff524f399`, 480x320/4spp/2 CPU threads, exposure -.52, same `V7_Camera_Reference_ThreeQuarter`.
- Original PMT/v8.10/v8.11/v8.12 real comparison `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_10_V8_11_V8_12_ACTUAL_CYCLES_COMPARE.png` SHA256 `e40d0d312177f1c1fd575148fea4bfadb3a166d16cdd86d6864f972b73d16b42`. Original PMT 960x640 10 spp downsampled, candidates 480x320 4 spp. Same camera only; photometric equivalence NOT established. The long tan strip is no longer visually prominent in v8.12.
- AST/py_compile/23 source guards PASS; GitHub CI is source-only, never counts as a Blender/Quest 3 test. Proprietary sources and editable .blend kept private off GitHub.

`RENDER_VALIDATION=PREVIEW_ONLY`. `FULL_RESOLUTION_MATCHED_CYCLES=UNTESTED`. `OVC/GAME_RUNTIME/QUEST3=UNTESTED`. Next independent v8.13: physical original PMT lower seat-cushion channel ridges/pleats plus normal/roughness fidelity.
