# OutRun 2006 localization reverse map

Canonical EXE SHA-256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`

## 1. Dynamic text path — CONFIRMED

The canonical text loader begins at RVA `0x00065DF0`.

It calls the language getter and indexes the path-pointer table at VA `0x0064B91C`. The six canonical paths in index order are:

| Language index | Canonical path |
|---:|---|
| 0 | `\text\english_us.bin` |
| 1 | `\text\french.bin` |
| 2 | `\text\german.bin` |
| 3 | `\text\italian.bin` |
| 4 | `\text\spanish.bin` |
| 5 | `\text\english.bin` |

The supplied file manifest additionally lists `Text/English_Korean.bin` (94,076 bytes), but that file's bytes were not included in the current asset bundle. Its internal content is therefore **not yet parsed or validated**.

Other manifest sizes:

- `English_US.bin` 94,748
- `French.bin` 106,188
- `German.bin` 106,074
- `Italian.bin` 98,722
- `Spanish.bin` 99,384

## 2. Text binary runtime contract — CONFIRMED from EXE

After loading a text blob, the game:

1. stores the blob base at global VA `0x007F8D70`;
2. treats `base + 8` as an array of relative DWORD string pointers and stores it at `0x007F8D74`;
3. walks pointer entries until a zero pointer;
4. converts every relative pointer to an absolute pointer by adding the blob base;
5. walks each string as 16-bit code units;
6. **copies only the low byte of each UTF-16LE code unit back into the same buffer** and NUL-terminates the resulting byte string.

`Sumo_GetStringFromId` is RVA `0x00065EB0` and returns `pointerTable[id]` as the runtime byte string.

### Consequence for Korean

A Korean UTF-16LE syllable cannot survive the stock conversion. Replacing `English_US.bin` with UTF-16 Hangul alone is not sufficient.

The analyzer includes a strict candidate parser for this `+8 relative-pointer table -> UTF-16LE strings` layout. It is intentionally reported as a candidate parser until actual `Text/*.bin` bytes are supplied and pass the guards.

## 3. Font renderer limit — CONFIRMED from EXE

Relevant anchors:

- glyph draw function RVA `0x0002B720` (VA `0x0042C720`)
- `sprSetPrintFont` RVA `0x0002BA60`
- `put_sprite_ex` RVA `0x0002CFE0`

The stock glyph draw path:

- rejects signed/extended byte characters;
- rejects values greater than `0x7F`;
- handles text one byte at a time;
- maps a glyph index onto a 16x16 atlas by splitting low and high nibbles;
- `sprSetPrintFont` searches up to 10 font descriptors.

The supplied `spr_font_xst.sz` contains 10 textures / 10 sprite records and `Media/Font.xpr` is a separate XPR0 font-related asset.

### Implication

There are two localization paths and they should not be conflated:

1. **Texture/graphic UI translation** — can reuse existing XST/Sprani geometry and replace translated texture payload.
2. **Dynamic text translation** — needs an encoding + font-renderer extension. Options should be chosen only after the real translated text set is measured (unique Hangul syllables, line lengths and call sites).

A one-byte extension could expose at most the remaining byte space and is not a general Korean solution. A robust full translation will likely require a multibyte/Unicode-aware decoder plus glyph-page/atlas selection or an equivalent font backend.

## 4. Five-language sprite families — CONFIRMED

Sixteen supplied XST families contain all `E/F/G/I/S` variants. For **all 16**, the system-memory prefix and parsed XST structure are byte-identical across languages; only the video/texture payload hash changes.

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

This is strong evidence that translation graphics can preserve the original sprite rectangles/animation layout and swap only language-specific texture data.

## 5. Sprani/XST bridge — CONFIRMED structure, semantic names still runtime-gated

Representative top-level Sprani animation counts:

| Sprani | Animation records | Matching XST sprites | XST textures |
|---|---:|---:|---:|
| GAME_CVT | 108 | 338 | 7 |
| RANKING_CVT | 41 | 108 | 3 |
| ROUTE_CVT | 32 | 80 | 12 |
| SELECTOR_CVT | 96 | 523 | 38 |

Canonical XST loading uses a 75-slot (`0x4B`) language/variant stride. Runtime HUD diagnostics already expose XST-set and sprite identities, so the long-term reusable chain is:

`text/UI producer -> Sprani animation -> XST set -> sprite/texture -> runtime caller -> translated asset`.

## 6. Next localization evidence required

Highest value missing input is the actual `Text` directory, especially `English_Korean.bin` and `English_US.bin`. Once available, the shared analyzer should report:

- pointer count / string count;
- exact structural compatibility between English_US and English_Korean;
- unique Korean syllable count;
- longest strings and expansion ratio;
- strings containing formatting/control tokens;
- IDs used by high-frequency HUD/menu call sites.

Do not commit the original text blobs; commit only extracted IDs, hashes and translation metadata appropriate for the localization project.
