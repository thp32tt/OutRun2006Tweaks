# Korean Runtime K3: Compact Hangul Glyph Path

## Why the stock renderer cannot display Hangul

Reverse engineering of the canonical `OR2006C2C.EXE` shows three independent blockers.

### 1. Text BIN loader truncates UTF-16LE
The text loader near VA `0x465DF0` copies only the low byte of each UTF-16LE code unit into the runtime string buffer.

### 2. Width/layout is byte-oriented
VA `0x42C480`:
- scans for NUL one byte at a time,
- reads current byte from `[esi-1]`,
- reads next byte from `[esi]`,
- calls VA `0x42C410` for pair/glyph spacing.

VA `0x42C610` also advances the text cursor using `AL`/next-byte `CL`.

### 3. Glyph drawing rejects non-ASCII
VA `0x42C720` takes the glyph character in `AL` and explicitly rejects:
- negative/high-bit bytes,
- values greater than `0x7F`,
- newline/tab/space.

The legacy glyph atlas is addressed as a 16x16 grid.

## Current corpus measurement

The current Korean text + graphics translation corpus needs only:

- **505 distinct precomposed Hangul syllables**
- 2 pages x 256 cells are sufficient (512 total slots)

This is much smaller than shipping all 11,172 precomposed Hangul syllables.

Machine-readable assignment:
`localization/font/hangul_glyph_manifest.json`

## K3 architecture

1. Keep ASCII on the original path whenever possible.
2. Store Korean translation source as UTF-8.
3. Decode UTF-8 before the stock one-byte glyph loop.
4. Map Hangul syllables to the stable glyph manifest.
5. Render Hangul through a dedicated two-page atlas.
6. Use per-glyph advance metrics for width/layout.
7. Preserve newlines/spaces and existing alignment semantics.
8. Fall back to original English text if Korean initialization/signature checks fail.

## Proof stages

### K3-A
Render only the four glyphs needed by `화면 위치` while leaving ASCII untouched.

### K3-B
Use the stable manifest and two 16x16 pages for all currently required 505 syllables.

### K3-C
Add punctuation/Latin fallback, wrapping, alignment and name-entry behavior.

## Canonical executable research addresses

- `0x42C410`: glyph-pair spacing/kerning helper
- `0x42C480`: string width measurement loop
- `0x42C610`: cursor advance per current/next byte
- `0x42C720`: single-glyph drawing path; 7-bit ASCII gate
- `0x42C2F0`: glyph metadata lookup
- `0x465EB0`: text ID resolver

All runtime patches must signature-check the executable before installation.

## Distribution rule

Do not ship a font file. Generate raster atlas assets during development from a suitably licensed Hangul font and distribute only the derived atlas/metrics needed by the mod.
