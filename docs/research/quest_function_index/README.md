# Quest ARM64 complete named-function inventory — 2026-10-16

**Read-only acquisition:** N100 `/home/chatgpt-runner/apk/_static_out/liboutrun_quest_core.so` provided ELF `.symtab` and `.strtab` byte chunks only; actual section decoding, de-duplication and classification occurred in the ChatGPT tool runtime. N100 ran **no new disassembler/decompiler**.

- Executable .text ELF section index 14, function symbol rows with nonzero size: **14341**.
- Unique entry-address function records: **14076** (multiple symbol rows may share an address).
- Groups by AArch64 Itanium mangled prefixes: other=5374, stdc++=4316, game/platform=3468, quest/OpenXR=34, GLES/compat=79, driving=776, enhancements=29.
- 5 TSV parts with **all 14076 unique function entrypoints**, address and size, mangled name: [symbol_index_01.tsv](symbol_index_01.tsv) · [symbol_index_02.tsv](symbol_index_02.tsv) · [symbol_index_03.tsv](symbol_index_03.tsv) · [symbol_index_04.tsv](symbol_index_04.tsv) · [symbol_index_05.tsv](symbol_index_05.tsv).
- High-interest entries count 90 (XR frame and swapchains; GLES/D3D9 draw flush and mesh cache; cockpit/HUD/shadow/flaring).
- No game code, artwork, shaders or binary assets committed.

**What this is:** complete *named function symbol inventory*, a PC re-porting worklist, **not a high-level C/C++ decompilation**. Function names and addresses alone cannot establish shader or game logic correctness. Imported functions and unlabelled/inlined code are not recovered. Need actual ARM64 instruction decoder and controlled decompiler outputs per function before claiming pseudocode recovery.

Detailed grounded functional/PCVR mapping: [QUEST_APK_FULL_VR_FUNCTION_COCKPIT_ADOPTION_20261016.md](../QUEST_APK_FULL_VR_FUNCTION_COCKPIT_ADOPTION_20261016.md). Canonical comparison: [QUEST_COCKPIT_APK_ANALYSIS_20261016.md](../QUEST_COCKPIT_APK_ANALYSIS_20261016.md).

**Porting order:** Quest `XrSessionHost` XR frame/eye lifetime → `GlD3D9Device` cache/flush and shader state → `native_race_hud_display` producer ownership → `shadow_draw_422550` stencil/texture lifetime → `native_race_effects_flare_420560` eye/world effect → cockpit occupant/glass/controller scopes → `sphere_in_stereo` culling. Record real ABI/data structures and clean-room C++ on distinct Windows R84/DX11 branches. Keep `RUNTIME_VALIDATION=UNTESTED` absent HMD evidence.
