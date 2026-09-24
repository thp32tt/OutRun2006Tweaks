# OutRun 2 SP (Japan) PS2 HUD / Sprite knowledge map

## Highest-value files

1. `JSPRANI.PS2` — 2-D sprite animation/layout data. All 46 archive entries are zlib streams.
2. `JSPRITE.PS2` — sprite/texture atlas banks. All 53 archive entries are zlib streams.
3. `SLPM_666.28` — contains file-name tables, resource IDs, loader/relocator, sprite resolver, and a code section literally named `Sprani_Update`.
4. `COMMON.PS2` — not the main HUD store, but contains `\common\lens_flare_offset.bin`, relevant to the VR lens-flare issue.
5. `SYSTEM.PS2` — device/runtime modules; contains `LGDEV.IRX` and `USBD.IRX` for FFB, not HUD rendering.

`BK.PS2`, `CHR.PS2`, `GHOST.PS2`, `GHOSTS.PS2`, and `IOPRP310.IMG` are low priority for HUD classification.

## Exact archive-name hashing

The retail EE executable function at `0x001749F0` was recovered. Archive child names use the relative suffix with a leading backslash:

```text
h = 0
for c in reverse("\\filename.ext"):
    c = ASCII_UPPER(c)
    h = (h * 131 + c) & 0xffffffff
```

This maps **50/50 named JSPRITE files** and **43/43 named JSPRANI files** to exact archive entries. Each pack contains three additional hashed entries that are not named by the retail executable table.

## Stable resource-ID pairing

The JSPRANI name pointer table is at `0x0032AA58`. The loader at `0x00116C50` subtracts `0x20`, therefore animation resources are IDs `0x20..0x4A`.

The JSPRITE pointer table at `0x0035C96C` uses the same IDs for the corresponding atlas bank. During relocation, `0x00117018` writes the resource ID into the high 16 bits of every frame sprite ID. `0x00117330` later resolves that 32-bit ID as:

- high16 = resource bank
- low16 = sprite index

All 43 paired animation banks validate against their XST bank: the maximum low-16 sprite index is exactly `XST sprite_count - 1`.

This gives VR HUD classification a semantic identity stronger than D3D render-state heuristics.

## Resource ID map

| ID | JSPRANI semantic |
| --- | --- |
| `0x20` | LOGO |
| `0x21` | LOGO_E |
| `0x22` | TITLE_CVT |
| `0x23..0x2A` | car meter banks |
| `0x2B` | GAME_CVT |
| `0x2C` | ETC_CVT |
| `0x2D` | FIGHT |
| `0x2E` | SELECTOR_CVT |
| `0x2F` | LOADING_CVT |
| `0x30..0x31` | remaining car meter banks |
| `0x32` | ADV_CVT |
| `0x33` | COMMON_CVT |
| `0x34` | ROUTE_CVT |
| `0x35` | ENDING_CVT |
| `0x36..0x3B` | name-entry/name banks |
| `0x3C` | EFCT_FLOR |
| `0x3D` | RANKING_CVT |
| `0x3E` | FLAG_RANK |
| `0x3F` | CLAR_RANK |
| `0x40` | JENN_RANK |
| `0x41` | HOLL_RANK |
| `0x42` | CONGRATS_CVT |
| `0x43` | STAFFROLL_CVT |
| `0x44` | SUMO_FE_CVT |
| `0x45` | DEMOSPLASH_CVT |
| `0x46` | FRUITY_CVT |
| `0x47` | SPLASH_CVT |
| `0x48` | SUMO_LOADING |
| `0x49` | SUMO_VSLOAD |
| `0x4A` | TAEXTRA_CVT |

JSPRITE also has standalone banks: `0x00 spr_font_xst`, `0x03 spr_etc_xst`, `0x12 spr_select_xst`, `0x13 spr_warning_xst`, `0x14 spr_name_entry_xst`, `0x15 spr_ranking_xst`, `0x17 spr_sumo_fe_xst`.

## Key HUD banks

