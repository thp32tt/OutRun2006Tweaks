# Dino NoGlass FitV6 — R26+HUD user-model test package (2026-11-05)

## GitHub source and model provenance
- Branch: `feature/dino-fitv6-r26-test-20261105`.
- Model originally provided in the user's conversation: `Dino246_NoGlass_FitV6_UniformProportions.glb` (11,066,336 bytes).
- Input GLB SHA-256: `148f25de78d5bac36a5c4851cdea369620f120180741a0ad77f33c4969f9ac2d`.
- Geometry is FitV6 with the 0.879983286 uniform transform already applied; **no additional rescaling**.
- The uploaded binary is not committed to GitHub. This document records the actual uploaded-byte conversion, not a synthetic GLB.

## Conversion result and static validation
- Source adapter: `tools/cockpit/dino_v15_external/convert_fitv6.py`.
- Output on local ChatGPT build environment: `Dino246_Cockpit_LHD_v15.ovc` (48,932,625 bytes).
- Output SHA-256: `eba3510b2848b13702452ca6e0216ac99ad0528d0c40fd47c182e003ea5d1e6b`.
- OVC2: 48 meshes, 44 materials, 77,281 vertices, 135,376 triangles; CRC32 `c68c8b5d`.
- PASS: GLB exact SHA, OVC2 header/length/CRC, all mesh indices and triangles, DDS mip-chain sizes, vertex coordinate and UV equality against GLB float32, maximum vertex coordinate difference = 0.0 and UV difference = 0.0.
- The `v15` in the sidecar filename is the pre-existing R26 loader file ABI, **not the model content**.
- Material treatment is fixed-function albedo only; normal/metallic-roughness PBR rendering is not implemented in R26.

## Packaging provenance
- R26 external-cockpit game DLL: GitHub Actions `dino-v15-r26-safe.yml` SUCCESS, run `42001396048`, source SHA `56eef67ad4ef008beb1e10e0a988198d966c31c8`, DLL SHA-256 `d53491d8661d9f8ecebac1af8bb69ff342563ec44c53f818d7f6d816e98ba61e`.
- R26 Focus OpenXR host and launcher: GitHub Actions `vr-dx9ex-user-test-build.yml` SUCCESS, run `41555872989`, source SHA `12b70b89a70e756e063a9549c669505819c9548a`.
- Converter's own synthetic smoke and Windows EXE workflow SUCCESS: `dino-fitv6-converter.yml` run `42036862485`; the original uploaded GLB was converted and statically checked separately in the local environment.
- Test package: `OutRun2_VR_R26_Dino246_FitV6_TEST_20261105.zip`, size 19,671,110 bytes, SHA-256 `7bf72e85860ee2d14e6f32820271ece48c40fb018decc21e1f7f10e16f7ab690`.
- Package includes R26 x86 `dinput8.dll`, OpenXR host, R26 launch scripts, exact uploaded V6 OVC2, configured `[VR] DriverSeatView=true` and `DinoExternalCockpit=true`, manifest and static validation receipt, checksums and Korean instructions. Package lives in the user's conversation, **not** GitHub release assets.

## Safety and runtime validation
- Native `OR2006C2C.EXE`, PMT, XPR and original game assets are unchanged.
- External V6 loading is guarded by VR+stereo+driver-seat+gameplay and player Dino car kind 1, with no loading on car selection screen.
- Restore existing `dinput8.dll` and INI from user's backup to roll back. To disable sidecar alone set `[VR] DinoExternalCockpit=false` and restart.
- Static file validation: `PASS`. Physical Windows/Quest 3 gameplay, car selection stability, alignment, performance and crash verification: `RUNTIME_VALIDATION=UNTESTED`.
