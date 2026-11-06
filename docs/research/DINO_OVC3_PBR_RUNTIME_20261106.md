# Dino external cockpit OVC3: normal / roughness / metallic (2026-11-06)

Branch: `feature/dino-external-pbr-runtime-v1-20261106`. Never replace the original game PMT/XPR assets.

## What is implemented

- **OVC3** keeps the OVC2 36-byte header, meshes, indices, UVs and albedo DDS payload byte-for-byte; changes magic/version to `OVRCABH3`/3 and adds `OVCPBR3!` material records.
- Each material record: 3 little-endian f32s (`roughness`, `metallic`, `normalScale`) followed by length-prefixed optional normal-map DDS and ORM DDS. Zero map length means no map. ORM is R=occlusion, G=roughness, B=metallic.
- Portable parser bounds-checks all PBR factors, map formats/mips, CRC and combined 112-MiB GPU budget *before* modifying the active model.
- D3D9 Shader Model 3.0 vertex + pixel shader with tangent basis computed from triangle derivatives (preserves the current FVF/vertex stride), GGX direct-light specular, Fresnel, ambient and normal-map response. Each stereo eye uses the world/view/projection and camera position supplied by the verified original eye draw.
- GPU textures/shaders are released on Reset and device changes. Shader compile, shader bind or optional map allocation failure falls back to existing fixed-function textured model instead of hard-failing the draw. Existing OVC1/OVC2 models render through the unchanged default pipeline.
- D3DCompiler_47 is dynamically loaded: there is no hard dependency on a D3DX runtime. Unsupported SM3 hardware falls back.

**Limitations:** This is an **initial metal/roughness PBR shader**, not a full image-based-lighting/environment-reflection implementation. The directional/ambient light is currently an approximate world-space source, *not* yet sampled from original OutRun night/day lighting. No final HMD visual/performance certification. Albedo remains the original DDS unless separately upgraded.

## Build OVC3 from your current OVC2 and Blender maps

1. Preserve the original `Dino246_Cockpit_LHD_v15.ovc`. Export normal and packed ORM maps from Blender at 512/1024/2048 power-of-two dimensions; PNG or DDS. Use OpenGL-style tangent-space normals; ORM = ambient occlusion (R), roughness (G), metallic (B).
2. Next to the map files create `dino-pbr-materials.json`:

```json
{
  "materials": [
    {
      "index": 0,
      "roughness": 0.75,
      "metallic": 0.05,
      "normalScale": 1.0,
      "normal": "material0_normal.png",
      "orm": "material0_orm.png"
    },
    {
      "index": 1,
      "roughness": 0.40,
      "metallic": 0.90,
      "normalScale": 0.8
    }
  ]
}
```

3. Run the converter in its repo working directory (Pillow is needed **only** for PNG):

```powershell
py -m pip install Pillow
py tools/upgrade_dino_ovc_pbr.py --input-ovc "D:\model\Dino246_Cockpit_LHD_v15.ovc" --materials-json "D:\model\dino-pbr-materials.json" --output-ovc "D:\pbr-test\Dino246_Cockpit_LHD_v15.ovc"
```

4. Test only against a **matched PBR-enabled R26 Win32 DLL/OpenXR host** build and a copy of your original game folder. The original/installed stable OVC2 and DLL should be backed up first. The stable runtime path uses `Dino246_Cockpit_LHD_v15.ovc` by default. Only the explicit PBR copy-run mode sets the process-only `OUTRUN_VR_DINO_PBR_TEST=1` flag, selecting the *separate* `Dino246_Cockpit_LHD_v15_PBR.ovc` file. A missing/corrupt PBR sidecar does not replace the stable file. **Do not** deploy a new OVC3 file with an old DLL (old parser rejects the OVC3 signature). The PBR branch's CI packages a matching Win32 DLL and x64 OpenXR host with matching `SOURCE_SHA.txt` and `HOST_BUILD_SOURCE_SHA.txt`. Do not launch a PBR DLL alongside a host from another source SHA. This is a build artifact, **not** a complete ready-to-run model package. `RUN-QUEST-APK-DINO-PBR.cmd` and `QuestCockpit-CopyRun.ps1 -Mode PBR` additionally require a complete `QUEST_APK_COPYRUN_PAYLOAD` with a verified `IDENTITY.json` (including `DinoPbrModelSha256`) and the new OVC3 model. Do not use a former FitV6 payload/manifest as the PBR package.

## Validation

- Linux C++ parser: `tests/test_dino_external_sidecar.cpp`, `tests/test_dino_external_hq.cpp`, `tests/test_dino_external_pbr.cpp`.
- Python OVC2→OVC3 converter: `python3 -m unittest tools.tests.test_upgrade_dino_ovc_pbr`.
- Windows real shader bytecode compilation: `tools/tests/test_dino_pbr_hlsl_win.cpp` with D3DCompiler_47 (`vs_3_0`, `ps_3_0`).
- Windows R26/HUD 32-bit game DLL and same-checkout x64 OpenXR host: `.github/workflows/dino-external-pbr.yml`.
- Windows PowerShell parse, exact-SHA preflight and synthetic install/conflict/restore: `tools/tests/test_dino_pbr_copyrun.ps1`.
- Pending HMD checks: per-eye material shading and handedness, rotated/mirrored UVs, seat/column/dash normal response, frame pacing in beach/greenery areas, Reset/exit/menu crash reproduction and regression against OVC2.

## Format & safety notes

- Only OVC2 accepts upgrade; use a new output path, never in-place overwrite the input file.
- The packer validates 2048-maximum power-of-two DDS sizes, bounded mip payloads, material index uniqueness, finite PBR factors and byte budgets.
- Failure to find a map or parse invalid map data aborts before writing the final output.
- BC1/BC3 DDS supports high-resolution material sets within the 112-MiB GPU budget; uncompressed 2K maps across many materials can exceed the budget. 
