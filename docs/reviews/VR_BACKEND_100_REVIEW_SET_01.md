# VR Backend 100-Review Campaign — Set 01/10

Review baseline: R70 structure-squash plus DX11 branch `vr-dx11-native-r71` HEAD `3313f4bafb949186a5c733e4406ed98659acad29`.
Method: ten deliberately different review lenses. A later set must use findings from this set to choose its directions instead of repeating the same scan.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S01-R01 | R70-to-branch source-graph delta | PASS_WITH_DEBT | Branch is ahead of R70 and not behind it. The compiled graph is narrowed through R70 production facades, but the facades still include historical implementation chains, so physical modularization debt remains. |
| S01-R02 | Single compiled-owner/facade rule | PASS | CMake marks historical owners HEADER_FILE_ONLY and requires the three production facades: ex_device_pipeline.cpp, stereo_pipeline.cpp, renderer_pipeline.cpp. |
| S01-R03 | Backend isolation | PASS | DX11 and DXVK remain isolated development branches with separate target metadata. No DX12 launch target is exposed by the one-click selector contract. |
| S01-R04 | One-click target locking | PASS | Invoke-OutRunVROneClick resolves target metadata and blocks backend/variant changes unless AllowTargetOverride is explicitly supplied. |
| S01-R05 | Package identity preflight | PARTIAL | Source SHA, branch, renderer and launch backend are cross-checked before root mutation. Variant identity is not cross-checked. |
| S01-R06 | Selector payload provenance | HIGH | Select-OutRunVRBackend chooses slots/<VariantId> before backends/<backend>. Preflight verifies backends/d3d9 payload identity, not a pre-existing slot payload. A stale slot can therefore bypass the intended payload attestation when the package is overlaid onto a directory containing old slots. |
| S01-R07 | Build metadata consistency | MEDIUM | VR_ONE_CLICK_TARGET uses VariantId=R69_FIXPACK while BUILD_INPUTS.json is generated with VariantId=ACTIVE_R26_HUD_R69. They describe related lineage but are not the same identity token and preflight does not compare them. |
| S01-R08 | Environment restoration | PASS | Outer launcher restores OUTRUN_VR_DX11_CENSUS in finally; runner restores semantic/HUD/profile/identity/Vulkan/DXVK environment values after the game process returns. |
| S01-R09 | Session sealing / post-selection identity | MEDIUM | Collector preserves target/preflight metadata and backend summaries, but preflight is created before selector mutation. There is no second attestation of the exact root dinput8.dll/host/d3d9.dll that the game will load after selection. |
| S01-R10 | CI enforcement quality | PARTIAL | One-click contract catches required files/text and Python/PowerShell syntax, but much of the enforcement is textual substring matching rather than behavioral tests. It can prove wiring text exists, not that payload precedence and mutation behavior are correct. |

## Deduplicated findings

- **F01 HIGH — stale slot payload can outrank verified backend payload.**
- **F02 MEDIUM — VariantId is split between R69_FIXPACK and ACTIVE_R26_HUD_R69.**
- **F03 MEDIUM — preflight is pre-mutation only; loaded-root payload is not attested after selector copy/remove operations.**
- **F04 LOW/STRUCTURE — R70 facades solve compiled ownership, but historical include-chain complexity remains behind the facade.**
- **F05 LOW/TESTING — CI one-click contract is mainly textual and needs behavior-level payload-selection tests.**

## Set 02 direction derived from Set 01

Set 02 will not repeat facade/branch checks. It will focus on the execution identity chain: slot precedence, root mutation atomicity, pre/post-selection hashes, crash/interruption during mutation, stale host/provider cleanup, SOURCE_SHA provenance, VariantId normalization, session manifest consistency, selector re-entry/idempotence, and failure rollback.

## Campaign rule

A finding already recorded above is not counted as a new finding in later sets unless new evidence changes severity, scope, or root cause.

### DX11-specific note

DX11 native draw ownership is still dormant; Set 01 therefore treats the D3D11 files as observation/bootstrap code and does not score visual parity as implemented native rendering.
