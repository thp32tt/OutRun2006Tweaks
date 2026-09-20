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
