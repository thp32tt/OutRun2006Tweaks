# 2026-10-08 Cross-domain texture side-effects review

Material purpose: high-speed D3DX decoder is shared by UI and scene loads, but the earlier fast-loader fallback protected **only UI**. Scene D3DXCreateTextureFromFileInMemoryEx_Custom_dest returned the fast decoder HRESULT directly. Unsupported D3DX formats / extra options could erase world/environment textures, and non-null pSrcInfo/pPalette out-parameters were silently bypassed on success. The loader also changed global D3DSAMP_MINFILTER/MAGFILTER/MIPFILTER at *resource-creation time*, which can leak into unrelated HUD, scene, effects and stereo rendering.

Source fix:
- Fast scene Ex path is now only attempted for exact narrow set of semantics it truly supports (null metadata outputs, zero ColorKey, original size/format, one/default mip, zero usage/MANAGED pool, trivial filters). Any rich Ex caller goes through original D3DX trampoline with original arguments.
- Even compatible fast scene decodes fall through to original D3DX trampoline when unsupported DDS or lock fails; owner of transient replacement data stays alive through both attempts.
- Texture *creation* never mutates device sampler state; the game's draw state retains authority.
- Protect with `tools/verify_vr_texture_scene_contract.py --self-test` (16 obligations + 10 negative source mutations) and canonical P0/HUD Inspector/DX9Ex exact-SHA gates.

Other identified but not automatically changed in this root-cause unit:
- `src/hooks_textures.cpp` mutates original DDS header by `memcpy(*ppSrcData, file, sizeof(DDS_FILE))`. This is deliberate historical interoperability and requires binary caller-memory contract before removal.
- `src/hooks_input.cpp` has detached perpetual DInput enumeration polling; needs shutdown/owner test before altering legacy input.
- `src/hooks_framerate.cpp` calls D3DDevice()->Reset during loading; requires active VR Reset hook provenance / current settings interaction inspection.

Static compile success cannot establish hardware visual correctness or resolve historical 00519 HMD failure. `RUNTIME_VALIDATION=UNTESTED`.
