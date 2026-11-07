# Ferrari 365 GTS/4 Daytona — source-envelope Blender v8.7 actual model

Date: 2026-11-08 KST. Branch: `feature/daytona365-blender-v8-20261108`.
Scope: original-game-derived second Ferrari 365 GTS/4 cockpit, independent private Blender asset; no OutRun/Quest runtime conversion.

## Exact input and original PMT measurement
- Real Blender v8.6 input: `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_6.blend`; SHA-256 `cb0eba836a69b3154012bd755fafac92b92b223be0e9394a876c322123e1f2f4`.
- Private original game `original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` opened in Blender 4.5.15 for aggregate bounds-only inspection. `object00_group01_material017_a0` contains 184 seat-object vertices spanning X [-0.57464,+0.57464], Y [-0.72863,-0.01985], Z [0.33179,0.85149] metres. `material018_a0` original console (24 vertices) spans X [-0.10683,+0.10683], Y [-0.23555,+0.20228], Z [0.33638,0.51887]. These measured constraints are numbers only, not a claim of exact surface match and not republished PMT source geometry.
- Prior v8.6 left cushion was X [-0.52518,-0.18082], front Y -0.16457; this genuinely differed from PMT extent. The same source camera `V7_Camera_Reference_ThreeQuarter` is preserved.

## Actual Blender source work
- `tools/blender_daytona365_v8_7_seat_source_contours_underdash.py`: made four original high-resolution seat shells wider in place without scaling the whole vehicle, extended front cushion **118 mm** by gradual parameter deformation, reshaped upper backrest width and shoulder bolsters, and added restrained geometric pleat channels. Top/underside upholstery geometry remains one connected source-derived object per shell, with original 49-mm cushion Z return and 54-mm backrest Y return.
- Measured new left cushion outer envelope X [-0.55376,-0.15224], Y [-0.600,-0.052], Z top [0.38950,0.46807]; left backrest X [-0.55330,-0.15270], Y [-0.72578,-0.48211]. Right side mirrored. Changes move toward the aggregate original without asserting pixel-perfect match.
- Four `V8_7_GEODESIC_LEATHER_UV` maps measure actual updated per-row/per-column physical lengths before mapping 5.45 texture repeats per metre. All existing v8.5 welts and v8.6 bolster inset seams are reprojected to the new surface; the new conformal front piping and horizontal pleat stitching are real curves.
- Outer 9-column joined seat side-return polygons (2,012 per cushion, 2,240 per backrest) use a separate source-image-derived packed PBR material. The original upholstery material and image nodes stay available; tangent Normal, ORM-green roughness, BaseColor and offline Height/microbump are preserved.
- New driver/passenger `V8_7_*_SCULPTED_UNDERDASH_KNEE_RETURN` physically modeled sloping footwell sheets, with solidify, normal smoothing, locally measured UV, and dark PBR; stay below Z 0.580m and outside center native switches. Sculpted previous v8.6 lower fairing remains below original-game switchbank lower bound Z 0.58656m.
- Source game gauges, photo switchbank, Ferrari wheel emblem and steering spokes, H-pattern chrome shifter and game/OVC files unchanged.

## Real source and render verification
- Blender **4.5.15 LTS**: real new editable v8.7 file SAVE and fresh separate-process REOPEN **PASS**, 104 meshes and 82 curves. `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_7.blend` **6,736,533 bytes**, SHA-256 `e247abed67d15b5562daa5374163cc4c3a18de7dd059bfc42d94c9227e0e61a3`.
- Source `tools/test_daytona365_v8_7_source_contract.py`: 19 source guards PASS, including no original game file edits and preserving the PBR/image pack boundary.
- Actual Blender Cycles rendered `docs/images/daytona365-v8/Daytona365_v8_7_ACTUAL_CYCLES_PREVIEW.png`: **480×320, 4 samples, 2 CPU threads, denoising, exposure -0.52**, SHA-256 `906ad0929dfffbbcca301016434a1f8bd60d102ccf524cad61733ca9efbc5243` (259,163 bytes). Blender render subprocess exit code **0**; the independent wrapper looked for a different marker and reported failed wrapper state, but Blender stdout contains the true success marker and a verifiable output PNG/provenance. Do not rerender this already verified evidence to satisfy wrapper naming.
- Original PMT / v8.6 / v8.7 true three-panel Cycles comparison: `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_6_vs_V8_7_ACTUAL_CYCLES_PREVIEW_COMPARE.png`, SHA-256 `192a6846543c4040c98f6bd2dedf01c298d78001c6f45c3fac2a44394180d132` (537,598 bytes). Original PMT was **960×640, 10 spp and downsampled**; v8.6/v8.7 both **480×320, 4 spp**. Same calibrated camera/framing but **NOT photometrically matched to original**.
- Actual v8.6-to-v8.7 RGB comparison: 133,670 of 153,600 RGB pixels differ, average per-channel absolute difference 10.5185; measures material geometry change, **not** a model-fidelity percentage.
- Private editable ZIP: `/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/Daytona365_BLENDER_REWORK_v8_7_PRIVATE.zip` (7,459,974 bytes, 12 entries, SHA-256 `c6292202dc340cf524049a899d888e92968e1d41d8c4be5f8919f829c9db3b94`) ZIP integrity PASS. Contains new Blender file, genuine rendered comparison, manifests, scripts, excludes PMT/DDS/OVC/EXE.
- GitHub Actions source-only gate is added in `.github/workflows/daytona-blender-v8.yml`; CI never asserts actual Blender execution/Quest 3 runtime.

**RENDER_VALIDATION=PREVIEW_ONLY.**
**FULL_RESOLUTION_MATCHED_ORIGINAL_CYCLES=UNTESTED.**
**GAME_RUNTIME/OVC/QUEST3=UNTESTED.**

## Remaining visible gap / next stage
The real original PMT has a larger, dark rear-seat/headrest silhouette and a more vertically complex center-console lower fascia. The v8.7 tan leather seat is widened and more complete but has different upper-back crest, padding segmentation and material character. For **v8.8**, focus on the actual reference-dependent **upper backrest/headrest contour and original front cushion pleat segmentation**, without scaling the whole car or hiding the original controls. Verify real renders at consistent 960×640/10 spp only on authorized workstation/GitHub runner with private scene available; do not burn CPU on N100.
