# Quest APK PC re-porting: whole-native-function audit index

Date: 2026-10-16. Source: user-owned local copy on N100 `apk/_static_out/liboutrun_quest_core.so`. Analysis-only; no proprietary binary/assets copied into Git.

## Completed evidence
- Read-only ELF `readelf -Ws` + `c++filt` catalog generated at `apk/_static_out/porting_audit/all_functions.jsonl` (N100), plus `function_summary.json`.
- 14,341 unique, defined, nonzero-size functions with symbol name/address/size and heuristic subsystem category: renderer 1,112; HUD 169; shadow 139; cockpit 32; XR 23; flare 14; other 12,852.
- Earlier raw executable symbol row count 22,621 included aliases and duplicate symbol-table entries; these figures have different definitions and must not be confused.
- Focused AArch64 direct BL edges in `apk/_static_out/quest_callgraph_selected.json` cover key XrSessionHost, GLES-D3D9 device, HUD, shadows, flare and cockpit functions; this is **not** whole-program control-flow or source-level decompilation.
- The APK ELF is ARM64 GLES/OpenXR; Windows R84 is x86 D3D9Ex + x64 OpenXR host; DX11 is a separate branch.

## Whole-program decompilation / PC re-porting work breakdown
1. **Inventory/coverage:** map every function by ELF VA, demangled name, size, section, duplicate aliases, PLT/relocations, TLS, string/xref references; separate library boilerplate from actual game functions.
2. **Control flow:** recover basic blocks, conditional and tail calls, indirect/virtual dispatch, vtables and data xrefs using an installed AArch64 decompiler. Track confidence and gaps for each function. No claim of 100% coverage until independently verified.
3. **Interface and state:** reconstruct game object structs, native PC D3D9 abstraction, scene order, mesh lifetime, shader state, alpha, depth/stencil, XR predicted-time, swapchain lifecycle and stereo culling.
4. **Cockpit:** follow TLS writers/readers for `cockpit_render_active`, vehicle, occupant, glass opacity/premultiplication, body correction and hand tracking. Recover draw order and material identity before implementing PC analogues.
5. **Visual regression:** per-eye HUD, menus, flare, car shadows, translucent windscreen, start/result overlays and recenter. Preserve R84 native producer ownership and fallback paths.
6. **Windows adaptation:** write independent C++ implementations for portable behavior only, without copying game art or third-party source; map each proposed fix to one PC code owner and an executable regression.
7. **Validation:** compile x86 game hooks and x64 XR host; exact-SHA GitHub CI, rollback/fallback, and Quest 3 HMD checks. Until executed, `RUNTIME_VALIDATION=UNTESTED`.

## Function-level evidence schema
Each subsequent reconstructed function must record `elf_va`, `name`, `size`, `section`, `caller_xrefs`, `callee_xrefs`, `global_reads_writes`, `pseudocode_status`, `confidence`, `pc_owner`, `adoption_decision`, `test_evidence`. Distinguish observed binary evidence from inferences.

## Porting guardrails
- No APK or game assets checked in.
- Existing DX9Ex, DX11 and DXVK branches retain independent owners; no speculative full renderer replacement.
- The prior material cockpit guard is `55199519fa538a9a7b03337beee01a6474a4642b`, but exact-SHA DX9Ex Active CI was cancelled; do not label Windows build verified or count a new score.
- See [focused cockpit/native evidence](QUEST_APK_FULL_VR_FUNCTION_COCKPIT_ADOPTION_20261016.md).
