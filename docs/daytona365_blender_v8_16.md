# Ferrari 365 GTS/4 Daytona Blender v8.16 — physically formed backrest wing / lumbar PBR

2026-11-08 KST. Production branch: `feature/daytona365-blender-v8-20261108`. A separate simultaneous author had already saved/validated the v8.15 seat **cushion** side bolster and front apron, so this is **distinct BACKREST work** and does not earn any duplicate v8.15 credit.

## Independently completed real modeling

- Source: immutable actual Blender v8.15 scene SHA-256 `19728e96bb3b09ea92138cb4201218ac4479cdfaa7b624e375587fc0ef872006`. Isolated working copy in `/home/chatgpt-runner/work_handoff/daytona365_v816_ai2_0817/blender_v8/`. Previous scene remains intact.
- Edited both **existing** `V8_L/R_TAPERED_PADDED_BACKREST` meshes in place. Preserved each 8,614-vertex/8,612-face topology and 54 mm physical back-face return. Sculpted 3,838 changed front vertices per seat: side wings up to 8.8 mm forward, lumbar up to 4.5 mm forward, shoulder corners widened up to 3.2 mm, constrained to original PMT group017 **aggregate** bounds, not copied PMT vertices.
- Regenerated real surface-distance UV `V8_16_Backrest_Metric_Tangent_UV` and aligned `V8_16_Aligned_Wing_Tangent_Normal_UV`; reprojected eleven pre-existing physical backrest stitching curves per seat, added two actual modeled side-wing seams per seat. Existing v8.15 cushion geometry, v8.13 pleat normal, original V5 backs, native switchbank, gauges, chrome H-gate and steering source mesh are preserved.
- Cloned source-packed leather BaseColor, tangent Normal, ORM **green roughness**, Height/Bump. Darkened side/crown leather within source reference. Generated a new **256x256 analytical wing micro-normal** image SHA-256 `be65af2646e15a0345ef0cbe6ac6b9cc308a121fb13b65292abaccc3f6105cd2`, connected before original packed Normal and packed into the .blend. This analytic texture is not claimed to be extracted from original game.

## Real render and provenance

- Official Blender **4.5.15 LTS** saved private `Daytona365_Cockpit_Blender_PBR_v8_16.blend` 6,793,425 bytes; SHA-256 **`d0f3406886262359e9c079ee7eeb122d9a9ac5739d5ffb9148055c9422ee77da`**. Fresh independent Blender reload PASS, **106 meshes / 98 curves**.
- Actual same-camera Cycles preview, 480x320, 4 spp, 2 CPU threads, denoised, exposure -0.52: `docs/images/daytona365-v8/Daytona365_v8_16_ACTUAL_CYCLES_PREVIEW.png`, SHA-256 **`8b7a0bdfa4df0947e428f34881a3d4233712973bc9b3aa2978db3846da6ad1c1`**.
- Actual original PMT/v8.15/v8.16 comparison `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_15_V8_16_ACTUAL_CYCLES_COMPARE.png`, SHA-256 **`cab8f72a7cb79d3ba5e4ac9c9d4e5e90b5817581b6d8b9118029a2909e3ad81c`**. Original PMT Cycles used 960x640, 10 spp and was downsampled; candidates 480x320, 4 spp. The resulting ROI difference is not a quality score and does not establish matched photometric rendering.
- Local standalone AST/compile source contract PASS (18 focused guards). CI workflow tests **source only**, not Blender. The editable blend, original PMT/DDS/OVC/game binaries stay private, and no game/VR/Model2 branch was touched.

**RENDER_VALIDATION = PREVIEW_ONLY. FULL_RESOLUTION_MATCHED_CYCLES = UNTESTED. OVC/GAME_RUNTIME/QUEST3 = UNTESTED.**

Next distinct improvement: original dashboard gauge-binnacle hood depth and contour compared with the actual PMT render, without redoing seat work.
