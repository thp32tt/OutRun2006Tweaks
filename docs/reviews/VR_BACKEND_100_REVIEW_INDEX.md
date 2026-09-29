# VR Backend 100-Review Campaign Index

This index links the ten sequential review sets for the DX11/DXVK structure campaign.
Each set contains ten distinct review passes and derives the next set's directions from its findings.

## Review sets

1. [Set 01 — structure / one-click baseline](VR_BACKEND_100_REVIEW_SET_01.md)
2. [Set 02 — execution identity / selector mutation](VR_BACKEND_100_REVIEW_SET_02.md)
3. [Set 03 — Reset / device / resource lifetime](VR_BACKEND_100_REVIEW_SET_03.md)
4. [Set 04 — render semantics / disassembly provenance](VR_BACKEND_100_REVIEW_SET_04.md)
5. [Set 05 — DX11 translation exactness / census validity](VR_BACKEND_100_REVIEW_SET_05.md)
6. [Set 06 — DXVK SAFE / provider compatibility](VR_BACKEND_100_REVIEW_SET_06.md)
7. [Set 07 — transport / synchronization / OpenXR handoff](VR_BACKEND_100_REVIEW_SET_07.md)
8. [Set 08 — hot-path performance / instrumentation distortion](VR_BACKEND_100_REVIEW_SET_08.md)
9. [Set 09 — failure diagnostics / CI behavioral coverage](VR_BACKEND_100_REVIEW_SET_09.md)
10. [Set 10 — cross-system convergence / merge readiness](VR_BACKEND_100_REVIEW_SET_10.md)

## Campaign totals

- Sets: **10**
- Review passes: **100**
- Shared baseline: `vr-r70-structure-squash`
- Active branches: `vr-dx11-native-r71`, `vr-dxvk-r71-disasm`
- DX12: frozen/reference-only
- Production-source edits made by this campaign: **0**
- Merge gate: **OPEN**

## Current allocation policy (2026-09-29)

- DX11 Native: primary implementation/performance lane (~50% nominal effort).
- DXVK: secondary implementation/performance lane (~40% nominal effort).
- DX9Ex: protected baseline/fallback and regression maintenance only (normally <=10%); no new standalone performance optimization.
- DX12/D3D9On12: frozen/reference-only unless explicitly reopened by the user.
- Distribution target: must scale below the RTX 4070 development machine; minimum GPU remains unclaimed until measured on exact builds.
- Performance acceptance should emphasize stable frame time and lower-tier 72 Hz viability before higher-end 80/90 Hz quality targets.

## Main unresolved groups

### Structure / facade debt
- **F04 CLOSED at software/source-graph level 2026-09-30 — CONVERSION-DXVK-00093:** phases 1-17 removed the production renderer/D3D9Ex/stereo historical wrapper edges while retaining compatibility and diagnostic wrappers. Phase 18 pins the default stereo facade at canonical `stereo_renderer.cpp` (R9 over `stereo_renderer_r7.inc`), rejects versioned R13-R34 wrappers from both the production branch and canonical base, and keeps Safe/C1/C2/R26-HUD as explicit diagnostic owners. Exact result `31b510e2ea678ba834fa36285e6f213beb0aa30b` passed Backend Conversion Gate `36635766920`, Build `36635771317`, OpenXR architecture `36635771313` (6/6 jobs), HUD Inspector `36635771206`, and Hosted Package PR/push `36635771345`/`36635767082`. This closes F04 structure debt only; no Quest3/VDXR or in-game correctness/performance claim is made.

