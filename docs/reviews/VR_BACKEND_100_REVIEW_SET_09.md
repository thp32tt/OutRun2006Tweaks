# VR Backend 100-Review Campaign — Set 09/10

Derived from Set 08 runner/profile findings. Set 09 reviews failure handling, diagnostic survivability and CI behavioral coverage in ten distinct passes.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S09-R01 | Game launch exception | HIGH_DIAGNOSTICS | Environment restoration is protected by `finally`, but if `Start-Process` itself throws, control does not reach the post-game host wait/collector block. A launch failure can therefore produce no sealed analysis ZIP for the prepared session. |
| S09-R02 | Nonzero game exit | PASS | Once the game process starts and exits normally from the OS perspective, its nonzero exit code is saved, the collector runs first, and the game failure is propagated only after diagnostics are sealed. |
| S09-R03 | Host teardown failure | HIGH_DIAGNOSTICS | Runner waits for the host, force-stops it if necessary, but throws before collector invocation if the host still survives. The most interesting host-stuck failure can therefore prevent automatic log sealing. |
| S09-R04 | Collector failure vs game result | MEDIUM_DIAGNOSTICS | Collector failure is returned immediately before the saved game exit code. If both the game and collection fail, collection status wins and the original game exit code is not the final process status. |
| S09-R05 | Preflight/selector failure evidence | HIGH_DIAGNOSTICS | Preflight happens before session creation and selector can fail during sequential root mutation before a new session manifest exists. Console output and possibly VR_ONE_CLICK_PREFLIGHT.json remain, but the normal automatic ZIP contract is not guaranteed for these failures. |
| S09-R06 | Analyzer failure containment | PASS | DX11/backend analyzer and general session analyzer exceptions are converted into error text files inside the session instead of aborting collection. Optional analysis failure reduces evidence quality without losing the primary bundle. |
| S09-R07 | Package-wide checksum enforcement | MEDIUM | Build emits SHA256SUMS.txt, while runtime preflight independently hashes critical EXE/DLL/host/provider files. It does not verify the complete SHA256SUMS manifest, so altered launcher/analyzer/checklist/support files can escape package-wide integrity detection. |
| S09-R08 | One-click behavioral CI | HIGH_TEST_GAP | Test-VROneClickContract validates PowerShell/Python syntax and searches required text/paths, but does not execute selector/preflight against a temporary fake game tree. Slot precedence, partial mutation, rollback, post-selection hashes and target-lock behavior are not behavior-tested. |
| S09-R09 | Workflow stale-run control | PASS | Hosted build/OpenXR workflows cancel stale runs. PC-fast uses a branch-specific concurrency group and validates checkout SHA, so DX11/DXVK no longer cancel each other's requested self-hosted package builds. |
| S09-R10 | Self-hosted package provenance | PASS_WITH_CAVEAT | PC-fast checks out the exact trigger SHA, embeds source/build/target metadata and package hashes, and can upload the ZIP as an artifact. The persistent build cache is deliberate and the canonical CMake contract is rechecked, but final trust still requires successful build/runtime evidence for that exact SHA. |

## Findings carried forward

- **F31 HIGH diagnostics:** Start-Process launch exceptions bypass automatic collection.
- **F32 HIGH diagnostics:** an unkillable/stuck host blocks automatic collection.
- **F33 MEDIUM diagnostics:** collector failure can obscure the saved game exit code in the final process status.
- **F34 MEDIUM integrity:** complete SHA256SUMS is generated but not enforced at runtime.
- **F35 HIGH test gap:** one-click CI is structural/textual rather than an end-to-end selector/preflight behavior test.
- Existing F03/F06 are reinforced: the weakest diagnostic boundary is the same pre-session sequential mutation window.

## Set 10 direction derived from Set 09

The final set will be a **cross-system convergence review**, not a repetition of earlier file scans. Ten lenses: canonical semantic source, package-to-loaded-binary identity, reset/lifecycle reference parity, DX11 activation barrier, DXVK SAFE promotion barrier, transport parity, benchmark validity, diagnostic survivability, CI proof strength, and final one-run/merge-gate readiness. Each pass will explicitly reconcile findings from Sets 01-09 and state what evidence is still required.

No production source changes are made by this review commit.
