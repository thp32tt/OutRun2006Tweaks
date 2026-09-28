# 2026-09-28 — Three-way crash diagnostic test packages

## Purpose
Rebuild the failed combined localization test as three subsystem diagnostics:
1. TEXT_ONLY
2. GRAPHICS_ONLY
3. COMBINED

This is crash diagnosis / mitigation evidence only. It is not release approval and does not replace isolated per-DDS in-game validation.

## Source state
- Repository: `thp32tt/OutRun2006Tweaks`
- Branch: `korean-localization-clean`
- HD payload packaging HEAD: `950e339122cb3f86f089cb98fe746d2600888661`
- Runtime source commit: `1326f96840bfec7accf2e4016c238b8980b82853`
- Runtime build run: `36200209935`
- Runtime artifact id: `10891921525`
- Compare from runtime commit through packaging HEAD found no changes to `src/**`, `OutRun2006Tweaks.ini`, `OutRun2006Tweaks.lods.ini`, or `localization/text/runtime_ko.tsv`.
- Current HD payload workflow run: `36440212867` — PASS
- Current HD payload artifact id: `10977780985`
- Current HD payload artifact digest: `sha256:da0e17c79d0ea3ad0af9f0eaaf2f8eb7d09e6b96471640135d2dec501aa884ef`
- HD candidate DDS count: 16.
- Korean runtime text rows: 1,355.

## Crash mitigation / isolation change
The failed package crash entered `TextureReplacement::D3DXCreateTextureFromFileInMemory_Custom_dest` while `UseNewTextureAllocator=true`.

Current `src/hooks_textures.cpp` selects:
- `D3DXCreateTextureFromFileInMemory_Custom_dest` when `UseNewTextureAllocator=true`
- `D3DXCreateTextureFromFileInMemory_Orig_dest` when `UseNewTextureAllocator=false`

All three diagnostics therefore force:
- `UseNewTextureAllocator=false`
- `EnableTextureCache=false`
- `SceneTextureReplacement=false`

TEXT_ONLY additionally forces `UITextureReplacement=false`.
GRAPHICS_ONLY and COMBINED use `UITextureReplacement=true`.

Each package includes a `RUN_TEST_*.bat` so command-line overrides enforce the diagnostic settings even if an existing `OutRun2006Tweaks.user.ini` contains conflicting values.

This bypasses the allocator path present in the recorded crash. It does not by itself prove the allocator was the sole root cause.

## Packages

### TEXT_ONLY
- File: `OutRun2_Korean_TEXT_ONLY_CrashFixedDiag_20260928.zip`
- SHA-256: `dbeb09bde1c2ab5ce0d0cdbdc96efb1f0a4acef647a2fcc96a1a33c92d766b46`
- DDS: 0
- runtime_ko.tsv: 1,355 rows
- `UITextureReplacement=false`
- `KoreanTextOverlayTest=true`
- `KoreanTrace=true`

### GRAPHICS_ONLY
- File: `OutRun2_Korean_GRAPHICS_ONLY_CrashFixedDiag_20260928.zip`
- SHA-256: `116209f429c851f86f49d7b09f21db5a5d84cd45bc9cd658f467ea324076e3e0`
- DDS: 16 current HD candidates
- runtime_ko.tsv: absent
- `UITextureReplacement=true`
- `KoreanTextOverlayTest=false`
- `KoreanTrace=false`

### COMBINED
- File: `OutRun2_Korean_COMBINED_CrashFixedDiag_20260928.zip`
- SHA-256: `61246d8b641efdc5cf7b371297a0f8c80b82747bb10c40b7d7f5b99c49c29817`
- DDS: 16 current HD candidates
- runtime_ko.tsv: 1,355 rows
- `UITextureReplacement=true`
- `KoreanTextOverlayTest=true`
- `KoreanTrace=true`

## Static package QA
- GitHub current-HD payload creation: PASS.
- 16/16 DDS payload hash verification against workflow-generated `DDS_SHA256SUMS.txt`: PASS.
- ZIP CRC/integrity test: PASS for all three.
- Expected DDS counts: PASS (0 / 16 / 16).
- Expected text-table presence: PASS.
- Expected INI diagnostic flags: PASS.
- Command-line BAT diagnostic overrides: PASS.
- `OR2006C2C.exe` exclusion: PASS.
- VR/FFB/DX9Ex/DX11/DXVK changes: none.

## Runtime status
- AUTOMATION_VALIDATION=PASS
- RUNTIME_VALIDATION=UNTESTED

GRAPHICS_ONLY and COMBINED deliberately contain the complete current 16-DDS diagnostic set. They do not count as isolated DDS_ONLY approval evidence. Current per-DDS promotion rules and in-game gates remain unchanged.
