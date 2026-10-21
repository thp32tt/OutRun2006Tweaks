# DX9Ex — 2026-10-21 all-source-improvements standalone test snapshot

- Purpose: reproduce all **implemented** DX9Ex changes integrated by 2026-10-21 18:57 KST without changing the active development branch.
- Parent source revision: `b746eb6b854e40797c98ea3ecb2f5ed3a14a7f90` from `vr-d3d9ex-focus`.
- Test branch: `test/dx9ex-all-improvements-20261021`.
- Changes to the actual game/host C++ source in this snapshot relative to the parent: **none**. The test workflow and this provenance document are test-specific additions. The test branch also contains a build-script-only PowerShell XML traversal portability fix in `tools/Build-OutRunPCFast.ps1`; no game or host C++ source differs from the pinned parent.
- Main included source fixes: stabilized driver-seat mode and camera anchor (no oscillating zoom); sticky cockpit session and camera restore; DX11 R57-style rank/rival source parity and original signed clip-W rank behavior; safer draw-distance node indexing, bounds, allocation and epoch tracking; queued D3DX telemetry ownership; existing R26 HUD/OpenXR rendering improvements through the parent revision.
- Reviews under `docs/reviews/dx9ex/automation/` are review-only notes, **not claims that proposed code was implemented**.
- Game DLL and OpenXR host: x86 `dinput8.dll` and x64 `outrun-vr-host.exe` via the repository's `tools/Build-OutRunPCFast.ps1` R26+HUD contract.
- Test workflow: `.github/workflows/dx9ex-daily-test-20261021.yml`; it pins checkout to event SHA, verifies output provenance, runs static checks, and uploads an independent ZIP. It does not replace the active `vr-d3d9ex-focus` branch or its normal LATEST drop.
- Package identity: `BUILD_INPUTS.json`, `SOURCE_SHA.txt`, `SHA256SUMS.txt`, `PC_BUILD_INFO.txt`.
- Build status: determined by GitHub Actions, not presumed by this document.
- `RUNTIME_VALIDATION=UNTESTED` until tested on the actual Quest 3/VDXR/Windows setup.

## Test steps
1. Download the ZIP artifact from the **DX9Ex 2026-10-21 Standalone Test** GitHub Actions run, extract it separately (back up your existing mod first).
2. Follow the ZIP's included launch instructions; prefer CORRECTNESS before PERFORMANCE.
3. Test cockpit enter/leave, repeated view changes, camera zoom, rank/rival HUD, busy scenes and Reset/recenter; record regressions.
4. Save `OutRun2_VR_ANALYZE_*.zip` for follow-up.
