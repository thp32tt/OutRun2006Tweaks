# DX9Ex runtime test build request — 2026-10-04 22:16 KST

- Branch: `vr-d3d9ex-focus`
- Runtime source checkpoint before this build-trigger record: `44322402216fde565ccf99fd257153a0f1d0a369`
- Purpose: package the latest DX9Ex structural-refactor state for real Quest 3 / VDXR validation.
- Static/build status: structural cycle 1000 completed; later R34 guard/dispatcher folding tests are present.
- Runtime status before test: `UNTESTED`.

## Runtime checks

1. Open F11 Tweaks/ImGui in menu and gameplay; confirm gameplay overlay is single, not doubled.
2. Check HUD and car-attached rank/marker ownership while moving the head; report doubled/head-locked elements.
3. Run stage transition and gameplay Reset/device-loss-like transitions; watch for missing/duplicated stereo output or crashes.
4. Check lens flare/shadow/white HUD regressions and obvious frame-pacing regressions.
5. Preserve logs from the bundled test harness if any defect appears.

This file is a provenance/build-trigger record only; it does not change runtime code.
