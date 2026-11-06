# Dino 246 — Blender/PBR photo-match execution handoff (2026-11-06)

## Status and scope

This is a **real locally generated** working-kit milestone, but not a completed photo-faithful Blender model. The full private package `Dino246_Blender_PBR_v5_STAGING_20261106.zip` was generated in ChatGPT's working container and is available as a user conversation artifact; no copyrighted original OutRun resource or the user-provided concept-image binary is committed into public GitHub.

- ZIP bytes: **75,200,944**, SHA-256 `3a524847dbc3cb7521ece18882203ce5f6b915214424710ff8c6ef16df6d225b`, ZIP internal CRC test PASS.
- Input original-derived `Dino246_ConceptDetail_Cockpit_v4.glb` SHA-256 `e97c55f70132dd47321a4d4f4681c08c7adf11fa652eb53b80e82fd2b69a6743`, **481 source meshes**.
- Canonical photo supplied in the user's 2026-11-06 chat, SHA-256 `0c4d19980684571b283dd1070954c92f5a0ef236849a04db48b027fcb1cca53e`, **1448×1086**. See `docs/research/DINO246_LOCKED_VISUAL_REFERENCE_V5_20261106.md`. Never substitute another AI-generated interior as the new canonical reference.

## Package files generated and statically verified

- `reference/DINO246_LOCKED_REFERENCE.png`: exact original conversation reference image.
- `model/Dino246_ConceptDetail_Cockpit_v4.glb`: actual previous 3D editable scene data.
- `textures/<material>_basecolor.png`, `<material>_normal.png`, `<material>_orm.png` for each of **leather, vinyl, plastic, metal, carpet, seat**: 18 validated PNG images, all **2048×2048**. Normal channel uses tangent-space **OpenGL +Y**. Packed ORM channels are **R:AO, G:roughness, B:metallic**. Source photo supplies representative color; deterministic microscopic procedural grain supplies surface detail. **No diffusion/image-generation artwork has been applied.**
- `tools/make_pbr_maps.py`: reproducible generator for those 18 textures, strict canonical SHA check, manifest JSON.
- `tools/blender_rework_v5.py`: Blender 4.5+ or 5.x Python GUI/headless authoring script. Expected import, image-node PBR connections, normal/roughness/metal workflow, viewport reference background, target-specific deletion of v4's unrelated rectangular vents and radio, creating two physical round dash-top vent meshes plus three passenger-side toggle mesh sets, camera/lights, `.blend` and separate GLB export. It **must be runtime-tested in Blender**.
- `RUN-BLENDER-DINO-V5.cmd`: PC launcher with missing-input checks and Blender executable discovery; untested on a live Windows PC.
- `tools/test_v5_package.py`: PASS in ChatGPT local Python runtime for file hashes, source mesh count, 18 PNG dimensions, ORM channel semantics, Python AST and batch static checks.

## Material workflow

Follow official Blender glTF material topology: Image Texture Base Color (sRGB) → Principled BSDF Base Color; packed ORM (Non-Color) → Separate Color → Principled BSDF Roughness from G and Metallic from B; normal PNG (Non-Color) → Normal Map (Tangent Space, +Y) → Principled BSDF Normal. Export using glTF 2.0 `GLB`; after inspecting the user image's anatomy and original car PMT, correct UV seams/unwrap and bake details.

References: https://docs.blender.org/manual/en/4.4/addons/import_export/scene_gltf2.html and https://www.khronos.org/gltf/pbr/

## Mandatory remaining gates

1. **Need actual Blender runtime** on user's RTX 4070 Windows PC; neither the current ChatGPT local environment nor N100 has Blender available. No validated `.blend`, no runtime-modified GLB, no final in-game model, and no render are claimed at this stage.
2. The existing gauge family/layout remains incorrect relative to the exact user target (needs 2 large + 4 small) and will require manual/semiautomatic sculpted Blender fixes; also refine the dash fascia, leather upholstery sculpt and cabin geometry against the canonical target.
3. UV seams, material scale/texture softness, chrome alloy shader, AO/contact shadows and realistic stitched-seat normal bakes require visual inspection in Blender. Photograph-level fidelity cannot be established merely by producing 2K procedural noise maps.
4. R26 needs a separate optimized .ovc material conversion plus original cockpit draw suppression, camera fit vs APK, source-pinned launcher and headset validation before any copy-and-run installer.
5. `RUNTIME_VALIDATION=UNTESTED`. Keep the original and functioning R26 installation unchanged, and count this as a **preparation milestone**, not a shipped user-facing VR graphics upgrade.

## Exact-score note

No AI2 scoreboard credit is claimed for a still-unexecuted Blender pipeline. Actual material-generator output is validated, but claiming Blender model completion or runtime performance based solely on code generation is not justified. Same workflow follow-ups and repeats must not create duplicate points.
