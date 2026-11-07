# Daytona 365 GTS/4 original-PMT cockpit PBR experiment (2026-11-07)

**Status:** static structural checks PASS on N100. **No runtime R26/OVC or Quest3 testing.** This branch does not modify Dino assets or production render hooks.

## Scope and provenance
- Original player car: `Cars/obj_plcar_dayts_pmt.sz`. SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`. Only read, never modified.
- Original asset is not committed. The existing converter `tools/dino_original_pmt_to_glb.py` is reused as a read-only PMT/GLB parser; **Dino output is not changed**.
- Real Daytona reference photos on the private N100 are for visual study only; third-party imagery is not included in public commits.
- Generic leather micrograin comes from an image-generated illustrative crop reduced to a 32×32 high-frequency seed, not a vehicle-specific regenerated UV atlas or photorealistic texture replacement.

## Generated private N100 outputs
`/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/Daytona365_InteriorRework_v1_PRIVATE.zip`

| Output | What it represents |
|---|---|
| `Daytona365_OriginalCar_CockpitPBR_v1.glb` | 27 original object-0 submeshes, 6,554→7,736 triangles |
| `Daytona365_InteriorSurfaces_ONLY_v1.glb` | 6 selected cockpit-related texture/material groups, 442→1,624 triangles; **not the entire interior** |
| `Daytona365_Steering_LOCAL_PBR_v1.glb` | Object 22 candidate, 331 triangles, original local coordinates, mount transform unverified |
| `textures/` | 4× upscaled diffuse plus approximate tangent-space normal, packed roughness, AO |
| `MANIFEST.json`, `VALIDATION.json` | SHA provenance, inventory, GLB bounds/references, material coverage |

## Working requirements
Run from the checked out repository in the prepared private N100 environment with Pillow installed, using `tools/daytona365_pmt_cockpit_pbr.py`. The script uses the user-authorized N100 game directory as its input and writes only under the directory containing the script; change the input path for another machine as needed. Run `tools/daytona365_extract_preview.py` for previews and `tools/test_daytona365_pmt_cockpit_pbr.py` for static tests. The scripts do not open the original in write mode.

## Next integration gates
1. Confirm the cockpit subset and wheel identity using source draw owners, not by blindly trusting PMT object indices.
2. Obtain the exact wheel mount/pivot transform instead of positioning at geometry AABB center.
3. Convert GLB to a supported R26 OVC sidecar with correct materials, coordinate basis and source scale. glTF normalTexture does **not** prove the OVC loader supports normal maps.
4. Suppress legacy player-car/cockpit rendering *only* when the replacement is fully loaded, and restore it on failure or menu transition; avoid twin wheel/chassis draw.
5. Perform exact-source build, VR bilateral display/performance, selection menu, and finish-to-menu crash tests before promotion.

Do not publish private original PMT, extracted DDS, or copyrighted reference photos. No score is claimed for runtime completion.
