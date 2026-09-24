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


## Stock font resource map

The canonical executable has 10 font descriptors at VA `0x76F7B8`. Function `0x42CA60` selects one descriptor and copies its state into the active globals around `0x956BA0`.

The embedded `spr_font_xst` DDS resources have been hash-mapped to the descriptor resource handles. The machine-readable mapping is:

`localization/font/stock_font_map.json`

Notable result:

- resource handle 1 -> `CE41E71C_256x128.dds`
- descriptor index 1 -> handle 1, 16x16 cell, base code 0
- it is the only one of the 10 embedded stock font resources without a corresponding high-resolution replacement in the analyzed texture pack.

This makes handle 1 interesting for K3 research, but **not yet safe to repurpose**. Runtime `KoreanK3Trace` font-state evidence must show how/where the handle is used before any replacement or page-switching experiment.

The current K3 direction is therefore:

1. Log actual font-handle usage per target screen.
2. Preserve active stock ASCII resources.
3. Reuse the stock `0x42CFE0` text batch queue.
4. Select a Korean atlas/page only inside a controlled Korean glyph path.
5. Restore the original font state before returning to the stock ASCII path.


## K3-A state isolation contract

The stock renderer stores the active font in writable globals, so Korean rendering must be scoped and reversible.

For every Korean render segment:

1. Snapshot the complete stock font state:
   - texture pointer
   - kerning pointer
   - resource handle
   - texture width/height
   - cursor X/Y
   - cell width/height
   - scale X/Y
   - color/layer
   - base code/flags
   - letter spacing/line advance
2. Switch only the fields required by the Korean atlas page.
3. Submit Korean glyph commands through the existing `0x42CFE0` batch path.
4. Preserve cursor progression and alignment semantics.
5. Restore every snapshotted stock field before returning to the original renderer.
6. If any signature, texture, descriptor, or page prerequisite is missing, render the original English text and do not mutate the stock font state.

### Page switching

The compact corpus uses 505 syllables across two 256-cell pages. A Korean glyph index maps to:

```text
page = index / 256
cell = index % 256
row  = cell / 16
col  = cell % 16
```

The page switch must occur only when the requested Korean glyph page differs from the currently bound Korean page. ASCII remains on the stock renderer.

### K3-A proof scope

The first behavior-changing proof is deliberately limited to text ID 0:

```text
Screen Position
-> 화면 위치
```

Only the four required Hangul glyphs are accepted by the proof gate. Any unexpected Korean code point falls back to the original English string. This keeps the first runtime patch falsifiable and limits blast radius.
