# OutRun 2006 localization reverse map

Canonical EXE SHA-256: \`68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3\`  
Verified localization branch: \`korean-localization-prototype@9394b832b93b83303fe029e45182c7b3a64d8d54\`  
Localization tracking issue: #25

## 1. txet text format — VERIFIED on English_Korean.bin

The localization project already verified the actual binary format and a byte-identical round trip:

\`\`\`text
0x00  char[4]  "txet"
0x04  uint32   total file size
0x08  uint32[] record offsets
...            UTF-16LE record payloads
\`\`\`

For the analyzed \`English_Korean.bin\`:

- size: 94,076 bytes
- SHA-256: \`d95b2f04d801c4b8c93017c487f122db49441310c1015b068875d8b91ca6d73d\`
- records: 1,356
- simple single-string records: 1,351
- multi/special records: 4
- null pointer entries: 1
- extract -> rebuild: **BYTE_IDENTICAL**

Some records contain multiple NUL-separated UTF-16LE strings, so a naive one-string-per-ID exporter is lossy. The dedicated localization tool preserves each raw record slice.

The analyzed regional \`English_Korean.bin\` is **not itself a Korean translation**: 1,340 of 1,356 records matched \`English_US.bin\`; the remaining differences were mainly SCEK/DNAS regional text. No Hangul text was present before the prototype patch.

A resource-only test replaced ID 0 \`Screen Position\` with \`화면 위치\`, rebuilt the file and retained all 1,356 records. This proves the resource editor, not in-game Hangul rendering.

The shared analyzer now understands the same txet layout so VR/FFB/localization research can consume the same ID map without duplicating format guesses.

## 2. Canonical dynamic-text runtime path — CONFIRMED

The canonical text loader starts at RVA \`0x00065DF0\` and indexes the path table at VA \`0x0064B91C\`:

| Language index | Canonical path |
|---:|---|
| 0 | \`\\text\\english_us.bin\` |
| 1 | \`\\text\\french.bin\` |
| 2 | \`\\text\\german.bin\` |
| 3 | \`\\text\\italian.bin\` |
| 4 | \`\\text\\spanish.bin\` |
| 5 | \`\\text\\english.bin\` |

The loader stores the blob at \`0x007F8D70\`, stores the pointer table (\`base + 8\`) at \`0x007F8D74\`, relocates each record offset by adding the blob base, then converts each 16-bit string to a byte string **by copying only the low byte of each UTF-16LE code unit**.

\`Sumo_GetStringFromId\` at RVA \`0x00065EB0\` returns the resulting runtime pointer.

### Consequence

The txet file can losslessly contain Hangul, but stock runtime loading destroys the Unicode code point before rendering. A translated BIN alone is therefore insufficient.

## 3. Font/glyph path — CONFIRMED

Relevant anchors:

- glyph draw RVA \`0x0002B720\`
- \`sprSetPrintFont\` RVA \`0x0002BA60\`
- \`put_sprite_ex\` RVA \`0x0002CFE0\`
- localization branch also tracks width/layout around \`0x42C480\`, glyph lookup around \`0x42C300\`, and line/layout handling around \`0x48EB60\` as research anchors requiring signature validation before production use

The stock glyph path:

- processes one byte per glyph;
- rejects signed/extended byte values;
- rejects values above \`0x7F\`;
- splits low/high nibbles into a 16x16 atlas position;
- searches up to 10 font descriptors.

The supplied \`spr_font_xst.sz\` contains 10 textures / 10 sprite entries. The examined stock font atlases contain Latin letters, digits and symbols but no Hangul glyph set.

Therefore Korean needs both:

1. a Unicode-safe runtime string path; and
2. a Hangul-capable glyph path/atlas.

## 4. Five-language texture UI families — CONFIRMED

Sixteen supplied XST families contain complete \`E/F/G/I/S\` variants. In every family, the parsed XST structure and system-memory prefix are identical across languages; only video/texture payload differs.

| Family | Textures | Sprites |
|---|---:|---:|
| CLAR_RANK | 5 | 18 |
| CONGRATS_CVT | 2 | 9 |
| ETC_CVT | 11 | 698 |
| FIGHT | 1 | 34 |
| FLAG_RANK | 4 | 17 |
| FRUITY_CVT | 2 | 195 |
| GAME_CVT | 7 | 338 |
| HOLL_RANK | 2 | 18 |
| JENN_RANK | 2 | 18 |
| LOADING_CVT | 5 | 18 |
| RANKING_CVT | 3 | 108 |
| ROUTE_CVT | 12 | 80 |
| SELECTOR_CVT | 38 | 523 |
| SUMO_FE_CVT | 129 | 1,564 |
| SUMO_LOADING | 4 | 5 |
| SUMO_VSLOAD | 4 | 278 |

This supports a clean separation: embedded UI graphics can be translated by texture payload while reusing original animation/layout structures.

Representative Sprani/XST counts:

| Sprani | Anim records | XST sprites | Textures |
|---|---:|---:|---:|
| GAME_CVT | 108 | 338 | 7 |
| RANKING_CVT | 41 | 108 | 3 |
| ROUTE_CVT | 32 | 80 | 12 |
| SELECTOR_CVT | 96 | 523 | 38 |

Canonical XST selection uses a 75-slot (\`0x4B\`) language/variant stride, providing a bridge from runtime \`xstsetIndex\` to language-specific resource package.

## 5. Shared localization pipeline

The shared knowledge base and the dedicated localization branch have distinct roles:

- \`tools/localization/txet_tool.py\` — authoritative lossless txet editor used by the Korean project.
- \`tools/reverse/analyze_game_data.py\` — cross-project read-only scanner; reports txet/XST/Sprani/Scripts/COLI structure and hashes.
- \`src/hooks_localization.cpp\` — localization-only, signature-gated logging hook; must remain isolated until minimal Hangul rendering is proven.

Do not move experimental localization runtime hooks into \`vr-d3d9ex-focus\` before K3/minimal Hangul render proof. Shared metadata/tools are safe to reuse earlier because they change no runtime behavior.
