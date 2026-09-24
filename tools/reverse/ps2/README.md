# PS2 reverse map tooling

The canonical analysis is split across `docs/reverse/PS2_FFB_MAP.md`, `docs/reverse/PS2_HUD_MAP.md`, `docs/reverse/PS2_SYSTEM_MAP.md`, `reverse/ps2/semantics.json`, and `reverse/ps2/hud_semantics.json`.

The full generated map is intentionally not committed because it contains a large disassembly derived from the retail PS2 executable. A local generated package contains the SQLite database, JSONL indexes, full EE disassembly and IOPRP module disassemblies.

Regenerate the compact core map from the original binaries:

```bash
python3 tools/reverse/ps2/build_ps2_map.py /path/to/SLPM_666.28 /path/to/IOPRP310.IMG /tmp/outrun2-ps2-map
```

Use `ps2query.py` against a generated `ps2_knowledge_map.sqlite`:

```bash
python3 tools/reverse/ps2/ps2query.py --db /path/to/ps2_knowledge_map.sqlite 0x1354B0
python3 tools/reverse/ps2/ps2query.py --db /path/to/ps2_knowledge_map.sqlite ForceEffect
```

Input identity for the current map:

- `SLPM_666.28`: `bc5dd6d836bf34546ef9f047ad2bcb99c5ef5a713767a161d0c342af33f38c34`
- `IOPRP310.IMG`: `1cf5475f533f04d161bbb4b08179df156afeb7b400f207c88dcf1e39466679b6`

`LGDEV.IRX` and `USBD.IRX` have now been recovered from `SYSTEM.PS2`. The next FFB task is the IOP RPC/effect payload map. For HUD work, use `extract_ps2_pack.py` to unpack JSPRANI/JSPRITE and `analyze_sprani.py` to inspect verified animation/layout fields.


Extract a resource pack:

```bash
python3 tools/reverse/ps2/extract_ps2_pack.py JSPRANI.PS2 --out /tmp/jsprani
python3 tools/reverse/ps2/extract_ps2_pack.py JSPRITE.PS2 --out /tmp/jsprite
```

Analyze a decompressed JSPRANI entry:

```bash
python3 tools/reverse/ps2/analyze_sprani.py /tmp/jsprani/044_FE1FC030_zlib.bin --resource-id 0x2B
```
