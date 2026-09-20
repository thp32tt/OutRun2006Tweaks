# VR Run State

Updated: 2026-09-20 22:51 KST

## Current checkpoint
- C0 RECOVER: complete
- C1 REVIEW: uploaded 5f9028de retest logs reviewed
- C2 IMPLEMENT: complete
- C3 VALIDATE: all backend builds, hosts, selector smoke tests, package checks, and general Win32 build passed
- C4 COMMIT: complete
- C5 PACKAGE: complete
- C6 STATE: complete

## Frozen retest candidate
- Integration: `803144005c0e45352602917a2f51804ec6b18ae6`
- Matrix: `VRM-20260920-803144005c0e`
- D3D9: `803144005c0e45352602917a2f51804ec6b18ae6`
- DXVK game/host: `5e58ee35e14636dbfad3ad3744d350aa09859992`
- DXVK provider: `5bb301ab22f7b41d68a879bf84c1e3d10ae0c473`
- Multiview patcher: `0ef3253da1738b07e67358a027311c7bcedaa001`
- DX12: `ab8e00ab4a21e4ebb23fbc4046abda51e885bcb6`
- Unified workflow: `35514339728` success
- General Build workflow: `35514339665` success
- Runtime ZIP SHA256: `e48b1648ce80f7027e3cdea3bbb13192cc56c5bd99628ee886759e6d8916e065`

## Findings addressed
The previous 5f9028de retest proved the boot regression was fixed: 2D and D3D9 SAFE start normally. Gameplay then exposed a separate transport problem. SAFE configuration said `DirectGpuOnly=false`, but R9 still consulted a stale process environment value and suppressed SBS fallback, leaving the Host with no completed stereo frame. The Host then treated the full-width mono desktop as SBS and cropped its left half, producing the observed enlarged half-screen mono image.

The frozen candidate makes game-side R9 follow the parsed setting directly, and the Host only left-half-crops a source explicitly marked completed SBS. The same fixes are synchronized to the DXVK branch.

DX12 previously reached D3D9On12 but failed device creation with invalid-call presentation parameters. The DX12 branch now preserves legacy `CreateDevice` semantics and performs one bounded compatibility retry without falling back to native D3D9. Its Host also carries the corrected fallback crop policy.

## Resume cursor
Retest only three short gates:
1. A_CONTROL: enter gameplay and verify true stereo appears instead of half-width zoom.
2. E_DXVK_SAFE: repeat the same gate.
3. F_DX12_STRICT: verify device creation/menu first; only continue into gameplay if startup succeeds.

If A_CONTROL still has no completed stereo frame, analyze the new session ZIP before changing any additional renderer code.
