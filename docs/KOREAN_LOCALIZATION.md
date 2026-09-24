# Korean Localization Prototype

This branch isolates Korean-localization research from the VR integration branch.

## Baseline

- Branch: `korean-localization-prototype`
- Base: `vr-d3d9ex-focus`
- Runtime changes are disabled until a minimal text-rendering proof is validated.
- Game assets are not committed to this repository.

## Asset analysis

The first localization sample archive contained 324 files, including 243 DDS textures.

Important groups:

- `Text/English_US.bin`
- `Text/English_Korean.bin`
- `config_text/*.TXT`
- `Sprite/spr_font_xst.sz`
- `textures/load/spr_font_xst/`
- language-specific Sprite/Sprani resources such as `*_Exst`, `*_Fxst`, `*_Gxst`, `*_Ixst`, and `*_Sxst`

### English_Korean.bin is not a Korean translation

The Korean-region file still contains English UI strings. In the analyzed copy, 1,340 of 1,356 entries matched `English_US.bin`; the remaining differences were mainly SCEK/DNAS regional text. No Hangul glyph text was present.

## txet BIN format

The analyzed text files use this layout:

```text
0x00  char[4]  "txet"
0x04  uint32   total file size
0x08  uint32[] entry offsets
...            UTF-16LE record payload
```

The first payload offset determines the offset-table size. For `English_Korean.bin`:

- total entries: 1,356
- simple single-string records: 1,351
- multi/special records: 4
- null-pointer entries: 1

Some records contain multiple NUL-separated UTF-16LE strings. A naive NUL-terminated exporter loses bytes, so the localization tool preserves each record's raw byte slice.

## Verified data test

`tools/localization/txet_tool.py` was tested against the analyzed `English_Korean.bin`.

Original:

```text
size=94076
entries=1356
sha256=d95b2f04d801c4b8c93017c487f122db49441310c1015b068875d8b91ca6d73d
```

Extract -> rebuild result:

```text
ROUNDTRIP=BYTE_IDENTICAL
sha256=d95b2f04d801c4b8c93017c487f122db49441310c1015b068875d8b91ca6d73d
```

A second test replaced entry 0, `Screen Position`, with `화면 위치`. The resulting BIN parsed correctly and retained all 1,356 entries.

This only proves the resource editor. It does not yet prove in-game Hangul rendering.

## Runtime blocker

Reverse-engineering of the canonical executable shows that the current text path does not preserve UTF-16 characters. The loader copies only the low byte of each UTF-16LE code unit.

Observed sequence near the text loader:

```asm
mov dl, BYTE PTR [eax]
mov BYTE PTR [ecx], dl
add eax, 2
```

For Hangul, that destroys the Unicode code point before rendering.

Candidate locations identified during analysis:

- `0x465DF0` - text BIN loading path
- `0x465EB0` - string ID resolver
- `0x48EB60` - line/layout handling
- `0x42C480` - text width handling
- `0x42C300` area - glyph lookup

These addresses are research notes for the analyzed executable and must be signature/version-validated before any production hook is enabled.

## Font blocker

The examined `spr_font_xst` atlases contain Latin letters, digits, and symbols but no Hangul glyph set. Korean support therefore needs both:

1. a Unicode-safe string path, and
2. a Hangul-capable glyph path/font atlas.

## Implementation stages

### K0 - Resource tooling
Status: PASS

- lossless txet extract/rebuild
- safe single-record patching
- refuse multi/special-record replacement by default

### K1 - Runtime trace hook
Status: NEXT

Add logging-only hooks around the text resolver and renderer. No text replacement. Confirm which function receives string ID 0 and how the renderer consumes the returned buffer.

### K2 - Minimal Korean string override

Override one known string only:

```text
ID 0
Screen Position
-> 화면 위치
```

Keep localization disabled by default and require an explicit experimental option.

### K3 - Minimal Hangul renderer

Prototype only the glyphs needed for `화면 위치`. This avoids building a full Korean font before the pipeline is proven.

### K4 - Font system

After K3 succeeds, choose between:

- full precomposed Hangul atlas,
- dynamically generated glyph atlas, or
- Hangul Jamo composition.

The choice will be made from measured renderer limits, not assumed in advance.

### K5 - Texture localization

Replace English text embedded in DDS/Sprite resources. Keep image localization separate from dynamic text localization.

### K6 - Translation database

Export all 1,356 IDs to a reviewable translation table and regenerate the final BIN/resources reproducibly.

## Regression rules

- Do not merge localization experiments into `vr-d3d9ex-focus` until K3 is proven.
- Localization must default to OFF.
- Hooks must validate the expected executable/signature before patching.
- A failure in Korean initialization must fall back to the unmodified game text path.
- VR rendering, FFB, input, and existing localization-independent behavior must remain unchanged.
