# PS2 reverse map tooling

The current reverse-engineering knowledge is split into:

- `docs/reverse/PS2_FFB_MAP.md` — original EE-side FFB anchors.
- `docs/reverse/PS2_FFB_STRUCTS.md` — verified 0x3C force-effect layout and EE<->IOP RPC command map.
- `docs/reverse/PS2_HUD_MAP.md` — JSPRITE/JSPRANI resource IDs, game-state map, and sprite-animation anchors.
- `reverse/ps2/semantics.json` — FFB semantic anchors.
- `reverse/ps2/hud_semantics.json` — HUD semantic anchors.

The full generated map is intentionally not committed because it contains a large disassembly derived from the retail PS2 executable.

## Build/query the executable map

```bash
python3 tools/reverse/ps2/build_ps2_map.py /path/to/SLPM_666.28 /path/to/IOPRP310.IMG /tmp/outrun2-ps2-map
python3 tools/reverse/ps2/ps2query.py --db /tmp/outrun2-ps2-map/ps2_knowledge_map.sqlite 0x1354B0
python3 tools/reverse/ps2/ps2query.py --db /tmp/outrun2-ps2-map/ps2_knowledge_map.sqlite ForceEffect
```

## Extract PS2 resource containers

The observed `SYSTEM.PS2`, `JSPRITE.PS2`, `JSPRANI.PS2`, `COMMON.PS2`, `BK.PS2`, and `DRIVER.PS2` containers share the same 16-byte entry table format. Entries may be raw or zlib-compressed.

```bash
python3 tools/reverse/ps2/extract_ps2_archive.py /path/to/JSPRANI.PS2 /tmp/jsprani
python3 tools/reverse/ps2/extract_ps2_archive.py /path/to/SYSTEM.PS2 /tmp/system
```

Validated examples:

- `DRIVER.PS2`: 4/4 entries zlib-compressed.
- `JSPRANI.PS2`: 46/46 entries zlib-compressed.
- `SYSTEM.PS2`: 11 raw entries; 8 are PS2 IOP ELF/IRX modules.
- SYSTEM entry hash `2bc3970e` is the Logitech `lgdev` wheel/FFB IOP module, version 1.12.003.
- SYSTEM entry hash `5c70405a` is the `USB_driver`/`usbd` module.

Input identity for the main executable map:

- `SLPM_666.28`: `bc5dd6d836bf34546ef9f047ad2bcb99c5ef5a713767a161d0c342af33f38c34`
- `IOPRP310.IMG`: `1cf5475f533f04d161bbb4b08179df156afeb7b400f207c88dcf1e39466679b6`

For PC VR work, query the PS2 map as comparative evidence first, then verify the corresponding PC producer/caller before implementing runtime changes.