### A. Backend-neutral semantics
- Shared WVP/address anchors are live and consistent.
- **F13/F14 producer-catalog centralization closed 2026-09-28; F13 live runtime adoption remains incremental:** the reviewed 25-range catalog is centralized in `disasm_render_contract.hpp`; runtime `hud_semantics.hpp` delegates to it and `analyze_outrun_exe.py` is mechanically checked against it. Exact-SHA gate `36391517935` passes on `d2d02c774ee85046acd42a453f2cf1f392927a20`. `CONVERSION-DXVK-00095` routed the 15 already-proven `DispTimeAttack2D` callsites through `GameSemantic::ClassifyCriticalProducer`; validated tree `0a9471b603623e77ec51ac0a85d11341690b1d58` passed its hosted gates. `CONVERSION-DXVK-00097` added the eight canonical `DispRank` clip callsites without widening ranges; exact result `0490608b0f5f76d6fffbcb239e3f93379b616a19` passed Gate/Build/OpenXR/HUD/package validation. `CONVERSION-DXVK-00099` now routes the two exact `NaviPub_DispTimeAttackGoal` caller edges `0xBEA5A/0xBEA5F` through the shared classifier while preserving `BE020/BE150` helper behavior and bounded appended-node tagging. Initial source `37e630004647d75e59ad7f8a19fe5b1ed5c8d01c` passed Gate/Build/OpenXR/HUD but exposed a stale hosted-package R66 marker; repaired validation-bearing result `2d6a399d4bc0acc61a22165ba60a2b60897e4518` changed only that package verifier and passed Backend Conversion Gate `36645960402`, Build `36645966272`, OpenXR architecture `36645966281` (6/6), HUD Inspector `36645966260`, and Hosted Package push/PR `36645960384`/`36645966225`. `CONVERSION-DXVK-00101` continues the same bounded F13 adoption for exact `C2CTestSlipstream` caller `0xBD32E`: the existing right-side sprite-spacing correction is preserved while the immediate `ScreenHud` handoff now comes from `GameSemantic::ClassifyCriticalProducer(CallerRva)` with a compile-time `ScreenHud` assertion. Exact result `85936507d864ce0e5063d4e3f4b63135c31e35f3` passed Backend Conversion Gate workflow #320, Build `36646674960`, OpenXR architecture `36646675095` (6/6), HUD Inspector `36646675031`, and Hosted Package push #67 / PR #68 (`36646674956`). Remaining producer families require separate exact provenance; no Quest3/VDXR visual result is claimed.
- **F15 closed 2026-09-28:** shared `SpacePolicy` now expresses `ProjectedWorldMarker2D` and `ProjectedScreenEffect2D`, with an explicit constexpr bridge to runtime `RenderScope` and semantic-verifier coverage. Existing producer ranges were intentionally not reclassified without separate exact producer evidence. Exact-SHA gate `36397508347` PASS on `f66e49fb170e685a852960c6bddd481734b34609`.
- **F16 closed 2026-09-29:** the fixed SpriteNode exact-semantic table now fails closed on overflow instead of evicting the oldest live published owner. Existing-node updates remain allowed while full; a new unique registration increments `SpriteNodeSemanticOverflowRejected` and is rejected until capacity is available. `outrun-vr-semantic-tag-overflow-smoke` behavior-tests oldest-tag preservation, fallback for the rejected node, and later recovery. Exact result `033c2838ca6ea9f1463f4fd6776321e58d772fb8` passed Backend Conversion Gate `36562592052`, Build `36562596953`, OpenXR architecture `36562596979`, and HUD Inspector `36562596965`. This is software/CI closure only; no HMD visual result is claimed.

### B. One-click payload identity
- Preflight is strong before mutation.
- **F01/F03 structurally sealed for the one-click target path 2026-09-28:** a target-named `slots/<VariantId>` payload is rejected unless its source SHA plus game DLL/host hashes match the canonical packaged backend, and the selector attests the exact root game DLL/host/provider bytes plus forbidden-file state before session handoff. The attestation is persisted as `ROOT_PAYLOAD_ATTESTATION.json` (`e4f0ca88479d131a743b30e4ece92a90433b5784`, gate `36394761652` PASS).
- **F02 closed for DXVK one-click 2026-09-29:** `VR_ONE_CLICK_TARGET.json::VariantId` is now the single package/run identity. PC-fast writes that canonical value to both packaged backend `VARIANT_ID.txt` files and `BUILD_INPUTS.json`; preflight rejects mismatched D3D9/DXVK backend metadata or BUILD_INPUTS VariantId, and behavior CI exercises both negative cases. Initial result `634ac6593f22e8ec982ee5814c9213dc1f9c35f7` exposed a stale baseline-verifier literal; final exact result `e64f4c5acfd701e182b870171ee6e2085eeb49d4` updated the verifier without weakening the protected `R69_FIXPACK` target and passed Backend Conversion Gate `36565326204`, Build `36565333137`, OpenXR architecture `36565333146`, and HUD Inspector `36565333070`. This closes package identity normalization only; runtime/HMD behavior is unchanged and untested.
- **F05 closed for DXVK one-click 2026-09-29:** executable one-click behavior coverage now reaches the canonical VariantId failure path at all three identity layers. `CONVERSION-DXVK-00057` adds an explicit D3D9-backend `VARIANT_ID.txt` mismatch negative control alongside the existing `BUILD_INPUTS.json` and DXVK-backend mismatch controls, and the reactivation verifier requires all three exact fail-closed markers. Exact result `a97cf26d2f6d081448dbe8695730407b8642494b` passed Backend Conversion Gate `36568405570`, Build `36568411746`, OpenXR architecture `36568411761`, and HUD Inspector `36568411751`. This is regression/CI hardening only and does not add HMD/runtime evidence.
- **F06 closed 2026-09-28:** backend selection now snapshots mutable root binaries/config/state before mutation, restores the prior state after injected mid-selection failure, removes a partially created session root, and preserves the backup directory if rollback itself fails. `Test-BackendSelectorTransaction.ps1` executes this behavior in the one-click gate.
- **F07 closed for the pre-session boundary 2026-09-28:** selector failures before normal session creation persist structured diagnostics for source resolution, process guard, pending-log archival, transaction snapshot and mutation/session setup with root-sidecar fallback; one-click preflight failures also persist structured evidence and invalidate stale prior PASS reports. Exact-SHA gate `36396768691` passes on `8f8595d0c2cc6db80afd89f0108b02438dd4e10e`. Post-launch exception/stuck-host survivability remains separate S09 F31/F32 work.

