# VR Backend 100-Review Campaign — Set 02/10

Derived from Set 01 findings F01-F05. This set reviews the execution identity chain and does not re-score general facade structure.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S02-R01 | Slot-vs-backend payload precedence | HIGH | Selector resolves `slots/<VariantId>` before `backends/<payloadBackend>`. A pre-existing slot can replace the dinput8/host chosen by the package contract. |
| S02-R02 | Preflight-to-loaded-root continuity | HIGH | Preflight hashes files under `backends/d3d9` and `backends/dxvk`, then selector copies/removes root DLLs. There is no post-selection hash attestation proving the root files about to be loaded equal the preflight identities. |
| S02-R03 | Selector mutation atomicity | HIGH | Root mutation is sequential: archive logs, copy dinput8, copy/remove host/provider/patcher, rewrite INI, then create session metadata. Failure in the middle can leave a mixed backend state. |
| S02-R04 | Failure rollback | HIGH | Selector has no transaction/rollback snapshot for root dinput8.dll, d3d9.dll, host, patcher or INI. A failed copy/remove/INI write requires another successful selector run to recover. |
| S02-R05 | Variant identity normalization | MEDIUM | Target/session use `R69_FIXPACK`; backend metadata/build inputs use `ACTIVE_R26_HUD_R69` (and DXVK backend also writes `DXVK_SAFE_R71`). These are lineage labels, not one canonical run identity. |
| S02-R06 | Pre-launch failure diagnostics | MEDIUM | Session manifest is created only after root mutation and INI changes. A selector failure before that point has no normal session bundle and is primarily console-only evidence. |
| S02-R07 | Re-entry/idempotence | PASS_WITH_CAVEAT | Running selector again is generally convergent: stale logs are archived and required/forbidden files are recopied/removed. It is not atomic, so idempotence does not remove the interruption window. |
| S02-R08 | DXVK cached-provider integrity | HIGH_DXVK | Acquire-OutRunDXVK accepts an existing cached x86 d3d9.dll after only PE-machine validation. It does not compare the cache against PROVENANCE.txt or a pinned expected release hash before reuse. |
| S02-R09 | DXVK acquisition provenance | MEDIUM_DXVK | Downloaded archive/provider hashes are recorded after acquisition, but no expected upstream checksum/signature is verified. An explicitly supplied `DxvkD3D9` can also be any x86 PE provider, so “official stock DXVK” is not cryptographically enforced by the build script. |
| S02-R10 | Evidence after stale-slot selection | PARTIAL | Selector reads SOURCE_SHA from the actually chosen slot/backend source, so a stale slot can surface a different SHA in session metadata. That is useful forensic evidence, but there is no preventive comparison to BUILD_INPUTS before game launch. |

## Findings carried forward

- **F01 remains HIGH:** stale slot can outrank the verified backend payload.
- **F02 remains MEDIUM:** multiple VariantId namespaces exist.
- **F03 escalates to HIGH:** preflight-to-root continuity is not sealed after mutation.
- **F06 HIGH:** backend selection is not transactional and has no rollback.
- **F07 MEDIUM:** selector failures before session creation are weakly diagnosable.
- **F08 HIGH DXVK:** cached provider reuse is not hash-pinned to previously recorded provenance.
- **F09 MEDIUM DXVK:** “official stock” provenance is descriptive, not cryptographically enforced.

## Set 03 direction derived from Set 02

Set 03 will review **device/reset/resource lifetime** because partial root switching and provider replacement make lifecycle correctness the next failure boundary. Ten lenses: D3D9Ex creation/promotion, third-party provider locality, Reset ordering, state-block lifetime, stereo resource generation, device-loss paths, host startup/teardown, shared handle lifetime, frame-ring ownership, and recenter/reset interaction.

No source fix is performed by this review commit; this file is the evidence ledger for the next set.
