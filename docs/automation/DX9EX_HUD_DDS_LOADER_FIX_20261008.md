# DX9Ex P0 fast DDS loader source-root fix — 2026-10-08 KST

## Reconstructed concrete source defects

The current `src/hooks_textures.cpp` `D3DXCreateTextureFromFileInMemoryEx_Custom` fast path called `IDirect3DTexture9::LockRect` using `D3DLOCK_DISCARD` on every mip, even for `D3DPOOL_MANAGED` UI textures with zero dynamic Usage. Direct3D9 documents DISCARD for dynamic textures; dynamic and MANAGED modes are incompatible. The wrong flag may fail `LockRect` and lead to missing menu/car-selection/YES-NO HUD textures.

Additional direct source defects: a DDS header and mip payload were accessed without checking `dataSize`, replacement selection accepted a DDS magic without verifying sufficient first mip data, an upload ignored D3D9 `Pitch` and copied packed rows contiguously, and the failure path `Release` left a dangling `*ppTexture`.

## Material changes

1. Bounds-check DDS header length and requested mip bytes before creating D3D9 texture, reject zero/implausible dimensions.
2. Use plain `LockRect` for MANAGED and static textures; use DISCARD only on the top mip of explicitly dynamic textures.
3. Upload each DXT block row and regular pixel row against actual `lockedRect.Pitch` while retaining the existing A8B8G8R8 channel conversion.
4. Release-and-null output on lock/row-pitch/UnlockRect errors; reject malformed replacement files **before** replacing the original source pointer or header, so original menu texture remains eligible.
5. New `tools/verify_vr_hud_dds_loader.py --self-test` checks 14 source contracts and eight intentionally invalid mutants. Integrated into P0, HUD Inspector CI and DX9Ex source path watch.

**Limit:** compile/static SUCCESS does not prove past 00519 visual failures fully fixed. Runtime status must stay `UNTESTED` pending one final, evidence-driven headset pass after remaining source static gaps are resolved. Do not schedule repeated trial builds.

Microsoft refs:
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/performance-optimizations
- https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3dtexture9-lockrect
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/accessing-surface-memory-directly
