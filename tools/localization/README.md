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
