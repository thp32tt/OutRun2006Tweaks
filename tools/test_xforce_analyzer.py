#!/usr/bin/env python3
"""Host-only invariants for tools/analyze_xforce_capture.py."""
import math
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = spec_from_file_location("xforce_analyzer", ROOT / "tools/analyze_xforce_capture.py")
assert SPEC and SPEC.loader
MOD = module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)

def require(value, message):
    if not value:
        raise SystemExit(message)

physics = [MOD.Row(100, {"modern": 0.1}), MOD.Row(108, {"modern": 0.2})]
neighbors = [MOD.Row(104, {"dbc": 1.0})]
pairs = MOD.pair_rows(physics, neighbors)
require(len(pairs) == 1, "pair_rows reused one neighbor sample")

physics = [MOD.Row(100 + i * 16, {"modern": float(i)}) for i in range(6)]
neighbors = [MOD.Row(101 + i * 16, {"dbc": float(i)}) for i in range(6)]
pairs = MOD.pair_rows(physics, neighbors)
require(len(pairs) == 6, "pair_rows lost ordinary near-synchronous samples")
require(all(pairs[i][1].tick < pairs[i + 1][1].tick for i in range(5)), "pair_rows lost chronology")
require(max(delta for _, _, delta in pairs) == 1, "pair_rows nearest timestamp failed")

target = [math.sin(i * 0.37) + 0.2 * math.cos(i * 0.11) for i in range(60)]
pairs = []
for i in range(60):
    physics_row = MOD.Row(1000 + i * 16, {"modern": target[i]})
    candidate = target[i - 1] if i else 0.0
    neighbor_row = MOD.Row(1001 + i * 16, {"dbc": candidate})
    pairs.append((physics_row, neighbor_row, 1))
r, lag = MOD.best_lag_correlation(pairs, "dbc", "modern")
require(r is not None and r > 0.99999 and lag == 1, "lag scan failed one-record phase recovery")
print("X-Force analyzer host invariants passed")
