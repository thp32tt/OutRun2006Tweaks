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

## Main unresolved groups

### A. Backend-neutral semantics
- Shared WVP/address anchors are live and consistent.
- **F13/F14 closed 2026-09-28:** the reviewed 25-range producer catalog is centralized in `disasm_render_contract.hpp`; runtime `hud_semantics.hpp` delegates to it and `analyze_outrun_exe.py` is mechanically checked against it. Exact-SHA gate `36391517935` passes on `d2d02c774ee85046acd42a453f2cf1f392927a20`.
- Projected-world/projected-screen classes are still richer than the current shared SpacePolicy (F15 remains open).

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
- **F08/F09 closed 2026-09-28:** DXVK 3.1.1 acquisition pins the expected release archive SHA-256, rejects mismatched/unpinned archives, repairs a tampered cache from verified archive bytes, and refuses an explicit package provider unless it exactly matches the verified stock provider. Pinned-acquisition regression and Win32 gate pass on `d2d02c774ee85046acd42a453f2cf1f392927a20` (gate `36391517935`).
- **F24 closed 2026-09-28:** runtime analyzer requires preflight version plus one exact observed DXVK runtime version before claiming stock-provider verification; missing, mismatched, or ambiguous version evidence fails closed (`4fc17768bb3cbb8242567f5c9ca9ce54526339dd`, gate `36390216273`).
- F12 remains open: a full game-device recreation still needs explicit provider/capability re-attestation.
- Exact-build Quest 3 two-pass visual parity is still required.

### E. Performance evidence
- DX11/DXVK SAFE currently use fixed conservative 60-Hz/cadence-off arguments rather than profile-equivalent settings.
- HUD inspector/shader fingerprint/DX11 census make current sessions diagnostic, not clean benchmarks.
- R32 ACK polling/pressure-only Flush policy is accepted.

### F. Diagnostics / CI
- Normal game failures are sealed before exit-code propagation.
- Launch exceptions, stuck host teardown and pre-session selector failures can bypass automatic ZIP collection.
- One-click CI is mostly structural/textual; behavior tests are still needed.
- The stale baseline/one-click verifier literals were reconciled (`243f5600dc2064cb795a283286e27ae399510b32`, `1090264633ee7dd30eba883721114ed7a5039620`). The exposed compile failure was traced to accidental truncation of `outrun_renderer.cpp` and `stereo_renderer_r7.inc` by earlier disassembly-contract centralization commits; full bodies were restored without reverting the intended shared-contract substitutions (`8cbf77086ce143c496e66f94d815c760df9c6c30`, `e46be02786f80aa9e554a24323714194b586d1f6`). Backend Conversion Gate run `36389674398` then passed through Win32 build, binary verification and artifact upload. Runtime/HMD validation remains UNTESTED.

## Evidence-driven implementation order

1. **DONE 2026-09-28:** Reconcile stale gate verifiers and restore the accidentally truncated renderer bodies. Backend Conversion Gate run `36389674398` passes through Win32 build/binary verification/artifact upload on `e46be02786f80aa9e554a24323714194b586d1f6`; no runtime claim is made.
2. **PARTIAL 2026-09-28:** F13/F14 producer-catalog drift/omissions are closed at `d2d02c774ee85046acd42a453f2cf1f392927a20` with exact-SHA gate `36391517935` PASS. F15 projected semantic expressiveness remains open.
3. Seal selector payload identity and transactional failure behavior.
4. Tighten DX11 census/activation gates and transport parity.
5. **PROVENANCE/VERSION DONE 2026-09-28:** F24 runtime-version attestation plus F08/F09 archive/cache/package-provider provenance are enforced and gate-tested. F12 device-recreation re-attestation is the remaining DXVK lifecycle evidence item.
6. Obtain stock DXVK SAFE and DX11 observation one-run Quest 3 evidence.
7. Separate clean performance profiles from discovery instrumentation.
8. Only after graphics/lifecycle gates close, consider DXVK multiview or native DX11 draw ownership promotion.

The detailed reasoning, evidence and per-pass results remain in Set 01 through Set 10.
