# OutRun 2006 localization tools

## Inspect

```bash
python tools/localization/txet_tool.py inspect "Text/English_Korean.bin"
```

## Lossless extraction and rebuild

```bash
python tools/localization/txet_tool.py extract "Text/English_Korean.bin" english_korean.json
python tools/localization/txet_tool.py rebuild english_korean.json rebuilt.bin
cmp "Text/English_Korean.bin" rebuilt.bin
```

A successful unchanged round trip must be byte-identical.

## Patch one simple string

```bash
python tools/localization/txet_tool.py patch \
  "Text/English_Korean.bin" \
  English_Korean.test.bin \
  --index 0 \
  --text "화면 위치"
```

The tool intentionally refuses records that contain multiple/special payload segments.

## Important

Creating a BIN with Korean text does not make the game display Hangul. The stock executable reduces UTF-16LE characters to one byte before the existing glyph renderer, and the stock font atlas does not contain Hangul. Runtime/font work is tracked in `docs/KOREAN_LOCALIZATION.md`.

## Runtime trace analysis

After a K1/K2/K3 test, analyze the game log with:

```bash
python tools/localization/analyze_korean_trace.py OutRun2006Tweaks.log \
  --json localization_work/trace.json \
  --markdown localization_work/trace.md
```

The analyzer extracts:
- observed text IDs and K2 proof override,
- context-sensitive IDs 96/97/279/280,
- K3 width strings and high-bit detection,
- observed glyph bytes,
- active font handle/texture/cell/scale/spacing state.

This is the preferred input to K3-A implementation decisions.
