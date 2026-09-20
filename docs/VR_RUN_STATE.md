# VR Run State

Updated: 2026-09-20 22:52 KST

## Current checkpoint
- C0 RECOVER: complete — 2D and D3D9 SAFE startup regression cleared on the previous recovery build
- C1 REVIEW: complete — runtime logs isolated the flat half-screen symptom to transport/fallback policy rather than common game startup
- C2 IMPLEMENT: complete — SAFE transport policy, host fallback crop guard, and DX12 D3D9On12 device-creation semantics updated
- C3 VALIDATE: complete — all unified backend jobs and package validation succeeded
- C4 COMMIT: complete
- C5 PACKAGE: complete — frozen tester ZIP produced
- C6 STATE: complete

## Frozen recovery candidate
- Integration commit: `803144005c0e45352602917a2f51804ec6b18ae6`
- Matrix: `VRM-20260920-803144005c0e`
- Unified workflow: `35514339728` — success
- Build workflow: `35514339665` — success
- Unified artifact: `10606816032`
- Artifact ZIP SHA256: `1517890fd2efe90f9c5fe8f345d7fd695b534b33de5ad1937441836f386e6cca`
- Tester inner ZIP SHA256: `e48b1648ce80f7027e3cdea3bbb13192cc56c5bd99628ee886759e6d8916e065`

## Backend source identity
- D3D9 SAFE: `803144005c0e45352602917a2f51804ec6b18ae6`
- DXVK game + host: `5e58ee35e14636dbfad3ad3744d350aa09859992`
- DXVK provider: `5bb301ab22f7b41d68a879bf84c1e3d10ae0c473`
- Multiview patcher: `0ef3253da1738b07e67358a027311c7bcedaa001`
- DX12 strict: `ab8e00ab4a21e4ebb23fbc4046abda51e885bcb6`

## Runtime evidence that led to this candidate
The previous recovery package reached normal startup in 2D and D3D9 SAFE. D3D9 SAFE and DXVK SAFE then showed the same enlarged/cropped left-half flat image in gameplay, while DX12 STRICT failed device creation.

The logs and source review showed:
1. SAFE configuration had `DirectGpuOnly=false`, but the game R9 transport gate read stale CRT environment values and stayed in direct-only mode. That suppressed SBS/Desktop Duplication fallback even though no shared-eye transport was ready.
2. The host recovery theater always cropped the left half, even when the desktop source was a normal full-width mono frame. That exactly produced the observed half-screen zoom.
3. DX12 reached `Direct3DCreate9On12Ex`, then failed device creation with `D3DERR_INVALIDCALL`. The strict branch now uses legacy D3D9On12 `CreateDevice` semantics and a bounded compatibility retry without permitting native D3D9 fallback.

## Fixes frozen into this matrix
- D3D9 SAFE: `R9DirectOnlyTransport()` follows parsed `Settings::VRDirectGpuOnly` directly.
- DXVK SAFE/MULTIVIEW: same game-side transport fix synchronized to the DXVK branch.
- D3D11 OpenXR hosts: left-half crop is used only for a frame explicitly marked completed SBS; otherwise recovery shows full-width mono.
- DX12 STRICT: legacy `CreateDevice` contract first, then one bounded presentation normalization retry while staying on D3D9On12.
- `SkyGlowFactor = 1` remains packaged.

## Non-blocking branch CI notes
Two generic branch workflows still have stale checks unrelated to the unified tester result: the DXVK generic R34/OFF build exercises an older incompatible renderer combination, and its host verification script uses PowerShell's reserved `$Host` variable; the DX12 generic verifier searches for the old strict-pass marker string. The unified workflow builds and stages the intended SAFE/DX12 payloads successfully and is the acceptance path for this tester.

## Next runtime test
Use only the frozen `VRM-20260920-803144005c0e` tester. Test D3D9 SAFE first and look for actual geometry stereo rather than a flat recovery theater. If D3D9 is good, test DXVK SAFE. Then test DX12 STRICT only far enough to see whether device creation/startup now passes; deeper DX12 rendering work comes after that boundary is cleared.
