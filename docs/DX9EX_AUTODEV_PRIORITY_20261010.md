# DX9Ex VR defect-first execution policy — 2026-10-10

Status: latest explicit user priority override. This file supersedes conflicting priorities in AGENTS.md and older DX9Ex queue/controller contracts; retain safety, branch isolation and baseline protections. Docker controller runtime deployment must be verified separately.

## Immediate focus
- DX11 Native A remains global conversion priority. DX9Ex C work is limited to unresolved user-visible VR defects, stereoscopic correctness, OpenXR runtime interoperability, and measured VR performance. Do not fill a 50% allocation quota with low-value work.
- P0: fix only outstanding confirmed optics: central lens flare dot doubled/headlocked (preserve other discs), stage +TIME and GOAL progress title/time doubled/headlocked (preserve completed results), car-detached rank markers, remaining shadow/HUD attachment issues confirmed by HMD feedback. Preserve all previously user-accepted optical PASS paths.
- P1: stereo/camera/pose/recenter correctness, VD/OpenXR per-eye resolution and reset lifecycle where needed to fix observed VR issues; GPU/CPU frame pacing in dense buildings/sand/particles. 72 Hz stable is the immediate user-visible performance gate; higher 90/120 FPS are subsequent measured optimization targets, not substitutes for correctness.
- FFB v0.2 and currently working gamepad/input are FROZEN. Do not alter XInput/SDL rumble, disconnect stop, initialization or FFB source merely for cleanup/refactoring. Allow a narrowly scoped integration bugfix only if a reproducible user-reported VR regression and focused negative test demonstrate necessity; never change upstream FFB release.
- Defer general R84/refactoring, state-machine hardening, defensive edge-case patches, repeated same-SHA CI, status-only reports, and unrelated controller bookkeeping. No automatic next-stage fallback to unrelated work merely because HMD verification is pending.

## Acceptance
1. Tie each new task to a specific outstanding VR symptom and the exact original producer/path or reproducible performance trace.
2. Make a bounded material source change with targeted regression checks protecting known-good paths; avoid speculative global remapping.
3. Record exact-SHA GitHub CI results separately from Quest3/VDXR HMD acceptance. Until tested on hardware, RUNTIME_VALIDATION=UNTESTED, not PASS.
4. No feature-complete claim based on commit count, CI alone, or repeated audits. Preserve immutable dx9ex-baseline-20261010 and lane isolation.
5. External controller must reload this policy each dispatch; any old FFB-first/R84-first/50%-quota ordering is superseded. Verify actual controller deployment independently.
