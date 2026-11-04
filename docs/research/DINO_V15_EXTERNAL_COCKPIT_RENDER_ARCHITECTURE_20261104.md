# Dino 246 GTS v15: external-cockpit draw path instead of PMT .sz replacement

Status: architecture recommendation, no external runtime draw implementation yet.
Date: 2026-11-04 KST. User-owned offline mod, independent test branch.

## Evidence

- Current user dump: 0xC0000005, native game EXE RVA 0x3C030 (0x0043C030), write address 0x17638000, before VR stereo frames.
- Previous R1 dump: exact same native instruction, write address 0x16F66000.
- R1 and R2 expanded the compressed Dino PMT zlib stream. R2 still crashed. The original uncompressed PMT is 739,216 bytes; R2 is 1,881,432 bytes; R3 structural correction is 1,888,920 bytes.
- The decomp repository r4dius/outrun2-decomp at e1e1c592b802a6f3f7020a676abd3ba1be479e62 reconstructs loader and drawing logic: platform/pc_scene_select_car.cpp 0x46C090 -> 0x46A560 car draw; platform/vehicle_model_draw.cpp 0x46A560 (selection) and 0x46AE70 (gameplay) submit original model IDs into 0x405360/0x4056D0 draw stages; platform/pc_pmt_loader.cpp 0x42E4F0 loads per-format vertex/index buffers and shader records; platform/retail_asset_store.cpp maps vehicle asset requests mode 8 or 11 to existing .sz.
- The decomp repository is a native platform reimplementation of the PC game (README documents Switch/macOS/PS5/Xbox) and is not a drop-in patched Windows EXE. Its 128 MiB zlib and PMT limits are reimplementation safety guards, not proof of the Windows game allocator.
- R3 correctly expands shader cache matrix from 2*34*24B to 3*104*24B, links root mesh0 primitive count 2 -> 3; N100 exact-original PMT synthetic validation passed. The two structural fixes cannot independently solve a DEFLATE fault that happens before the model is parsed.

## Recommended implementation contract (do not continue growing native .sz)

1. Keep the user's original SHA-256 verified Cars/obj_plcar_dino_pmt.sz unchanged. Game remains responsible for loading the original Dino shell and wheel/driver systems; never ship original assets.
2. Package the external LHD v15 sidecar as separate .dcm/BC1 textures (19 materials, 70 groups) with a distinct digest and dimensional/finite-index validation. No XPR modifications and no growth of native PMT decompressed size.
3. In the existing VR mod's 32-bit guest D3D9 stateful render integration, create managed VB/IB and DDS textures independently of the game's PMT loader. Respect one device lifetime per resource cache, Release on Reset/lost-device, and check all Create/Lock/Draw API failures. Do not call native PMT loader for sidecar.
4. Do not render the sidecar in car selection, menu, or 2D game modes. Gate to Dino 246 GTS, camera 1 driver-seat view, active stereoscopic gameplay and stable world view. Derive vehicle world pose from same player-car draw as 0x405360/0x46AE70. Bind LHD model in model-local coordinates; don't directly use head pose as vehicle transform. Renderer supplies eye-specific view/projection.
5. Stage after original car's opaque draw with depth test/write consistent with cockpit and a separate transparent-glass pass. Preserve/restore all D3D9 render states, shaders, FVF/declaration, streams, texture stages, sampler settings and transforms via scoped state ownership. Avoid doubling render pass across original mono and both VR eyes. Keep physical car body and exterior VR view unchanged.
6. Use existing v15 normals/UVs for D3DFVF_XYZ|D3DFVF_NORMAL|D3DFVF_TEX1. Initially 19 BC1 albedo textures; glTF PBR normal/metal-rough material parity is a later shader enhancement.
7. Preserve accessibility of R1/R2 users: first provide byte-for-byte original restore and fail-closed SHA check. Never write unknown PMT or overwrite verified original backups. Deployment should be sidecar-only.
8. One feature branch, one nightly test ZIP. Instrument a modest one-shot menu/car model draw counter and per-eye guest Draw calls; turn off by default afterward. Never claim HMD PASS from CI alone.

## Explicit gates
- Control A: original exact-SHA PMT with sidecar disabled must not crash in car selection. If A crashes, fault cannot be attributed to cockpit PMT patch.
- Control B: same original PMT with sidecar installed but disabled must behave identically to A.
- Control C: sidecar enabled but still in car selection must not create GPU cockpit resources or submit cockpit draws.
- Control D: cockpit camera 1 in gameplay creates resources once and renders matching content in both OpenXR eyes without head-locked motion.
- Control E: camera switch and device Reset cleanly disable/rebuild sidecar resources, while exterior and occupants behave as before.
- Do not modify official release or core branches until user HMD verification.

## Source-of-truth links
- https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/pc_scene_select_car.cpp
- https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/vehicle_model_draw.cpp
- https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/pc_pmt_loader.cpp
- https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/pc_pmt_records.hpp
- https://github.com/thp32tt/OutRun2006Tweaks/tree/test/dino-cockpit-v15-pmt-r3-20261104

RUNTIME_VALIDATION=UNTESTED. This is a source-guided design, not a proven crash repair.
