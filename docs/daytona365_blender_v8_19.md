# Ferrari 365 GTS/4 Daytona — Blender v8.19 physical door/dash transition

Date: 2026-11-08 KST. Production only on `feature/daytona365-blender-v8-20261108`. No source-game, DX11/DX9Ex, Model2VR or Quest 3 runtime integration.

## Genuine Blender geometry/material improvements

- Source: immutable official Blender 4.5.15 LTS `Daytona365_Cockpit_Blender_PBR_v8_18_r2.blend` SHA256 `bde686212360eb7450697d3f762351eabe19751af54fa3ea58493063fcf72a4a`.
- Two existing 465-vertex/840-face original-derived leather door meshes: each moves 49 leading upper vertices at most approximately 4.6 mm, retains original dark door source-packed material and metric UV, recalculates normals.
- Existing two 8-vertex box door-top-cap objects are **replaced in place** with 17-station, 8-perimeter, 136-vertex/130-face physically curved rails while keeping original object/pivot and named source anchors. Adds a separate physically closed 128-vertex/122-face narrow side endcap to each front dash-to-door transition and four actually rendered 16-point stitches. This is original-source-envelope guided fabrication **not** recovered exact PMT vertices.
- Cloned original **packed BlackLeather BaseColor/Normal/ORM Green roughness/HeightOffline PBR** with physically dark non-metal finish. New independently analytic packed 256x256 tangent normal map SHA256 `ced314fe055b8d0fc38eadbf8895b82175cd65e94f19c0ea7e4e7b6457f16c61`; metric and aligned normal UV. Native gauges/switches/gear/steering, prior v8.17 cowl and v8.18 surrounds and all four seats validated unchanged.
- Initial v8.19 candidate closeup exposed excessively vertical side wedge; **final r2** adds smooth endcap radius taper and reduces peak. No previous .blend version overwritten and preliminary version earns no separate credit.

## Actual official Blender and render evidence

- Final private **`Daytona365_Cockpit_Blender_PBR_v8_19_r2.blend`**, official Blender 4.5.15 LTS saved/reopened PASS. SHA256 **`f018aee762f714f84fc3bec12991e217778d1eade598861511729bf901469300`**, size **6,852,319 bytes**, **112 meshes/106 curves**. Private editables/original PMT, DDS, OVC, EXE kept in authorized N100 private storage only.
- [Actual same camera Cycles 480x320 4spp preview](images/daytona365-v8/Daytona365_v8_19_r2_ACTUAL_CYCLES_PREVIEW.png): SHA256 `07d938acc28f8aa126793168a01befe183673899f0f93734c7d970de5cc98dc8`, two CPU threads, denoised, exposure -0.52.
- [Actual original PMT vs v8.18-r2 vs v8.19-r2 comparison](images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_18_V8_19_R2_ACTUAL_CYCLES_COMPARE.png): SHA256 `56990497807dd62647754f36e6d94f8f603cc9648047bcefcfa98b2505339ee5`. Genuine original PMT 960x640/10 spp downsized to 480x320, candidate 480x320/4 spp, so not photometrically or sample matched.
- [Additional actual side-endcap diagnostic Cycles](images/daytona365-v8/Daytona365_v8_19_r2_ENDCAP_CLOSEUP_ACTUAL_CYCLES.png): SHA256 `6fb50f70da022e1b5a2310cc89630d1f75874ccb892430e179a51b446801086c`. Unique left-side camera documents shape; NOT PMT same-camera proof.
- `tools/test_daytona365_v8_19_source_contract.py` AST/compile + 24 source guards PASS; CI source contract is not Blender. Real Blender saved/reopened/rendered separately. `RENDER_VALIDATION=PREVIEW_ONLY`; `MATCHED_FULL_RESOLUTION/OVC/GAME/QUEST3=UNTESTED`.

**Next independent improvement:** physically measure source-original steering hub/spokes-to-column/lower gauge-shroud depth, avoiding repeat of previously corrected rim material.
