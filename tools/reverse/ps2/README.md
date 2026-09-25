# PS2 reverse map tooling

The canonical analysis result is documented in `docs/reverse/PS2_FFB_MAP.md` and `reverse/ps2/semantics.json`.

The full generated map is intentionally not committed because it contains a large disassembly derived from the retail PS2 executable. A local generated package contains the SQLite database, JSONL indexes, full EE disassembly and IOPRP module disassemblies.

Regenerate the compact core map from the original binaries:

```bash
python3 tools/reverse/ps2/build_ps2_map.py /path/to/SLPM_666.28 /path/to/IOPRP310.IMG /tmp/outrun2-ps2-map
```

Use `ps2query.py` against a generated `ps2_knowledge_map.sqlite`:

```bash
python3 tools/reverse/ps2/ps2query.py --db /path/to/ps2_knowledge_map.sqlite 0x1354B0
python3 tools/reverse/ps2/ps2query.py --db /path/to/ps2_knowledge_map.sqlite ForceEffect
python3 tools/reverse/ps2/ps2query.py --db /path/to/ps2_knowledge_map.sqlite SpringCondition
```

The compact builder imports the curated records in `reverse/ps2/semantics.json` into an optional `semantics` table. Rich one-off maps may additionally contain `string_xrefs`; the query tool detects that table when present and remains usable when it is absent. `tools/reverse/ps2/test_ps2query.py` guards both compact and enriched query paths.

Input identity for the current map:

- `SLPM_666.28`: `bc5dd6d836bf34546ef9f047ad2bcb99c5ef5a713767a161d0c342af33f38c34`
- `IOPRP310.IMG`: `1cf5475f533f04d161bbb4b08179df156afeb7b400f207c88dcf1e39466679b6`

The next required FFB binary is `LGDEV.IRX`, which is referenced by the EE executable but absent from `IOPRP310.IMG`.