### C. DX11 activation
- Native draw remains correctly dormant.
- Current census is discovery evidence, not an activation proof.
- Resource behavior, input-layout and shader readiness are not yet complete exactness gates.
- Native eye-ring transport must inherit proven run/generation/fence/consumer-ACK semantics.

### D. DXVK SAFE
- Same-provider D3D9/D3D9Ex behavior is strong.
- Multiview isolation is correct.
- **F08/F09 closed 2026-09-28:** DXVK 3.1.1 acquisition pins the expected release archive SHA-256, rejects mismatched/unpinned archives, repairs a tampered cache from verified archive bytes, and refuses an explicit package provider unless it exactly matches the verified stock provider. Pinned-acquisition regression and Win32 gate pass on `d2d02c774ee85046acd42a453f2cf1f392927a20` (gate `36391517935`).
- **F24 closed 2026-09-28:** runtime analyzer requires preflight version plus one exact observed DXVK runtime version before claiming stock-provider verification; missing, mismatched, or ambiguous version evidence fails closed (`4fc17768bb3cbb8242567f5c9ca9ce54526339dd`, gate `36390216273`).
- **F12 closed 2026-09-28:** every successful classic/Ex device creation emits a provider/capability re-attestation; the DXVK analyzer requires creation attestations to be present and all to pass before a stock-provider verdict. Analyzer regression plus Backend Conversion Gate `36392744533` pass on `718aca2486857ae51da4e7797b1c5b3b9f38cb8f`. Runtime/HMD behavior remains untested.
- **DXVK-REACTIVATE-001 software closure 2026-09-29:** the stale `READY` queue item is reconciled to `DONE`. A dedicated `verify_dxvk_reactivation_contract.py` now fail-closes drift across the `dxvk-safe` target, pinned DXVK 3.1.1 provider/provenance, selector multiview isolation, preflight/package identity, device-recreation re-attestation, analyzer lifecycle and hosted Win32 build. Exact-SHA Backend Conversion Gate `36484701256` PASS on `8f812341ff6cb7d6a5605f6203d5601b22dad832`. This is software reactivation only.
- **F25 closed 2026-09-29:** the R71 plan now describes selector activation as a bounded snapshot/rollback/root-attestation transaction rather than implying filesystem-wide atomic replacement. `verify_dxvk_reactivation_contract.py` ties the plan to the actual Start/Restore/Remove selector transaction lifecycle and `Test-BackendSelectorTransaction.ps1`. After correcting an invented `Complete-BackendSwitchTransaction` verifier marker, exact SHA `8ffbe8d1ce14b978fc201c065872edf9705d5ee1` passed Backend Conversion Gate `36502258316`, Build `36502262877`, OpenXR architecture `36502262827`, and HUD Inspector `36502262924`.
- Exact-build Quest 3 two-pass visual parity is still required.

### E. Performance evidence
- **DXVK SAFE clean-profile infrastructure closed 2026-09-28:** `dxvk-safe + PERFORMANCE` now consumes the canonical PERFORMANCE cadence policy, explicitly forces `HudInspector=false`, and disables shader fingerprinting while preserving DXVK provider/runtime-version logging. Source result `27bd1e89bdac1d547bd9994eb5ea51901d08d81a`; Build `36414470101`, OpenXR `36414470068`, and HUD Inspector `36414470078` PASS on validation checkpoint `d288dec167dc770db2ff2f2264b9781acded5929`.
- DX11 performance methodology remains open because DX11 profile equivalence and census/fingerprint benchmark isolation are not closed by this DXVK-only task.
- DXVK runtime/performance verdict remains **UNTESTED** until an exact-build Quest 3/VDXR same-scene PERFORMANCE run is available.
- **F30 guarded 2026-09-29:** production R23 DirectGPU is statically bounded to exactly one left/right host-owned hold `CopyResource` pair, with legacy private snapshot/Flush work excluded from the production direct commit wrapper. Gate `36493723474` PASS on `807c60a62a70451600f9cef50d031ff2883d5b72`. This prevents copy amplification; it does not prove the pair is or is not a runtime bottleneck.
- R32 ACK polling/pressure-only Flush policy is accepted.

