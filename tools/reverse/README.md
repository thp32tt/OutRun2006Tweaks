# OutRun 2006 EXE Knowledge Map

This directory contains the durable reverse-engineering interface for the canonical
`OR2006C2C.EXE`. The executable itself is never committed.

## Goal

Analyze the entire canonical executable once, preserve machine-readable evidence,
and query it later without repeating broad reverse engineering for every HUD,
camera, rendering, input, FFB, menu, or game-state question.

The map is keyed to the exact executable identity in
`docs/VR_BINARY_CONTRACT.json`. A map built from a different SHA-256 is rejected.

## What is exported

`ExportOutRunMap.java` runs after normal Ghidra auto-analysis and emits:

- `manifest.json` — program identity, image base, language/compiler identity.
- `functions.jsonl` — every discovered function, body range, signature, thunk/external state.
- `decompile.jsonl` — Ghidra decompiler C text per function unless `-NoDecompile` is used.
- `instructions.jsonl` — every decoded instruction with RVA, owning function and bytes.
- `calls.jsonl` — direct call-site edges recovered from instruction references.
- `xrefs.jsonl` — instruction-origin cross references.
- `strings.jsonl` — defined string data.
- `symbols.jsonl` — Ghidra symbol table.

`build_exe_map.py` loads the export into `outrun_exe_map.sqlite`, imports the
canonical binary-contract anchors, imports `seed_semantics.json`, and creates
an FTS5 text index when the local SQLite build supports it.

## Build on Windows

Prerequisites:

- Python 3.
- Ghidra installed locally.
- Internet access only if the canonical EXE is not already supplied.

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File tools\reverse\Build-OutRunExeMap.ps1 \
  -GhidraHome "C:\Tools\ghidra"
```

To use an already downloaded executable:

```powershell
powershell -ExecutionPolicy Bypass -File tools\reverse\Build-OutRunExeMap.ps1 \
  -GhidraHome "C:\Tools\ghidra" \
  -ExePath "D:\OutRun2006\OR2006C2C.EXE"
```

For a faster map that skips full decompilation but still exports the complete
instruction/call/xref/function map:

```powershell
powershell -ExecutionPolicy Bypass -File tools\reverse\Build-OutRunExeMap.ps1 \
  -GhidraHome "C:\Tools\ghidra" -NoDecompile
```

Default generated location:

```text
reverse/OR2006C2C/generated/<canonical-sha-prefix>/
```

## Query examples

```powershell
python tools\reverse\exequery.py --db reverse\OR2006C2C\generated\68ceb3868290\outrun_exe_map.sqlite 0x2D762
python tools\reverse\exequery.py --db reverse\OR2006C2C\generated\68ceb3868290\outrun_exe_map.sqlite HUD
python tools\reverse\exequery.py --db reverse\OR2006C2C\generated\68ceb3868290\outrun_exe_map.sqlite "rank marker"
python tools\reverse\exequery.py --db reverse\OR2006C2C\generated\68ceb3868290\outrun_exe_map.sqlite Calc3D2D
```

Address queries return the containing function/decompile, nearby instructions,
incoming/outgoing calls, xrefs, nearby strings, semantic annotations and current
source bindings. Text queries search functions, decompiled C, strings, symbols,
binary contracts and semantic annotations.

## Durable semantic layer

Do not edit generated Ghidra output to record project knowledge. Add confirmed
meaning to `seed_semantics.json` (or a future reviewed semantic file) with:

- stable ID;
- exact RVA;
- semantic kind/name/tags;
- confidence;
- note;
- evidence references.

Addresses inferred only from heuristics must not be marked high confidence.
Runtime-verified behavior and canonical-byte evidence should remain distinct.

## Project integration rule

Before adding or changing any executable-RVA hook:

1. Verify `docs/VR_BINARY_CONTRACT.json`.
2. Query this map for the target RVA and surrounding function.
3. Inspect incoming/outgoing calls and xrefs.
4. Record any newly confirmed semantic anchor.
5. Keep the current regression/baseline gates unchanged.

The map is evidence and navigation infrastructure. It does not override runtime
Quest 3 / VDXR evidence or the protected working baseline.

## Validation

`python tools/reverse/test_exe_map.py` builds and queries a synthetic map. The
`EXE Map Tools` pull-request workflow also runs Python syntax checks plus this
self-test. Full Ghidra execution remains an environment-level check because the
exporter requires a Ghidra installation and the canonical executable.
