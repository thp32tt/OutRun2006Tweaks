# VR Backend 100-Review Campaign — Set 01/10

Review baseline: R70 structure-squash plus DXVK branch `vr-dxvk-r71-disasm` HEAD `d0c3767afe69aff8fafa211d2715be468a9b2463`.
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

## Post-review progress — F04 facade modularization

F04 remains an open structural finding, but two bounded renderer edges are now removed. The current DXVK branch extracts the R13 hardening body and R23/R27/R28 eligibility body into include-free overlays. Production R23 no longer nests `outrun_renderer_r13.cpp`, and production R29 no longer nests `outrun_renderer_r23.cpp`; compatibility wrappers remain for the safe/diagnostic facade choices.

`CONVERSION-DXVK-00061` exact result `6c46bd6aa111e84781bdebca2fa25e232ff3490b` passed Backend Conversion Gate `36577007581`, Build `36577017102`, OpenXR architecture `36577016752`, and HUD Inspector `36577016670`. The verifier explicitly rejects reintroduction of either historical renderer .cpp edge and stale OpenXR marker ownership. This is source-graph/build evidence only. Stereo and D3D9Ex chains still retain versioned include layering, so F04 is not closed and runtime validation remains UNTESTED.

`CONVERSION-DXVK-00063` phase 3 removes the top-level production D3D9Ex facade edge to `ex_device_upgrade_r15.cpp`. The R15 implementation body now lives in include-free `ex_device_upgrade_r15_overlay.inc`; the historical R15 file remains as a compatibility/build-graph wrapper. After retargeting baseline, architecture, and R32 review guards to the extracted implementation owners, exact result `d3cdeb3b8e53c7a9cb6359137e1db128e4ff1692` passed Backend Conversion Gate `36583754063`, Build `36583762624`, OpenXR architecture `36583762752`, HUD Inspector `36583762665`, and both hosted-package runs `36583762629`/`36583753778`. F04 remains open because the deeper D3D9Ex R14/R13/base layering and stereo versioned include chains are still physically nested. No Quest3/VDXR or in-game execution was performed, so runtime validation remains UNTESTED.

`CONVERSION-DXVK-00065` phase 4 removes the next production D3D9Ex wrapper edge, `ex_device_pipeline.cpp -> ex_device_upgrade_r14.cpp`. The unchanged R14 namespace implementation body now lives in include-free `ex_device_upgrade_r14_overlay.inc`; the historical R14 wrapper remains available for compatibility/build-graph paths, while production composes R13/base + R14 overlay + R15 overlay directly. Exact result `9093668dc6052db11122aa908e17597358d773a6` passed Backend Conversion Gate `36588776139`, Build `36588782824`, OpenXR architecture `36588782832` (all six jobs), HUD Inspector `36588783126`, and hosted package runs `36588782977`/`36588776360`. The R14 implementation body matches the pre-extraction body exactly after newline normalization. F04 remains open for the production R13->base edge and stereo versioned include chains; runtime validation remains UNTESTED.

`CONVERSION-DXVK-00067` phase 5 removes the final production D3D9Ex versioned-wrapper edge, `ex_device_pipeline.cpp -> ex_device_upgrade_r13.cpp`. The unchanged 244-line R13 namespace implementation body now lives in include-free `ex_device_upgrade_r13_overlay.inc`; production composes `r13_bridge.hpp` + the optimization-bounded `ex_device_upgrade.cpp` base + R13/R14/R15 overlays directly, while historical R13/R14/R15 wrappers remain compatibility/build-graph owners. Exact result `888cda6918e5e9639969cfde1a2ed344015eccdd` passed Backend Conversion Gate `36592888839`, Build `36592896343`, OpenXR architecture `36592896345` (all six jobs), HUD Inspector `36592896476`, and hosted package runs `36592896708`/`36592888566`; PC Fast `36592888565` was skipped by policy. The R13 implementation body matches the pre-extraction body exactly after newline normalization. F04 remains open only for stereo historical include-chain layering; runtime validation remains UNTESTED.

`CONVERSION-DXVK-00069` phase 6 removes the outermost default production stereo wrapper edge, `stereo_pipeline.cpp -> stereo_renderer_r34.cpp`. The unchanged R34 implementation body moved to include-free `stereo_renderer_r34_overlay.inc`; production composes R33 + render semantics + R34 overlay directly while the historical R34 wrapper remains compatibility/build-graph only. Exact result `dd020ca9e40a2f5ae5dd945bd2c7f22ff78401aa` passed Backend Conversion Gate `36596456436`, Build `36596463432`, OpenXR architecture `36596463418` (all six jobs), HUD Inspector `36596463435`, and hosted package runs `36596463391`/`36596456468`. Runtime validation remains UNTESTED.

`CONVERSION-DXVK-00071` phase 7 removes the next default production stereo wrapper edge, `R33 -> R32`. The unchanged 909-line R33 `OutRunVRStereo` body now lives in include-free `stereo_renderer_r33_overlay.inc`; production `stereo_pipeline.cpp` directly composes `stereo_renderer_r32.cpp` + R33 overlay + render semantics + R34 overlay. Exact result `b1b1391174d66802e1f6e1b33924794167d16029` passed Backend Conversion Gate `36599521950`, Build `36599530866`, OpenXR architecture `36599530943` (all six jobs), HUD Inspector `36599531115`, and hosted package runs `36599531077`/`36599521936`; PC Fast `36599522102` was skipped by policy. F04 remains open for deeper stereo historical layering beginning at R32->R31. Runtime validation remains UNTESTED.

## Set 02 direction derived from Set 01

Set 02 will not repeat facade/branch checks. It will focus on the execution identity chain: slot precedence, root mutation atomicity, pre/post-selection hashes, crash/interruption during mutation, stale host/provider cleanup, SOURCE_SHA provenance, VariantId normalization, session manifest consistency, selector re-entry/idempotence, and failure rollback.

## Campaign rule

A finding already recorded above is not counted as a new finding in later sets unless new evidence changes severity, scope, or root cause.

### DXVK-specific note

DXVK remains stock 3.1.1 SAFE/two-pass. Set 01 does not treat the historical multiview fork as an active implementation path.
