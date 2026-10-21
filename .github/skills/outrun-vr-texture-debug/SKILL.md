---
name: outrun-vr-texture-debug
description: Investigate OutRun 2006 DDS, texture atlas, HUD pixelation, aspect distortion and alpha/transparency regressions.
---

# Texture / UV Diagnosis
1. Identify exact source DDS / replacement hash / atlas region, UV rectangle and expected logical source resolution.
2. Compare original compression, alpha mode, mip count, filtering, pixel dimensions, D3D9 supported formats and anisotropy/LOD.
3. Compare original game source viewport, UI logical viewport, D3D eye RT and OpenXR swapchain separately.
4. Test one copied DDS only, never overwrite original textures and never upload proprietary originals to public GitHub.
5. Compare screenshots from same scene and exact build; preserve provenance of captured input.
6. Do not declare sharpened or fixed pixels from static format inspection; HMD acceptance is separate.
