# DX9Ex automatic development policy — 2026-10-10

Status: requested activation; controller deployment remains separate.

## Immutable baseline
- Snapshot branch: `dx9ex-baseline-20261010`
- Pinned source commit: `fcd18ddd89f6dd40a8246fcf8591f086811149f1`
- Never commit new work to snapshot branch; no force-push/reset of baseline.
- Development target: `vr-d3d9ex-focus`. Re-read latest HEAD before changes.

## Strict work priority (0 highest)
0. Port latest *verified released* FFB implementation into DX9Ex, preserving existing VR behavior. Identify upstream release tag/SHA, inspect license and APIs, port in isolated changes, and validate input/FFB regression. Do not confuse untagged HEAD with latest release.
1. Complete DX9Ex structural optimization/refactoring, resolving remaining TODOs with domain-isolation and hook/device-loss/recenter/HUD regression guards.
2. Follow Virtual Desktop/OpenXR runtime recommended per-eye render target dimensions (and refresh/resize lifecycle); avoid using desktop monitor pixel size or hardcoded Quest resolution. Handle runtime changes safely with bounds and rollback.
3. Optimize frame pacing and GPU/CPU performance, targeting **120 FPS / 120 Hz** on **RTX 4070 12 GB**, **Virtual Desktop High streaming quality**, and **Quest 3**. Follow OpenXR-recommended per-eye resolution at VD High (do not substitute a fixed pixel count). Frame budget **8.33 ms**. Measure app-rendered FPS separately from VD display/stream FPS, SSW/reprojection, encode/network/decode latency, and dropped frames. Do not count synthetic/reprojected frames as native 120 FPS. Capture measured before/after evidence, prioritizing dense buildings/sand/particles. Maintain visual quality unless a documented user-approved tradeoff is required.

## Execution contract
- DX9Ex lane enabled in controller only after controller config update and redeploy; do not claim activation from this document alone.
- Run end-to-end inspect -> implement -> test -> material commit -> CI -> result; avoid inspect-only completion.
- Respect separate DX11/DXVK/localization branches; do not overwrite concurrent work.
- Retain baseline as recovery point and compare changes against pinned SHA.
- Record progress to GitHub regularly, avoid duplicate TASK_ID scoring, distinguish static/CI checks from actual HMD runtime testing.
