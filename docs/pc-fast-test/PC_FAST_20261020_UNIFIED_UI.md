# PC fast-build request — 2026-10-20 KST

- Trigger: `[pc-build]` on branch `vr-d3d9ex-focus`
- Underlying code SHA: `abfabee4a9f815e2b5105e1e6e1c6d2048d56a9d`
- Requested build: incremental `tools/Build-OutRunPCFast.ps1`
- Runner: `[self-hosted, Windows, X64, outrun-pc]`
- Upload: `OutRun2-VR-PC-FAST-<request-commit-SHA>`
- Scope: request only, no DX9Ex C++/shader/build-script changes
- Test purpose: unified native 3D render resolution and independent 640x480 logical 2D menu coordinate mapping
- Validation: PC compile/package is NOT Quest3/VDXR runtime validation.
