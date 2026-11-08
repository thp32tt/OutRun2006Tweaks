# Ferrari 365 GTS/4 Daytona Blender v8.18 — original switchbank / center-stack formed surrounds

2026-11-08 KST. Dedicated source branch `feature/daytona365-blender-v8-20261108`. This is NEW work **after** verified v8.17 physical gauge hood; no previously completed cowl or seat work is repeated or rescored.

## New source-preserving physical geometry and packed PBR

- Genuine immutable input private v8.17 .blend SHA256 `fcbe1755599de7a67af43bf7497f8889a756cb5e529efc031ccb1279e3abf1c7`, source branch SHA `d95a5c7a64a317853599be6bcb978d9d6bd7637a`. Work isolated at `/home/chatgpt-runner/work_handoff/daytona365_v818_ai2_0926/blender_v8/`.
- Physically sculpted **430 original dashboard center-face vertices** on the same `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` (original 1,885 vertices/3,584 polygons kept) to form a localized up-to-11.5mm recessed center. Source original `V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING` remains the same 16-vertex lower panel, with 3mm top return.
- Added two genuine closed 3D molded switchbank side rails `V8_18_L/R_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN` and one closed lower sill `V8_18_SOURCE_SWITCHBANK_LOWER_MOLDED_SILL`, each **104 vertices/98 faces**, using formed multiple longitudinal stations, recalculated polygon normals, actual physical return and metric UV. Added **four real 3D welt paths**. Authentic source 70-vertex photo switchbank, 20-vertex high-res gauge, 908-vertex metal bezel, native H-gate/steering, v8.17 formed hood and v8.15/16 seats retain original vertex signatures.
- Genuine original source switchbank x ±0.14203m, z [0.58656,0.84727]m provided real geometric clearance; newly formed rails remain outside |x| 0.146m, lower sill lies below source bank z minimum. Original PMT reference is a same-camera image and source-measured envelope, NOT a recovered original game mesh claim.
- Custom PBR clones original packed BlackLeather BaseColor/tangent Normal/ORM **green channel roughness**/Height, metallic=0 and dark restrained leather. **672 original dashboard polygons** selected, plus three formed rails/sill and source lower fairing. New metric UV and independent aligned detail UV, true **256×256 packed analytical tangent detail normal** SHA256 `e826139809e0e57e61863339c0aca7d77b02b4beb0ccf771a64f99d5cbc41beb` mixed into the original packed normal before NormalMap.
- Initial visually too-thick rail candidate was genuinely saved/previewed then superseded. The final **r2** retains the original scene, shortens upper rail and changes outer section width/forward depth to remain restrained in source PMT comparison. No candidate overwrote another immutable .blend.

## Official Blender save / fresh reopen / Cycles actual evidence

- Blender 4.5.15 LTS saved private **`Daytona365_Cockpit_Blender_PBR_v8_18_r2.blend`**, SHA256 **`bde686212360eb7450697d3f762351eabe19751af54fa3ea58493063fcf72a4a`**, 6,836,757 bytes. Fresh independent process reopening **PASS**, **110 meshes, 102 curves**, original source-gauge geometry and packed maps verified.
- Actual Cycles same-camera preview: `docs/images/daytona365-v8/Daytona365_v8_18_r2_ACTUAL_CYCLES_PREVIEW.png`, SHA256 **`1ee8c56cbfb3c5302b3ce09ce8d06472974fba2e70bc8ef331457fd2e0978169`**, **480×320, 4 spp, 2 CPU threads**, denoised, exposure -0.52.
- Actual original PMT / verified v8.17 / v8.18-r2 three-way comparison: `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_17_V8_18_R2_ACTUAL_CYCLES_COMPARE.png`, SHA256 **`f529109aaf654c06da3f91e7b9ee2be6a378ec0ee86b7d5f3393789693e28b32`**. The genuine original PMT 960×640 10spp was downsampled to 480×320; candidates use 480×320 4spp. Color ROI differences are NOT photometrically matched or a game-likeness score.
- Local AST / source compilation / 30 source-guard contract **PASS**. CI is source-only; **actual independent Blender save/reopen/Cycles did run separately**. All heavy proprietary editable source and original game PMT/DDS/OVC/EXE remain private.

**RENDER_VALIDATION=PREVIEW_ONLY; FULL_RESOLUTION_MATCHED_CYCLES, OVC, ORIGINAL_GAME, QUEST3 = UNTESTED.** No game/VR/Model2 branches modified.

Next independent original-source mismatch: left/right dashboard-to-door endcaps and dark door-card trim continuity.
