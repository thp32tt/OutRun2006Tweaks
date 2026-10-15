# Second cross-source review: complete replacement DDS mip payload

2026-10-08, DX9Ex vr-d3d9ex-focus.

Confirmed cross-feature source defect: `HandleTexture()` validates only the first mip before overwriting the original source DDS header, changing UI sprite scaling and routing to a replacement buffer. A replacement with a well-formed header/first level but truncated later mip levels can then fail in the original D3DX scene/cube decoder, leaving the original game memory header changed and risking missing environment/UI resources. Previous 00548 descriptor-size hardening did not close this gap.

Fix: check `DDSD_MIPMAPCOUNT`, reject zero or more than 32 declared levels, walk every declared level and validate calculated format byte count against remaining payload **before** original header overwrite and sprite scale changes. Keep historical original-header compatibility behavior otherwise unchanged. Add six negative test cases to `verify_vr_hud_dds_loader.py` (20 total mutations) and its P0/EXE HUD Inspector/DX9Ex Active exact-SHA validation.

Follow-up: GPU/driver-side D3DX failures can still occur after metadata checks; a separate scoped original-data restoration/texture fallthrough design needs careful lifecycle/producer proof before implementation. RUNTIME_VALIDATION=UNTESTED.
