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


## DX9EX-PKG-001 — Four candidate binaries built; assembly parser failed
Status: FIXED / OFFLINE PACKAGE VALIDATED

Workflow run `35516112968` successfully built four distinct Win32 game DLLs and the shared x64 D3D11 OpenXR host. The package job failed before copying files because PowerShell parsed `$variant:` as an invalid scoped variable. Commit `2827f20` changed it to `${variant}:`. Successful binaries were reused rather than rebuilt solely for this packaging error.

## DX9EX-CONFIG-001 — Required cadence/fallback keys absent from shipped INI
Status: FIXED IN `ee94dc8051b6de8c0b6ce67d9bdd8b613b98363c`

The DX9Ex packager requires `FramerateUnlockExperimental`, `DisableDesktopDuplication`, `FrameCadenceMode` and `FrameCadenceTargetHz`, but the branch INI did not declare those keys. That would have caused the next package attempt to fail after the parser fix and made runtime defaults less auditable. The keys now exist in their owning Performance/VR sections. The package pins the requested values and verifies exact lines before archiving.

## DX9EX-PKG-002 — Candidate package integrity
Status: VALIDATED OFFLINE / HARDWARE RUNTIME PENDING

Matrix `DX9EX-20260920-f46024f7005c` contains P1-P4 as four independent ZIPs. Every ZIP has a distinct game DLL, the same verified host, variant/matrix/source identity, automatic log launcher, scenario, Korean quick guide and internal SHA256SUMS. All checksums passed. Forbidden `d3d9.dll`, `multiviewpatcher.dll`, DX12 host and backend directories are absent. Quest 3/VDXR correctness and pacing remain user-runtime-required.

## VR-HUD-SEMANTICS-001 — UIScaling-derived HUD semantic baseline
Status: BASELINE / SOURCE-INTEGRATED / CI-PENDING

The shipped 4:3/16:9 UI reverse engineering is now the VR semantic
source-of-truth. Time Attack, Rank, REV/gear, Ghost/You/Diff, goal time,
Heart totals, Rival HUD, girlfriend speech, ranking emoji/text and related C2C
HUD are explicitly SCREEN_HUD. Rival-car rank markers (`sub_4BAD20`) and
attached car/world hearts are explicitly WORLD_BILLBOARD. Runtime trace schema
v2, static EXE analysis and automatic coverage use the same semantic names.
See `docs/VR_HUD_SEMANTIC_BASELINE.md`.
