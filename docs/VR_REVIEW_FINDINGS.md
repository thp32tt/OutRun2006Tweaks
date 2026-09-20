# VR Review Findings

## PKG-001 — Duplicate selector entry point
Status: FIXED

The unified test package exposed both `Select-OutRunVRBackend.cmd` and `OutRunVR-Backend-Selector.cmd`. The GUI selector is the intended tester entry point; the PowerShell backend engine remains internal. The duplicate CLI CMD wrapper is no longer copied to the tester ZIP.

## PKG-002 — Release/compliance files clutter tester ZIP
Status: FIXED IN WORKFLOW / CI VALIDATION PENDING

License/notice/corresponding-source files are no longer copied into the runtime tester ZIP. CI now creates a separate compliance ZIP so release obligations can be retained without mixing them into the user's test folder.

## PKG-003 — Lean package contract
Status: STATICALLY VALIDATED

The workflow now fails if the tester package contains the duplicate selector wrapper or license/notice/source-only files, and it verifies the required selector, launcher, collector, configuration, build identity, and test-scenario files.


## VR-TRANSPORT-001 — SAFE mode ignored DirectGpuOnly=false
Status: FIXED IN FROZEN MATRIX `VRM-20260920-803144005c0e`

The game-side R9 transport policy read `OUTRUN_VR_DIRECT_ONLY` through the CRT environment cache. The launcher/host could log `DirectGpuOnly=false` while R9 still behaved as direct-only, suppressing SBS/Desktop Duplication fallback and leaving the host without a completed stereo frame. R9 now follows the parsed setting directly. The same fix is synchronized to the DXVK game branch.

## VR-HOST-001 — Recovery theater cropped mono as SBS
Status: FIXED IN FROZEN MATRIX `VRM-20260920-803144005c0e`

The gameplay recovery path always rendered the left half of the desktop source. When stereo never became active, the source was a normal full-width mono frame, so this produced the observed enlarged left-half image. The host now crops only when shared frame state explicitly reports `StereoSbsActive` and `RenderFrameStereoComplete`; otherwise it uses full-width mono.

## VR-DX12-001 — D3D9On12 CreateDeviceEx invalid-call boundary
Status: FIXED FOR RETEST / RUNTIME VALIDATION PENDING

The failing DX12 log reached `Direct3DCreate9On12Ex` successfully, then device creation failed with `D3DERR_INVALIDCALL`. The strict branch now preserves the legacy D3D9 `CreateDevice` contract on the D3D9On12 provider and performs one bounded presentation-parameter normalization retry. Native D3D9 fallback remains disabled.

## CI-LEGACY-001 — Generic branch workflows contain stale checks
Status: NON-BLOCKING FOR UNIFIED TESTER

The DXVK generic R34/OFF configuration still compiles an older incompatible renderer combination and its host verification script assigns PowerShell's reserved `$Host` variable. The DX12 generic verifier also searches for a pre-change strict-pass marker. These failures do not affect the accepted unified workflow `35514339728`, whose intended D3D9 SAFE, DXVK SAFE host/game, DX12 strict, provider, multiview, and package jobs all passed.


## DX9EX-FOCUS-001 — SAFE-DRAW package discarded later correction chain
Status: CONFIRMED / STRATEGY CHANGED

The delivered A_CONTROL runtime logged `OUTRUN_VR_SAFE_DRAW_COMPARE`: R26/R23/R22/R13/R9 remained active while R29-R34 and renderer R29 were excluded. The user observed only the driver and shadow as acceptable while most other graphics returned to the older broken state. Treat this SAFE path as regression evidence only, not the production target.

## DX9EX-PERF-001 — Conservative path has severe draw amplification
Status: CONFIRMED / UNDER P1-P4 COMPARISON

Gameplay telemetry reached roughly 1,800-2,000 draws per Present with semantic rejection exceeding 568k. R26 retains independent mono safety replay plus stereo work, whereas R29 was introduced specifically to remove that steady-state third replay and repeated validation. P1/P2 therefore test the fast path with restored world classification before adding later overlays.

## DX9EX-PACING-001 — Recovery test forced 60 FPS into a 90 Hz XR session
Status: FIXED IN NEW TEST POLICY

The previous recovery launcher forced `FramerateLimit=60`, interpolation OFF and cadence OFF while the host reported a 90 Hz OpenXR display period. The DX9Ex-focus candidates use PhaseLock with runtime-selected refresh, interpolation enabled and safe 60 Hz only before valid XR cadence exists.

## BACKENDS-PAUSED-001 — DXVK/DX12 development frozen
Status: POLICY

DXVK SAFE reproduced the graphics regression with worse subjective HMD stutter. DX12 still fails at the same device-creation boundary after `Direct3DCreate9On12Ex`. Neither backend is to be compiled or packaged during the DX9Ex reference phase.
