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

### A. Backend-neutral semantics
- Shared WVP/address anchors are live and consistent.
- Producer/HUD catalogs are not yet one source of truth.
- `hud_semantics.hpp` has ranges missing from the analyzer/shared producer map.
- Projected-world/projected-screen classes are richer than the current shared SpacePolicy.

### B. One-click payload identity
- Preflight is strong before mutation.
- A stale `slots/<VariantId>` payload can outrank the verified backend payload.
- Selector mutation is sequential and has no rollback.
- No post-selection attestation seals the exact root DLL/host/provider bytes that will load.

### C. DX11 activation
- Native draw remains correctly dormant.
- Current census is discovery evidence, not an activation proof.
- Resource behavior, input-layout and shader readiness are not yet complete exactness gates.
- Native eye-ring transport must inherit proven run/generation/fence/consumer-ACK semantics.

### D. DXVK SAFE
- Same-provider D3D9/D3D9Ex behavior is strong.
- Multiview isolation is correct.
- Provider cache/upstream provenance needs stronger enforcement.
- Runtime analyzer must require positive version evidence before claiming stock-version verification.
- Exact-build Quest 3 two-pass visual parity is still required.

### E. Performance evidence
- DX11/DXVK SAFE currently use fixed conservative 60-Hz/cadence-off arguments rather than profile-equivalent settings.
- HUD inspector/shader fingerprint/DX11 census make current sessions diagnostic, not clean benchmarks.
- R32 ACK polling/pressure-only Flush policy is accepted.

### F. Diagnostics / CI
- Normal game failures are sealed before exit-code propagation.
- Launch exceptions, stuck host teardown and pre-session selector failures can bypass automatic ZIP collection.
- One-click CI is mostly structural/textual; behavior tests are still needed.
- Current hosted Build is blocked before compilation by stale `P8_STEREO_SHARED_PREDICATE` verifier text expecting `return Game::is_vr_gameplay_presentation();`.

## Evidence-driven implementation order

1. Reconcile the stale proven-baseline verifier so CI can reach configure/compile.
2. Unify semantic catalogs and runtime producer classification.
3. Seal selector payload identity and transactional failure behavior.
4. Tighten DX11 census/activation gates and transport parity.
5. Tighten DXVK provenance/version evidence.
6. Obtain stock DXVK SAFE and DX11 observation one-run Quest 3 evidence.
7. Separate clean performance profiles from discovery instrumentation.
8. Only after graphics/lifecycle gates close, consider DXVK multiview or native DX11 draw ownership promotion.

The detailed reasoning, evidence and per-pass results remain in Set 01 through Set 10.
