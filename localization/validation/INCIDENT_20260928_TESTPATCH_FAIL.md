# 2026-09-28 Korean HD/Text combined test patch failure

Failed package: `OutRun2_Korean_HD_Text_Test_20260927.zip`

## Runtime evidence
- Exception: `0xC0000005` access violation in `VCRUNTIME140.dll!memmove`.
- Backtrace enters `DINPUT8.dll TextureReplacement::D3DXCreateTextureFromFileInMemory_Custom_dest`.
- Active configuration at crash included `UITextureReplacement=true`, `UseNewTextureAllocator=true`, and `KoreanTextOverlayTest=true`.
- The Korean text table loaded all 1,355 rows, but trace evidence still returned original English strings on multiple IDs.
- The package contained 16 HD DDS candidates at once, so no individual DDS is assigned crash responsibility without one-candidate isolation.

## Visual regression evidence
- Pause menu remained English.
- Heart Attack title/description remained English in affected screens.
- Course Select / rankings mixed English and Korean and showed corrupted ranking glyphs.
- In-race Korean HUD labels appeared low-resolution/aliased.
- OutRun Miles banner showed clipping/geometry overlap.
- Score/stage/result text showed overlap/ghosting/clipping.
- Rival remained English.
- Single Player / OutRun2SP showed inconsistent partial localization.

## Recovery gate
1. Treat the failed combined package as invalid validation evidence.
2. Re-test `TEXT_ONLY` with zero replacement DDS and texture replacement disabled.
3. Re-test each unapproved HD DDS separately as `DDS_ONLY` with `KoreanTextOverlayTest=false`.
4. A TextureReplacement crash reopens only the isolated candidate under test; do not batch-promote.
5. Allow `COMBINED` only after text runtime and every included DDS have isolated `INGAME_PASS`.
6. Allow `RELEASE` only after D final approval and zero open visual/runtime regressions.

Static QA results remain useful evidence, but no static result is treated as in-game approval.
