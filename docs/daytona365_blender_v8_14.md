# Ferrari 365 GTS/4 Daytona Blender v8.14 — source PMT018 shifter underdeck

2026-11-08 KST. Only the dedicated feature/daytona365-blender-v8-20261108 branch is changed. Original game/VR runtime, Model2 VR and UW2 remain untouched.

## Independent physical geometry and source-linked PBR

- The real original PMT vs actual v8.13 Cycles comparison showed an overly boxy shifter leather underdeck behind the original H gate. The original V8_1_COMPACT_SHIFTER_LEATHER_DECK was an 8-vertex, 6-polygon transformed box spanning X ±67.5mm; Y [-194.5,-27.5]mm; Z [.4045,.4235]m.
- **v8.14** reworks that SAME existing object in place to 10 physical transverse stations x 10 perimeter samples = **100 vertices, 92 faces**, with rounded shoulder, a rising pad underneath chrome, recalculated normals, 3D bevel/weighted normal and two actually modeled 3D stitch curves. It remains within original PMT group018 aggregate X ±106.83mm, Y [-235.55,+202.28]mm, Z [.33638,.51887]m. The group018 bounds are source-measured aggregate constraints; original PMT vertices are NOT copied or claimed to be matched.
- Metric tangent UV V8_14_PMT018_DECK_METRIC_TANGENT_UV follows surface perimeter and longitudinal length, not default unstretched UV. The original 32-vertex chrome H gate, 433-vertex black shift knob, controls, source rim and v8.13 seven-pleat seat meshes are preserved.
- New deck-only V8_14_PMT018_Shifter_Deck_Grain_Source_PBR clones the original source-linked BlackLeather BaseColor, tangent Normal, ORM green roughness and Height. All four genuine maps remain packed, including non-color Normal/ORM/Height. Attenuation of the existing BaseColor and restrained original-source roughness/normal are used without generating artificial game textures.

## Verified actual Blender result

- Genuine immutable private v8.13 input SHA-256: 130accf3db850df025c836c0364d5a8dfebcf6001a88e61d19135b4331499cc7.
- Official Blender 4.5.15 LTS saved private Blender v8.14 scene SHA-256 **6de017b7f62b60a8484eef1b5eb8c851db037bd2ab88b1d09a79259b91702c77**, 6,451,798 bytes. Independent fresh-open PASS; 106 meshes and 94 curves. The input v8.13 checkpoint remains unmodified.
- True Blender Cycles same-camera preview: docs/images/daytona365-v8/Daytona365_v8_14_ACTUAL_CYCLES_PREVIEW.png, SHA-256 **d9d8638b0abfd36b7efa66423cf490b5600423b8170e23cc55b3c5b9bd4007c1**. 480x320, 4 samples/pixel, 2 CPU threads, denoised; exposure -0.52, V7_Camera_Reference_ThreeQuarter.
- Original PMT/v8.13/v8.14 actual rendered comparison: docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_13_V8_14_ACTUAL_CYCLES_COMPARE.png, SHA-256 **48626a63d668f5ce3f54d81c8154b267ea633d8acaeb3d4408a4f22fdca1ba02**.
- Genuine original PMT used 960x640/10 spp then was downsampled; both new candidates used 480x320/4 spp, same camera. This does **not** establish equal-sample photometric equivalence; the isolated ROI delta of [2.614,2.513,2.474] is not a quality score and cannot attribute pixels solely to geometry.
- A separate, namespaced work directory avoided concurrent v8.13 authoring. Its immutable v8.14 .blend and verification/preview/compare provenance were copied without overwrite into the authorized private blender_v8 path. Public GitHub stores ONLY Blender Python scripts/source-only validation and actual PNG render evidence, not game PMT, DDS, executable, OVC or editable .blend.

**RENDER_VALIDATION=PREVIEW_ONLY.** FULL_RESOLUTION_MATCHED_CYCLES, OVC, GAME_RUNTIME, QUEST3: **UNTESTED**. GitHub Actions checks source AST/compile/guards only. Next independent visual candidate: original PMT side bolsters and lower front seat apron proportions rather than rescore seven-seat pleats or H-gate underdeck.
