# Full-source cross-domain deep review — 2026-10-08

The HUD-only 1000/5000 loops were regression checks, not whole-source impact analysis. This review adds:

- source/header inventory across `src/**` (C++, H, HPP, INC), SHA/dimensions for every path;
- cross-module build flags and real active R26+HUD vs R33 comparison;
- source-level risk candidates: detached DInput enumeration, fast-load D3D Reset, legacy EXE strcpy, original DDS header mutation, last-tail rank semantic tag, generic 2D shader-vs-fixed-function owner;
- scene D3DX Ex metadata/fallback and texture-creation sampler-state correctness;
- MSVC `/analyze` Windows Win32 compilation of actual active game variant, with full warnings artifact.

A flagged candidate is not an automatically proven bug. Only exact-SHA code fixes and green source/build/static gates may be considered build-verified; prior 00519 Quest3 visual failures stay open until one frozen HMD run.

Independent source scan: `python tools/verify_vr_fullsource_impact.py`. Hosted workflow: `DX9Ex Full Source Impact Review`. Never bulk-clone into N100 simply to run this review.
