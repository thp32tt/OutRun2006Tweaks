# PS2 reverse map tooling

The canonical analysis result is documented in `docs/reverse/PS2_FFB_MAP.md` and `reverse/ps2/semantics.json`.

The full generated map is intentionally not committed because it contains a large disassembly derived from the retail PS2 executable. A local generated package contains the SQLite database, JSONL indexes, full EE disassembly and IOPRP module disassemblies.

Use `ps2query.py` against a generated `ps2_knowledge_map.sqlite`:

```bash
python3 tools/reverse/ps2/ps2query.py --db /path/to/ps2_knowledge_map.sqlite 0x1354B0
python3 tools/reverse/ps2/ps2query.py --db /path/to/ps2_knowledge_map.sqlite ForceEffect
```

Input identity for the current map:

- `SLPM_666.28`: `bc5dd6d836bf34546ef9f047ad2bcb99c5ef5a713767a161d0c342af33f38c34`
- `IOPRP310.IMG`: `1cf5475f533f04d161bbb4b08179df156afeb7b400f207c88dcf1e39466679b6`

The next required FFB binary is `LGDEV.IRX`, which is referenced by the EE executable but absent from `IOPRP310.IMG`.
