# R56 D3D9On12 current-base probe

This directory is intentionally isolated from the production DX9Ex path.

The old DX12 branch is hundreds of commits behind the current R56 renderer lineage, so this probe reconstructs only the first correctness gate on the current base rather than merging the stale renderer.

The probe now validates:

1. caller-owned hardware D3D12 device + DIRECT queue;
2. system `Direct3DCreate9On12Ex` with `Enable9On12=TRUE`;
3. the **legacy `IDirect3D9::CreateDevice` contract used by OutRun**;
4. one bounded presentation-parameter normalization retry while remaining strictly on D3D9On12;
5. `IDirect3DDevice9On12` and same-adapter identity;
6. D3D9 render-target -> underlying `ID3D12Resource` ownership transfer;
7. explicit fence-backed `ReturnUnderlyingResource`;
8. legacy `IDirect3DDevice9::Reset` after interop resources are released.

No native-D3D9 fallback is introduced here and no R56 HUD/world semantic logic is duplicated.

A successful runtime probe ends with:

```text
d3d9on12_bridge=PASS
legacy_create_device=PASS
resource_interop=PASS
legacy_reset=PASS
DX12_POC_RESULT=PASS
```

Only after these gates pass should the old D3D12 transport concepts be re-authored on the R56 lineage. The stale DX12 renderer itself is not a merge source.