| ID | animation bank | roots | tracks | nodes | X range | Y range | XST sprites |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `0x23` | METER_246GTS | 1 | 2 | 2 | 14..126 | 126..126 | 2 |
| `0x27` | METER_F40 | 1 | 2 | 2 | 14..126 | 126..126 | 2 |
| `0x2B` | GAME_CVT | 107 | 626 | 1003 | 14..650 | 6..490 | 124 |
| `0x2C` | ETC_CVT | 268 | 923 | 2221 | 2..640 | 1..510 | 145 |
| `0x34` | ROUTE_CVT | 32 | 151 | 854 | 10..512 | 4..510 | 22 |
| `0x3D` | RANKING_CVT | 41 | 176 | 493 | 14..685 | 3..322 | 28 |
| `0x3E` | FLAG_RANK | 7 | 31 | 83 | 30..512 | 30..398 | 13 |
| `0x3F` | CLAR_RANK | 7 | 38 | 90 | 30..512 | 30..358 | 13 |
| `0x40` | JENN_RANK | 7 | 38 | 90 | 30..512 | 30..398 | 12 |
| `0x41` | HOLL_RANK | 7 | 38 | 90 | 30..512 | 30..398 | 12 |

`GAME_CVT` uses 124 low-16 sprite indices (`0x0000..0x007B`), therefore the PS2 full sprite IDs for that bank are `0x002B0000..0x002B007B`.

Coordinates cluster around the original 640x480 UI space and include off-edge animation values such as X around 685 or Y above 480. Do not clamp them when reconstructing transitions.

## JSPRANI binary structure recovered

Each pack entry is zlib-compressed. The decompressed blob starts with a 32-bit payload length; logical offsets are relative to the bytes immediately after that length field.

The logical payload begins with a zero-terminated root-offset array. Each root contains two collections:

- root +0x00 = collection-A count
- root +0x04 = collection-A pointer
- root +0x08 = collection-B/track count
- root +0x0C = collection-B/track pointer
- collection A uses 0x24-byte records; +0x1C = child-node count, +0x20 = pointer to 0x4C-byte nodes
- collection B uses 0x18-byte track records; +0x00/+0x04 are X/Y integers, +0x0C is frame count, +0x10 is pointer to 0x14-byte frame records
- a frame record's first word contains the low-16 sprite index before relocation

The exact semantics of every field in the 0x18/0x24/0x4C records remain partially unresolved. Do not assign names beyond verified fields.

## Code anchors

- `0x00116C50` — JSPRANI async loader
- `0x00116F90` — loaded animation relocation path
- `0x00117018` — patches `resourceId << 16` into frame sprite IDs
- `0x00117330` — resolves full sprite ID through bank + low16 index
- `0x001749F0` — pack filename hash
- `0x001768F0` — animation-root relocator
- `0x0030DBA0` — dedicated `Sprani_Update` ELF code section
- `0x0030E480` — Sprani update wrapper/caller
- `0x0030E5A8` — group/node iterator; observed 0x4C node stride

## Implication for the PC VR HUD work

The PC executable contains the same `ani_SPRANI_*` and `spr_sprani_*` resource families. This is strong cross-version semantic evidence, but **the numeric PC resource IDs must be independently verified** before being used in production.

Recommended production path:

1. Capture or propagate the PC 32-bit sprite ID at `sprani_play_ae_auth_alpha` / sprite queue production.
2. Recover the PC resource table/order and prove its high-16 bank mapping.
3. Add verified bank provenance to the existing caller-based `hud_semantics.hpp` classification.
4. Keep the known PC world-rival-marker producer (`sub_4BAD20`) explicitly `WORLD_BILLBOARD`. A rank-named texture bank is not sufficient evidence that every draw is screen-space HUD.
5. Use JSPRANI X/Y data as a layout oracle for original 640x480 positioning and transitions, not as a direct PC memory-layout assumption.

## Other supplied packs

- `COMMON.PS2`: exact hash match for `\common\lens_flare_offset.bin`; useful for the VR lens-flare stereo issue.
- `BK.PS2`: stage/background/collision assets; low HUD value.
- `CHR.PS2`: character model/data; low HUD value.
- `GHOST.PS2` / `GHOSTS.PS2`: replay/ghost data; low HUD value.
- `IOPRP310.IMG`: system IOP runtime; not a HUD source.
