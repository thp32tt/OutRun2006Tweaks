# REA / Ghidra independent verification of Quest cockpit source recovery — 2026-10-25

## Scope and identity
- This is authorized offline analysis of the user's Quest OutRun APK. All extracted binary slices were made locally on N100; no binary uploads to GitHub.
- Original native ELF SHA-256: `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`.
- REA CLI `6.5.0`; REA Ghidra analysis engine `12.1.4`; Node `22.23.3`, Ubuntu 24.04.
- REA `doctor --json` confirms the native Ghidra provider (Ghidra 12.1.4, full JDK 25.0.4.1). Overall doctor=false due to optional Hopper/IDA/JADX and agent-skill registration gaps, not native Ghidra missing.
- Full ELF REA `analyze` was attempted but timed out after 260s, producing **no usable original-ELF-wide evidence**. Subsequent bounded extraction under the original `.text` ELF `file_offset = virtual_address - 0x1000` produced actual native AArch64 byte-identical slices.
- REA `function --target-format raw-binary --architecture arm64 --entry-point 0x0 --provider ghidra` executed successfully for THREE slices; each response is a local machine-readable REA Evidence JSON (not uploaded). These slices deliberately omit external code, so unresolved callees and pseudocode truncations are expected and must not be mistaken for native code damage.

## Independently verified REA function evidence

| Original ELF function | Real ELF start | Original slice bytes | REA observed function body | Incoming/outgoing call confidence | REA evidence id |
|---|---|---:|---|---|---|
| `race_camera_view_switch` | `0x119240C` | 536 | one range `[0x0..0x217]`, 536 bytes | 41 outgoing refs, 10 unresolved calls | `ev_3b72ec32f824d53bb9fcda4eca7280e739ae2225322e426d885af05e1736e080` |
| `Flush::draw_404700` | `0x10B9894` | 2,664 | ranges `[0x0..0xA3F]` and `[0xA50..0xA67]`, 2,648 bytes | 224 outgoing refs, 40 unresolved calls | `ev_1c9f2816e5235af64a8dee1623c2b60c04e645964f23772f9fac8b211e9a760d` |
| `PcSceneRenderer::render_frame` | `0x10CBE9C` | 2,816 | ranges `[0x0..0xA2F]` and `[0xA74..0xAFF]`, 2,748 bytes | 199 outgoing refs, 27 unresolved calls | `ev_c15ec946f24f83736d9e9bb830054fef11d1019ac59fe423de85aca3267446da` |

Raw slice SHA-256 respectively:
- camera: `5de61214babea4aecac586b5f28ece5d44b0cac08a9f46d5113555df36fd6c84`;
- glass: `b3c1351b93493df95250fc27d6308b9a64926441f48ea5c77e69daf4eecc616c`;
- frame: `fe0bde5f22089fcac9a52bcb2c9f4a761a1f08578a09d3ed183e3610c9d5334e`.

All three REA runs: exit code 0, Ghidra version 12.1.4, recorded JSON with the evidence identifiers above. Pseudocode character counts: 3,262 / 17,173 / 16,341. **Each reports Ghidra's `Control flow encountered bad instruction data` warning**, and callee coverage is `partial`; thus pseudo-C is a diagnostic artifact, not verified complete original source. The partial function-body regions on two samples describe REA/Ghidra's best discovered raw-slice CFG, **not proof that the omitted bytes are unused at runtime**.

## Earlier machine-code findings retained as stronger evidence
- Quest frame mode-1 gate `cameraControls[+0x34A] == 1` plus renderer and frame flags.
- Cockpit body correction is a separate 16-float TLS matrix; independent synthetic FP interpreter test for both identity inputs gives `diag(-1,-1,-1,+1)`; full physical mapping not proved.
- Game guest matrix `+0xF0..+0x12C` temporarily changed to identity, then normal **and exception** cleanup restore 16/16 slots; both clear scoped TLS.
- Glass specialization gates on `DrawEntry.flags&2`, `DrawEntry.pass==1`, effective blend 19/20 and diffuse alpha near 0.55/0.425; scopes opacity `0.25` during draw, resets to 1.0 afterwards. Public PC PMT structure confirms the +0x20 and +0x34 field names. The writer/semantic of bit1 is not proved.

## Reproduction on the user's N100
- `apk/_analysis_focus/quest_rea_environment_check_20261025.py`: REA/Ghidra/JDK doctor and provider availability.
- `apk/_analysis_focus/quest_rea_prepare_slices_20261025.py`: reproducible binary exact-slice extraction.
- `apk/_analysis_focus/quest_rea_function_slices_20261025.py`: actual REA analysis runs; raw JSON Evidence under `apk/_analysis_focus/rea_slices/*.rea.result.json`.
- `apk/_analysis_focus/rea_results_metrics_20261025.py`: deterministic machine-readable evidence accounting.
- Existing `quest20261025_matrix_lifecycle_verified.json`: slot and identity checks against real ELF disassembly.

## Unresolved
The full 22MB ELF REA import needs a longer/optimized session; targeted raw REA does not resolve external PLT or global xrefs. Native producers of glass queue bit1 and exact player windshield faces remain unknown. Driver position/HMD frame algebra and stereo runtime behavior are untested.

No game source changes. No PC build/CI. `REVIEW_ONLY`, `CODE_CHANGE=NO`, `RUNTIME_VALIDATION=UNTESTED`. The source-recovery target is **behaviorally equivalent code**, not byte-for-byte restoration of the original authored C++.
