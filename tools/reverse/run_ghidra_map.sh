#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXE="${1:-}"
OUT="${2:-$ROOT/reverse/OR2006C2C}"
GHIDRA_HOME="${GHIDRA_HOME:-}"

if [[ -z "$EXE" || ! -f "$EXE" ]]; then
  echo "usage: GHIDRA_HOME=/path/to/ghidra $0 /path/to/OR2006C2C.EXE [output-dir]" >&2
  exit 2
fi
if [[ -z "$GHIDRA_HOME" || ! -x "$GHIDRA_HOME/support/analyzeHeadless" ]]; then
  echo "GHIDRA_HOME must point to a Ghidra install containing support/analyzeHeadless" >&2
  exit 2
fi

mkdir -p "$OUT/raw"
python3 "$ROOT/tools/verify_vr_binary_contract.py" \
  --exe "$EXE" \
  --manifest "$ROOT/docs/VR_BINARY_CONTRACT.json" \
  --source-root "$ROOT"

rm -rf "$OUT/raw" "$OUT/ghidra-project"
mkdir -p "$OUT/raw" "$OUT/ghidra-project"

"$GHIDRA_HOME/support/analyzeHeadless" \
  "$OUT/ghidra-project" OutRunExeMap \
  -import "$EXE" \
  -overwrite \
  -analysisTimeoutPerFile 1800 \
  -scriptPath "$ROOT/tools/reverse/ghidra" \
  -postScript ExportOutRunMap.java "$OUT/raw"

python3 "$ROOT/tools/reverse/build_exe_map.py" \
  --export-dir "$OUT/raw" \
  --db "$OUT/exe_map.sqlite" \
  --summary "$OUT/summary.json" \
  --semantics "$ROOT/reverse/semantics.json" \
  --binary-contract "$ROOT/docs/VR_BINARY_CONTRACT.json"

python3 "$ROOT/tools/reverse/exequery.py" --db "$OUT/exe_map.sqlite" 0x2D734 --context 6
