# DX9Ex — 2026-10-21/22 all-source-improvements standalone test snapshot

- Purpose: build an isolated test package containing the **implemented/actionable** DX9Ex source changes accumulated during the 2026-10-21 review cycle, without modifying the active development branch.
- Original snapshot parent: `b746eb6b854e40797c98ea3ecb2f5ed3a14a7f90` from `vr-d3d9ex-focus` (review 01272 point).
- Test branch: `test/dx9ex-all-improvements-20261021`.
- Additional integrated source set: the existing `vr-dx9ex-review105-integration-20261021` changes (SkyGlow target-scissor isolation, ScreenOverlay2D HUD scalar routing and matching regression checks), plus the latest `vr-d3d9ex-focus` rival-marker exact projector restoration and current hosted PC-fast package builder.
- Test-profile INI keeps the review105 A/B setting `Hud1080pReference = false`; restore `true` for the original-default comparison.
- Main carried source fixes also include stabilized driver-seat mode/camera anchor, sticky cockpit session/restore, rank/rival source parity work, safer draw-distance indexing/bounds/allocation/epoch tracking, queued D3DX ownership work and the R26+HUD/OpenXR improvements already present at the pinned parent.
- Reviews 01273 onward are explicitly `REVIEW_ONLY` and mostly conditional diagnostics/behavior candidates. They are evidence and test guidance, **not blindly enabled runtime mutations** when their own acceptance prerequisite was not established.
- Game DLL and OpenXR host: x86 `dinput8.dll` and x64 `outrun-vr-host.exe`, built by `tools/Build-OutRunPCFast.ps1` under the R26+HUD exact-SHA contract.
- Test workflow: `.github/workflows/dx9ex-daily-test-20261021.yml`; it builds the exact test-branch event SHA and uploads an independent ZIP artifact.
- Package identity: `BUILD_INPUTS.json`, `SOURCE_SHA.txt`, `SHA256SUMS.txt`, `PC_BUILD_INFO.txt`.
- `RUNTIME_VALIDATION=UNTESTED` until the exact ZIP is exercised on Quest 3 / VDXR / Windows.

## Test steps
1. Extract the standalone ZIP separately and back up the currently installed mod.
2. Launch with the packaged DX9Ex test entrypoint; use CORRECTNESS first.
3. Check cockpit enter/leave and repeated view changes/zoom, rank + rival marker placement, ESC/menu/HUD scaling, SkyGlow/bloom, +TIME/GOAL/result HUD, busy scenes, Reset/recenter and host startup.
4. Save the generated `OutRun2_VR_ANALYZE_*.zip` for regression analysis.