### F. Diagnostics / CI
- Normal game failures are sealed before exit-code propagation.
- Pre-session selector/preflight failures persist durable structured diagnostics even when no normal session exists.
- **F31/F32 closed at automated diagnostic-survivability level 2026-09-28:** game launch/wait exceptions are retained until collection completes, and a host that survives forced teardown triggers a non-destructive emergency session snapshot instead of aborting before collection. Emergency collection preserves root logs/captures and the current session rather than rotating state. `Test-RunOutRunVRFailureDiagnostics.ps1` behavior-tests the launch-failure and emergency-snapshot contracts. Exact-SHA Backend Conversion Gate `36399100147` PASS on `b0ae61d7f0eb930d252caafe3b9b9db603d44ee9`.
- **F33 closed 2026-09-28:** diagnostic collection failure is recorded separately in `COLLECTOR_FAILURE.json`; host teardown, launch/wait and game-exit failures keep final-result precedence, and collector failure propagates only when the primary run succeeded. The behavior gate forces collection failure after launch failure and verifies the original runner failure remains authoritative. Exact-SHA Backend Conversion Gate `36400113895` PASS on `f6e98496c236244c608a5e0d0ac9fe723b87dd96`.
- **F34 closed for DXVK one-click 2026-09-29:** package `SHA256SUMS.txt` is now enforced before selector mutation by a packaged integrity helper; malformed/unsafe/duplicate entries, missing files and content hash mismatches fail closed. Behavior gate `36470762665` PASS on `1d46bf5a4ce1cba8752d481db297a44cf850a64c`. Cross-backend closure still requires the equivalent helper on the other active backend branch.
- **F35 closed for DXVK one-click 2026-09-29:** executable CI now covers temporary-package preflight identity, target slot precedence, package/provider mismatch rejection, backend/variant target-lock, selector rollback, and successful post-selection root attestation. Gate `36475255748` PASS on `45e13a807c2deea6d66987331a9ca5dc32bf19a5`. Cross-backend closure still requires equivalent adoption.
- The stale baseline/one-click verifier literals were reconciled (`243f5600dc2064cb795a283286e27ae399510b32`, `1090264633ee7dd30eba883721114ed7a5039620`). The exposed compile failure was traced to accidental truncation of `outrun_renderer.cpp` and `stereo_renderer_r7.inc` by earlier disassembly-contract centralization commits; full bodies were restored without reverting the intended shared-contract substitutions (`8cbf77086ce143c496e66f94d815c760df9c6c30`, `e46be02786f80aa9e554a24323714194b586d1f6`). Backend Conversion Gate run `36389674398` then passed through Win32 build, binary verification and artifact upload. Runtime/HMD validation remains UNTESTED.

## Evidence-driven implementation order

1. **DONE 2026-09-28:** Reconcile stale gate verifiers and restore the accidentally truncated renderer bodies. Backend Conversion Gate run `36389674398` passes through Win32 build/binary verification/artifact upload on `e46be02786f80aa9e554a24323714194b586d1f6`; no runtime claim is made.
2. **DONE 2026-09-28:** F13/F14 producer-catalog drift/omissions are closed at `d2d02c774ee85046acd42a453f2cf1f392927a20`, and F15 projected semantic expressiveness is closed at `f66e49fb170e685a852960c6bddd481734b34609` with exact-SHA gate `36397508347` PASS. No existing producer range was reclassified by the F15 type/bridge extension.
3. **DONE 2026-09-28 for one-click failure survivability:** F01/F03 payload identity, F06 transactional rollback, F07 pre-session diagnostics, and post-launch F31/F32/F33 diagnostic survivability/result precedence are sealed. F33 exact-SHA Backend Conversion Gate `36400113895` PASS on `f6e98496c236244c608a5e0d0ac9fe723b87dd96`, artifact `10960415770` (`sha256:035d26ee030930ae88d8dc5133481369ba4fd3dedb2db73a37de48de7a2b0e1a`).
4. Tighten DX11 census/activation gates and transport parity.
5. **PROVENANCE/VERSION/LIFECYCLE DONE 2026-09-28:** F24 runtime-version attestation, F08/F09 archive/cache/package-provider provenance, and F12 device-recreation provider/capability re-attestation are enforced and gate-tested. Hardware visual/runtime validation is still required.
6. Obtain stock DXVK SAFE and DX11 observation one-run Quest 3 evidence.
7. **DXVK SAFE portion DONE 2026-09-28:** clean PERFORMANCE cadence/instrumentation isolation is implemented and automatically validated. DX11 methodology remains open, and DXVK performance conclusions still require exact-build Quest 3/VDXR runtime evidence.
8. Only after graphics/lifecycle gates close, consider DXVK multiview or native DX11 draw ownership promotion.

The detailed reasoning, evidence and per-pass results remain in Set 01 through Set 10.
