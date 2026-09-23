# OR2006C2C Executable Knowledge Map

This subsystem turns the canonical `OR2006C2C.EXE` into a reusable reverse-engineering index instead of repeatedly rediscovering RVAs from scratch.

## Identity and safety

The input executable is accepted only when `tools/verify_vr_binary_contract.py` matches `docs/VR_BINARY_CONTRACT.json`. The current canonical identity is SHA-256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, PE32/x86, image base `0x00400000`. The EXE itself is never committed.

## Generated map

Ghidra headless analysis exports:

- `program.jsonl` — executable identity and analysis metadata
- `functions.jsonl` — function boundaries/names/signatures
- `instructions.jsonl` — complete analyzed instruction stream with RVA, bytes and containing function
- `calls.jsonl` — call sites and caller/callee relationships
- `xrefs.jsonl` — instruction references for reverse traversal
- `strings.jsonl` — analyzed string data
- `imports.jsonl` — external/imported functions

`build_exe_map.py` converts these records into `exe_map.sqlite`, indexes the major relationships, imports verified RVA contracts, and layers manually confirmed semantics from `reverse/semantics.json`.

Generated raw exports and SQLite databases are build artifacts and should not be committed. Only the scripts, semantic annotations and small summaries belong in Git.

## N100 / Linux usage

Prerequisites: a 64-bit JDK supported by the selected Ghidra release, Ghidra, Python 3, and the canonical EXE.

```bash
export GHIDRA_HOME=/opt/ghidra
bash tools/reverse/run_ghidra_map.sh /path/to/OR2006C2C.EXE
```

Query by RVA or VA:

```bash
python3 tools/reverse/exequery.py 0x2D734
python3 tools/reverse/exequery.py 0x42D734
```

Search semantic/function/string/instruction text:

```bash
python3 tools/reverse/exequery.py HUD
python3 tools/reverse/exequery.py RankMarker
python3 tools/reverse/exequery.py D3DXMatrixTransformation2D
```

## Development rule

For a new EXE-dependent hook or a recurring rendering/input/FFB issue:

1. Query this map first.
2. Traverse callers/callees/XREFs from the nearest verified semantic anchor.
3. Add newly confirmed meanings to `reverse/semantics.json` with evidence and confidence.
4. Promote any RVA used by production source to `docs/VR_BINARY_CONTRACT.json` with a byte signature and source binding.
5. Do not broaden a semantic tag based only on proximity or a visual heuristic.

This separates raw disassembly evidence from semantic conclusions and prevents historical guesses from silently becoming production contracts.
